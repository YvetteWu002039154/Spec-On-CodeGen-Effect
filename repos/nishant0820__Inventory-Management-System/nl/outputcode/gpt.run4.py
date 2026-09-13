import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple, Any

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None


DB_FILE = "inventory.db"


class ValidationError(ValueError):
    pass


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _require_non_empty(value: str, field: str) -> str:
    v = (value or "").strip()
    if not v:
        raise ValidationError(f"{field} is required")
    return v


def _require_int(value: str, field: str, min_value: Optional[int] = None) -> int:
    try:
        i = int(str(value).strip())
    except Exception:
        raise ValidationError(f"{field} must be an integer")
    if min_value is not None and i < min_value:
        raise ValidationError(f"{field} must be >= {min_value}")
    return i


def _require_float(value: str, field: str, min_value: Optional[float] = None) -> float:
    try:
        f = float(str(value).strip())
    except Exception:
        raise ValidationError(f"{field} must be a number")
    if min_value is not None and f < min_value:
        raise ValidationError(f"{field} must be >= {min_value}")
    return f


@dataclass(frozen=True)
class Employee:
    emp_id: str
    name: str
    email: str
    gender: str
    contact: str
    dob: str
    doj: str
    password: str
    usertype: str
    address: str


@dataclass(frozen=True)
class Supplier:
    invoice: str
    name: str
    contact: str
    desc: str


@dataclass(frozen=True)
class Category:
    cat_id: str
    name: str


@dataclass(frozen=True)
class Product:
    pid: str
    category: str
    supplier: str
    name: str
    price: float
    qty: int
    status: str


@dataclass(frozen=True)
class BillItem:
    pid: str
    name: str
    price: float
    qty: int

    @property
    def total(self) -> float:
        return round(self.price * self.qty, 2)


