import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple, Any, Dict

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None


DB_FILE = "inventory_management.db"


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Employee:
    emp_id: str
    name: str
    email: str
    phone: str
    address: str
    gender: str
    dob: str
    doj: str
    salary: float


@dataclass(frozen=True)
class Supplier:
    sup_id: str
    name: str
    email: str
    phone: str
    address: str


@dataclass(frozen=True)
class Category:
    cat_id: str
    name: str
    description: str


@dataclass(frozen=True)
class Product:
    prod_id: str
    category: str
    supplier: str
    name: str
    price: float
    qty: int
    status: str


@dataclass(frozen=True)
class BillItem:
    prod_id: str
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
            CREATE TABLE IF NOT EXISTS employees (
                emp_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                gender TEXT NOT NULL,
                dob TEXT NOT NULL,
                doj TEXT NOT NULL,
                salary REAL NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS suppliers (
                sup_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                cat_id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                prod_id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                supplier TEXT NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                qty INTEGER NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY(category) REFERENCES categories(name) ON UPDATE CASCADE ON DELETE RESTRICT,
                FOREIGN KEY(supplier) REFERENCES suppliers(name) ON UPDATE CASCADE ON DELETE RESTRICT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bills (
                invoice_no TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                created_at TEXT NOT NULL,
                subtotal REAL NOT NULL,
                tax REAL NOT NULL,
                discount REAL NOT NULL,
                total REAL NOT NULL,
                items_json TEXT NOT NULL
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


class Repositories:
    def __init__(self, db: Database) -> None:
        self._db = db

    @staticmethod
    def _require_nonempty(value: str, field: str) -> str:
        v = (value or "").strip()
        if not v:
            raise ValidationError(f"{field} is required")
        return v

    @staticmethod
    def _require_float(value: str, field: str) -> float:
        try:
            f = float(value)
        except Exception:
            raise ValidationError(f"{field} must be a number")
        return f

    @staticmethod
    def _require_int(value: str, field: str) -> int:
        try:
            i = int(value)
        except Exception:
            raise ValidationError(f"{field} must be an integer")
        return i

    def upsert_employee(self, e: Employee) -> None:
        self._db.execute(
            """
            INSERT INTO employees(emp_id,name,email,phone,address,gender,dob,doj,salary)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(emp_id) DO UPDATE SET
                name=excluded.name,
                email=excluded.email,
                phone=excluded.phone,
                address=excluded.address,
                gender=excluded.gender,
                dob=excluded.dob,
                doj=excluded.doj,
                salary=excluded.salary
            """,
            (e.emp_id, e.name, e.email, e.phone, e.address, e.gender, e.dob, e.doj, e.salary),
        )

    def delete_employee(self, emp_id: str) -> None:
        self._db.execute("DELETE FROM employees WHERE emp_id=?", (emp_id,))

    def list_employees(self, search: str = "") -> List[Employee]:
        if search.strip():
            rows = self._db.query(
                """
                SELECT * FROM employees
                WHERE emp_id LIKE ? OR name LIKE ? OR phone LIKE ? OR email LIKE ?
                ORDER BY name
                """,
                (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"),
            )
        else:
            rows = self._db.query("SELECT * FROM employees ORDER BY name")
        return [
            Employee(
                emp_id=r["emp_id"],
                name=r["name"],
                email=r["email"],
                phone=r["phone"],
                address=r["address"],
                gender=r["gender"],
                dob=r["dob"],
                doj=r["doj"],
                salary=float(r["salary"]),
            )
            for r in rows
        ]

    def get_employee(self, emp_id: str) -> Optional[Employee]:
        rows = self._db.query("SELECT * FROM employees WHERE emp_id=?", (emp_id,))
        if not rows:
            return None
        r = rows[0]
        return Employee(
            emp_id=r["emp_id"],
            name=r["name"],
            email=r["email"],
            phone=r["phone"],
            address=r["address"],
            gender=r["gender"],
            dob=r["dob"],
            doj=r["doj"],
            salary=float(r["salary"]),
        )

    def upsert_supplier(self, s: Supplier) -> None:
        self._db.execute(
            """
            INSERT INTO suppliers(sup_id,name,email,phone,address)
            VALUES(?,?,?,?,?)
            ON CONFLICT(sup_id) DO UPDATE SET
                name=excluded.name,
                email=excluded.email,
                phone=excluded.phone,
                address=excluded.address
            """,
            (s.sup_id, s.name, s.email, s.phone, s.address),
        )

    def delete_supplier(self, sup_id: str) -> None:
        self._db.execute("DELETE FROM suppliers WHERE sup_id=?", (sup_id,))

    def list_suppliers(self, search: str = "") -> List[Supplier]:
        if search.strip():
            rows = self._db.query(
                """
                SELECT * FROM suppliers
                WHERE sup_id LIKE ? OR name LIKE ? OR phone LIKE ? OR email LIKE ?
                ORDER BY name
                """,
                (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"),
            )
        else:
            rows = self._db.query("SELECT * FROM suppliers ORDER BY name")
        return [
            Supplier(
                sup_id=r["sup_id"],
                name=r["name"],
                email=r["email"],
                phone=r["phone"],
                address=r["address"],
            )
            for r in rows
        ]

    def list_supplier_names(self) -> List[str]:
        rows = self._db.query("SELECT name FROM suppliers ORDER BY name")
        return [r["name"] for r in rows]

    def upsert_category(self, c: Category) -> None:
        self._db.execute(
            """
            INSERT INTO categories(cat_id,name,description)
            VALUES(?,?,?)
            ON CONFLICT(cat_id) DO UPDATE SET
                name=excluded.name,
                description=excluded.description
            """,
            (c.cat_id, c.name, c.description),
        )

    def delete_category(self, cat_id: str) -> None:
        self._db.execute("DELETE FROM categories WHERE cat_id=?", (cat_id,))

    def list_categories(self, search: str = "") -> List[Category]:
        if search.strip():
            rows = self._db.query(
                """
                SELECT * FROM categories
                WHERE cat_id LIKE ? OR name LIKE ? OR description LIKE ?
                ORDER BY name
                """,
                (f"%{search}%", f"%{search}%", f"%{search}%"),
            )
        else:
            rows = self._db.query("SELECT * FROM categories ORDER BY name")
        return [Category(cat_id=r["cat_id"], name=r["name"], description=r["description"]) for r in rows]

    def list_category_names(self) -> List[str]:
        rows = self._db.query("SELECT name FROM categories ORDER BY name")
        return [r["name"] for r in rows]

    def upsert_product(self, p: Product) -> None:
        self._db.execute(
            """
            INSERT INTO products(prod_id,category,supplier,name,price,qty,status)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(prod_id) DO UPDATE SET
                category=excluded.category,
                supplier=excluded.supplier,
                name=excluded.name,
                price=excluded.price,
                qty=excluded.qty,
                status=excluded.status
            """,
            (p.prod_id, p.category, p.supplier, p.name, p.price, p.qty, p.status),
        )

    def delete_product(self, prod_id: str) -> None:
        self._db.execute("DELETE FROM products WHERE prod_id=?", (prod_id,))

    def list_products(self, search: str = "") -> List[Product]:
        if search.strip():
            rows = self._db.query(
                """
                SELECT * FROM products
                WHERE prod_id LIKE ? OR name LIKE ? OR category LIKE ? OR supplier LIKE ?
                ORDER BY name
                """,
                (f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"),
            )
        else:
            rows = self._db.query("SELECT * FROM products ORDER BY name")
        return [
            Product(
                prod_id=r["prod_id"],
                category=r["category"],
                supplier=r["supplier"],
                name=r["name"],
                price=float(r["price"]),
                qty=int(r["qty"]),
                status=r["status"],
            )
            for r in rows
        ]

    def get_product(self, prod_id: str) -> Optional[Product]:
        rows = self._db.query("SELECT * FROM products WHERE prod_id=?", (prod_id,))
        if not rows:
            return None
        r = rows[0]
        return Product(
            prod_id=r["prod_id"],
            category=r["category"],
            supplier=r["supplier"],
            name=r["name"],
            price=float(r["price"]),
            qty=int(r["qty"]),
            status=r["status"],
        )

    def adjust_product_stock(self, prod_id: str, delta_qty: int) -> None:
        p = self.get_product(prod_id)
        if p is None:
            raise ValidationError("Product not found")
        new_qty = p.qty + delta_qty
        if new_qty < 0:
            raise ValidationError("Insufficient stock")
        status = p.status
        if new_qty == 0:
            status = "Inactive"
        self._db.execute("UPDATE products SET qty=?, status=? WHERE prod_id=?", (new_qty, status, prod_id))

    def save_bill(
        self,
        invoice_no: str,
        customer_name: str,
        customer_phone: str,
        created_at: str,
        subtotal: float,
        tax: float,
        discount: float,
        total: float,
        items_json: str,
    ) -> None:
        self._db.execute(
            """
            INSERT INTO bills(invoice_no,customer_name,customer_phone,created_at,subtotal,tax,discount,total,items_json)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(invoice_no) DO UPDATE SET
                customer_name=excluded.customer_name,
                customer_phone=excluded.customer_phone,
                created_at=excluded.created_at,
                subtotal=excluded.subtotal,
                tax=excluded.tax,
                discount=excluded.discount,
                total=excluded.total,
                items_json=excluded.items_json
            """,
            (invoice_no, customer_name, customer_phone, created_at, subtotal, tax, discount, total, items_json),
        )

    def get_bill(self, invoice_no: str) -> Optional[sqlite3.Row]:
        rows = self._db.query("SELECT * FROM bills WHERE invoice_no=?", (invoice_no,))
        return rows[0] if rows else None

    def list_bills(self, search: str = "") -> List[sqlite3.Row]:
        if search.strip():
            return self._db.query(
                """
                SELECT * FROM bills
                WHERE invoice_no LIKE ? OR customer_name LIKE ? OR customer_phone LIKE ?
                ORDER BY created_at DESC
                """,
                (f"%{search}%", f"%{search}%", f"%{search}%"),
            )
        return self._db.query("SELECT * FROM bills ORDER BY created_at DESC")

    def counts(self) -> Dict[str, int]:
        def c(table: str) -> int:
            r = self._db.query(f"SELECT COUNT(*) AS n FROM {table}")
            return int(r[0]["n"]) if r else 0

        return {
            "employees": c("employees"),
            "suppliers": c("suppliers"),
            "categories": c("categories"),
            "products": c("products"),
            "bills": c("bills"),
        }


class ImageLoader:
    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, Tuple[int, int]], Any] = {}

    def load(self, path: str, size: Tuple[int, int]) -> Optional[Any]:
        if Image is None or ImageTk is None:
            return None
        key = (path, size)
        if key in self._cache:
            return self._cache[key]
        if not path or not os.path.exists(path):
            return None
        try:
            img = Image.open(path)
            img = img.resize(size)
            tk_img = ImageTk.PhotoImage(img)
            self._cache[key] = tk_img
            return tk_img
        except Exception:
            return None


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


class EntityManagerWindow(BaseWindow):
    def __init__(self, master: tk.Tk, title: str) -> None:
        super().__init__(master, title)
        self._search_var = tk.StringVar()
        self._build_header()
        self._build_body()

    def _build_header(self) -> None:
        frm = ttk.Frame(self)
        frm.pack(fill="x", padx=10, pady=10)

        ttk.Label(frm, text="Search:").pack(side="left")
        ent = ttk.Entry(frm, textvariable=self._search_var, width=40)
        ent.pack(side="left", padx=(5, 5))
        ent.bind("<Return>", lambda e: self.refresh())

        ttk.Button(frm, text="Search", command=self.refresh).pack(side="left", padx=(0, 5))
        ttk.Button(frm, text="Clear", command=self._clear_search).pack(side="left")

    def _build_body(self) -> None:
        self._body = ttk.Frame(self)
        self._body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _clear_search(self) -> None:
        self._search_var.set("")
        self.refresh()

    def refresh(self) -> None:
        raise NotImplementedError


class EmployeeWindow(EntityManagerWindow):
    def __init__(self, master: tk.Tk, repo: Repositories) -> None:
        self._repo = repo
        super().__init__(master, "Employees")
        self._selected_id: Optional[str] = None
        self._build_form()
        self._build_table()
        self.refresh()

    def _build_form(self) -> None:
        frm = ttk.LabelFrame(self._body, text="Employee Details")
        frm.pack(fill="x", pady=(0, 10))

        self._vars: Dict[str, tk.StringVar] = {
            "emp_id": tk.StringVar(),
            "name": tk.StringVar(),
            "email": tk.StringVar(),
            "phone": tk.StringVar(),
            "address": tk.StringVar(),
            "gender": tk.StringVar(),
            "dob": tk.StringVar(),
            "doj": tk.StringVar(),
            "salary": tk.StringVar(),
        }

        fields = [
            ("Employee ID", "emp_id"),
            ("Name", "name"),
            ("Email", "email"),
            ("Phone", "phone"),
            ("Address", "address"),
            ("Gender", "gender"),
            ("DOB (YYYY-MM-DD)", "dob"),
            ("DOJ (YYYY-MM-DD)", "doj"),
            ("Salary", "salary"),
        ]

        for i, (label, key) in enumerate(fields):
            r = i // 3
            c = (i % 3) * 2
            ttk.Label(frm, text=label).grid(row=r, column=c, sticky="w", padx=8, pady=6)
            ttk.Entry(frm, textvariable=self._vars[key], width=28).grid(row=r, column=c + 1, sticky="w", padx=8, pady=6)

        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=6, sticky="w", padx=8, pady=8)
        ttk.Button(btns, text="Save", command=self._save).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Delete", command=self._delete).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Clear", command=self._clear_form).pack(side="left")

    def _build_table(self) -> None:
        frm = ttk.LabelFrame(self._body, text="Employees")
        frm.pack(fill="both", expand=True)

        cols = ("emp_id", "name", "email", "phone", "gender", "dob", "doj", "salary")
        self._tree = ttk.Treeview(frm, columns=cols, show="headings", height=12)
        for c in cols:
            self._tree.heading(c, text=c.upper())
            self._tree.column(c, width=120, anchor="w")
        self._tree.column("name", width=160)
        self._tree.column("email", width=180)
        self._tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(frm, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def _on_select(self, _evt: Any) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        item = self._tree.item(sel[0])
        values = item.get("values", [])
        if not values:
            return
        emp_id = str(values[0])
        e = self._repo.get_employee(emp_id)
        if e is None:
            return
        self._selected_id = e.emp_id
        self._vars["emp_id"].set(e.emp_id)
        self._vars["name"].set(e.name)
        self._vars["email"].set(e.email)
        self._vars["phone"].set(e.phone)
        self._vars["address"].set(e.address)
        self._vars["gender"].set(e.gender)
        self._vars["dob"].set(e.dob)
        self._vars["doj"].set(e.doj)
        self._vars["salary"].set(str(e.salary))

    def _clear_form(self) -> None:
        self._selected_id = None
        for v in self._vars.values():
            v.set("")

    def _save(self) -> None:
        try:
            emp_id = Repositories._require_nonempty(self._vars["emp_id"].get(), "Employee ID")
            name = Repositories._require_nonempty(self._vars["name"].get(), "Name")
            email = Repositories._require_nonempty(self._vars["email"].get(), "Email")
            phone = Repositories._require_nonempty(self._vars["phone"].get(), "Phone")
            address = Repositories._require_nonempty(self._vars["address"].get(), "Address")
            gender = Repositories._require_nonempty(self._vars["gender"].get(), "Gender")
            dob = Repositories._require_nonempty(self._vars["dob"].get(), "DOB")
            doj = Repositories._require_nonempty(self._vars["doj"].get(), "DOJ")
            salary = Repositories._require_float(self._vars["salary"].get(), "Salary")
            e = Employee(emp_id=emp_id, name=name, email=email, phone=phone, address=address, gender=gender, dob=dob, doj=doj, salary=salary)
            self._repo.upsert_employee(e)
            self.refresh()
            messagebox.showinfo("Success", "Employee saved")
        except ValidationError as ve:
            messagebox.showerror("Validation Error", str(ve))
        except sqlite3.IntegrityError as ie:
            messagebox.showerror("Database Error", str(ie))

    def _delete(self) -> None:
        emp_id = (self._vars["emp_id"].get() or "").strip()
        if not emp_id:
            messagebox.showerror("Error", "Employee ID is required to delete")
            return
        if not messagebox.askyesno("Confirm", f"Delete employee {emp_id}?"):
            return
        self._repo.delete_employee(emp_id)
        self._clear_form()
        self.refresh()

    def refresh(self) -> None:
        for i in self._tree.get_children():
            self._tree.delete(i)
        for e in self._repo.list_employees(self._search_var.get()):
            self._tree.insert("", "end", values=(e.emp_id, e.name, e.email, e.phone, e.gender, e.dob, e.doj, f"{e.salary:.2f}"))


class SupplierWindow(EntityManagerWindow):
    def __init__(self, master: tk.Tk, repo: Repositories) -> None:
        self._repo = repo
        super().__init__(master, "Suppliers")
        self._build_form()
        self._build_table()
        self.refresh()

    def _build_form(self) -> None:
        frm = ttk.LabelFrame(self._body, text="Supplier Details")
        frm.pack(fill="x", pady=(0, 10))

        self._vars: Dict[str, tk.StringVar] = {
            "sup_id": tk.StringVar(),
            "name": tk.StringVar(),
            "email": tk.StringVar(),
            "phone": tk.StringVar(),
            "address": tk.StringVar(),
        }

        fields = [
            ("Supplier ID", "sup_id"),
            ("Name", "name"),
            ("Email", "email"),
            ("Phone", "phone"),
            ("Address", "address"),
        ]

        for i, (label, key) in enumerate(fields):
            r = i // 3
            c = (i % 3) * 2
            ttk.Label(frm, text=label).grid(row=r, column=c, sticky="w", padx=8, pady=6)
            ttk.Entry(frm, textvariable=self._vars[key], width=28).grid(row=r, column=c + 1, sticky="w", padx=8, pady=6)

        btns = ttk.Frame(frm)
        btns.grid(row=2, column=0, columnspan=6, sticky="w", padx=8, pady=8)
        ttk.Button(btns, text="Save", command=self._save).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Delete", command=self._delete).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Clear", command=self._clear_form).pack(side="left")

    def _build_table(self) -> None:
        frm = ttk.LabelFrame(self._body, text="Suppliers")
        frm.pack(fill="both", expand=True)

        cols = ("sup_id", "name", "email", "phone", "address")
        self._tree = ttk.Treeview(frm, columns=cols, show="headings", height=12)
        for c in cols:
            self._tree.heading(c, text=c.upper())
            self._tree.column(c, width=140, anchor="w")
        self._tree.column("name", width=180)
        self._tree.column("email", width=200)
        self._tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(frm, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def _on_select(self, _evt: Any) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        values = self._tree.item(sel[0]).get("values", [])
        if not values:
            return
        self._vars["sup_id"].set(str(values[0]))
        self._vars["name"].set(str(values[1]))
        self._vars["email"].set(str(values[2]))
        self._vars["phone"].set(str(values[3]))
        self._vars["address"].set(str(values[4]))

    def _clear_form(self) -> None:
        for v in self._vars.values():
            v.set("")

    def _save(self) -> None:
        try:
            sup_id = Repositories._require_nonempty(self._vars["sup_id"].get(), "Supplier ID")
            name = Repositories._require_nonempty(self._vars["name"].get(), "Name")
            email = Repositories._require_nonempty(self._vars["email"].get(), "Email")
            phone = Repositories._require_nonempty(self._vars["phone"].get(), "Phone")
            address = Repositories._require_nonempty(self._vars["address"].get(), "Address")
            s = Supplier(sup_id=sup_id, name=name, email=email, phone=phone, address=address)
            self._repo.upsert_supplier(s)
            self.refresh()
            messagebox.showinfo("Success", "Supplier saved")
        except ValidationError as ve:
            messagebox.showerror("Validation Error", str(ve))
        except sqlite3.IntegrityError as ie:
            messagebox.showerror("Database Error", str(ie))

    def _delete(self) -> None:
        sup_id = (self._vars["sup_id"].get() or "").strip()
        if not sup_id:
            messagebox.showerror("Error", "Supplier ID is required to delete")
            return
        if not messagebox.askyesno("Confirm", f"Delete supplier {sup_id}?"):
            return
        try:
            self._repo.delete_supplier(sup_id)
        except sqlite3.IntegrityError as ie:
            messagebox.showerror("Database Error", str(ie))
            return
        self._clear_form()
        self.refresh()

    def refresh(self) -> None:
        for i in self._tree.get_children():
            self._tree.delete(i)
        for s in self._repo.list_suppliers(self._search_var.get()):
            self._tree.insert("", "end", values=(s.sup_id, s.name, s.email, s.phone, s.address))


class CategoryWindow(EntityManagerWindow):
    def __init__(self, master: tk.Tk, repo: Repositories) -> None:
        self._repo = repo
        super().__init__(master, "Categories")
        self._build_form()
        self._build_table()
        self.refresh()

    def _build_form(self) -> None:
        frm = ttk.LabelFrame(self._body, text="Category Details")
        frm.pack(fill="x", pady=(0, 10))

        self._vars: Dict[str, tk.StringVar] = {
            "cat_id": tk.StringVar(),
            "name": tk.StringVar(),
            "description": tk.StringVar(),
        }

        ttk.Label(frm, text="Category ID").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self._vars["cat_id"], width=28).grid(row=0, column=1, sticky="w", padx=8, pady=6)

        ttk.Label(frm, text="Name").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self._vars["name"], width=28).grid(row=0, column=3, sticky="w", padx=8, pady=6)

        ttk.Label(frm, text="Description").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self._vars["description"], width=70).grid(row=1, column=1, columnspan=3, sticky="w", padx=8, pady=6)

        btns = ttk.Frame(frm)
        btns.grid(row=2, column=0, columnspan=4, sticky="w", padx=8, pady=8)
        ttk.Button(btns, text="Save", command=self._save).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Delete", command=self._delete).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Clear", command=self._clear_form).pack(side="left")

    def _build_table(self) -> None:
        frm = ttk.LabelFrame(self._body, text="Categories")
        frm.pack(fill="both", expand=True)

        cols = ("cat_id", "name", "description")
        self._tree = ttk.Treeview(frm, columns=cols, show="headings", height=12)
        for c in cols:
            self._tree.heading(c, text=c.upper())
            self._tree.column(c, width=180, anchor="w")
        self._tree.column("description", width=360)
        self._tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(frm, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def _on_select(self, _evt: Any) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        values = self._tree.item(sel[0]).get("values", [])
        if not values:
            return
        self._vars["cat_id"].set(str(values[0]))
        self._vars["name"].set(str(values[1]))
        self._vars["description"].set(str(values[2]))

    def _clear_form(self) -> None:
        for v in self._vars.values():
            v.set("")

    def _save(self) -> None:
        try:
            cat_id = Repositories._require_nonempty(self._vars["cat_id"].get(), "Category ID")
            name = Repositories._require_nonempty(self._vars["name"].get(), "Name")
            description = Repositories._require_nonempty(self._vars["description"].get(), "Description")
            c = Category(cat_id=cat_id, name=name, description=description)
            self._repo.upsert_category(c)
            self.refresh()
            messagebox.showinfo("Success", "Category saved")
        except ValidationError as ve:
            messagebox.showerror("Validation Error", str(ve))
        except sqlite3.IntegrityError as ie:
            messagebox.showerror("Database Error", str(ie))

    def _delete(self) -> None:
        cat_id = (self._vars["cat_id"].get() or "").strip()
        if not cat_id:
            messagebox.showerror("Error", "Category ID is required to delete")
            return
        if not messagebox.askyesno("Confirm", f"Delete category {cat_id}?"):
            return
        try:
            self._repo.delete_category(cat_id)
        except sqlite3.IntegrityError as ie:
            messagebox.showerror("Database Error", str(ie))
            return
        self._clear_form()
        self.refresh()

    def refresh(self) -> None:
        for i in self._tree.get_children():
            self._tree.delete(i)
        for c in self._repo.list_categories(self._search_var.get()):
            self._tree.insert("", "end", values=(c.cat_id, c.name, c.description))


class ProductWindow(EntityManagerWindow):
    def __init__(self, master: tk.Tk, repo: Repositories) -> None:
        self._repo = repo
        super().__init__(master, "Products")
        self._build_form()
        self._build_table()
        self.refresh()

    def _build_form(self) -> None:
        frm = ttk.LabelFrame(self._body, text="Product Details")
        frm.pack(fill="x", pady=(0, 10))

        self._vars: Dict[str, tk.StringVar] = {
            "prod_id": tk.StringVar(),
            "category": tk.StringVar(),
            "supplier": tk.StringVar(),
            "name": tk.StringVar(),
            "price": tk.StringVar(),
            "qty": tk.StringVar(),
            "status": tk.StringVar(value="Active"),
        }

        ttk.Label(frm, text="Product ID").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self._vars["prod_id"], width=22).grid(row=0, column=1, sticky="w", padx=8, pady=6)

        ttk.Label(frm, text="Name").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self._vars["name"], width=26).grid(row=0, column=3, sticky="w", padx=8, pady=6)

        ttk.Label(frm, text="Category").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self._cat_cb = ttk.Combobox(frm, textvariable=self._vars["category"], width=20, state="readonly")
        self._cat_cb.grid(row=1, column=1, sticky="w", padx=8, pady=6)

        ttk.Label(frm, text="Supplier").grid(row=1, column=2, sticky="w", padx=8, pady=6)
        self._sup_cb = ttk.Combobox(frm, textvariable=self._vars["supplier"], width=24, state="readonly")
        self._sup_cb.grid(row=1, column=3, sticky="w", padx=8, pady=6)

        ttk.Label(frm, text="Price").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self._vars["price"], width=22).grid(row=2, column=1, sticky="w", padx=8, pady=6)

        ttk.Label(frm, text="Quantity").grid(row=2, column=2, sticky="w", padx=8, pady=6)
        ttk.Entry(frm, textvariable=self._vars["qty"], width=26).grid(row=2, column=3, sticky="w", padx=8, pady=6)

        ttk.Label(frm, text="Status").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        self._status_cb = ttk.Combobox(frm, textvariable=self._vars["status"], width=20, state="readonly", values=["Active", "Inactive"])
        self._status_cb.grid(row=3, column=1, sticky="w", padx=8, pady=6)

        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=4, sticky="w", padx=8, pady=8)
        ttk.Button(btns, text="Save", command=self._save).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Delete", command=self._delete).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="Clear", command=self._clear_form).pack(side="left")

        self._refresh_dropdowns()

    def _refresh_dropdowns(self) -> None:
        cats = self._repo.list_category_names()
        sups = self._repo.list_supplier_names()
        self._cat_cb["values"] = cats
        self._sup_cb["values"] = sups

    def _build_table(self) -> None:
        frm = ttk.LabelFrame(self._body, text="Products")
        frm.pack(fill="both", expand=True)

        cols = ("prod_id", "name", "category", "supplier", "price", "qty", "status")
        self._tree = ttk.Treeview(frm, columns=cols, show="headings", height=12)
        for c in cols:
            self._tree.heading(c, text=c.upper())
            self._tree.column(c, width=120, anchor="w")
        self._tree.column("name", width=180)
        self._tree.column("category", width=140)
        self._tree.column("supplier", width=160)
        self._tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(frm, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def _on_select(self, _evt: Any) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        values = self._tree.item(sel[0]).get("values", [])
        if not values:
            return
        self._vars["prod_id"].set(str(values[0]))
        self._vars["name"].set(str(values[1]))
        self._vars["category"].set(str(values[2]))
        self._vars["supplier"].set(str(values[3]))
        self._vars["price"].set(str(values[4]))
        self._vars["qty"].set(str(values[5]))
        self._vars["status"].set(str(values[6]))

    def _clear_form(self) -> None:
        for k, v in self._vars.items():
            if k == "status":
                v.set("Active")
            else:
                v.set("")
        self._refresh_dropdowns()

    def _save(self) -> None:
        try:
            self._refresh_dropdowns()
            prod_id = Repositories._require_nonempty(self._vars["prod_id"].get(), "Product ID")
            name = Repositories._require_nonempty(self._vars["name"].get(), "Name")
            category = Repositories._require_nonempty(self._vars["category"].get(), "Category")
            supplier = Repositories._require_nonempty(self._vars["supplier"].get(), "Supplier")
            price = Repositories._require_float(self._vars["price"].get(), "Price")
            qty = Repositories._require_int(self._vars["qty"].get(), "Quantity")
            if qty < 0:
                raise ValidationError("Quantity cannot be negative")
            status = Repositories._require_nonempty(self._vars["status"].get(), "Status")
            p = Product(prod_id=prod_id, category=category, supplier=supplier, name=name, price=price, qty=qty, status=status)
            self._repo.upsert_product(p)
            self.refresh()
            messagebox.showinfo("Success", "Product saved")
        except ValidationError as ve:
            messagebox.showerror("Validation Error", str(ve))
        except sqlite3.IntegrityError as ie:
            messagebox.showerror("Database Error", str(ie))

    def _delete(self) -> None:
        prod_id = (self._vars["prod_id"].get() or "").strip()
        if not prod_id:
            messagebox.showerror("Error", "Product ID is required to delete")
            return
        if not messagebox.askyesno("Confirm", f"Delete product {prod_id}?"):
            return
        self._repo.delete_product(prod_id)
        self._clear_form()
        self.refresh()

    def refresh(self) -> None:
        self._refresh_dropdowns()
        for i in self._tree.get_children():
            self._tree.delete(i)
        for p in self._repo.list_products(self._search_var.get()):
            self._tree.insert("", "end", values=(p.prod_id, p.name, p.category, p.supplier, f"{p.price:.2f}", p.qty, p.status))


class BillsWindow(EntityManagerWindow):
    def __init__(self, master: tk.Tk, repo: Repositories) -> None:
        self._repo = repo
        super().__init__(master, "Bills")
        self._build_table()
        self._build_viewer()
        self.refresh()

    def _build_table(self) -> None:
        frm = ttk.LabelFrame(self._body, text="Saved Bills")
        frm.pack(fill="both", expand=True, pady=(0, 10))

        cols = ("invoice_no", "customer_name", "customer_phone", "created_at", "total")
        self._tree = ttk.Treeview(frm, columns=cols, show="headings", height=10)
        for c in cols:
            self._tree.heading(c, text=c.upper())
            self._tree.column(c, width=160, anchor="w")
        self._tree.column("created_at", width=190)
        self._tree.column("total", width=100, anchor="e")
        self._tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(frm, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def _build_viewer(self) -> None:
        frm = ttk.LabelFrame(self._body, text="Bill Details")
        frm.pack(fill="both", expand=True)

        self._text = tk.Text(frm, height=12, wrap="none")
        self._text.pack(fill="both", expand=True, padx=6, pady=6)
        self._text.configure(state="disabled")

        btns = ttk.Frame(frm)
        btns.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(btns, text="Export to File", command=self._export).pack(side="left")

    def _on_select(self, _evt: Any) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        invoice_no = str(self._tree.item(sel[0]).get("values", [""])[0])
        row = self._repo.get_bill(invoice_no)
        if row is None:
            return
        self._set_text(self._format_bill_row(row))

    def _set_text(self, s: str) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", s)
        self._text.configure(state="disabled")

    def _format_bill_row(self, row: sqlite3.Row) -> str:
        import json

        items = []
        try:
            items = json.loads(row["items_json"])
        except Exception:
            items = []
        lines = []
        lines.append(f"Invoice No: {row['invoice_no']}")
        lines.append(f"Customer: {row['customer_name']}")
        lines.append(f"Phone: {row['customer_phone']}")
        lines.append(f"Date: {row['created_at']}")
        lines.append("")
        lines.append("Items:")
        lines.append("  ID        Name                          Price     Qty     Total")
        lines.append("  ----------------------------------------------------------------")
        for it in items:
            pid = str(it.get("prod_id", ""))
            name = str(it.get("name", ""))
            price = float(it.get("price", 0.0))
            qty = int(it.get("qty", 0))
            total = float(it.get("total", round(price * qty, 2)))
            lines.append(f"  {pid:<8}  {name:<28.28}  {price:>7.2f}  {qty:>5}  {total:>8.2f}")
        lines.append("")
        lines.append(f"Subtotal: {float(row['subtotal']):.2f}")
        lines.append(f"Tax:      {float(row['tax']):.2f}")
        lines.append(f"Discount: {float(row['discount']):.2f}")
        lines.append(f"Total:    {float(row['total']):.2f}")
        return "\n".join(lines)

    def _export(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showerror("Error", "Select a bill to export")
            return
        invoice_no = str(self._tree.item(sel[0]).get("values", [""])[0])
        row = self._repo.get_bill(invoice_no)
        if row is None:
            messagebox.showerror("Error", "Bill not found")
            return
        content = self._format_bill_row(row)
        path = filedialog.asksaveasfilename(
            title="Save Bill",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile=f"bill_{invoice_no}.txt",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Success", f"Exported to {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def refresh(self) -> None:
        for i in self._tree.get_children():
            self._tree.delete(i)
        for r in self._repo.list_bills(self._search_var.get()):
            self._tree.insert(
                "",
                "end",
                values=(r["invoice_no"], r["customer_name"], r["customer_phone"], r["created_at"], f"{float(r['total']):.2f}"),
            )


class BillingWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: Repositories) -> None:
        self._repo = repo
        self._items: List[BillItem] = []
        self._invoice_no = tk.StringVar(value=self._generate_invoice_no())
        self._cust_name = tk.StringVar()
        self._cust_phone = tk.StringVar()
        self._prod_id = tk.StringVar()
        self._prod_name = tk.StringVar()
        self._prod_price = tk.StringVar()
        self._prod_qty = tk.StringVar(value="1")
        self._tax = tk.StringVar(value="0")
        self._discount = tk.StringVar(value="0")
        self._subtotal = tk.StringVar(value="0.00")
        self._total = tk.StringVar(value="0.00")
        super().__init__(master, "Billing")
        self._build_ui()
        self._refresh_products_list()

    def _generate_invoice_no(self) -> str:
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        inv = ttk.LabelFrame(top, text="Invoice")
        inv.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ttk.Label(inv, text="Invoice No").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(inv, textvariable=self._invoice_no, width=24, state="readonly").grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Button(inv, text="New", command=self._new_invoice).grid(row=0, column=2, sticky="w", padx=8, pady=6)

        cust = ttk.LabelFrame(top, text="Customer")
        cust.pack(side="left", fill="x", expand=True)
        ttk.Label(cust, text="Name").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(cust, textvariable=self._cust_name, width=28).grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Label(cust, text="Phone").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(cust, textvariable=self._cust_phone, width=28).grid(row=1, column=1, sticky="w", padx=8, pady=6)

        mid = ttk.Frame(self)
        mid.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = ttk.LabelFrame(mid, text="Add Item")
        left.pack(side="left", fill="y", padx=(0, 10))

        ttk.Label(left, text="Product ID").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(left, textvariable=self._prod_id, width=26).grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Button(left, text="Find", command=self._find_product).grid(row=0, column=2, sticky="w", padx=8, pady=6)

        ttk.Label(left, text="Name").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(left, textvariable=self._prod_name, width=40, state="readonly").grid(row=1, column=1, columnspan=2, sticky="w", padx=8, pady=6)

        ttk.Label(left, text="Price").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(left, textvariable=self._prod_price, width=26, state="readonly").grid(row=2, column=1, sticky="w", padx=8, pady=6)

        ttk.Label(left, text="Qty").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(left, textvariable=self._prod_qty, width=26).grid(row=3, column=1, sticky="w", padx=8, pady=6)

        ttk.Button(left, text="Add to Cart", command=self._add_to_cart).grid(row=4, column=0, columnspan=3, sticky="ew", padx=8, pady=8)
        ttk.Button(left, text="Remove Selected", command=self._remove_selected).grid(row=5, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))

        right = ttk.LabelFrame(mid, text="Cart")
        right.pack(side="left", fill="both", expand=True)

        cols = ("prod_id", "name", "price", "qty", "total")
        self._tree = ttk.Treeview(right, columns=cols, show="headings", height=12)
        for c in cols:
            self._tree.heading(c, text=c.upper())
            self._tree.column(c, width=120, anchor="w")
        self._tree.column("name", width=220)
        self._tree.column("price", width=90, anchor="e")
        self._tree.column("qty", width=70, anchor="e")
        self._tree.column("total", width=100, anchor="e")
        self._tree.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(right, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        bottom = ttk.LabelFrame(self, text="Totals")
        bottom.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(bottom, text="Tax").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(bottom, textvariable=self._tax, width=12).grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Label(bottom, text="Discount").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Entry(bottom, textvariable=self._discount, width=12).grid(row=0, column=3, sticky="w", padx=8, pady=6)

        ttk.Label(bottom, text="Subtotal").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(bottom, textvariable=self._subtotal, width=12, state="readonly").grid(row=1, column=1, sticky="w", padx=8, pady=6)
        ttk.Label(bottom, text="Total").grid(row=1, column=2, sticky="w", padx=8, pady=6)
        ttk.Entry(bottom, textvariable=self._total, width=12, state="readonly").grid(row=1, column=3, sticky="w", padx=8, pady=6)

        ttk.Button(bottom, text="Recalculate", command=self._recalc).grid(row=0, column=4, rowspan=2, sticky="ns", padx=8, pady=6)
        ttk.Button(bottom, text="Save Bill", command=self._save_bill).grid(row=0, column=5, rowspan=2, sticky="ns", padx=8, pady=6)

        self._tax.trace_add("write", lambda *_: self._recalc())
        self._discount.trace_add("write", lambda *_: self._recalc())

    def _refresh_products_list(self) -> None:
        pass

    def _new_invoice(self) -> None:
        self._invoice_no.set(self._generate_invoice_no())
        self._cust_name.set("")
        self._cust_phone.set("")
        self._prod_id.set("")
        self._prod_name.set("")
        self._prod_price.set("")
        self._prod_qty.set("1")
        self._tax.set("0")
        self._discount.set("0")
        self._items.clear()
        for i in self._tree.get_children():
            self._tree.delete(i)
        self._recalc()

    def _find_product(self) -> None:
        pid = (self._prod_id.get() or "").strip()
        if not pid:
            messagebox.showerror("Error", "Enter Product ID")
            return
        p = self._repo.get_product(pid)
        if p is None:
            messagebox.showerror("Error", "Product not found")
            return
        if p.status != "Active":
            messagebox.showerror("Error", "Product is inactive")
            return
        self._prod_name.set(p.name)
        self._prod_price.set(f"{p.price:.2f}")

    def _add_to_cart(self) -> None:
        try:
            pid = Repositories._require_nonempty(self._prod_id.get(), "Product ID")
            p = self._repo.get_product(pid)
            if p is None:
                raise ValidationError("Product not found")
            if p.status != "Active":
                raise ValidationError("Product is inactive")
            qty = Repositories._require_int(self._prod_qty.get(), "Quantity")
            if qty <= 0:
                raise ValidationError("Quantity must be greater than 0")
            if qty > p.qty:
                raise ValidationError("Insufficient stock")
            existing = next((it for it in self._items if it.prod_id == pid), None)
            if existing:
                new_qty = existing.qty + qty
                if new_qty > p.qty:
                    raise ValidationError("Insufficient stock")
                self._items = [BillItem(it.prod_id, it.name, it.price, new_qty) if it.prod_id == pid else it for it in self._items]
            else:
                self._items.append(BillItem(prod_id=p.prod_id, name=p.name, price=p.price, qty=qty))
            self._render_cart()
            self._recalc()
        except ValidationError as ve:
            messagebox.showerror("Validation Error", str(ve))

    def _remove_selected(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showerror("Error", "Select an item to remove")
            return
        values = self._tree.item(sel[0]).get("values", [])
        if not values:
            return
        pid = str(values[0])
        self._items = [it for it in self._items if it.prod_id != pid]
        self._render_cart()
        self._recalc()

    def _render_cart(self) -> None:
        for i in self._tree.get_children():
            self._tree.delete(i)
        for it in self._items:
            self._tree.insert("", "end", values=(it.prod_id, it.name, f"{it.price:.2f}", it.qty, f"{it.total:.2f}"))

    def _recalc(self) -> None:
        subtotal = round(sum(it.total for it in self._items), 2)
        try:
            tax = float((self._tax.get() or "0").strip() or "0")
        except Exception:
            tax = 0.0
        try:
            discount = float((self._discount.get() or "0").strip() or "0")
        except Exception:
            discount = 0.0
        total = round(subtotal + tax - discount, 2)
        if total < 0:
            total = 0.0
        self._subtotal.set(f"{subtotal:.2f}")
        self._total.set(f"{total:.2f}")

    def _save_bill(self) -> None:
        import json

        try:
            invoice_no = Repositories._require_nonempty(self._invoice_no.get(), "Invoice No")
            customer_name = Repositories._require_nonempty(self._cust_name.get(), "Customer Name")
            customer_phone = Repositories._require_nonempty(self._cust_phone.get(), "Customer Phone")
            if not self._items:
                raise ValidationError("Cart is empty")
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            subtotal = float(self._subtotal.get())
            tax = float((self._tax.get() or "0").strip() or "0")
            discount = float((self._discount.get() or "0").strip() or "0")
            total = float(self._total.get())

            for it in self._items:
                p = self._repo.get_product(it.prod_id)
                if p is None:
                    raise ValidationError(f"Product not found: {it.prod_id}")
                if it.qty > p.qty:
                    raise ValidationError(f"Insufficient stock for {it.prod_id}")

            for it in self._items:
                self._repo.adjust_product_stock(it.prod_id, -it.qty)

            items_json = json.dumps(
                [{"prod_id": it.prod_id, "name": it.name, "price": it.price, "qty": it.qty, "total": it.total} for it in self._items],
                ensure_ascii=False,
            )
            self._repo.save_bill(invoice_no, customer_name, customer_phone, created_at, subtotal, tax, discount, total, items_json)
            messagebox.showinfo("Success", f"Bill saved: {invoice_no}")
            self._new_invoice()
        except ValidationError as ve:
            messagebox.showerror("Validation Error", str(ve))
        except sqlite3.IntegrityError as ie:
            messagebox.showerror("Database Error", str(ie))
        except Exception as e:
            messagebox.showerror("Error", str(e))


class Dashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1100x650")
        self.minsize(1000, 600)

        self._db = Database(DB_FILE)
        self._repo = Repositories(self._db)
        self._img_loader = ImageLoader()
        self._header_img_path: Optional[str] = None
        self._header_img_ref: Optional[Any] = None

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._tick()

    def _on_close(self) -> None:
        try:
            self._db.close()
        finally:
            self.destroy()

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=10)

        self._title_lbl = ttk.Label(header, text="Inventory Management System", font=("Arial", 18, "bold"))
        self._title_lbl.pack(side="left")

        ttk.Button(header, text="Load Header Image", command=self._load_header_image).pack(side="left", padx=10)

        self._time_lbl = ttk.Label(header, text="", font=("Arial", 11))
        self._time_lbl.pack(side="right")

        self._img_lbl = ttk.Label(self)
        self._img_lbl.pack(fill="x", padx=10)

        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.LabelFrame(main, text="Dashboard")
        left.pack(side="left", fill="y", padx=(0, 10))

        ttk.Button(left, text="Employees", width=22, command=self._open_employees).pack(padx=10, pady=(10, 6))
        ttk.Button(left, text="Suppliers", width=22, command=self._open_suppliers).pack(padx=10, pady=6)
        ttk.Button(left, text="Categories", width=22, command=self._open_categories).pack(padx=10, pady=6)
        ttk.Button(left, text="Products", width=22, command=self._open_products).pack(padx=10, pady=6)
        ttk.Button(left, text="Billing", width=22, command=self._open_billing).pack(padx=10, pady=6)
        ttk.Button(left, text="Bills (Search/Export)", width=22, command=self._open_bills).pack(padx=10, pady=6)
        ttk.Button(left, text="Exit", width=22, command=self._on_close).pack(padx=10, pady=(20, 10))

        right = ttk.LabelFrame(main, text="Summary")
        right.pack(side="left", fill="both", expand=True)

        self._summary_vars: Dict[str, tk.StringVar] = {
            "employees": tk.StringVar(value="0"),
            "suppliers": tk.StringVar(value="0"),
            "categories": tk.StringVar(value="0"),
            "products": tk.StringVar(value="0"),
            "bills": tk.StringVar(value="0"),
        }

        grid = ttk.Frame(right)
        grid.pack(fill="x", padx=10, pady=10)

        labels = [
            ("Employees", "employees"),
            ("Suppliers", "suppliers"),
            ("Categories", "categories"),
            ("Products", "products"),
            ("Bills", "bills"),
        ]
        for i, (label, key) in enumerate(labels):
            r = i // 2
            c = (i % 2) * 2
            ttk.Label(grid, text=f"{label}:", font=("Arial", 12, "bold")).grid(row=r, column=c, sticky="w", padx=8, pady=8)
            ttk.Label(grid, textvariable=self._summary_vars[key], font=("Arial", 12)).grid(row=r, column=c + 1, sticky="w", padx=8, pady=8)

        ttk.Button(right, text="Refresh Summary", command=self._refresh_summary).pack(anchor="w", padx=18, pady=(0, 10))

        self._refresh_summary()

    def _load_header_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All Files", "*.*")],
        )
        if not path:
            return
        self._header_img_path = path
        self._render_header_image()

    def _render_header_image(self) -> None:
        if not self._header_img_path:
            self._img_lbl.configure(image="")
            self._header_img_ref = None
            return
        w = max(self.winfo_width() - 40, 300)
        h = 140
        img = self._img_loader.load(self._header_img_path, (w, h))
        if img is None:
            self._img_lbl.configure(text=os.path.basename(self._header_img_path))
            self._img_lbl.configure(image="")
            self._header_img_ref = None
        else:
            self._img_lbl.configure(text="")
            self._img_lbl.configure(image=img)
            self._header_img_ref = img

    def _tick(self) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._time_lbl.configure(text=now)
        self._refresh_summary()
        self._render_header_image()
        self.after(1000, self._tick)

    def _refresh_summary(self) -> None:
        counts = self._repo.counts()
        for k, v in counts.items():
            if k in self._summary_vars:
                self._summary_vars[k].set(str(v))

    def _open_employees(self) -> None:
        EmployeeWindow(self, self._repo)

    def _open_suppliers(self) -> None:
        SupplierWindow(self, self._repo)

    def _open_categories(self) -> None:
        CategoryWindow(self, self._repo)

    def _open_products(self) -> None:
        ProductWindow(self, self._repo)

    def _open_billing(self) -> None:
        BillingWindow(self, self._repo)

    def _open_bills(self) -> None:
        BillsWindow(self, self._repo)


def main() -> None:
    app = Dashboard()
    app.mainloop()


if __name__ == "__main__":
    main()