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


DB_FILE = "inventory.db"
BILLS_DIR = "bills"


def ensure_dir(path: str) -> None:
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


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
    salary: float


@dataclass(frozen=True)
class Supplier:
    invoice: str
    name: str
    contact: str
    desc: str


@dataclass(frozen=True)
class Category:
    name: str


@dataclass(frozen=True)
class Product:
    name: str
    category: str
    supplier: str
    price: float
    qty: int
    status: str


@dataclass(frozen=True)
class BillItem:
    product_id: int
    name: str
    price: float
    qty: int

    @property
    def total(self) -> float:
        return float(self.price) * int(self.qty)


class Database:
    def __init__(self, db_path: str = DB_FILE) -> None:
        self.db_path = db_path
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.execute("PRAGMA foreign_keys = ON")
        return con

    def _init_db(self) -> None:
        with self._connect() as con:
            cur = con.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS employee(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    emp_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    gender TEXT NOT NULL,
                    contact TEXT NOT NULL,
                    dob TEXT NOT NULL,
                    doj TEXT NOT NULL,
                    password TEXT NOT NULL,
                    usertype TEXT NOT NULL,
                    address TEXT NOT NULL,
                    salary REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS supplier(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    contact TEXT NOT NULL,
                    desc TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS category(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS product(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    supplier TEXT NOT NULL,
                    price REAL NOT NULL,
                    qty INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(name, category, supplier)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS bill(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_no TEXT UNIQUE NOT NULL,
                    customer_name TEXT NOT NULL,
                    customer_contact TEXT NOT NULL,
                    total REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS bill_item(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bill_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    price REAL NOT NULL,
                    qty INTEGER NOT NULL,
                    total REAL NOT NULL,
                    FOREIGN KEY(bill_id) REFERENCES bill(id) ON DELETE CASCADE,
                    FOREIGN KEY(product_id) REFERENCES product(id) ON DELETE RESTRICT
                )
                """
            )
            con.commit()

    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> None:
        with self._connect() as con:
            con.execute(sql, params)
            con.commit()

    def fetchall(self, sql: str, params: Tuple[Any, ...] = ()) -> List[Tuple[Any, ...]]:
        with self._connect() as con:
            cur = con.execute(sql, params)
            return cur.fetchall()

    def fetchone(self, sql: str, params: Tuple[Any, ...] = ()) -> Optional[Tuple[Any, ...]]:
        with self._connect() as con:
            cur = con.execute(sql, params)
            return cur.fetchone()

    def count(self, table: str) -> int:
        row = self.fetchone(f"SELECT COUNT(*) FROM {table}")
        return int(row[0]) if row else 0


class EmployeeRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, e: Employee) -> None:
        if not e.emp_id.strip():
            raise ValueError("Employee ID is required")
        if not e.name.strip():
            raise ValueError("Employee name is required")
        if not e.email.strip():
            raise ValueError("Employee email is required")
        if not e.contact.strip():
            raise ValueError("Employee contact is required")
        if not e.password.strip():
            raise ValueError("Employee password is required")
        if not e.usertype.strip():
            raise ValueError("Employee usertype is required")
        if e.salary < 0:
            raise ValueError("Salary must be non-negative")

        self.db.execute(
            """
            INSERT INTO employee(emp_id,name,email,gender,contact,dob,doj,password,usertype,address,salary,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                e.emp_id.strip(),
                e.name.strip(),
                e.email.strip(),
                e.gender.strip(),
                e.contact.strip(),
                e.dob.strip(),
                e.doj.strip(),
                e.password,
                e.usertype.strip(),
                e.address.strip(),
                float(e.salary),
                now_str(),
            ),
        )

    def update(self, emp_id: str, e: Employee) -> None:
        if emp_id.strip() != e.emp_id.strip():
            raise ValueError("Employee ID cannot be changed")
        self.db.execute(
            """
            UPDATE employee
            SET name=?,email=?,gender=?,contact=?,dob=?,doj=?,password=?,usertype=?,address=?,salary=?
            WHERE emp_id=?
            """,
            (
                e.name.strip(),
                e.email.strip(),
                e.gender.strip(),
                e.contact.strip(),
                e.dob.strip(),
                e.doj.strip(),
                e.password,
                e.usertype.strip(),
                e.address.strip(),
                float(e.salary),
                e.emp_id.strip(),
            ),
        )

    def delete(self, emp_id: str) -> None:
        self.db.execute("DELETE FROM employee WHERE emp_id=?", (emp_id.strip(),))

    def list(self, query: str = "") -> List[Tuple[Any, ...]]:
        q = query.strip()
        if not q:
            return self.db.fetchall(
                "SELECT emp_id,name,email,gender,contact,dob,doj,usertype,address,salary FROM employee ORDER BY id DESC"
            )
        like = f"%{q}%"
        return self.db.fetchall(
            """
            SELECT emp_id,name,email,gender,contact,dob,doj,usertype,address,salary
            FROM employee
            WHERE emp_id LIKE ? OR name LIKE ? OR email LIKE ? OR contact LIKE ? OR usertype LIKE ?
            ORDER BY id DESC
            """,
            (like, like, like, like, like),
        )

    def get(self, emp_id: str) -> Optional[Employee]:
        row = self.db.fetchone(
            """
            SELECT emp_id,name,email,gender,contact,dob,doj,password,usertype,address,salary
            FROM employee WHERE emp_id=?
            """,
            (emp_id.strip(),),
        )
        if not row:
            return None
        return Employee(
            emp_id=row[0],
            name=row[1],
            email=row[2],
            gender=row[3],
            contact=row[4],
            dob=row[5],
            doj=row[6],
            password=row[7],
            usertype=row[8],
            address=row[9],
            salary=float(row[10]),
        )


class SupplierRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, s: Supplier) -> None:
        if not s.invoice.strip():
            raise ValueError("Supplier invoice is required")
        if not s.name.strip():
            raise ValueError("Supplier name is required")
        if not s.contact.strip():
            raise ValueError("Supplier contact is required")
        self.db.execute(
            """
            INSERT INTO supplier(invoice,name,contact,desc,created_at)
            VALUES(?,?,?,?,?)
            """,
            (s.invoice.strip(), s.name.strip(), s.contact.strip(), s.desc.strip(), now_str()),
        )

    def update(self, invoice: str, s: Supplier) -> None:
        if invoice.strip() != s.invoice.strip():
            raise ValueError("Supplier invoice cannot be changed")
        self.db.execute(
            "UPDATE supplier SET name=?,contact=?,desc=? WHERE invoice=?",
            (s.name.strip(), s.contact.strip(), s.desc.strip(), s.invoice.strip()),
        )

    def delete(self, invoice: str) -> None:
        self.db.execute("DELETE FROM supplier WHERE invoice=?", (invoice.strip(),))

    def list(self, query: str = "") -> List[Tuple[Any, ...]]:
        q = query.strip()
        if not q:
            return self.db.fetchall("SELECT invoice,name,contact,desc FROM supplier ORDER BY id DESC")
        like = f"%{q}%"
        return self.db.fetchall(
            """
            SELECT invoice,name,contact,desc
            FROM supplier
            WHERE invoice LIKE ? OR name LIKE ? OR contact LIKE ? OR desc LIKE ?
            ORDER BY id DESC
            """,
            (like, like, like, like),
        )

    def names(self) -> List[str]:
        rows = self.db.fetchall("SELECT name FROM supplier ORDER BY name ASC")
        return [r[0] for r in rows]


class CategoryRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, c: Category) -> None:
        if not c.name.strip():
            raise ValueError("Category name is required")
        self.db.execute(
            "INSERT INTO category(name,created_at) VALUES(?,?)",
            (c.name.strip(), now_str()),
        )

    def update(self, old_name: str, new_name: str) -> None:
        if not old_name.strip() or not new_name.strip():
            raise ValueError("Category name is required")
        self.db.execute("UPDATE category SET name=? WHERE name=?", (new_name.strip(), old_name.strip()))
        self.db.execute("UPDATE product SET category=? WHERE category=?", (new_name.strip(), old_name.strip()))

    def delete(self, name: str) -> None:
        name = name.strip()
        if not name:
            return
        row = self.db.fetchone("SELECT COUNT(*) FROM product WHERE category=?", (name,))
        if row and int(row[0]) > 0:
            raise ValueError("Cannot delete category in use by products")
        self.db.execute("DELETE FROM category WHERE name=?", (name,))

    def list(self, query: str = "") -> List[Tuple[Any, ...]]:
        q = query.strip()
        if not q:
            return self.db.fetchall("SELECT name FROM category ORDER BY name ASC")
        like = f"%{q}%"
        return self.db.fetchall("SELECT name FROM category WHERE name LIKE ? ORDER BY name ASC", (like,))

    def names(self) -> List[str]:
        rows = self.db.fetchall("SELECT name FROM category ORDER BY name ASC")
        return [r[0] for r in rows]


class ProductRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, p: Product) -> None:
        if not p.name.strip():
            raise ValueError("Product name is required")
        if not p.category.strip():
            raise ValueError("Product category is required")
        if not p.supplier.strip():
            raise ValueError("Product supplier is required")
        if p.price < 0:
            raise ValueError("Price must be non-negative")
        if p.qty < 0:
            raise ValueError("Quantity must be non-negative")
        if p.status.strip() not in ("Active", "Inactive"):
            raise ValueError("Status must be Active or Inactive")

        self.db.execute(
            """
            INSERT INTO product(name,category,supplier,price,qty,status,created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (
                p.name.strip(),
                p.category.strip(),
                p.supplier.strip(),
                float(p.price),
                int(p.qty),
                p.status.strip(),
                now_str(),
            ),
        )

    def update(self, product_id: int, p: Product) -> None:
        if product_id <= 0:
            raise ValueError("Invalid product id")
        if p.price < 0 or p.qty < 0:
            raise ValueError("Invalid price/qty")
        if p.status.strip() not in ("Active", "Inactive"):
            raise ValueError("Status must be Active or Inactive")
        self.db.execute(
            """
            UPDATE product
            SET name=?,category=?,supplier=?,price=?,qty=?,status=?
            WHERE id=?
            """,
            (
                p.name.strip(),
                p.category.strip(),
                p.supplier.strip(),
                float(p.price),
                int(p.qty),
                p.status.strip(),
                int(product_id),
            ),
        )

    def delete(self, product_id: int) -> None:
        self.db.execute("DELETE FROM product WHERE id=?", (int(product_id),))

    def list(self, query: str = "") -> List[Tuple[Any, ...]]:
        q = query.strip()
        if not q:
            return self.db.fetchall(
                "SELECT id,name,category,supplier,price,qty,status FROM product ORDER BY id DESC"
            )
        like = f"%{q}%"
        return self.db.fetchall(
            """
            SELECT id,name,category,supplier,price,qty,status
            FROM product
            WHERE name LIKE ? OR category LIKE ? OR supplier LIKE ? OR status LIKE ?
            ORDER BY id DESC
            """,
            (like, like, like, like),
        )

    def get(self, product_id: int) -> Optional[Tuple[Any, ...]]:
        return self.db.fetchone(
            "SELECT id,name,category,supplier,price,qty,status FROM product WHERE id=?",
            (int(product_id),),
        )

    def find_by_name(self, name: str) -> List[Tuple[Any, ...]]:
        like = f"%{name.strip()}%"
        return self.db.fetchall(
            "SELECT id,name,category,supplier,price,qty,status FROM product WHERE name LIKE ? ORDER BY name ASC",
            (like,),
        )

    def adjust_stock(self, product_id: int, delta_qty: int) -> None:
        row = self.db.fetchone("SELECT qty FROM product WHERE id=?", (int(product_id),))
        if not row:
            raise ValueError("Product not found")
        current = int(row[0])
        new_qty = current + int(delta_qty)
        if new_qty < 0:
            raise ValueError("Insufficient stock")
        self.db.execute("UPDATE product SET qty=? WHERE id=?", (new_qty, int(product_id)))


class BillRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create_bill(self, invoice_no: str, customer_name: str, customer_contact: str, items: List[BillItem]) -> int:
        invoice_no = invoice_no.strip()
        customer_name = customer_name.strip()
        customer_contact = customer_contact.strip()
        if not invoice_no:
            raise ValueError("Invoice number is required")
        if not customer_name:
            raise ValueError("Customer name is required")
        if not customer_contact:
            raise ValueError("Customer contact is required")
        if not items:
            raise ValueError("At least one item is required")

        total = sum(i.total for i in items)
        with self.db._connect() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO bill(invoice_no,customer_name,customer_contact,total,created_at) VALUES(?,?,?,?,?)",
                (invoice_no, customer_name, customer_contact, float(total), now_str()),
            )
            bill_id = int(cur.lastrowid)
            for it in items:
                cur.execute(
                    """
                    INSERT INTO bill_item(bill_id,product_id,name,price,qty,total)
                    VALUES(?,?,?,?,?,?)
                    """,
                    (bill_id, int(it.product_id), it.name, float(it.price), int(it.qty), float(it.total)),
                )
            con.commit()
            return bill_id

    def get_bill(self, invoice_no: str) -> Optional[Dict[str, Any]]:
        row = self.db.fetchone(
            "SELECT id,invoice_no,customer_name,customer_contact,total,created_at FROM bill WHERE invoice_no=?",
            (invoice_no.strip(),),
        )
        if not row:
            return None
        bill_id = int(row[0])
        items = self.db.fetchall(
            "SELECT product_id,name,price,qty,total FROM bill_item WHERE bill_id=? ORDER BY id ASC",
            (bill_id,),
        )
        return {
            "id": bill_id,
            "invoice_no": row[1],
            "customer_name": row[2],
            "customer_contact": row[3],
            "total": float(row[4]),
            "created_at": row[5],
            "items": items,
        }

    def list_invoices(self, query: str = "") -> List[Tuple[Any, ...]]:
        q = query.strip()
        if not q:
            return self.db.fetchall(
                "SELECT invoice_no,customer_name,customer_contact,total,created_at FROM bill ORDER BY id DESC"
            )
        like = f"%{q}%"
        return self.db.fetchall(
            """
            SELECT invoice_no,customer_name,customer_contact,total,created_at
            FROM bill
            WHERE invoice_no LIKE ? OR customer_name LIKE ? OR customer_contact LIKE ?
            ORDER BY id DESC
            """,
            (like, like, like),
        )


class ImageManager:
    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, Tuple[int, int]], Any] = {}

    def load(self, path: str, size: Tuple[int, int]) -> Optional[Any]:
        if Image is None or ImageTk is None:
            return None
        key = (path, size)
        if key in self._cache:
            return self._cache[key]
        if not os.path.isfile(path):
            return None
        img = Image.open(path)
        img = img.resize(size)
        tk_img = ImageTk.PhotoImage(img)
        self._cache[key] = tk_img
        return tk_img


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
        self.repo = repo
        self._build()
        self._refresh()

    def _build(self) -> None:
        self.geometry("1050x600")

        form = ttk.LabelFrame(self, text="Employee Details")
        form.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_emp_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_gender = tk.StringVar(value="Male")
        self.var_contact = tk.StringVar()
        self.var_dob = tk.StringVar()
        self.var_doj = tk.StringVar()
        self.var_password = tk.StringVar()
        self.var_usertype = tk.StringVar(value="Employee")
        self.var_salary = tk.StringVar(value="0")
        self.var_search = tk.StringVar()

        labels = [
            ("Emp ID", self.var_emp_id),
            ("Name", self.var_name),
            ("Email", self.var_email),
            ("Gender", self.var_gender),
            ("Contact", self.var_contact),
            ("DOB (YYYY-MM-DD)", self.var_dob),
            ("DOJ (YYYY-MM-DD)", self.var_doj),
            ("Password", self.var_password),
            ("User Type", self.var_usertype),
            ("Salary", self.var_salary),
        ]

        for i, (txt, var) in enumerate(labels):
            r = i // 4
            c = (i % 4) * 2
            ttk.Label(form, text=txt).grid(row=r, column=c, padx=6, pady=6, sticky="w")
            if txt == "Gender":
                cb = ttk.Combobox(form, textvariable=var, values=["Male", "Female", "Other"], state="readonly", width=18)
                cb.grid(row=r, column=c + 1, padx=6, pady=6, sticky="w")
            elif txt == "User Type":
                cb = ttk.Combobox(form, textvariable=var, values=["Admin", "Employee"], state="readonly", width=18)
                cb.grid(row=r, column=c + 1, padx=6, pady=6, sticky="w")
            elif txt == "Password":
                ttk.Entry(form, textvariable=var, width=22, show="*").grid(row=r, column=c + 1, padx=6, pady=6, sticky="w")
            else:
                ttk.Entry(form, textvariable=var, width=22).grid(row=r, column=c + 1, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Address").grid(row=3, column=0, padx=6, pady=6, sticky="nw")
        self.txt_address = tk.Text(form, width=70, height=3)
        self.txt_address.grid(row=3, column=1, columnspan=7, padx=6, pady=6, sticky="w")

        btns = ttk.Frame(self)
        btns.pack(side=tk.TOP, fill=tk.X, padx=10, pady=0)

        ttk.Button(btns, text="Save", command=self._save).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Update", command=self._update).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=5, pady=5)

        search = ttk.LabelFrame(self, text="Search")
        search.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        ttk.Entry(search, textvariable=self.var_search, width=40).pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Button(search, text="Search", command=self._refresh).pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Button(search, text="Show All", command=self._show_all).pack(side=tk.LEFT, padx=6, pady=6)

        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("emp_id", "name", "email", "gender", "contact", "dob", "doj", "usertype", "address", "salary")
        self.table = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.table.heading(c, text=c.upper())
            self.table.column(c, width=100, anchor="w")
        self.table.column("address", width=220)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.table.yview)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.table.configure(yscrollcommand=sb_y.set)

        self.table.bind("<<TreeviewSelect>>", self._on_select)

    def _employee_from_form(self) -> Employee:
        address = self.txt_address.get("1.0", tk.END).strip()
        salary = float(self.var_salary.get().strip() or "0")
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
            address=address,
            salary=salary,
        )

    def _save(self) -> None:
        try:
            e = self._employee_from_form()
            self.repo.add(e)
            messagebox.showinfo("Success", "Employee added")
            self._refresh()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _update(self) -> None:
        try:
            e = self._employee_from_form()
            if not e.emp_id:
                raise ValueError("Select an employee to update")
            self.repo.update(e.emp_id, e)
            messagebox.showinfo("Success", "Employee updated")
            self._refresh()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _delete(self) -> None:
        try:
            emp_id = self.var_emp_id.get().strip()
            if not emp_id:
                raise ValueError("Select an employee to delete")
            if not messagebox.askyesno("Confirm", "Delete selected employee?"):
                return
            self.repo.delete(emp_id)
            messagebox.showinfo("Success", "Employee deleted")
            self._refresh()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _clear(self) -> None:
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_email.set("")
        self.var_gender.set("Male")
        self.var_contact.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_password.set("")
        self.var_usertype.set("Employee")
        self.var_salary.set("0")
        self.txt_address.delete("1.0", tk.END)

    def _show_all(self) -> None:
        self.var_search.set("")
        self._refresh()

    def _refresh(self) -> None:
        for i in self.table.get_children():
            self.table.delete(i)
        rows = self.repo.list(self.var_search.get())
        for r in rows:
            self.table.insert("", tk.END, values=r)

    def _on_select(self, _evt: Any) -> None:
        sel = self.table.selection()
        if not sel:
            return
        values = self.table.item(sel[0], "values")
        if not values:
            return
        self.var_emp_id.set(values[0])
        self.var_name.set(values[1])
        self.var_email.set(values[2])
        self.var_gender.set(values[3])
        self.var_contact.set(values[4])
        self.var_dob.set(values[5])
        self.var_doj.set(values[6])
        self.var_usertype.set(values[7])
        self.txt_address.delete("1.0", tk.END)
        self.txt_address.insert("1.0", values[8])
        self.var_salary.set(str(values[9]))
        emp = self.repo.get(values[0])
        if emp:
            self.var_password.set(emp.password)


class SupplierWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: SupplierRepository) -> None:
        super().__init__(master, "Suppliers")
        self.repo = repo
        self._build()
        self._refresh()

    def _build(self) -> None:
        self.geometry("900x550")

        form = ttk.LabelFrame(self, text="Supplier Details")
        form.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_invoice = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_search = tk.StringVar()

        ttk.Label(form, text="Invoice").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_invoice, width=25).grid(row=0, column=1, padx=6, pady=6, sticky="w")
        ttk.Label(form, text="Name").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_name, width=25).grid(row=0, column=3, padx=6, pady=6, sticky="w")
        ttk.Label(form, text="Contact").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_contact, width=25).grid(row=1, column=1, padx=6, pady=6, sticky="w")
        ttk.Label(form, text="Description").grid(row=1, column=2, padx=6, pady=6, sticky="nw")
        self.txt_desc = tk.Text(form, width=40, height=3)
        self.txt_desc.grid(row=1, column=3, padx=6, pady=6, sticky="w")

        btns = ttk.Frame(self)
        btns.pack(side=tk.TOP, fill=tk.X, padx=10, pady=0)
        ttk.Button(btns, text="Save", command=self._save).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Update", command=self._update).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=5, pady=5)

        search = ttk.LabelFrame(self, text="Search")
        search.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        ttk.Entry(search, textvariable=self.var_search, width=40).pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Button(search, text="Search", command=self._refresh).pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Button(search, text="Show All", command=self._show_all).pack(side=tk.LEFT, padx=6, pady=6)

        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("invoice", "name", "contact", "desc")
        self.table = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.table.heading(c, text=c.upper())
            self.table.column(c, width=150, anchor="w")
        self.table.column("desc", width=350)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.table.yview)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.table.configure(yscrollcommand=sb_y.set)

        self.table.bind("<<TreeviewSelect>>", self._on_select)

    def _supplier_from_form(self) -> Supplier:
        return Supplier(
            invoice=self.var_invoice.get().strip(),
            name=self.var_name.get().strip(),
            contact=self.var_contact.get().strip(),
            desc=self.txt_desc.get("1.0", tk.END).strip(),
        )

    def _save(self) -> None:
        try:
            s = self._supplier_from_form()
            self.repo.add(s)
            messagebox.showinfo("Success", "Supplier added")
            self._refresh()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _update(self) -> None:
        try:
            s = self._supplier_from_form()
            if not s.invoice:
                raise ValueError("Select a supplier to update")
            self.repo.update(s.invoice, s)
            messagebox.showinfo("Success", "Supplier updated")
            self._refresh()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _delete(self) -> None:
        try:
            invoice = self.var_invoice.get().strip()
            if not invoice:
                raise ValueError("Select a supplier to delete")
            if not messagebox.askyesno("Confirm", "Delete selected supplier?"):
                return
            self.repo.delete(invoice)
            messagebox.showinfo("Success", "Supplier deleted")
            self._refresh()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _clear(self) -> None:
        self.var_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete("1.0", tk.END)

    def _show_all(self) -> None:
        self.var_search.set("")
        self._refresh()

    def _refresh(self) -> None:
        for i in self.table.get_children():
            self.table.delete(i)
        rows = self.repo.list(self.var_search.get())
        for r in rows:
            self.table.insert("", tk.END, values=r)

    def _on_select(self, _evt: Any) -> None:
        sel = self.table.selection()
        if not sel:
            return
        values = self.table.item(sel[0], "values")
        if not values:
            return
        self.var_invoice.set(values[0])
        self.var_name.set(values[1])
        self.var_contact.set(values[2])
        self.txt_desc.delete("1.0", tk.END)
        self.txt_desc.insert("1.0", values[3])


class CategoryWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: CategoryRepository) -> None:
        super().__init__(master, "Categories")
        self.repo = repo
        self._build()
        self._refresh()

    def _build(self) -> None:
        self.geometry("600x450")

        form = ttk.LabelFrame(self, text="Category")
        form.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_name = tk.StringVar()
        self.var_new_name = tk.StringVar()
        self.var_search = tk.StringVar()

        ttk.Label(form, text="Name").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_name, width=30).grid(row=0, column=1, padx=6, pady=6, sticky="w")
        ttk.Label(form, text="New Name").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_new_name, width=30).grid(row=0, column=3, padx=6, pady=6, sticky="w")

        btns = ttk.Frame(self)
        btns.pack(side=tk.TOP, fill=tk.X, padx=10, pady=0)
        ttk.Button(btns, text="Save", command=self._save).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Rename", command=self._rename).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=5, pady=5)

        search = ttk.LabelFrame(self, text="Search")
        search.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        ttk.Entry(search, textvariable=self.var_search, width=40).pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Button(search, text="Search", command=self._refresh).pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Button(search, text="Show All", command=self._show_all).pack(side=tk.LEFT, padx=6, pady=6)

        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("name",)
        self.table = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.table.heading("name", text="NAME")
        self.table.column("name", width=400, anchor="w")
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.table.yview)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.table.configure(yscrollcommand=sb_y.set)

        self.table.bind("<<TreeviewSelect>>", self._on_select)

    def _save(self) -> None:
        try:
            c = Category(name=self.var_name.get().strip())
            self.repo.add(c)
            messagebox.showinfo("Success", "Category added")
            self._refresh()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _rename(self) -> None:
        try:
            old = self.var_name.get().strip()
            new = self.var_new_name.get().strip()
            if not old or not new:
                raise ValueError("Select a category and provide new name")
            self.repo.update(old, new)
            messagebox.showinfo("Success", "Category renamed")
            self._refresh()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _delete(self) -> None:
        try:
            name = self.var_name.get().strip()
            if not name:
                raise ValueError("Select a category to delete")
            if not messagebox.askyesno("Confirm", "Delete selected category?"):
                return
            self.repo.delete(name)
            messagebox.showinfo("Success", "Category deleted")
            self._refresh()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _clear(self) -> None:
        self.var_name.set("")
        self.var_new_name.set("")

    def _show_all(self) -> None:
        self.var_search.set("")
        self._refresh()

    def _refresh(self) -> None:
        for i in self.table.get_children():
            self.table.delete(i)
        rows = self.repo.list(self.var_search.get())
        for r in rows:
            self.table.insert("", tk.END, values=r)

    def _on_select(self, _evt: Any) -> None:
        sel = self.table.selection()
        if not sel:
            return
        values = self.table.item(sel[0], "values")
        if not values:
            return
        self.var_name.set(values[0])
        self.var_new_name.set(values[0])


class ProductWindow(BaseWindow):
    def __init__(self, master: tk.Tk, repo: ProductRepository, cat_repo: CategoryRepository, sup_repo: SupplierRepository) -> None:
        super().__init__(master, "Products")
        self.repo = repo
        self.cat_repo = cat_repo
        self.sup_repo = sup_repo
        self._build()
        self._refresh()

    def _build(self) -> None:
        self.geometry("1050x600")

        form = ttk.LabelFrame(self, text="Product Details")
        form.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_category = tk.StringVar()
        self.var_supplier = tk.StringVar()
        self.var_price = tk.StringVar(value="0")
        self.var_qty = tk.StringVar(value="0")
        self.var_status = tk.StringVar(value="Active")
        self.var_search = tk.StringVar()

        ttk.Label(form, text="ID").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_id, width=10, state="readonly").grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Name").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_name, width=25).grid(row=0, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Category").grid(row=0, column=4, padx=6, pady=6, sticky="w")
        self.cb_category = ttk.Combobox(form, textvariable=self.var_category, values=self.cat_repo.names(), state="readonly", width=22)
        self.cb_category.grid(row=0, column=5, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Supplier").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        self.cb_supplier = ttk.Combobox(form, textvariable=self.var_supplier, values=self.sup_repo.names(), state="readonly", width=22)
        self.cb_supplier.grid(row=1, column=1, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Price").grid(row=1, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_price, width=25).grid(row=1, column=3, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Quantity").grid(row=1, column=4, padx=6, pady=6, sticky="w")
        ttk.Entry(form, textvariable=self.var_qty, width=25).grid(row=1, column=5, padx=6, pady=6, sticky="w")

        ttk.Label(form, text="Status").grid(row=2, column=0, padx=6, pady=6, sticky="w")
        ttk.Combobox(form, textvariable=self.var_status, values=["Active", "Inactive"], state="readonly", width=22).grid(
            row=2, column=1, padx=6, pady=6, sticky="w"
        )

        ttk.Button(form, text="Reload Lists", command=self._reload_lists).grid(row=2, column=3, padx=6, pady=6, sticky="w")

        btns = ttk.Frame(self)
        btns.pack(side=tk.TOP, fill=tk.X, padx=10, pady=0)
        ttk.Button(btns, text="Save", command=self._save).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Update", command=self._update).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Delete", command=self._delete).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btns, text="Clear", command=self._clear).pack(side=tk.LEFT, padx=5, pady=5)

        search = ttk.LabelFrame(self, text="Search")
        search.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        ttk.Entry(search, textvariable=self.var_search, width=40).pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Button(search, text="Search", command=self._refresh).pack(side=tk.LEFT, padx=6, pady=6)
        ttk.Button(search, text="Show All", command=self._show_all).pack(side=tk.LEFT, padx=6, pady=6)

        table_frame = ttk.Frame(self)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("id", "name", "category", "supplier", "price", "qty", "status")
        self.table = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.table.heading(c, text=c.upper())
            self.table.column(c, width=120, anchor="w")
        self.table.column("name", width=200)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.table.yview)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.table.configure(yscrollcommand=sb_y.set)

        self.table.bind("<<TreeviewSelect>>", self._on_select)

    def _reload_lists(self) -> None:
        self.cb_category["values"] = self.cat_repo.names()
        self.cb_supplier["values"] = self.sup_repo.names()

    def _product_from_form(self) -> Product:
        return Product(
            name=self.var_name.get().strip(),
            category=self.var_category.get().strip(),
            supplier=self.var_supplier.get().strip(),
            price=float(self.var_price.get().strip() or "0"),
            qty=int(float(self.var_qty.get().strip() or "0")),
            status=self.var_status.get().strip(),
        )

    def _save(self) -> None:
        try:
            p = self._product_from_form()
            self.repo.add(p)
            messagebox.showinfo("Success", "Product added")
            self._refresh()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _update(self) -> None:
        try:
            pid = int(self.var_id.get().strip() or "0")
            if pid <= 0:
                raise ValueError("Select a product to update")
            p = self._product_from_form()
            self.repo.update(pid, p)
            messagebox.showinfo("Success", "Product updated")
            self._refresh()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _delete(self) -> None:
        try:
            pid = int(self.var_id.get().strip() or "0")
            if pid <= 0:
                raise ValueError("Select a product to delete")
            if not messagebox.askyesno("Confirm", "Delete selected product?"):
                return
            self.repo.delete(pid)
            messagebox.showinfo("Success", "Product deleted")
            self._refresh()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _clear(self) -> None:
        self.var_id.set("")
        self.var_name.set("")
        self.var_category.set("")
        self.var_supplier.set("")
        self.var_price.set("0")
        self.var_qty.set("0")
        self.var_status.set("Active")

    def _show_all(self) -> None:
        self.var_search.set("")
        self._refresh()

    def _refresh(self) -> None:
        self._reload_lists()
        for i in self.table.get_children():
            self.table.delete(i)
        rows = self.repo.list(self.var_search.get())
        for r in rows:
            self.table.insert("", tk.END, values=r)

    def _on_select(self, _evt: Any) -> None:
        sel = self.table.selection()
        if not sel:
            return
        values = self.table.item(sel[0], "values")
        if not values:
            return
        self.var_id.set(str(values[0]))
        self.var_name.set(values[1])
        self.var_category.set(values[2])
        self.var_supplier.set(values[3])
        self.var_price.set(str(values[4]))
        self.var_qty.set(str(values[5]))
        self.var_status.set(values[6])


class BillingWindow(BaseWindow):
    def __init__(self, master: tk.Tk, prod_repo: ProductRepository, bill_repo: BillRepository) -> None:
        super().__init__(master, "Billing")
        self.prod_repo = prod_repo
        self.bill_repo = bill_repo
        self.cart: List[BillItem] = []
        self._build()
        self._refresh_products()

    def _build(self) -> None:
        self.geometry("1200x650")

        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_invoice = tk.StringVar(value=f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        self.var_cust_name = tk.StringVar()
        self.var_cust_contact = tk.StringVar()
        self.var_search_prod = tk.StringVar()

        ttk.Label(top, text="Invoice No").grid(row=0, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(top, textvariable=self.var_invoice, width=25).grid(row=0, column=1, padx=6, pady=6, sticky="w")
        ttk.Label(top, text="Customer Name").grid(row=0, column=2, padx=6, pady=6, sticky="w")
        ttk.Entry(top, textvariable=self.var_cust_name, width=25).grid(row=0, column=3, padx=6, pady=6, sticky="w")
        ttk.Label(top, text="Customer Contact").grid(row=0, column=4, padx=6, pady=6, sticky="w")
        ttk.Entry(top, textvariable=self.var_cust_contact, width=25).grid(row=0, column=5, padx=6, pady=6, sticky="w")

        ttk.Label(top, text="Search Product").grid(row=1, column=0, padx=6, pady=6, sticky="w")
        ttk.Entry(top, textvariable=self.var_search_prod, width=25).grid(row=1, column=1, padx=6, pady=6, sticky="w")
        ttk.Button(top, text="Search", command=self._refresh_products).grid(row=1, column=2, padx=6, pady=6, sticky="w")
        ttk.Button(top, text="Show All", command=self._show_all_products).grid(row=1, column=3, padx=6, pady=6, sticky="w")

        mid = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        mid.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.Labelframe(mid, text="Products")
        right = ttk.Labelframe(mid, text="Cart")
        mid.add(left, weight=3)
        mid.add(right, weight=2)

        self.prod_table = ttk.Treeview(left, columns=("id", "name", "price", "qty", "status"), show="headings")
        for c, w in [("id", 60), ("name", 220), ("price", 90), ("qty", 70), ("status", 90)]:
            self.prod_table.heading(c, text=c.upper())
            self.prod_table.column(c, width=w, anchor="w")
        self.prod_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb1 = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.prod_table.yview)
        sb1.pack(side=tk.RIGHT, fill=tk.Y)
        self.prod_table.configure(yscrollcommand=sb1.set)

        cart_top = ttk.Frame(right)
        cart_top.pack(side=tk.TOP, fill=tk.X, padx=6, pady=6)

        self.var_add_qty = tk.StringVar(value="1")
        ttk.Label(cart_top, text="Qty").pack(side=tk.LEFT)
        ttk.Entry(cart_top, textvariable=self.var_add_qty, width=6).pack(side=tk.LEFT, padx=6)
        ttk.Button(cart_top, text="Add to Cart", command=self._add_to_cart).pack(side=tk.LEFT, padx=6)
        ttk.Button(cart_top, text="Remove Item", command=self._remove_from_cart).pack(side=tk.LEFT, padx=6)
        ttk.Button(cart_top, text="Clear Cart", command=self._clear_cart).pack(side=tk.LEFT, padx=6)

        self.cart_table = ttk.Treeview(right, columns=("product_id", "name", "price", "qty", "total"), show="headings")
        for c, w in [("product_id", 80), ("name", 180), ("price", 80), ("qty", 60), ("total", 90)]:
            self.cart_table.heading(c, text=c.upper())
            self.cart_table.column(c, width=w, anchor="w")
        self.cart_table.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=6)

        bottom = ttk.Frame(self)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        self.lbl_total = ttk.Label(bottom, text="Total: 0.00", font=("Arial", 12, "bold"))
        self.lbl_total.pack(side=tk.LEFT)

        ttk.Button(bottom, text="Generate Bill", command=self._generate_bill).pack(side=tk.RIGHT, padx=6)
        ttk.Button(bottom, text="Save Bill to File", command=self._save_bill_file).pack(side=tk.RIGHT, padx=6)

        self.txt_bill = tk.Text(self, height=10)
        self.txt_bill.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

    def _show_all_products(self) -> None:
        self.var_search_prod.set("")
        self._refresh_products()

    def _refresh_products(self) -> None:
        for i in self.prod_table.get_children():
            self.prod_table.delete(i)
        rows = self.prod_repo.list(self.var_search_prod.get())
        for r in rows:
            pid, name, _cat, _sup, price, qty, status = r
            self.prod_table.insert("", tk.END, values=(pid, name, price, qty, status))

    def _add_to_cart(self) -> None:
        try:
            sel = self.prod_table.selection()
            if not sel:
                raise ValueError("Select a product")
            values = self.prod_table.item(sel[0], "values")
            pid = int(values[0])
            name = str(values[1])
            price = float(values[2])
            stock_qty = int(values[3])
            status = str(values[4])
            if status != "Active":
                raise ValueError("Product is inactive")
            qty = int(float(self.var_add_qty.get().strip() or "0"))
            if qty <= 0:
                raise ValueError("Quantity must be positive")
            if qty > stock_qty:
                raise ValueError("Insufficient stock")

            for idx, it in enumerate(self.cart):
                if it.product_id == pid:
                    new_qty = it.qty + qty
                    if new_qty > stock_qty:
                        raise ValueError("Insufficient stock")
                    self.cart[idx] = BillItem(product_id=pid, name=name, price=price, qty=new_qty)
                    self._refresh_cart()
                    return

            self.cart.append(BillItem(product_id=pid, name=name, price=price, qty=qty))
            self._refresh_cart()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _remove_from_cart(self) -> None:
        try:
            sel = self.cart_table.selection()
            if not sel:
                raise ValueError("Select a cart item")
            values = self.cart_table.item(sel[0], "values")
            pid = int(values[0])
            self.cart = [it for it in self.cart if it.product_id != pid]
            self._refresh_cart()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _clear_cart(self) -> None:
        self.cart = []
        self._refresh_cart()

    def _refresh_cart(self) -> None:
        for i in self.cart_table.get_children():
            self.cart_table.delete(i)
        total = 0.0
        for it in self.cart:
            self.cart_table.insert("", tk.END, values=(it.product_id, it.name, f"{it.price:.2f}", it.qty, f"{it.total:.2f}"))
            total += it.total
        self.lbl_total.config(text=f"Total: {total:.2f}")

    def _render_bill_text(self, invoice_no: str, cust_name: str, cust_contact: str, items: List[BillItem]) -> str:
        lines: List[str] = []
        lines.append("INVENTORY MANAGEMENT SYSTEM - BILL")
        lines.append(f"Invoice No: {invoice_no}")
        lines.append(f"Date: {now_str()}")
        lines.append(f"Customer: {cust_name}")
        lines.append(f"Contact: {cust_contact}")
        lines.append("-" * 60)
        lines.append(f"{'Product':25} {'Price':>10} {'Qty':>6} {'Total':>12}")
        lines.append("-" * 60)
        grand = 0.0
        for it in items:
            grand += it.total
            pname = (it.name[:25]).ljust(25)
            lines.append(f"{pname} {it.price:>10.2f} {it.qty:>6d} {it.total:>12.2f}")
        lines.append("-" * 60)
        lines.append(f"{'Grand Total':>45} {grand:>12.2f}")
        lines.append("-" * 60)
        return "\n".join(lines)

    def _generate_bill(self) -> None:
        try:
            invoice_no = self.var_invoice.get().strip()
            cust_name = self.var_cust_name.get().strip()
            cust_contact = self.var_cust_contact.get().strip()
            if not self.cart:
                raise ValueError("Cart is empty")

            for it in self.cart:
                row = self.prod_repo.get(it.product_id)
                if not row:
                    raise ValueError(f"Product not found: {it.product_id}")
                stock_qty = int(row[5])
                status = str(row[6])
                if status != "Active":
                    raise ValueError(f"Product inactive: {it.name}")
                if it.qty > stock_qty:
                    raise ValueError(f"Insufficient stock for {it.name}")

            for it in self.cart:
                self.prod_repo.adjust_stock(it.product_id, -it.qty)

            self.bill_repo.create_bill(invoice_no, cust_name, cust_contact, self.cart)

            bill_text = self._render_bill_text(invoice_no, cust_name, cust_contact, self.cart)
            self.txt_bill.delete("1.0", tk.END)
            self.txt_bill.insert("1.0", bill_text)

            messagebox.showinfo("Success", "Bill generated and saved to database")
            self._refresh_products()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _save_bill_file(self) -> None:
        try:
            invoice_no = self.var_invoice.get().strip()
            content = self.txt_bill.get("1.0", tk.END).strip()
            if not invoice_no:
                raise ValueError("Invoice number is required")
            if not content:
                raise ValueError("Generate a bill first")
            ensure_dir(BILLS_DIR)
            path = os.path.join(BILLS_DIR, f"{invoice_no}.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content + "\n")
            messagebox.showinfo("Success", f"Bill saved: {path}")
        except Exception as ex:
            messagebox.showerror("Error", str(ex))


class BillViewerWindow(BaseWindow):
    def __init__(self, master: tk.Tk, bill_repo: BillRepository) -> None:
        super().__init__(master, "Bill Viewer")
        self.bill_repo = bill_repo
        self._build()
        self._refresh()

    def _build(self) -> None:
        self.geometry("1000x600")

        top = ttk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.var_search = tk.StringVar()
        ttk.Label(top, text="Search Invoice").pack(side=tk.LEFT, padx=6)
        ttk.Entry(top, textvariable=self.var_search, width=30).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Search", command=self._refresh).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Show All", command=self._show_all).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Open Bill File", command=self._open_bill_file).pack(side=tk.RIGHT, padx=6)

        mid = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        mid.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.Labelframe(mid, text="Bills")
        right = ttk.Labelframe(mid, text="Bill Details")
        mid.add(left, weight=2)
        mid.add(right, weight=3)

        self.table = ttk.Treeview(left, columns=("invoice_no", "customer_name", "customer_contact", "total", "created_at"), show="headings")
        for c, w in [("invoice_no", 140), ("customer_name", 160), ("customer_contact", 140), ("total", 90), ("created_at", 160)]:
            self.table.heading(c, text=c.upper())
            self.table.column(c, width=w, anchor="w")
        self.table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.table.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.table.configure(yscrollcommand=sb.set)
        self.table.bind("<<TreeviewSelect>>", self._on_select)

        self.txt = tk.Text(right)
        self.txt.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _show_all(self) -> None:
        self.var_search.set("")
        self._refresh()

    def _refresh(self) -> None:
        for i in self.table.get_children():
            self.table.delete(i)
        rows = self.bill_repo.list_invoices(self.var_search.get())
        for r in rows:
            self.table.insert("", tk.END, values=r)

    def _on_select(self, _evt: Any) -> None:
        sel = self.table.selection()
        if not sel:
            return
        values = self.table.item(sel[0], "values")
        if not values:
            return
        invoice_no = str(values[0])
        bill = self.bill_repo.get_bill(invoice_no)
        self.txt.delete("1.0", tk.END)
        if not bill:
            return
        lines: List[str] = []
        lines.append("BILL (from database)")
        lines.append(f"Invoice No: {bill['invoice_no']}")
        lines.append(f"Date: {bill['created_at']}")
        lines.append(f"Customer: {bill['customer_name']}")
        lines.append(f"Contact: {bill['customer_contact']}")
        lines.append("-" * 60)
        lines.append(f"{'Product':25} {'Price':>10} {'Qty':>6} {'Total':>12}")
        lines.append("-" * 60)
        for it in bill["items"]:
            _pid, name, price, qty, total = it
            pname = (str(name)[:25]).ljust(25)
            lines.append(f"{pname} {float(price):>10.2f} {int(qty):>6d} {float(total):>12.2f}")
        lines.append("-" * 60)
        lines.append(f"{'Grand Total':>45} {float(bill['total']):>12.2f}")
        self.txt.insert("1.0", "\n".join(lines))

    def _open_bill_file(self) -> None:
        ensure_dir(BILLS_DIR)
        path = filedialog.askopenfilename(
            title="Open Bill File",
            initialdir=BILLS_DIR,
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.txt.delete("1.0", tk.END)
            self.txt.insert("1.0", content)
        except Exception as ex:
            messagebox.showerror("Error", str(ex))


class Dashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1100x650")
        self.minsize(1000, 600)

        ensure_dir(BILLS_DIR)

        self.db = Database(DB_FILE)
        self.emp_repo = EmployeeRepository(self.db)
        self.sup_repo = SupplierRepository(self.db)
        self.cat_repo = CategoryRepository(self.db)
        self.prod_repo = ProductRepository(self.db)
        self.bill_repo = BillRepository(self.db)
        self.img_mgr = ImageManager()

        self._build()
        self._tick()

    def _build(self) -> None:
        header = ttk.Frame(self)
        header.pack(side=tk.TOP, fill=tk.X)

        self.lbl_title = ttk.Label(header, text="Inventory Management System", font=("Arial", 18, "bold"))
        self.lbl_title.pack(side=tk.LEFT, padx=10, pady=10)

        self.lbl_time = ttk.Label(header, text="", font=("Arial", 11))
        self.lbl_time.pack(side=tk.RIGHT, padx=10, pady=10)

        body = ttk.Frame(self)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        btn_style = {"width": 22}
        ttk.Button(left, text="Employees", command=self._open_employees, **btn_style).pack(pady=6)
        ttk.Button(left, text="Suppliers", command=self._open_suppliers, **btn_style).pack(pady=6)
        ttk.Button(left, text="Categories", command=self._open_categories, **btn_style).pack(pady=6)
        ttk.Button(left, text="Products", command=self._open_products, **btn_style).pack(pady=6)
        ttk.Button(left, text="Billing", command=self._open_billing, **btn_style).pack(pady=6)
        ttk.Button(left, text="Bill Viewer", command=self._open_bill_viewer, **btn_style).pack(pady=6)
        ttk.Button(left, text="Exit", command=self.destroy, **btn_style).pack(pady=6)

        right = ttk.Frame(body)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        stats = ttk.LabelFrame(right, text="Dashboard")
        stats.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))

        self.var_emp_count = tk.StringVar(value="0")
        self.var_sup_count = tk.StringVar(value="0")
        self.var_cat_count = tk.StringVar(value="0")
        self.var_prod_count = tk.StringVar(value="0")
        self.var_bill_count = tk.StringVar(value="0")

        self._stat_tile(stats, "Employees", self.var_emp_count, 0)
        self._stat_tile(stats, "Suppliers", self.var_sup_count, 1)
        self._stat_tile(stats, "Categories", self.var_cat_count, 2)
        self._stat_tile(stats, "Products", self.var_prod_count, 3)
        self._stat_tile(stats, "Bills", self.var_bill_count, 4)

        media = ttk.LabelFrame(right, text="Images")
        media.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(media, bg="white")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        img_path = os.path.join(os.getcwd(), "dashboard.png")
        self._dashboard_img = self.img_mgr.load(img_path, (600, 300))
        self._draw_image_or_placeholder()

        footer = ttk.Frame(self)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(footer, text="Bills directory: " + os.path.abspath(BILLS_DIR)).pack(side=tk.LEFT, padx=10, pady=6)

        self._refresh_counts()

    def _draw_image_or_placeholder(self) -> None:
        self.canvas.delete("all")
        w = self.canvas.winfo_width() or 800
        h = self.canvas.winfo_height() or 400
        if self._dashboard_img is not None:
            self.canvas.create_image(w // 2, h // 2, image=self._dashboard_img, anchor="center")
        else:
            self.canvas.create_rectangle(20, 20, w - 20, h - 20, outline="gray")
            self.canvas.create_text(
                w // 2,
                h // 2,
                text="Place an image named 'dashboard.png' in the current folder\n(PIL required for image support)",
                fill="black",
                font=("Arial", 12),
                justify="center",
            )

    def _stat_tile(self, parent: ttk.LabelFrame, title: str, var: tk.StringVar, col: int) -> None:
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=col, padx=10, pady=10, sticky="nsew")
        ttk.Label(frame, text=title, font=("Arial", 11, "bold")).pack()
        ttk.Label(frame, textvariable=var, font=("Arial", 16, "bold")).pack()
        parent.grid_columnconfigure(col, weight=1)

    def _tick(self) -> None:
        self.lbl_time.config(text=f"{today_str()}  {datetime.now().strftime('%H:%M:%S')}")
        self._refresh_counts()
        self.after(1000, self._tick)

    def _refresh_counts(self) -> None:
        self.var_emp_count.set(str(self.db.count("employee")))
        self.var_sup_count.set(str(self.db.count("supplier")))
        self.var_cat_count.set(str(self.db.count("category")))
        self.var_prod_count.set(str(self.db.count("product")))
        self.var_bill_count.set(str(self.db.count("bill")))

    def _open_employees(self) -> None:
        EmployeeWindow(self, self.emp_repo)

    def _open_suppliers(self) -> None:
        SupplierWindow(self, self.sup_repo)

    def _open_categories(self) -> None:
        CategoryWindow(self, self.cat_repo)

    def _open_products(self) -> None:
        ProductWindow(self, self.prod_repo, self.cat_repo, self.sup_repo)

    def _open_billing(self) -> None:
        BillingWindow(self, self.prod_repo, self.bill_repo)

    def _open_bill_viewer(self) -> None:
        BillViewerWindow(self, self.bill_repo)


def main() -> None:
    app = Dashboard()
    app.bind("<Configure>", lambda _e: app._draw_image_or_placeholder())
    app.mainloop()


if __name__ == "__main__":
    main()