class Database:
    def __init__(self, db_path: str = DB_FILE) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS employees(
                emp_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                gender TEXT NOT NULL,
                contact TEXT NOT NULL,
                dob TEXT NOT NULL,
                doj TEXT NOT NULL,
                password TEXT NOT NULL,
                usertype TEXT NOT NULL,
                address TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS suppliers(
                invoice TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                desc TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS categories(
                cat_id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS products(
                pid TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                supplier TEXT NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                qty INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(category) REFERENCES categories(name) ON UPDATE CASCADE ON DELETE RESTRICT,
                FOREIGN KEY(supplier) REFERENCES suppliers(invoice) ON UPDATE CASCADE ON DELETE RESTRICT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bills(
                invoice_no TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_contact TEXT NOT NULL,
                created_at TEXT NOT NULL,
                total REAL NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bill_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT NOT NULL,
                pid TEXT NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                qty INTEGER NOT NULL,
                total REAL NOT NULL,
                FOREIGN KEY(invoice_no) REFERENCES bills(invoice_no) ON DELETE CASCADE,
                FOREIGN KEY(pid) REFERENCES products(pid) ON UPDATE CASCADE ON DELETE RESTRICT
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


class EmployeeRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, e: Employee) -> None:
        self._db.execute(
            """
            INSERT INTO employees(emp_id,name,email,gender,contact,dob,doj,password,usertype,address,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (e.emp_id, e.name, e.email, e.gender, e.contact, e.dob, e.doj, e.password, e.usertype, e.address, _now_str()),
        )

    def update(self, e: Employee) -> None:
        cur = self._db.execute(
            """
            UPDATE employees
            SET name=?, email=?, gender=?, contact=?, dob=?, doj=?, password=?, usertype=?, address=?
            WHERE emp_id=?
            """,
            (e.name, e.email, e.gender, e.contact, e.dob, e.doj, e.password, e.usertype, e.address, e.emp_id),
        )
        if cur.rowcount == 0:
            raise ValidationError("Employee not found")

    def delete(self, emp_id: str) -> None:
        cur = self._db.execute("DELETE FROM employees WHERE emp_id=?", (emp_id,))
        if cur.rowcount == 0:
            raise ValidationError("Employee not found")

    def get(self, emp_id: str) -> Optional[Employee]:
        rows = self._db.query("SELECT * FROM employees WHERE emp_id=?", (emp_id,))
        if not rows:
            return None
        r = rows[0]
        return Employee(
            emp_id=r["emp_id"],
            name=r["name"],
            email=r["email"],
            gender=r["gender"],
            contact=r["contact"],
            dob=r["dob"],
            doj=r["doj"],
            password=r["password"],
            usertype=r["usertype"],
            address=r["address"],
        )

    def search(self, keyword: str) -> List[Employee]:
        k = f"%{keyword.strip()}%"
        rows = self._db.query(
            """
            SELECT * FROM employees
            WHERE emp_id LIKE ? OR name LIKE ? OR email LIKE ? OR contact LIKE ? OR usertype LIKE ?
            ORDER BY created_at DESC
            """,
            (k, k, k, k, k),
        )
        return [
            Employee(
                emp_id=r["emp_id"],
                name=r["name"],
                email=r["email"],
                gender=r["gender"],
                contact=r["contact"],
                dob=r["dob"],
                doj=r["doj"],
                password=r["password"],
                usertype=r["usertype"],
                address=r["address"],
            )
            for r in rows
        ]

    def all(self) -> List[Employee]:
        rows = self._db.query("SELECT * FROM employees ORDER BY created_at DESC")
        return [
            Employee(
                emp_id=r["emp_id"],
                name=r["name"],
                email=r["email"],
                gender=r["gender"],
                contact=r["contact"],
                dob=r["dob"],
                doj=r["doj"],
                password=r["password"],
                usertype=r["usertype"],
                address=r["address"],
            )
            for r in rows
        ]


class SupplierRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, s: Supplier) -> None:
        self._db.execute(
            """
            INSERT INTO suppliers(invoice,name,contact,desc,created_at)
            VALUES(?,?,?,?,?)
            """,
            (s.invoice, s.name, s.contact, s.desc, _now_str()),
        )

    def update(self, s: Supplier) -> None:
        cur = self._db.execute(
            """
            UPDATE suppliers
            SET name=?, contact=?, desc=?
            WHERE invoice=?
            """,
            (s.name, s.contact, s.desc, s.invoice),
        )
        if cur.rowcount == 0:
            raise ValidationError("Supplier not found")

    def delete(self, invoice: str) -> None:
        cur = self._db.execute("DELETE FROM suppliers WHERE invoice=?", (invoice,))
        if cur.rowcount == 0:
            raise ValidationError("Supplier not found")

    def get(self, invoice: str) -> Optional[Supplier]:
        rows = self._db.query("SELECT * FROM suppliers WHERE invoice=?", (invoice,))
        if not rows:
            return None
        r = rows[0]
        return Supplier(invoice=r["invoice"], name=r["name"], contact=r["contact"], desc=r["desc"])

    def search(self, keyword: str) -> List[Supplier]:
        k = f"%{keyword.strip()}%"
        rows = self._db.query(
            """
            SELECT * FROM suppliers
            WHERE invoice LIKE ? OR name LIKE ? OR contact LIKE ? OR desc LIKE ?
            ORDER BY created_at DESC
            """,
            (k, k, k, k),
        )
        return [Supplier(invoice=r["invoice"], name=r["name"], contact=r["contact"], desc=r["desc"]) for r in rows]

    def all(self) -> List[Supplier]:
        rows = self._db.query("SELECT * FROM suppliers ORDER BY created_at DESC")
        return [Supplier(invoice=r["invoice"], name=r["name"], contact=r["contact"], desc=r["desc"]) for r in rows]


class CategoryRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, c: Category) -> None:
        self._db.execute(
            """
            INSERT INTO categories(cat_id,name,created_at)
            VALUES(?,?,?)
            """,
            (c.cat_id, c.name, _now_str()),
        )

    def update(self, c: Category) -> None:
        cur = self._db.execute("UPDATE categories SET name=? WHERE cat_id=?", (c.name, c.cat_id))
        if cur.rowcount == 0:
            raise ValidationError("Category not found")

    def delete(self, cat_id: str) -> None:
        cur = self._db.execute("DELETE FROM categories WHERE cat_id=?", (cat_id,))
        if cur.rowcount == 0:
            raise ValidationError("Category not found")

    def get(self, cat_id: str) -> Optional[Category]:
        rows = self._db.query("SELECT * FROM categories WHERE cat_id=?", (cat_id,))
        if not rows:
            return None
        r = rows[0]
        return Category(cat_id=r["cat_id"], name=r["name"])

    def all(self) -> List[Category]:
        rows = self._db.query("SELECT * FROM categories ORDER BY created_at DESC")
        return [Category(cat_id=r["cat_id"], name=r["name"]) for r in rows]

    def search(self, keyword: str) -> List[Category]:
        k = f"%{keyword.strip()}%"
        rows = self._db.query(
            "SELECT * FROM categories WHERE cat_id LIKE ? OR name LIKE ? ORDER BY created_at DESC",
            (k, k),
        )
        return [Category(cat_id=r["cat_id"], name=r["name"]) for r in rows]

    def names(self) -> List[str]:
        rows = self._db.query("SELECT name FROM categories ORDER BY name ASC")
        return [r["name"] for r in rows]


class ProductRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, p: Product) -> None:
        self._db.execute(
            """
            INSERT INTO products(pid,category,supplier,name,price,qty,status,created_at)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (p.pid, p.category, p.supplier, p.name, p.price, p.qty, p.status, _now_str()),
        )

    def update(self, p: Product) -> None:
        cur = self._db.execute(
            """
            UPDATE products
            SET category=?, supplier=?, name=?, price=?, qty=?, status=?
            WHERE pid=?
            """,
            (p.category, p.supplier, p.name, p.price, p.qty, p.status, p.pid),
        )
        if cur.rowcount == 0:
            raise ValidationError("Product not found")

    def delete(self, pid: str) -> None:
        cur = self._db.execute("DELETE FROM products WHERE pid=?", (pid,))
        if cur.rowcount == 0:
            raise ValidationError("Product not found")

    def get(self, pid: str) -> Optional[Product]:
        rows = self._db.query("SELECT * FROM products WHERE pid=?", (pid,))
        if not rows:
            return None
        r = rows[0]
        return Product(
            pid=r["pid"],
            category=r["category"],
            supplier=r["supplier"],
            name=r["name"],
            price=float(r["price"]),
            qty=int(r["qty"]),
            status=r["status"],
        )

    def all(self) -> List[Product]:
        rows = self._db.query("SELECT * FROM products ORDER BY created_at DESC")
        return [
            Product(
                pid=r["pid"],
                category=r["category"],
                supplier=r["supplier"],
                name=r["name"],
                price=float(r["price"]),
                qty=int(r["qty"]),
                status=r["status"],
            )
            for r in rows
        ]

    def search(self, keyword: str) -> List[Product]:
        k = f"%{keyword.strip()}%"
        rows = self._db.query(
            """
            SELECT * FROM products
            WHERE pid LIKE ? OR name LIKE ? OR category LIKE ? OR supplier LIKE ? OR status LIKE ?
            ORDER BY created_at DESC
            """,
            (k, k, k, k, k),
        )
        return [
            Product(
                pid=r["pid"],
                category=r["category"],
                supplier=r["supplier"],
                name=r["name"],
                price=float(r["price"]),
                qty=int(r["qty"]),
                status=r["status"],
            )
            for r in rows
        ]

    def adjust_stock(self, pid: str, delta_qty: int) -> None:
        p = self.get(pid)
        if p is None:
            raise ValidationError("Product not found")
        new_qty = p.qty + delta_qty
        if new_qty < 0:
            raise ValidationError("Insufficient stock")
        self._db.execute("UPDATE products SET qty=? WHERE pid=?", (new_qty, pid))


class BillingRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create_bill(self, invoice_no: str, customer_name: str, customer_contact: str, items: List[BillItem]) -> None:
        invoice_no = _require_non_empty(invoice_no, "Invoice No")
        customer_name = _require_non_empty(customer_name, "Customer Name")
        customer_contact = _require_non_empty(customer_contact, "Customer Contact")
        if not items:
            raise ValidationError("At least one item is required")

        total = round(sum(i.total for i in items), 2)
        self._db.execute(
            "INSERT INTO bills(invoice_no,customer_name,customer_contact,created_at,total) VALUES(?,?,?,?,?)",
            (invoice_no, customer_name, customer_contact, _now_str(), total),
        )
        for it in items:
            self._db.execute(
                """
                INSERT INTO bill_items(invoice_no,pid,name,price,qty,total)
                VALUES(?,?,?,?,?,?)
                """,
                (invoice_no, it.pid, it.name, it.price, it.qty, it.total),
            )

    def get_bill(self, invoice_no: str) -> Optional[Tuple[sqlite3.Row, List[sqlite3.Row]]]:
        rows = self._db.query("SELECT * FROM bills WHERE invoice_no=?", (invoice_no,))
        if not rows:
            return None
        bill = rows[0]
        items = self._db.query("SELECT * FROM bill_items WHERE invoice_no=? ORDER BY id ASC", (invoice_no,))
        return bill, items

    def search_bills(self, keyword: str) -> List[sqlite3.Row]:
        k = f"%{keyword.strip()}%"
        return self._db.query(
            """
            SELECT * FROM bills
            WHERE invoice_no LIKE ? OR customer_name LIKE ? OR customer_contact LIKE ?
            ORDER BY created_at DESC
            """,
            (k, k, k),
        )

    def all_bills(self) -> List[sqlite3.Row]:
        return self._db.query("SELECT * FROM bills ORDER BY created_at DESC")


class BaseWindow(tk.Toplevel):
    def __init__(self, master: tk.Tk, title: str) -> None:
        super().__init__(master)
        self.title(title)
        self.transient(master)
        self.grab_set()
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        self.grab_release()
        self.destroy()


class EmployeeWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: EmployeeRepository) -> None:
        super().__init__(master, "Employees")
        self._repo = repo
        self._selected_id: Optional[str] = None

        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        form = ttk.LabelFrame(self, text="Employee Details")
        form.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        for i in range(6):
            form.columnconfigure(i, weight=1)

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
        self.var_search = tk.StringVar()

        fields = [
            ("Emp ID", self.var_emp_id),
            ("Name", self.var_name),
            ("Email", self.var_email),
            ("Gender", self.var_gender),
            ("Contact", self.var_contact),
            ("DOB (YYYY-MM-DD)", self.var_dob),
            ("DOJ (YYYY-MM-DD)", self.var_doj),
            ("Password", self.var_password),
            ("User Type", self.var_usertype),
            ("Address", self.var_address),
        ]

        for idx, (lbl, var) in enumerate(fields):
            r = idx // 2
            c = (idx % 2) * 3
            ttk.Label(form, text=lbl).grid(row=r, column=c, sticky="w", padx=6, pady=4)
            ent = ttk.Entry(form, textvariable=var)
            if lbl == "Password":
                ent.configure(show="*")
            ent.grid(row=r, column=c + 1, columnspan=2, sticky="ew", padx=6, pady=4)

        btns = ttk.Frame(form)
        btns.grid(row=5, column=0, columnspan=6, sticky="ew", padx=6, pady=6)
        for i in range(6):
            btns.columnconfigure(i, weight=1)

        ttk.Button(btns, text="Add", command=self._add).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(btns, text="Update", command=self._update).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(btns, text="Delete", command=self._delete).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(btns, text="Clear", command=self._clear).grid(row=0, column=3, sticky="ew", padx=4)
        ttk.Entry(btns, textvariable=self.var_search).grid(row=0, column=4, sticky="ew", padx=4)
        ttk.Button(btns, text="Search", command=self._search).grid(row=0, column=5, sticky="ew", padx=4)

        table_frame = ttk.LabelFrame(self, text="Employees")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("emp_id", "name", "email", "gender", "contact", "dob", "doj", "usertype", "address")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=120, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        sb_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        sb_y.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb_y.set)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _validate_employee(self) -> Employee:
        emp_id = _require_non_empty(self.var_emp_id.get(), "Emp ID")
        name = _require_non_empty(self.var_name.get(), "Name")
        email = _require_non_empty(self.var_email.get(), "Email")
        gender = _require_non_empty(self.var_gender.get(), "Gender")
        contact = _require_non_empty(self.var_contact.get(), "Contact")
        dob = _require_non_empty(self.var_dob.get(), "DOB")
        doj = _require_non_empty(self.var_doj.get(), "DOJ")
        password = _require_non_empty(self.var_password.get(), "Password")
        usertype = _require_non_empty(self.var_usertype.get(), "User Type")
        address = _require_non_empty(self.var_address.get(), "Address")
        return Employee(emp_id, name, email, gender, contact, dob, doj, password, usertype, address)

    def _refresh(self, rows: Optional[List[Employee]] = None) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        data = rows if rows is not None else self._repo.all()
        for e in data:
            self.tree.insert("", "end", values=(e.emp_id, e.name, e.email, e.gender, e.contact, e.dob, e.doj, e.usertype, e.address))

    def _clear(self) -> None:
        self._selected_id = None
        for v in (self.var_emp_id, self.var_name, self.var_email, self.var_gender, self.var_contact, self.var_dob, self.var_doj, self.var_password, self.var_usertype, self.var_address):
            v.set("")

    def _add(self) -> None:
        try:
            e = self._validate_employee()
            self._repo.add(e)
            self._refresh()
            self._clear()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Cannot add employee: {ex}")
        except ValidationError as ex:
            messagebox.showerror("Validation", str(ex))

    def _update(self) -> None:
        try:
            e = self._validate_employee()
            self._repo.update(e)
            self._refresh()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Cannot update employee: {ex}")
        except ValidationError as ex:
            messagebox.showerror("Validation", str(ex))

    def _delete(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        if not emp_id:
            messagebox.showerror("Validation", "Emp ID is required")
            return
        if not messagebox.askyesno("Confirm", "Delete selected employee?"):
            return
        try:
            self._repo.delete(emp_id)
            self._refresh()
            self._clear()
        except ValidationError as ex:
            messagebox.showerror("Error", str(ex))

    def _search(self) -> None:
        kw = self.var_search.get().strip()
        self._refresh(self._repo.search(kw) if kw else self._repo.all())

    def _on_select(self, _evt: object) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self._selected_id = str(vals[0])
        self.var_emp_id.set(vals[0])
        self.var_name.set(vals[1])
        self.var_email.set(vals[2])
        self.var_gender.set(vals[3])
        self.var_contact.set(vals[4])
        self.var_dob.set(vals[5])
        self.var_doj.set(vals[6])
        self.var_usertype.set(vals[7])
        self.var_address.set(vals[8])
        emp = self._repo.get(self._selected_id)
        if emp:
            self.var_password.set(emp.password)


class SupplierWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: SupplierRepository) -> None:
        super().__init__(master, "Suppliers")
        self._repo = repo
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        form = ttk.LabelFrame(self, text="Supplier Details")
        form.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        for i in range(6):
            form.columnconfigure(i, weight=1)

        self.var_invoice = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_desc = tk.StringVar()
        self.var_search = tk.StringVar()

        ttk.Label(form, text="Invoice").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.var_invoice).grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        ttk.Label(form, text="Name").grid(row=0, column=2, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.var_name).grid(row=0, column=3, sticky="ew", padx=6, pady=4)
        ttk.Label(form, text="Contact").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.var_contact).grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        ttk.Label(form, text="Description").grid(row=1, column=2, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.var_desc).grid(row=1, column=3, sticky="ew", padx=6, pady=4)

        btns = ttk.Frame(form)
        btns.grid(row=2, column=0, columnspan=6, sticky="ew", padx=6, pady=6)
        for i in range(6):
            btns.columnconfigure(i, weight=1)

        ttk.Button(btns, text="Add", command=self._add).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(btns, text="Update", command=self._update).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(btns, text="Delete", command=self._delete).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(btns, text="Clear", command=self._clear).grid(row=0, column=3, sticky="ew", padx=4)
        ttk.Entry(btns, textvariable=self.var_search).grid(row=0, column=4, sticky="ew", padx=4)
        ttk.Button(btns, text="Search", command=self._search).grid(row=0, column=5, sticky="ew", padx=4)

        table_frame = ttk.LabelFrame(self, text="Suppliers")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("invoice", "name", "contact", "desc")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=160, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        sb_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        sb_y.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb_y.set)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _validate_supplier(self) -> Supplier:
        invoice = _require_non_empty(self.var_invoice.get(), "Invoice")
        name = _require_non_empty(self.var_name.get(), "Name")
        contact = _require_non_empty(self.var_contact.get(), "Contact")
        desc = _require_non_empty(self.var_desc.get(), "Description")
        return Supplier(invoice=invoice, name=name, contact=contact, desc=desc)

    def _refresh(self, rows: Optional[List[Supplier]] = None) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        data = rows if rows is not None else self._repo.all()
        for s in data:
            self.tree.insert("", "end", values=(s.invoice, s.name, s.contact, s.desc))

    def _clear(self) -> None:
        for v in (self.var_invoice, self.var_name, self.var_contact, self.var_desc):
            v.set("")

    def _add(self) -> None:
        try:
            s = self._validate_supplier()
            self._repo.add(s)
            self._refresh()
            self._clear()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Cannot add supplier: {ex}")
        except ValidationError as ex:
            messagebox.showerror("Validation", str(ex))

    def _update(self) -> None:
        try:
            s = self._validate_supplier()
            self._repo.update(s)
            self._refresh()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Cannot update supplier: {ex}")
        except ValidationError as ex:
            messagebox.showerror("Validation", str(ex))

    def _delete(self) -> None:
        invoice = self.var_invoice.get().strip()
        if not invoice:
            messagebox.showerror("Validation", "Invoice is required")
            return
        if not messagebox.askyesno("Confirm", "Delete selected supplier?"):
            return
        try:
            self._repo.delete(invoice)
            self._refresh()
            self._clear()
        except ValidationError as ex:
            messagebox.showerror("Error", str(ex))
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Cannot delete supplier: {ex}")

    def _search(self) -> None:
        kw = self.var_search.get().strip()
        self._refresh(self._repo.search(kw) if kw else self._repo.all())

    def _on_select(self, _evt: object) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.var_invoice.set(vals[0])
        self.var_name.set(vals[1])
        self.var_contact.set(vals[2])
        self.var_desc.set(vals[3])


class CategoryWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: CategoryRepository) -> None:
        super().__init__(master, "Categories")
        self._repo = repo
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        form = ttk.LabelFrame(self, text="Category Details")
        form.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        for i in range(6):
            form.columnconfigure(i, weight=1)

        self.var_cat_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_search = tk.StringVar()

        ttk.Label(form, text="Category ID").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.var_cat_id).grid(row=0, column=1, sticky="ew", padx=6, pady=4)
        ttk.Label(form, text="Name").grid(row=0, column=2, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.var_name).grid(row=0, column=3, sticky="ew", padx=6, pady=4)

        btns = ttk.Frame(form)
        btns.grid(row=1, column=0, columnspan=6, sticky="ew", padx=6, pady=6)
        for i in range(6):
            btns.columnconfigure(i, weight=1)

        ttk.Button(btns, text="Add", command=self._add).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(btns, text="Update", command=self._update).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(btns, text="Delete", command=self._delete).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(btns, text="Clear", command=self._clear).grid(row=0, column=3, sticky="ew", padx=4)
        ttk.Entry(btns, textvariable=self.var_search).grid(row=0, column=4, sticky="ew", padx=4)
        ttk.Button(btns, text="Search", command=self._search).grid(row=0, column=5, sticky="ew", padx=4)

        table_frame = ttk.LabelFrame(self, text="Categories")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("cat_id", "name")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=220, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        sb_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        sb_y.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb_y.set)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _validate_category(self) -> Category:
        cat_id = _require_non_empty(self.var_cat_id.get(), "Category ID")
        name = _require_non_empty(self.var_name.get(), "Name")
        return Category(cat_id=cat_id, name=name)

    def _refresh(self, rows: Optional[List[Category]] = None) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        data = rows if rows is not None else self._repo.all()
        for c in data:
            self.tree.insert("", "end", values=(c.cat_id, c.name))

    def _clear(self) -> None:
        self.var_cat_id.set("")
        self.var_name.set("")

    def _add(self) -> None:
        try:
            c = self._validate_category()
            self._repo.add(c)
            self._refresh()
            self._clear()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Cannot add category: {ex}")
        except ValidationError as ex:
            messagebox.showerror("Validation", str(ex))

    def _update(self) -> None:
        try:
            c = self._validate_category()
            self._repo.update(c)
            self._refresh()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Cannot update category: {ex}")
        except ValidationError as ex:
            messagebox.showerror("Validation", str(ex))

    def _delete(self) -> None:
        cat_id = self.var_cat_id.get().strip()
        if not cat_id:
            messagebox.showerror("Validation", "Category ID is required")
            return
        if not messagebox.askyesno("Confirm", "Delete selected category?"):
            return
        try:
            self._repo.delete(cat_id)
            self._refresh()
            self._clear()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Cannot delete category: {ex}")
        except ValidationError as ex:
            messagebox.showerror("Error", str(ex))

    def _search(self) -> None:
        kw = self.var_search.get().strip()
        self._refresh(self._repo.search(kw) if kw else self._repo.all())

    def _on_select(self, _evt: object) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self.var_cat_id.set(vals[0])
        self.var_name.set(vals[1])


class ProductWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: ProductRepository, cat_repo: CategoryRepository, sup_repo: SupplierRepository) -> None:
        super().__init__(master, "Products")
        self._repo = repo
        self._cat_repo = cat_repo
        self._sup_repo = sup_repo
        self._build_ui()
        self._refresh()
        self._refresh_dropdowns()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        form = ttk.LabelFrame(self, text="Product Details")
        form.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        for i in range(6):
            form.columnconfigure(i, weight=1)

        self.var_pid = tk.StringVar()
        self.var_category = tk.StringVar()
        self.var_supplier = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_status = tk.StringVar(value="Active")
        self.var_search = tk.StringVar()

        ttk.Label(form, text="Product ID").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.var_pid).grid(row=0, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(form, text="Category").grid(row=0, column=2, sticky="w", padx=6, pady=4)
        self.cmb_category = ttk.Combobox(form, textvariable=self.var_category, state="readonly", values=[])
        self.cmb_category.grid(row=0, column=3, sticky="ew", padx=6, pady=4)

        ttk.Label(form, text="Supplier (Invoice)").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        self.cmb_supplier = ttk.Combobox(form, textvariable=self.var_supplier, state="readonly", values=[])
        self.cmb_supplier.grid(row=1, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(form, text="Name").grid(row=1, column=2, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.var_name).grid(row=1, column=3, sticky="ew", padx=6, pady=4)

        ttk.Label(form, text="Price").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.var_price).grid(row=2, column=1, sticky="ew", padx=6, pady=4)

        ttk.Label(form, text="Quantity").grid(row=2, column=2, sticky="w", padx=6, pady=4)
        ttk.Entry(form, textvariable=self.var_qty).grid(row=2, column=3, sticky="ew", padx=6, pady=4)

        ttk.Label(form, text="Status").grid(row=3, column=0, sticky="w", padx=6, pady=4)
        self.cmb_status = ttk.Combobox(form, textvariable=self.var_status, state="readonly", values=["Active", "Inactive"])
        self.cmb_status.grid(row=3, column=1, sticky="ew", padx=6, pady=4)

        ttk.Button(form, text="Refresh Lists", command=self._refresh_dropdowns).grid(row=3, column=3, sticky="e", padx=6, pady=4)

        btns = ttk.Frame(form)
        btns.grid(row=4, column=0, columnspan=6, sticky="ew", padx=6, pady=6)
        for i in range(6):
            btns.columnconfigure(i, weight=1)

        ttk.Button(btns, text="Add", command=self._add).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(btns, text="Update", command=self._update).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(btns, text="Delete", command=self._delete).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(btns, text="Clear", command=self._clear).grid(row=0, column=3, sticky="ew", padx=4)
        ttk.Entry(btns, textvariable=self.var_search).grid(row=0, column=4, sticky="ew", padx=4)
        ttk.Button(btns, text="Search", command=self._search).grid(row=0, column=5, sticky="ew", padx=4)

        table_frame = ttk.LabelFrame(self, text="Products")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("pid", "category", "supplier", "name", "price", "qty", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=130, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        sb_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        sb_y.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb_y.set)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _refresh_dropdowns(self) -> None:
        cats = self._cat_repo.names()
        sups = [s.invoice for s in self._sup_repo.all()]
        self.cmb_category.configure(values=cats)
        self.cmb_supplier.configure(values=sups)
        if cats and self.var_category.get() not in cats:
            self.var_category.set(cats[0])
        if sups and self.var_supplier.get() not in sups:
            self.var_supplier.set(sups[0])

    def _validate_product(self) -> Product:
        pid = _require_non_empty(self.var_pid.get(), "Product ID")
        category = _require_non_empty(self.var_category.get(), "Category")
        supplier = _require_non_empty(self.var_supplier.get(), "Supplier")
        name = _require_non_empty(self.var_name.get(), "Name")
        price = _require_float(self.var_price.get(), "Price", min_value=0.0)
        qty = _require_int(self.var_qty.get(), "Quantity", min_value=0)
        status = _require_non_empty(self.var_status.get(), "Status")
        return Product(pid=pid, category=category, supplier=supplier, name=name, price=price, qty=qty, status=status)

    def _refresh(self, rows: Optional[List[Product]] = None) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        data = rows if rows is not None else self._repo.all()
        for p in data:
            self.tree.insert("", "end", values=(p.pid, p.category, p.supplier, p.name, f"{p.price:.2f}", p.qty, p.status))

    def _clear(self) -> None:
        for v in (self.var_pid, self.var_name, self.var_price, self.var_qty):
            v.set("")
        self.var_status.set("Active")

    def _add(self) -> None:
        try:
            p = self._validate_product()
            self._repo.add(p)
            self._refresh()
            self._clear()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Cannot add product: {ex}")
        except ValidationError as ex:
            messagebox.showerror("Validation", str(ex))

    def _update(self) -> None:
        try:
            p = self._validate_product()
            self._repo.update(p)
            self._refresh()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Cannot update product: {ex}")
        except ValidationError as ex:
            messagebox.showerror("Validation", str(ex))

    def _delete(self) -> None:
        pid = self.var_pid.get().strip()
        if not pid:
            messagebox.showerror("Validation", "Product ID is required")
            return
        if not messagebox.askyesno("Confirm", "Delete selected product?"):
            return
        try:
            self._repo.delete(pid)
            self._refresh()
            self._clear()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Cannot delete product: {ex}")
        except ValidationError as ex:
            messagebox.showerror("Error", str(ex))

    def _search(self) -> None:
        kw = self.var_search.get().strip()
        self._refresh(self._repo.search(kw) if kw else self._repo.all())

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


class BillingWindow(BaseWindow):
    def __init__(self, master: tk.Tk, prod_repo: ProductRepository, bill_repo: BillingRepository) -> None:
        super().__init__(master, "Billing")
        self._prod_repo = prod_repo
        self._bill_repo = bill_repo
        self._items: List[BillItem] = []
        self._build_ui()
        self._refresh_products()
        self._refresh_cart()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        for i in range(8):
            top.columnconfigure(i, weight=1)

        self.var_invoice = tk.StringVar()
        self.var_cust_name = tk.StringVar()
        self.var_cust_contact = tk.StringVar()
        self.var_pid = tk.StringVar()
        self.var_qty = tk.StringVar(value="1")
        self.var_bill_search = tk.StringVar()

        ttk.Label(top, text="Invoice No").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(top, textvariable=self.var_invoice).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(top, text="Customer Name").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(top, textvariable=self.var_cust_name).grid(row=0, column=3, sticky="ew", padx=4, pady=4)
        ttk.Label(top, text="Customer Contact").grid(row=0, column=4, sticky="w", padx=4, pady=4)
        ttk.Entry(top, textvariable=self.var_cust_contact).grid(row=0, column=5, sticky="ew", padx=4, pady=4)

        ttk.Label(top, text="Product").grid(row=1, column=0, sticky="w", padx=4, pady=4)
        self.cmb_pid = ttk.Combobox(top, textvariable=self.var_pid, state="readonly", values=[])
        self.cmb_pid.grid(row=1, column=1, sticky="ew", padx=4, pady=4)
        ttk.Label(top, text="Qty").grid(row=1, column=2, sticky="w", padx=4, pady=4)
        ttk.Entry(top, textvariable=self.var_qty).grid(row=1, column=3, sticky="ew", padx=4, pady=4)
        ttk.Button(top, text="Add to Cart", command=self._add_to_cart).grid(row=1, column=4, sticky="ew", padx=4, pady=4)
        ttk.Button(top, text="Remove Item", command=self._remove_selected).grid(row=1, column=5, sticky="ew", padx=4, pady=4)
        ttk.Button(top, text="Clear Cart", command=self._clear_cart).grid(row=1, column=6, sticky="ew", padx=4, pady=4)
        ttk.Button(top, text="Refresh Products", command=self._refresh_products).grid(row=1, column=7, sticky="ew", padx=4, pady=4)

        mid = ttk.PanedWindow(self, orient="horizontal")
        mid.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        cart_frame = ttk.LabelFrame(mid, text="Cart")
        cart_frame.columnconfigure(0, weight=1)
        cart_frame.rowconfigure(0, weight=1)

        cols = ("pid", "name", "price", "qty", "total")
        self.cart_tree = ttk.Treeview(cart_frame, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.cart_tree.heading(c, text=c.upper())
            self.cart_tree.column(c, width=120, anchor="w")
        self.cart_tree.grid(row=0, column=0, sticky="nsew")
        sb_cart = ttk.Scrollbar(cart_frame, orient="vertical", command=self.cart_tree.yview)
        sb_cart.grid(row=0, column=1, sticky="ns")
        self.cart_tree.configure(yscrollcommand=sb_cart.set)

        bill_frame = ttk.LabelFrame(mid, text="Bill Viewer (Search by Invoice No)")
        bill_frame.columnconfigure(0, weight=1)
        bill_frame.rowconfigure(1, weight=1)

        search_row = ttk.Frame(bill_frame)
        search_row.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        search_row.columnconfigure(0, weight=1)
        ttk.Entry(search_row, textvariable=self.var_bill_search).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(search_row, text="Search", command=self._search_bill).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(search_row, text="Open Bill File", command=self._open_bill_file).grid(row=0, column=2, sticky="ew", padx=4)

        self.txt_bill = tk.Text(bill_frame, height=20, wrap="none")
        self.txt_bill.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        mid.add(cart_frame, weight=1)
        mid.add(bill_frame, weight=1)

        bottom = ttk.Frame(self)
        bottom.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=1)
        bottom.columnconfigure(2, weight=1)

        self.lbl_total = ttk.Label(bottom, text="Total: 0.00")
        self.lbl_total.grid(row=0, column=0, sticky="w", padx=4)
        ttk.Button(bottom, text="Generate Bill", command=self._generate_bill).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(bottom, text="Close", command=self._on_close).grid(row=0, column=2, sticky="ew", padx=4)

    def _refresh_products(self) -> None:
        products = [p for p in self._prod_repo.all() if p.status.lower() == "active" and p.qty > 0]
        values = [p.pid for p in products]
        self.cmb_pid.configure(values=values)
        if values and self.var_pid.get() not in values:
            self.var_pid.set(values[0])

    def _refresh_cart(self) -> None:
        for i in self.cart_tree.get_children():
            self.cart_tree.delete(i)
        total = 0.0
        for it in self._items:
            self.cart_tree.insert("", "end", values=(it.pid, it.name, f"{it.price:.2f}", it.qty, f"{it.total:.2f}"))
            total += it.total
        self.lbl_total.configure(text=f"Total: {total:.2f}")

    def _add_to_cart(self) -> None:
        try:
            pid = _require_non_empty(self.var_pid.get(), "Product")
            qty = _require_int(self.var_qty.get(), "Qty", min_value=1)
            p = self._prod_repo.get(pid)
            if p is None:
                raise ValidationError("Product not found")
            if p.status.lower() != "active":
                raise ValidationError("Product is inactive")
            if qty > p.qty:
                raise ValidationError("Insufficient stock")

            for idx, it in enumerate(self._items):
                if it.pid == pid:
                    new_qty = it.qty + qty
                    if new_qty > p.qty:
                        raise ValidationError("Insufficient stock")
                    self._items[idx] = BillItem(pid=it.pid, name=it.name, price=it.price, qty=new_qty)
                    self._refresh_cart()
                    return

            self._items.append(BillItem(pid=p.pid, name=p.name, price=p.price, qty=qty))
            self._refresh_cart()
        except ValidationError as ex:
            messagebox.showerror("Validation", str(ex))

    def _remove_selected(self) -> None:
        sel = self.cart_tree.selection()
        if not sel:
            return
        vals = self.cart_tree.item(sel[0], "values")
        pid = str(vals[0])
        self._items = [it for it in self._items if it.pid != pid]
        self._refresh_cart()

    def _clear_cart(self) -> None:
        self._items = []
        self._refresh_cart()

    def _generate_bill_text(self, invoice_no: str, customer_name: str, customer_contact: str, items: List[BillItem]) -> str:
        lines: List[str] = []
        lines.append("INVENTORY MANAGEMENT SYSTEM - BILL")
        lines.append(f"Invoice No: {invoice_no}")
        lines.append(f"Date/Time : {_now_str()}")
        lines.append(f"Customer  : {customer_name}")
        lines.append(f"Contact   : {customer_contact}")
        lines.append("-" * 60)
        lines.append(f"{'PID':<10}{'NAME':<25}{'PRICE':>8}{'QTY':>6}{'TOTAL':>10}")
        lines.append("-" * 60)
        grand = 0.0
        for it in items:
            grand += it.total
            nm = it.name[:24]
            lines.append(f"{it.pid:<10}{nm:<25}{it.price:>8.2f}{it.qty:>6d}{it.total:>10.2f}")
        lines.append("-" * 60)
        lines.append(f"{'GRAND TOTAL':>49}{grand:>11.2f}")
        lines.append("-" * 60)
        return "\n".join(lines)

    def _generate_bill(self) -> None:
        try:
            invoice_no = _require_non_empty(self.var_invoice.get(), "Invoice No")
            customer_name = _require_non_empty(self.var_cust_name.get(), "Customer Name")
            customer_contact = _require_non_empty(self.var_cust_contact.get(), "Customer Contact")
            if not self._items:
                raise ValidationError("Cart is empty")

            for it in self._items:
                p = self._prod_repo.get(it.pid)
                if p is None:
                    raise ValidationError(f"Product not found: {it.pid}")
                if it.qty > p.qty:
                    raise ValidationError(f"Insufficient stock for {it.pid}")

            self._bill_repo.create_bill(invoice_no, customer_name, customer_contact, self._items)

            for it in self._items:
                self._prod_repo.adjust_stock(it.pid, -it.qty)

            bill_text = self._generate_bill_text(invoice_no, customer_name, customer_contact, self._items)
            self.txt_bill.delete("1.0", "end")
            self.txt_bill.insert("1.0", bill_text)

            os.makedirs("bills", exist_ok=True)
            path = os.path.join("bills", f"{invoice_no}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(bill_text)

            messagebox.showinfo("Success", f"Bill generated and saved: {path}")
            self._clear_cart()
            self._refresh_products()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Cannot generate bill: {ex}")
        except ValidationError as ex:
            messagebox.showerror("Validation", str(ex))

    def _search_bill(self) -> None:
        inv = self.var_bill_search.get().strip()
        if not inv:
            return
        data = self._bill_repo.get_bill(inv)
        if data is None:
            self.txt_bill.delete("1.0", "end")
            self.txt_bill.insert("1.0", "Bill not found in database.\n")
            path = os.path.join("bills", f"{inv}.txt")
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.txt_bill.insert("end", "\nFound bill file:\n\n")
                        self.txt_bill.insert("end", f.read())
                except Exception:
                    pass
            return
        bill, items = data
        lines: List[str] = []
        lines.append("INVENTORY MANAGEMENT SYSTEM - BILL (FROM DATABASE)")
        lines.append(f"Invoice No: {bill['invoice_no']}")
        lines.append(f"Date/Time : {bill['created_at']}")
        lines.append(f"Customer  : {bill['customer_name']}")
        lines.append(f"Contact   : {bill['customer_contact']}")
        lines.append("-" * 60)
        lines.append(f"{'PID':<10}{'NAME':<25}{'PRICE':>8}{'QTY':>6}{'TOTAL':>10}")
        lines.append("-" * 60)
        for it in items:
            nm = str(it["name"])[:24]
            lines.append(f"{it['pid']:<10}{nm:<25}{float(it['price']):>8.2f}{int(it['qty']):>6d}{float(it['total']):>10.2f}")
        lines.append("-" * 60)
        lines.append(f"{'GRAND TOTAL':>49}{float(bill['total']):>11.2f}")
        lines.append("-" * 60)
        self.txt_bill.delete("1.0", "end")
        self.txt_bill.insert("1.0", "\n".join(lines))

    def _open_bill_file(self) -> None:
        os.makedirs("bills", exist_ok=True)
        path = filedialog.askopenfilename(initialdir=os.path.abspath("bills"), title="Open Bill", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.txt_bill.delete("1.0", "end")
                self.txt_bill.insert("1.0", f.read())
        except Exception as ex:
            messagebox.showerror("Error", f"Cannot open file: {ex}")


class BillStoreWindow(BaseWindow):
    def __init__(self, master: tk.Tk, bill_repo: BillingRepository) -> None:
        super().__init__(master, "Bill Store")
        self._bill_repo = bill_repo
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top.columnconfigure(0, weight=1)

        self.var_search = tk.StringVar()
        ttk.Entry(top, textvariable=self.var_search).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(top, text="Search", command=self._search).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(top, text="Refresh", command=self._refresh).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(top, text="Open Bill File", command=self._open_file).grid(row=0, column=3, sticky="ew", padx=4)

        table_frame = ttk.LabelFrame(self, text="Bills")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        cols = ("invoice_no", "customer_name", "customer_contact", "created_at", "total")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, width=160, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        sb_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        sb_y.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb_y.set)

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.txt = tk.Text(self, height=12, wrap="none")
        self.txt.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self._selected_invoice: Optional[str] = None

    def _refresh(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in self._bill_repo.all_bills():
            self.tree.insert("", "end", values=(r["invoice_no"], r["customer_name"], r["customer_contact"], r["created_at"], f"{float(r['total']):.2f}"))

    def _search(self) -> None:
        kw = self.var_search.get().strip()
        rows = self._bill_repo.search_bills(kw) if kw else self._bill_repo.all_bills()
        for i in self.tree.get_children():
            self.tree.delete(i)
        for r in rows:
            self.tree.insert("", "end", values=(r["invoice_no"], r["customer_name"], r["customer_contact"], r["created_at"], f"{float(r['total']):.2f}"))

    def _on_select(self, _evt: object) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        self._selected_invoice = str(vals[0])
        data = self._bill_repo.get_bill(self._selected_invoice)
        self.txt.delete("1.0", "end")
        if data is None:
            self.txt.insert("1.0", "Bill not found.\n")
            return
        bill, items = data
        lines: List[str] = []
        lines.append(f"Invoice No: {bill['invoice_no']}")
        lines.append(f"Date/Time : {bill['created_at']}")
        lines.append(f"Customer  : {bill['customer_name']}")
        lines.append(f"Contact   : {bill['customer_contact']}")
        lines.append(f"Total     : {float(bill['total']):.2f}")
        lines.append("")
        lines.append("Items:")
        for it in items:
            lines.append(f" - {it['pid']} | {it['name']} | {int(it['qty'])} x {float(it['price']):.2f} = {float(it['total']):.2f}")
        self.txt.insert("1.0", "\n".join(lines))

    def _open_file(self) -> None:
        os.makedirs("bills", exist_ok=True)
        inv = self._selected_invoice
        if inv:
            path = os.path.join("bills", f"{inv}.txt")
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.txt.delete("1.0", "end")
                        self.txt.insert("1.0", f.read())
                        return
                except Exception:
                    pass
        path2 = filedialog.askopenfilename(initialdir=os.path.abspath("bills"), title="Open Bill", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")])
        if not path2:
            return
        try:
            with open(path2, "r", encoding="utf-8") as f:
                self.txt.delete("1.0", "end")
                self.txt.insert("1.0", f.read())
        except Exception as ex:
            messagebox.showerror("Error", f"Cannot open file: {ex}")


class Dashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1100x650")
        self.minsize(900, 550)

        self._db = Database(DB_FILE)
        self._emp_repo = EmployeeRepository(self._db)
        self._sup_repo = SupplierRepository(self._db)
        self._cat_repo = CategoryRepository(self._db)
        self._prod_repo = ProductRepository(self._db)
        self._bill_repo = BillingRepository(self._db)

        self._img_refs: List[Any] = []
        self._build_ui()
        self._tick()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        try:
            self._db.close()
        finally:
            self.destroy()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=0)

        self.lbl_title = ttk.Label(header, text="Inventory Management System", font=("Arial", 20, "bold"))
        self.lbl_title.grid(row=0, column=0, sticky="w")

        self.lbl_time = ttk.Label(header, text="")
        self.lbl_time.grid(row=0, column=1, sticky="e")

        body = ttk.Frame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(body, text="Dashboard")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.columnconfigure(0, weight=1)

        right = ttk.LabelFrame(body, text="Overview")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        btn_frame = ttk.Frame(left)
        btn_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        for i in range(2):
            btn_frame.columnconfigure(i, weight=1)

        ttk.Button(btn_frame, text="Employees", command=self._open_employees).grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        ttk.Button(btn_frame, text="Suppliers", command=self._open_suppliers).grid(row=0, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(btn_frame, text="Categories", command=self._open_categories).grid(row=1, column=0, sticky="ew", padx=6, pady=6)
        ttk.Button(btn_frame, text="Products", command=self._open_products).grid(row=1, column=1, sticky="ew", padx=6, pady=6)
        ttk.Button(btn_frame, text="Billing", command=self._open_billing).grid(row=2, column=0, sticky="ew", padx=6, pady=6)
        ttk.Button(btn_frame, text="Bill Store", command=self._open_bill_store).grid(row=2, column=1, sticky="ew", padx=6, pady=6)

        img_frame = ttk.Frame(left)
        img_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        img_frame.columnconfigure(0, weight=1)

        self.lbl_img = ttk.Label(img_frame, text="(Image preview)")
        self.lbl_img.grid(row=0, column=0, sticky="nsew")

        ttk.Button(img_frame, text="Load Image", command=self._load_image).grid(row=1, column=0, sticky="ew", pady=(8, 0))

        self.lbl_counts = ttk.Label(right, text="", font=("Arial", 12))
        self.lbl_counts.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        ttk.Button(right, text="Refresh Overview", command=self._refresh_overview).grid(row=1, column=0, sticky="ew", padx=10)

        self.txt_recent = tk.Text(right, height=10, wrap="none")
        self.txt_recent.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)

        self._refresh_overview()

    def _tick(self) -> None:
        self.lbl_time.configure(text=datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S"))
        self.after(1000, self._tick)

    def _refresh_overview(self) -> None:
        emp = len(self._emp_repo.all())
        sup = len(self._sup_repo.all())
        cat = len(self._cat_repo.all())
        prod = len(self._prod_repo.all())
        bills = len(self._bill_repo.all_bills())
        self.lbl_counts.configure(text=f"Employees: {emp}    Suppliers: {sup}    Categories: {cat}    Products: {prod}    Bills: {bills}")

        recent = self._bill_repo.all_bills()[:10]
        lines = ["Recent Bills:"]
        for r in recent:
            lines.append(f" - {r['invoice_no']} | {r['customer_name']} | {r['created_at']} | {float(r['total']):.2f}")
        if len(lines) == 1:
            lines.append(" (none)")
        self.txt_recent.delete("1.0", "end")
        self.txt_recent.insert("1.0", "\n".join(lines))

    def _load_image(self) -> None:
        path = filedialog.askopenfilename(title="Select Image", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("All Files", "*.*")])
        if not path:
            return
        if Image is None or ImageTk is None:
            messagebox.showerror("Error", "PIL (Pillow) is not available.")
            return
        try:
            img = Image.open(path)
            img.thumbnail((420, 260))
            tk_img = ImageTk.PhotoImage(img)
            self._img_refs = [tk_img]
            self.lbl_img.configure(image=tk_img, text="")
        except Exception as ex:
            messagebox.showerror("Error", f"Cannot load image: {ex}")

    def _open_employees(self) -> None:
        EmployeeWindow(self, self._emp_repo)

    def _open_suppliers(self) -> None:
        SupplierWindow(self, self._sup_repo)

    def _open_categories(self) -> None:
        CategoryWindow(self, self._cat_repo)

    def _open_products(self) -> None:
        ProductWindow(self, self._prod_repo, self._cat_repo, self._sup_repo)

    def _open_billing(self) -> None:
        BillingWindow(self, self._prod_repo, self._bill_repo)

    def _open_bill_store(self) -> None:
        BillStoreWindow(self, self._bill_repo)


def main() -> None:
    app = Dashboard()
    app.mainloop()


if __name__ == "__main__":
    main()