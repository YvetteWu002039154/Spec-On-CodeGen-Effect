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
class Bill:
    invoice_no: str
    customer_name: str
    customer_contact: str
    date_time: str
    total: float
    discount: float
    net: float
    items_json: str


class Database:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def _create_tables(self) -> None:
        cur = self._conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS employee(
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
                salary REAL NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS supplier(
                invoice TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                desc TEXT NOT NULL
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS category(
                cat_id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS product(
                pid TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                supplier TEXT NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                qty INTEGER NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY(category) REFERENCES category(name) ON UPDATE CASCADE ON DELETE RESTRICT,
                FOREIGN KEY(supplier) REFERENCES supplier(name) ON UPDATE CASCADE ON DELETE RESTRICT
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bill(
                invoice_no TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_contact TEXT NOT NULL,
                date_time TEXT NOT NULL,
                total REAL NOT NULL,
                discount REAL NOT NULL,
                net REAL NOT NULL,
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


class EmployeeRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, e: Employee) -> None:
        self._validate(e)
        self._db.execute(
            """
            INSERT INTO employee(emp_id,name,email,gender,contact,dob,doj,password,usertype,address,salary)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                e.emp_id,
                e.name,
                e.email,
                e.gender,
                e.contact,
                e.dob,
                e.doj,
                e.password,
                e.usertype,
                e.address,
                float(e.salary),
            ),
        )

    def update(self, e: Employee) -> None:
        self._validate(e)
        self._db.execute(
            """
            UPDATE employee SET name=?,email=?,gender=?,contact=?,dob=?,doj=?,password=?,usertype=?,address=?,salary=?
            WHERE emp_id=?
            """,
            (
                e.name,
                e.email,
                e.gender,
                e.contact,
                e.dob,
                e.doj,
                e.password,
                e.usertype,
                e.address,
                float(e.salary),
                e.emp_id,
            ),
        )

    def delete(self, emp_id: str) -> None:
        if not emp_id.strip():
            raise ValueError("Employee ID is required")
        self._db.execute("DELETE FROM employee WHERE emp_id=?", (emp_id.strip(),))

    def get(self, emp_id: str) -> Optional[Employee]:
        rows = self._db.query("SELECT * FROM employee WHERE emp_id=?", (emp_id.strip(),))
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
            salary=float(r["salary"]),
        )

    def list_all(self) -> List[Employee]:
        rows = self._db.query("SELECT * FROM employee ORDER BY name")
        out: List[Employee] = []
        for r in rows:
            out.append(
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
                    salary=float(r["salary"]),
                )
            )
        return out

    def search(self, field: str, value: str) -> List[Employee]:
        allowed = {"emp_id", "name", "email", "contact", "usertype"}
        if field not in allowed:
            raise ValueError("Invalid search field")
        value = value.strip()
        rows = self._db.query(f"SELECT * FROM employee WHERE {field} LIKE ? ORDER BY name", (f"%{value}%",))
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
                salary=float(r["salary"]),
            )
            for r in rows
        ]

    def _validate(self, e: Employee) -> None:
        if not e.emp_id.strip():
            raise ValueError("Employee ID is required")
        if not e.name.strip():
            raise ValueError("Employee name is required")
        if not e.email.strip():
            raise ValueError("Employee email is required")
        if not e.gender.strip():
            raise ValueError("Employee gender is required")
        if not e.contact.strip():
            raise ValueError("Employee contact is required")
        if not e.dob.strip():
            raise ValueError("Employee DOB is required")
        if not e.doj.strip():
            raise ValueError("Employee DOJ is required")
        if not e.password.strip():
            raise ValueError("Employee password is required")
        if not e.usertype.strip():
            raise ValueError("Employee usertype is required")
        if not e.address.strip():
            raise ValueError("Employee address is required")
        if float(e.salary) < 0:
            raise ValueError("Employee salary must be non-negative")


class SupplierRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, s: Supplier) -> None:
        self._validate(s)
        self._db.execute(
            "INSERT INTO supplier(invoice,name,contact,desc) VALUES(?,?,?,?)",
            (s.invoice, s.name, s.contact, s.desc),
        )

    def update(self, s: Supplier) -> None:
        self._validate(s)
        self._db.execute(
            "UPDATE supplier SET name=?,contact=?,desc=? WHERE invoice=?",
            (s.name, s.contact, s.desc, s.invoice),
        )

    def delete(self, invoice: str) -> None:
        if not invoice.strip():
            raise ValueError("Supplier invoice is required")
        self._db.execute("DELETE FROM supplier WHERE invoice=?", (invoice.strip(),))

    def get(self, invoice: str) -> Optional[Supplier]:
        rows = self._db.query("SELECT * FROM supplier WHERE invoice=?", (invoice.strip(),))
        if not rows:
            return None
        r = rows[0]
        return Supplier(invoice=r["invoice"], name=r["name"], contact=r["contact"], desc=r["desc"])

    def list_all(self) -> List[Supplier]:
        rows = self._db.query("SELECT * FROM supplier ORDER BY name")
        return [Supplier(invoice=r["invoice"], name=r["name"], contact=r["contact"], desc=r["desc"]) for r in rows]

    def search(self, field: str, value: str) -> List[Supplier]:
        allowed = {"invoice", "name", "contact"}
        if field not in allowed:
            raise ValueError("Invalid search field")
        value = value.strip()
        rows = self._db.query(f"SELECT * FROM supplier WHERE {field} LIKE ? ORDER BY name", (f"%{value}%",))
        return [Supplier(invoice=r["invoice"], name=r["name"], contact=r["contact"], desc=r["desc"]) for r in rows]

    def list_names(self) -> List[str]:
        rows = self._db.query("SELECT name FROM supplier ORDER BY name")
        return [r["name"] for r in rows]

    def _validate(self, s: Supplier) -> None:
        if not s.invoice.strip():
            raise ValueError("Supplier invoice is required")
        if not s.name.strip():
            raise ValueError("Supplier name is required")
        if not s.contact.strip():
            raise ValueError("Supplier contact is required")
        if not s.desc.strip():
            raise ValueError("Supplier description is required")


class CategoryRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, c: Category) -> None:
        self._validate(c)
        self._db.execute("INSERT INTO category(cat_id,name) VALUES(?,?)", (c.cat_id, c.name))

    def update(self, c: Category) -> None:
        self._validate(c)
        self._db.execute("UPDATE category SET name=? WHERE cat_id=?", (c.name, c.cat_id))

    def delete(self, cat_id: str) -> None:
        if not cat_id.strip():
            raise ValueError("Category ID is required")
        self._db.execute("DELETE FROM category WHERE cat_id=?", (cat_id.strip(),))

    def get(self, cat_id: str) -> Optional[Category]:
        rows = self._db.query("SELECT * FROM category WHERE cat_id=?", (cat_id.strip(),))
        if not rows:
            return None
        r = rows[0]
        return Category(cat_id=r["cat_id"], name=r["name"])

    def list_all(self) -> List[Category]:
        rows = self._db.query("SELECT * FROM category ORDER BY name")
        return [Category(cat_id=r["cat_id"], name=r["name"]) for r in rows]

    def search(self, field: str, value: str) -> List[Category]:
        allowed = {"cat_id", "name"}
        if field not in allowed:
            raise ValueError("Invalid search field")
        value = value.strip()
        rows = self._db.query(f"SELECT * FROM category WHERE {field} LIKE ? ORDER BY name", (f"%{value}%",))
        return [Category(cat_id=r["cat_id"], name=r["name"]) for r in rows]

    def list_names(self) -> List[str]:
        rows = self._db.query("SELECT name FROM category ORDER BY name")
        return [r["name"] for r in rows]

    def _validate(self, c: Category) -> None:
        if not c.cat_id.strip():
            raise ValueError("Category ID is required")
        if not c.name.strip():
            raise ValueError("Category name is required")


class ProductRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, p: Product) -> None:
        self._validate(p)
        self._db.execute(
            """
            INSERT INTO product(pid,category,supplier,name,price,qty,status)
            VALUES(?,?,?,?,?,?,?)
            """,
            (p.pid, p.category, p.supplier, p.name, float(p.price), int(p.qty), p.status),
        )

    def update(self, p: Product) -> None:
        self._validate(p)
        self._db.execute(
            """
            UPDATE product SET category=?,supplier=?,name=?,price=?,qty=?,status=?
            WHERE pid=?
            """,
            (p.category, p.supplier, p.name, float(p.price), int(p.qty), p.status, p.pid),
        )

    def delete(self, pid: str) -> None:
        if not pid.strip():
            raise ValueError("Product ID is required")
        self._db.execute("DELETE FROM product WHERE pid=?", (pid.strip(),))

    def get(self, pid: str) -> Optional[Product]:
        rows = self._db.query("SELECT * FROM product WHERE pid=?", (pid.strip(),))
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

    def list_all(self) -> List[Product]:
        rows = self._db.query("SELECT * FROM product ORDER BY name")
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

    def search(self, field: str, value: str) -> List[Product]:
        allowed = {"pid", "name", "category", "supplier", "status"}
        if field not in allowed:
            raise ValueError("Invalid search field")
        value = value.strip()
        rows = self._db.query(f"SELECT * FROM product WHERE {field} LIKE ? ORDER BY name", (f"%{value}%",))
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
        pid = pid.strip()
        if not pid:
            raise ValueError("Product ID is required")
        if delta_qty == 0:
            return
        row = self._db.query("SELECT qty FROM product WHERE pid=?", (pid,))
        if not row:
            raise ValueError("Product not found")
        current = int(row[0]["qty"])
        new_qty = current + int(delta_qty)
        if new_qty < 0:
            raise ValueError("Insufficient stock")
        self._db.execute("UPDATE product SET qty=? WHERE pid=?", (new_qty, pid))

    def _validate(self, p: Product) -> None:
        if not p.pid.strip():
            raise ValueError("Product ID is required")
        if not p.category.strip():
            raise ValueError("Product category is required")
        if not p.supplier.strip():
            raise ValueError("Product supplier is required")
        if not p.name.strip():
            raise ValueError("Product name is required")
        if float(p.price) < 0:
            raise ValueError("Product price must be non-negative")
        if int(p.qty) < 0:
            raise ValueError("Product quantity must be non-negative")
        if not p.status.strip():
            raise ValueError("Product status is required")


class BillRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, b: Bill) -> None:
        self._validate(b)
        self._db.execute(
            """
            INSERT INTO bill(invoice_no,customer_name,customer_contact,date_time,total,discount,net,items_json)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                b.invoice_no,
                b.customer_name,
                b.customer_contact,
                b.date_time,
                float(b.total),
                float(b.discount),
                float(b.net),
                b.items_json,
            ),
        )

    def get(self, invoice_no: str) -> Optional[Bill]:
        rows = self._db.query("SELECT * FROM bill WHERE invoice_no=?", (invoice_no.strip(),))
        if not rows:
            return None
        r = rows[0]
        return Bill(
            invoice_no=r["invoice_no"],
            customer_name=r["customer_name"],
            customer_contact=r["customer_contact"],
            date_time=r["date_time"],
            total=float(r["total"]),
            discount=float(r["discount"]),
            net=float(r["net"]),
            items_json=r["items_json"],
        )

    def list_all(self) -> List[Bill]:
        rows = self._db.query("SELECT * FROM bill ORDER BY date_time DESC")
        return [
            Bill(
                invoice_no=r["invoice_no"],
                customer_name=r["customer_name"],
                customer_contact=r["customer_contact"],
                date_time=r["date_time"],
                total=float(r["total"]),
                discount=float(r["discount"]),
                net=float(r["net"]),
                items_json=r["items_json"],
            )
            for r in rows
        ]

    def search_by_invoice(self, invoice_no: str) -> List[Bill]:
        invoice_no = invoice_no.strip()
        rows = self._db.query("SELECT * FROM bill WHERE invoice_no LIKE ? ORDER BY date_time DESC", (f"%{invoice_no}%",))
        return [
            Bill(
                invoice_no=r["invoice_no"],
                customer_name=r["customer_name"],
                customer_contact=r["customer_contact"],
                date_time=r["date_time"],
                total=float(r["total"]),
                discount=float(r["discount"]),
                net=float(r["net"]),
                items_json=r["items_json"],
            )
            for r in rows
        ]

    def _validate(self, b: Bill) -> None:
        if not b.invoice_no.strip():
            raise ValueError("Invoice number is required")
        if not b.customer_name.strip():
            raise ValueError("Customer name is required")
        if not b.customer_contact.strip():
            raise ValueError("Customer contact is required")
        if not b.date_time.strip():
            raise ValueError("Date/time is required")
        if float(b.total) < 0:
            raise ValueError("Total must be non-negative")
        if float(b.discount) < 0:
            raise ValueError("Discount must be non-negative")
        if float(b.net) < 0:
            raise ValueError("Net must be non-negative")
        if not b.items_json.strip():
            raise ValueError("Bill items are required")


class InventoryService:
    def __init__(
        self,
        employees: EmployeeRepository,
        suppliers: SupplierRepository,
        categories: CategoryRepository,
        products: ProductRepository,
        bills: BillRepository,
    ) -> None:
        self.employees = employees
        self.suppliers = suppliers
        self.categories = categories
        self.products = products
        self.bills = bills

    def dashboard_counts(self) -> Dict[str, int]:
        return {
            "employees": len(self.employees.list_all()),
            "suppliers": len(self.suppliers.list_all()),
            "categories": len(self.categories.list_all()),
            "products": len(self.products.list_all()),
            "bills": len(self.bills.list_all()),
        }


class BaseManagerWindow(tk.Toplevel):
    def __init__(self, master: tk.Tk, title: str) -> None:
        super().__init__(master)
        self.title(title)
        self.geometry("1000x600")
        self.minsize(900, 550)
        self.transient(master)
        self.grab_set()

        self._top = tk.Frame(self, bd=2, relief=tk.RIDGE)
        self._top.pack(side=tk.TOP, fill=tk.X, padx=8, pady=8)

        self._body = tk.Frame(self)
        self._body.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=8)

        self._left = tk.LabelFrame(self._body, text="Form", padx=8, pady=8)
        self._left.pack(side=tk.LEFT, fill=tk.Y)

        self._right = tk.LabelFrame(self._body, text="Records", padx=8, pady=8)
        self._right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        self.grab_release()
        self.destroy()


class EmployeeManagerWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, service: InventoryService) -> None:
        super().__init__(master, "Employee Management")
        self._service = service

        tk.Label(self._top, text="Employee Management", font=("Arial", 16, "bold")).pack(side=tk.LEFT)

        self._search_by = tk.StringVar(value="name")
        self._search_txt = tk.StringVar()

        tk.Label(self._top, text="Search By:").pack(side=tk.LEFT, padx=(20, 4))
        ttk.Combobox(self._top, textvariable=self._search_by, values=["emp_id", "name", "email", "contact", "usertype"], width=12, state="readonly").pack(side=tk.LEFT)
        tk.Entry(self._top, textvariable=self._search_txt, width=25).pack(side=tk.LEFT, padx=6)
        tk.Button(self._top, text="Search", width=10, command=self._search).pack(side=tk.LEFT, padx=4)
        tk.Button(self._top, text="Show All", width=10, command=self._refresh).pack(side=tk.LEFT, padx=4)

        self._vars: Dict[str, tk.StringVar] = {
            "emp_id": tk.StringVar(),
            "name": tk.StringVar(),
            "email": tk.StringVar(),
            "gender": tk.StringVar(value="Select"),
            "contact": tk.StringVar(),
            "dob": tk.StringVar(),
            "doj": tk.StringVar(),
            "password": tk.StringVar(),
            "usertype": tk.StringVar(value="Select"),
            "salary": tk.StringVar(),
        }
        self._address = tk.Text(self._left, width=28, height=4)

        self._build_form()
        self._build_table()
        self._refresh()

    def _build_form(self) -> None:
        row = 0
        tk.Label(self._left, text="Emp ID").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._vars["emp_id"], width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Name").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._vars["name"], width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Email").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._vars["email"], width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Gender").grid(row=row, column=0, sticky="w")
        ttk.Combobox(self._left, textvariable=self._vars["gender"], values=["Select", "Male", "Female", "Other"], width=22, state="readonly").grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Contact").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._vars["contact"], width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="DOB (YYYY-MM-DD)").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._vars["dob"], width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="DOJ (YYYY-MM-DD)").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._vars["doj"], width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Password").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._vars["password"], width=25, show="*").grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="User Type").grid(row=row, column=0, sticky="w")
        ttk.Combobox(self._left, textvariable=self._vars["usertype"], values=["Select", "Admin", "Employee"], width=22, state="readonly").grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Address").grid(row=row, column=0, sticky="nw")
        self._address.grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Salary").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._vars["salary"], width=25).grid(row=row, column=1, pady=3)
        row += 1

        btns = tk.Frame(self._left)
        btns.grid(row=row, column=0, columnspan=2, pady=10)
        tk.Button(btns, text="Save", width=10, command=self._save).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Update", width=10, command=self._update).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Delete", width=10, command=self._delete).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Clear", width=10, command=self._clear).pack(side=tk.LEFT, padx=4)

    def _build_table(self) -> None:
        cols = ("emp_id", "name", "email", "gender", "contact", "dob", "doj", "usertype", "salary")
        self._tree = ttk.Treeview(self._right, columns=cols, show="headings")
        for c in cols:
            self._tree.heading(c, text=c)
            self._tree.column(c, width=110, anchor="w")
        self._tree.column("email", width=160)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb_y = ttk.Scrollbar(self._right, orient=tk.VERTICAL, command=self._tree.yview)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.configure(yscrollcommand=sb_y.set)

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def _on_select(self, _evt: Any) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        values = self._tree.item(sel[0], "values")
        emp_id = str(values[0])
        e = self._service.employees.get(emp_id)
        if not e:
            return
        self._vars["emp_id"].set(e.emp_id)
        self._vars["name"].set(e.name)
        self._vars["email"].set(e.email)
        self._vars["gender"].set(e.gender)
        self._vars["contact"].set(e.contact)
        self._vars["dob"].set(e.dob)
        self._vars["doj"].set(e.doj)
        self._vars["password"].set(e.password)
        self._vars["usertype"].set(e.usertype)
        self._vars["salary"].set(str(e.salary))
        self._address.delete("1.0", tk.END)
        self._address.insert(tk.END, e.address)

    def _clear(self) -> None:
        for k, v in self._vars.items():
            if k in ("gender", "usertype"):
                v.set("Select")
            else:
                v.set("")
        self._address.delete("1.0", tk.END)
        self._tree.selection_remove(self._tree.selection())

    def _read_employee(self) -> Employee:
        address = self._address.get("1.0", tk.END).strip()
        gender = self._vars["gender"].get().strip()
        usertype = self._vars["usertype"].get().strip()
        if gender == "Select":
            gender = ""
        if usertype == "Select":
            usertype = ""
        salary_str = self._vars["salary"].get().strip()
        salary = float(salary_str) if salary_str else 0.0
        return Employee(
            emp_id=self._vars["emp_id"].get().strip(),
            name=self._vars["name"].get().strip(),
            email=self._vars["email"].get().strip(),
            gender=gender,
            contact=self._vars["contact"].get().strip(),
            dob=self._vars["dob"].get().strip(),
            doj=self._vars["doj"].get().strip(),
            password=self._vars["password"].get().strip(),
            usertype=usertype,
            address=address,
            salary=salary,
        )

    def _save(self) -> None:
        try:
            e = self._read_employee()
            self._service.employees.add(e)
            messagebox.showinfo("Success", "Employee added successfully", parent=self)
            self._refresh()
            self._clear()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Database error: {ex}", parent=self)
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def _update(self) -> None:
        try:
            e = self._read_employee()
            if not self._service.employees.get(e.emp_id):
                raise ValueError("Employee not found")
            self._service.employees.update(e)
            messagebox.showinfo("Success", "Employee updated successfully", parent=self)
            self._refresh()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def _delete(self) -> None:
        try:
            emp_id = self._vars["emp_id"].get().strip()
            if not emp_id:
                raise ValueError("Employee ID is required")
            if not messagebox.askyesno("Confirm", "Delete selected employee?", parent=self):
                return
            self._service.employees.delete(emp_id)
            messagebox.showinfo("Success", "Employee deleted successfully", parent=self)
            self._refresh()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def _refresh(self) -> None:
        for i in self._tree.get_children():
            self._tree.delete(i)
        for e in self._service.employees.list_all():
            self._tree.insert("", tk.END, values=(e.emp_id, e.name, e.email, e.gender, e.contact, e.dob, e.doj, e.usertype, e.salary))

    def _search(self) -> None:
        try:
            field = self._search_by.get()
            value = self._search_txt.get()
            rows = self._service.employees.search(field, value)
            for i in self._tree.get_children():
                self._tree.delete(i)
            for e in rows:
                self._tree.insert("", tk.END, values=(e.emp_id, e.name, e.email, e.gender, e.contact, e.dob, e.doj, e.usertype, e.salary))
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)


class SupplierManagerWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, service: InventoryService) -> None:
        super().__init__(master, "Supplier Management")
        self._service = service

        tk.Label(self._top, text="Supplier Management", font=("Arial", 16, "bold")).pack(side=tk.LEFT)

        self._search_by = tk.StringVar(value="name")
        self._search_txt = tk.StringVar()

        tk.Label(self._top, text="Search By:").pack(side=tk.LEFT, padx=(20, 4))
        ttk.Combobox(self._top, textvariable=self._search_by, values=["invoice", "name", "contact"], width=12, state="readonly").pack(side=tk.LEFT)
        tk.Entry(self._top, textvariable=self._search_txt, width=25).pack(side=tk.LEFT, padx=6)
        tk.Button(self._top, text="Search", width=10, command=self._search).pack(side=tk.LEFT, padx=4)
        tk.Button(self._top, text="Show All", width=10, command=self._refresh).pack(side=tk.LEFT, padx=4)

        self._invoice = tk.StringVar()
        self._name = tk.StringVar()
        self._contact = tk.StringVar()
        self._desc = tk.Text(self._left, width=28, height=6)

        self._build_form()
        self._build_table()
        self._refresh()

    def _build_form(self) -> None:
        row = 0
        tk.Label(self._left, text="Invoice").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._invoice, width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Name").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._name, width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Contact").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._contact, width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Description").grid(row=row, column=0, sticky="nw")
        self._desc.grid(row=row, column=1, pady=3)
        row += 1

        btns = tk.Frame(self._left)
        btns.grid(row=row, column=0, columnspan=2, pady=10)
        tk.Button(btns, text="Save", width=10, command=self._save).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Update", width=10, command=self._update).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Delete", width=10, command=self._delete).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Clear", width=10, command=self._clear).pack(side=tk.LEFT, padx=4)

    def _build_table(self) -> None:
        cols = ("invoice", "name", "contact", "desc")
        self._tree = ttk.Treeview(self._right, columns=cols, show="headings")
        for c in cols:
            self._tree.heading(c, text=c)
            self._tree.column(c, width=160, anchor="w")
        self._tree.column("desc", width=300)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb_y = ttk.Scrollbar(self._right, orient=tk.VERTICAL, command=self._tree.yview)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.configure(yscrollcommand=sb_y.set)

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def _on_select(self, _evt: Any) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        values = self._tree.item(sel[0], "values")
        invoice = str(values[0])
        s = self._service.suppliers.get(invoice)
        if not s:
            return
        self._invoice.set(s.invoice)
        self._name.set(s.name)
        self._contact.set(s.contact)
        self._desc.delete("1.0", tk.END)
        self._desc.insert(tk.END, s.desc)

    def _clear(self) -> None:
        self._invoice.set("")
        self._name.set("")
        self._contact.set("")
        self._desc.delete("1.0", tk.END)
        self._tree.selection_remove(self._tree.selection())

    def _read_supplier(self) -> Supplier:
        return Supplier(
            invoice=self._invoice.get().strip(),
            name=self._name.get().strip(),
            contact=self._contact.get().strip(),
            desc=self._desc.get("1.0", tk.END).strip(),
        )

    def _save(self) -> None:
        try:
            s = self._read_supplier()
            self._service.suppliers.add(s)
            messagebox.showinfo("Success", "Supplier added successfully", parent=self)
            self._refresh()
            self._clear()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Database error: {ex}", parent=self)
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def _update(self) -> None:
        try:
            s = self._read_supplier()
            if not self._service.suppliers.get(s.invoice):
                raise ValueError("Supplier not found")
            self._service.suppliers.update(s)
            messagebox.showinfo("Success", "Supplier updated successfully", parent=self)
            self._refresh()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def _delete(self) -> None:
        try:
            invoice = self._invoice.get().strip()
            if not invoice:
                raise ValueError("Invoice is required")
            if not messagebox.askyesno("Confirm", "Delete selected supplier?", parent=self):
                return
            self._service.suppliers.delete(invoice)
            messagebox.showinfo("Success", "Supplier deleted successfully", parent=self)
            self._refresh()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def _refresh(self) -> None:
        for i in self._tree.get_children():
            self._tree.delete(i)
        for s in self._service.suppliers.list_all():
            self._tree.insert("", tk.END, values=(s.invoice, s.name, s.contact, s.desc))

    def _search(self) -> None:
        try:
            field = self._search_by.get()
            value = self._search_txt.get()
            rows = self._service.suppliers.search(field, value)
            for i in self._tree.get_children():
                self._tree.delete(i)
            for s in rows:
                self._tree.insert("", tk.END, values=(s.invoice, s.name, s.contact, s.desc))
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)


class CategoryManagerWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, service: InventoryService) -> None:
        super().__init__(master, "Category Management")
        self._service = service

        tk.Label(self._top, text="Category Management", font=("Arial", 16, "bold")).pack(side=tk.LEFT)

        self._search_by = tk.StringVar(value="name")
        self._search_txt = tk.StringVar()

        tk.Label(self._top, text="Search By:").pack(side=tk.LEFT, padx=(20, 4))
        ttk.Combobox(self._top, textvariable=self._search_by, values=["cat_id", "name"], width=12, state="readonly").pack(side=tk.LEFT)
        tk.Entry(self._top, textvariable=self._search_txt, width=25).pack(side=tk.LEFT, padx=6)
        tk.Button(self._top, text="Search", width=10, command=self._search).pack(side=tk.LEFT, padx=4)
        tk.Button(self._top, text="Show All", width=10, command=self._refresh).pack(side=tk.LEFT, padx=4)

        self._cat_id = tk.StringVar()
        self._name = tk.StringVar()

        self._build_form()
        self._build_table()
        self._refresh()

    def _build_form(self) -> None:
        row = 0
        tk.Label(self._left, text="Category ID").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._cat_id, width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Name").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._name, width=25).grid(row=row, column=1, pady=3)
        row += 1

        btns = tk.Frame(self._left)
        btns.grid(row=row, column=0, columnspan=2, pady=10)
        tk.Button(btns, text="Save", width=10, command=self._save).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Update", width=10, command=self._update).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Delete", width=10, command=self._delete).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Clear", width=10, command=self._clear).pack(side=tk.LEFT, padx=4)

    def _build_table(self) -> None:
        cols = ("cat_id", "name")
        self._tree = ttk.Treeview(self._right, columns=cols, show="headings")
        for c in cols:
            self._tree.heading(c, text=c)
            self._tree.column(c, width=220, anchor="w")
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb_y = ttk.Scrollbar(self._right, orient=tk.VERTICAL, command=self._tree.yview)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.configure(yscrollcommand=sb_y.set)

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def _on_select(self, _evt: Any) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        values = self._tree.item(sel[0], "values")
        cat_id = str(values[0])
        c = self._service.categories.get(cat_id)
        if not c:
            return
        self._cat_id.set(c.cat_id)
        self._name.set(c.name)

    def _clear(self) -> None:
        self._cat_id.set("")
        self._name.set("")
        self._tree.selection_remove(self._tree.selection())

    def _read_category(self) -> Category:
        return Category(cat_id=self._cat_id.get().strip(), name=self._name.get().strip())

    def _save(self) -> None:
        try:
            c = self._read_category()
            self._service.categories.add(c)
            messagebox.showinfo("Success", "Category added successfully", parent=self)
            self._refresh()
            self._clear()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Database error: {ex}", parent=self)
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def _update(self) -> None:
        try:
            c = self._read_category()
            if not self._service.categories.get(c.cat_id):
                raise ValueError("Category not found")
            self._service.categories.update(c)
            messagebox.showinfo("Success", "Category updated successfully", parent=self)
            self._refresh()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def _delete(self) -> None:
        try:
            cat_id = self._cat_id.get().strip()
            if not cat_id:
                raise ValueError("Category ID is required")
            if not messagebox.askyesno("Confirm", "Delete selected category?", parent=self):
                return
            self._service.categories.delete(cat_id)
            messagebox.showinfo("Success", "Category deleted successfully", parent=self)
            self._refresh()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def _refresh(self) -> None:
        for i in self._tree.get_children():
            self._tree.delete(i)
        for c in self._service.categories.list_all():
            self._tree.insert("", tk.END, values=(c.cat_id, c.name))

    def _search(self) -> None:
        try:
            field = self._search_by.get()
            value = self._search_txt.get()
            rows = self._service.categories.search(field, value)
            for i in self._tree.get_children():
                self._tree.delete(i)
            for c in rows:
                self._tree.insert("", tk.END, values=(c.cat_id, c.name))
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)


class ProductManagerWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, service: InventoryService) -> None:
        super().__init__(master, "Product Management")
        self._service = service

        tk.Label(self._top, text="Product Management", font=("Arial", 16, "bold")).pack(side=tk.LEFT)

        self._search_by = tk.StringVar(value="name")
        self._search_txt = tk.StringVar()

        tk.Label(self._top, text="Search By:").pack(side=tk.LEFT, padx=(20, 4))
        ttk.Combobox(self._top, textvariable=self._search_by, values=["pid", "name", "category", "supplier", "status"], width=12, state="readonly").pack(side=tk.LEFT)
        tk.Entry(self._top, textvariable=self._search_txt, width=25).pack(side=tk.LEFT, padx=6)
        tk.Button(self._top, text="Search", width=10, command=self._search).pack(side=tk.LEFT, padx=4)
        tk.Button(self._top, text="Show All", width=10, command=self._refresh).pack(side=tk.LEFT, padx=4)

        self._pid = tk.StringVar()
        self._category = tk.StringVar(value="Select")
        self._supplier = tk.StringVar(value="Select")
        self._name = tk.StringVar()
        self._price = tk.StringVar()
        self._qty = tk.StringVar()
        self._status = tk.StringVar(value="Active")

        self._build_form()
        self._build_table()
        self._refresh()
        self._refresh_dropdowns()

    def _build_form(self) -> None:
        row = 0
        tk.Label(self._left, text="Product ID").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._pid, width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Category").grid(row=row, column=0, sticky="w")
        self._cat_cb = ttk.Combobox(self._left, textvariable=self._category, values=["Select"], width=22, state="readonly")
        self._cat_cb.grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Supplier").grid(row=row, column=0, sticky="w")
        self._sup_cb = ttk.Combobox(self._left, textvariable=self._supplier, values=["Select"], width=22, state="readonly")
        self._sup_cb.grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Name").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._name, width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Price").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._price, width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Quantity").grid(row=row, column=0, sticky="w")
        tk.Entry(self._left, textvariable=self._qty, width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(self._left, text="Status").grid(row=row, column=0, sticky="w")
        ttk.Combobox(self._left, textvariable=self._status, values=["Active", "Inactive"], width=22, state="readonly").grid(row=row, column=1, pady=3)
        row += 1

        btns = tk.Frame(self._left)
        btns.grid(row=row, column=0, columnspan=2, pady=10)
        tk.Button(btns, text="Save", width=10, command=self._save).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Update", width=10, command=self._update).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Delete", width=10, command=self._delete).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Clear", width=10, command=self._clear).pack(side=tk.LEFT, padx=4)
        tk.Button(btns, text="Reload Lists", width=12, command=self._refresh_dropdowns).pack(side=tk.LEFT, padx=4)

    def _build_table(self) -> None:
        cols = ("pid", "category", "supplier", "name", "price", "qty", "status")
        self._tree = ttk.Treeview(self._right, columns=cols, show="headings")
        for c in cols:
            self._tree.heading(c, text=c)
            self._tree.column(c, width=120, anchor="w")
        self._tree.column("name", width=180)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb_y = ttk.Scrollbar(self._right, orient=tk.VERTICAL, command=self._tree.yview)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.configure(yscrollcommand=sb_y.set)

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def _refresh_dropdowns(self) -> None:
        cats = ["Select"] + self._service.categories.list_names()
        sups = ["Select"] + self._service.suppliers.list_names()
        self._cat_cb["values"] = cats
        self._sup_cb["values"] = sups
        if self._category.get() not in cats:
            self._category.set("Select")
        if self._supplier.get() not in sups:
            self._supplier.set("Select")

    def _on_select(self, _evt: Any) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        values = self._tree.item(sel[0], "values")
        pid = str(values[0])
        p = self._service.products.get(pid)
        if not p:
            return
        self._pid.set(p.pid)
        self._category.set(p.category)
        self._supplier.set(p.supplier)
        self._name.set(p.name)
        self._price.set(str(p.price))
        self._qty.set(str(p.qty))
        self._status.set(p.status)

    def _clear(self) -> None:
        self._pid.set("")
        self._category.set("Select")
        self._supplier.set("Select")
        self._name.set("")
        self._price.set("")
        self._qty.set("")
        self._status.set("Active")
        self._tree.selection_remove(self._tree.selection())

    def _read_product(self) -> Product:
        category = self._category.get().strip()
        supplier = self._supplier.get().strip()
        if category == "Select":
            category = ""
        if supplier == "Select":
            supplier = ""
        price_str = self._price.get().strip()
        qty_str = self._qty.get().strip()
        price = float(price_str) if price_str else 0.0
        qty = int(qty_str) if qty_str else 0
        return Product(
            pid=self._pid.get().strip(),
            category=category,
            supplier=supplier,
            name=self._name.get().strip(),
            price=price,
            qty=qty,
            status=self._status.get().strip(),
        )

    def _save(self) -> None:
        try:
            p = self._read_product()
            self._service.products.add(p)
            messagebox.showinfo("Success", "Product added successfully", parent=self)
            self._refresh()
            self._clear()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Database error: {ex}", parent=self)
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def _update(self) -> None:
        try:
            p = self._read_product()
            if not self._service.products.get(p.pid):
                raise ValueError("Product not found")
            self._service.products.update(p)
            messagebox.showinfo("Success", "Product updated successfully", parent=self)
            self._refresh()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def _delete(self) -> None:
        try:
            pid = self._pid.get().strip()
            if not pid:
                raise ValueError("Product ID is required")
            if not messagebox.askyesno("Confirm", "Delete selected product?", parent=self):
                return
            self._service.products.delete(pid)
            messagebox.showinfo("Success", "Product deleted successfully", parent=self)
            self._refresh()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def _refresh(self) -> None:
        for i in self._tree.get_children():
            self._tree.delete(i)
        for p in self._service.products.list_all():
            self._tree.insert("", tk.END, values=(p.pid, p.category, p.supplier, p.name, p.price, p.qty, p.status))

    def _search(self) -> None:
        try:
            field = self._search_by.get()
            value = self._search_txt.get()
            rows = self._service.products.search(field, value)
            for i in self._tree.get_children():
                self._tree.delete(i)
            for p in rows:
                self._tree.insert("", tk.END, values=(p.pid, p.category, p.supplier, p.name, p.price, p.qty, p.status))
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)


class BillingWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, service: InventoryService) -> None:
        super().__init__(master, "Billing")
        self._service = service

        tk.Label(self._top, text="Billing", font=("Arial", 16, "bold")).pack(side=tk.LEFT)

        self._invoice_no = tk.StringVar(value=self._generate_invoice_no())
        self._cust_name = tk.StringVar()
        self._cust_contact = tk.StringVar()
        self._discount = tk.StringVar(value="0")

        self._product_search = tk.StringVar()
        self._selected_pid = tk.StringVar()
        self._selected_qty = tk.StringVar(value="1")

        self._cart: List[Tuple[str, str, float, int]] = []

        self._build_left()
        self._build_right()
        self._refresh_products()
        self._recalc_totals()

    def _build_left(self) -> None:
        f = self._left
        for w in f.winfo_children():
            w.destroy()

        row = 0
        tk.Label(f, text="Invoice No").grid(row=row, column=0, sticky="w")
        tk.Entry(f, textvariable=self._invoice_no, width=25, state="readonly").grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(f, text="Customer Name").grid(row=row, column=0, sticky="w")
        tk.Entry(f, textvariable=self._cust_name, width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(f, text="Customer Contact").grid(row=row, column=0, sticky="w")
        tk.Entry(f, textvariable=self._cust_contact, width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(f, text="Discount").grid(row=row, column=0, sticky="w")
        tk.Entry(f, textvariable=self._discount, width=25).grid(row=row, column=1, pady=3)
        row += 1

        sep = ttk.Separator(f, orient=tk.HORIZONTAL)
        sep.grid(row=row, column=0, columnspan=2, sticky="ew", pady=8)
        row += 1

        tk.Label(f, text="Find Product").grid(row=row, column=0, sticky="w")
        tk.Entry(f, textvariable=self._product_search, width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Button(f, text="Search Products", width=18, command=self._refresh_products).grid(row=row, column=0, columnspan=2, pady=4)
        row += 1

        tk.Label(f, text="Select Product").grid(row=row, column=0, sticky="w")
        self._product_cb = ttk.Combobox(f, textvariable=self._selected_pid, values=[], width=22, state="readonly")
        self._product_cb.grid(row=row, column=1, pady=3)
        row += 1

        tk.Label(f, text="Quantity").grid(row=row, column=0, sticky="w")
        tk.Entry(f, textvariable=self._selected_qty, width=25).grid(row=row, column=1, pady=3)
        row += 1

        tk.Button(f, text="Add to Cart", width=18, command=self._add_to_cart).grid(row=row, column=0, columnspan=2, pady=6)
        row += 1

        tk.Button(f, text="Remove Selected", width=18, command=self._remove_selected).grid(row=row, column=0, columnspan=2, pady=2)
        row += 1

        tk.Button(f, text="Clear Cart", width=18, command=self._clear_cart).grid(row=row, column=0, columnspan=2, pady=2)
        row += 1

        tk.Button(f, text="Generate Bill", width=18, command=self._generate_bill).grid(row=row, column=0, columnspan=2, pady=10)
        row += 1

        tk.Button(f, text="New Invoice", width=18, command=self._new_invoice).grid(row=row, column=0, columnspan=2, pady=2)

    def _build_right(self) -> None:
        f = self._right
        for w in f.winfo_children():
            w.destroy()

        top = tk.Frame(f)
        top.pack(side=tk.TOP, fill=tk.X)

        self._total_var = tk.StringVar(value="0.00")
        self._net_var = tk.StringVar(value="0.00")

        tk.Label(top, text="Total:").pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(top, textvariable=self._total_var, font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=(0, 12))
        tk.Label(top, text="Net:").pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(top, textvariable=self._net_var, font=("Arial", 12, "bold")).pack(side=tk.LEFT)

        cols = ("pid", "name", "price", "qty", "line_total")
        self._tree = ttk.Treeview(f, columns=cols, show="headings")
        for c in cols:
            self._tree.heading(c, text=c)
            self._tree.column(c, width=140, anchor="w")
        self._tree.column("name", width=220)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=(8, 0))

        sb_y = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self._tree.yview)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y, pady=(8, 0))
        self._tree.configure(yscrollcommand=sb_y.set)

    def _generate_invoice_no(self) -> str:
        return datetime.now().strftime("INV%Y%m%d%H%M%S")

    def _refresh_products(self) -> None:
        term = self._product_search.get().strip()
        products = self._service.products.search("name", term) if term else self._service.products.list_all()
        active = [p for p in products if p.status.lower() == "active"]
        values = [p.pid for p in active]
        self._product_cb["values"] = values
        if values and self._selected_pid.get() not in values:
            self._selected_pid.set(values[0])
        if not values:
            self._selected_pid.set("")

    def _add_to_cart(self) -> None:
        try:
            pid = self._selected_pid.get().strip()
            if not pid:
                raise ValueError("Select a product")
            qty = int(self._selected_qty.get().strip() or "0")
            if qty <= 0:
                raise ValueError("Quantity must be positive")
            p = self._service.products.get(pid)
            if not p:
                raise ValueError("Product not found")
            if p.status.lower() != "active":
                raise ValueError("Product is inactive")
            if p.qty < qty:
                raise ValueError("Insufficient stock")

            for idx, (cpid, cname, cprice, cqty) in enumerate(self._cart):
                if cpid == pid:
                    new_qty = cqty + qty
                    if p.qty < new_qty:
                        raise ValueError("Insufficient stock")
                    self._cart[idx] = (cpid, cname, cprice, new_qty)
                    self._render_cart()
                    self._recalc_totals()
                    return

            self._cart.append((p.pid, p.name, float(p.price), qty))
            self._render_cart()
            self._recalc_totals()
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def _remove_selected(self) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        values = self._tree.item(sel[0], "values")
        pid = str(values[0])
        self._cart = [c for c in self._cart if c[0] != pid]
        self._render_cart()
        self._recalc_totals()

    def _clear_cart(self) -> None:
        self._cart = []
        self._render_cart()
        self._recalc_totals()

    def _render_cart(self) -> None:
        for i in self._tree.get_children():
            self._tree.delete(i)
        for pid, name, price, qty in self._cart:
            line_total = float(price) * int(qty)
            self._tree.insert("", tk.END, values=(pid, name, f"{price:.2f}", qty, f"{line_total:.2f}"))

    def _recalc_totals(self) -> None:
        total = sum(float(price) * int(qty) for _, _, price, qty in self._cart)
        try:
            discount = float(self._discount.get().strip() or "0")
        except Exception:
            discount = 0.0
        if discount < 0:
            discount = 0.0
        net = total - discount
        if net < 0:
            net = 0.0
        self._total_var.set(f"{total:.2f}")
        self._net_var.set(f"{net:.2f}")

    def _generate_bill(self) -> None:
        try:
            if not self._cart:
                raise ValueError("Cart is empty")
            cust_name = self._cust_name.get().strip()
            cust_contact = self._cust_contact.get().strip()
            if not cust_name:
                raise ValueError("Customer name is required")
            if not cust_contact:
                raise ValueError("Customer contact is required")

            total = float(self._total_var.get())
            discount = float(self._discount.get().strip() or "0")
            if discount < 0:
                raise ValueError("Discount must be non-negative")
            net = total - discount
            if net < 0:
                net = 0.0

            for pid, _, _, qty in self._cart:
                p = self._service.products.get(pid)
                if not p:
                    raise ValueError(f"Product not found: {pid}")
                if p.qty < qty:
                    raise ValueError(f"Insufficient stock for {pid}")

            for pid, _, _, qty in self._cart:
                self._service.products.adjust_stock(pid, -int(qty))

            items_json = self._cart_to_json()
            b = Bill(
                invoice_no=self._invoice_no.get().strip(),
                customer_name=cust_name,
                customer_contact=cust_contact,
                date_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                total=total,
                discount=discount,
                net=net,
                items_json=items_json,
            )
            self._service.bills.add(b)

            messagebox.showinfo("Success", f"Bill saved: {b.invoice_no}", parent=self)
            self._new_invoice()
        except sqlite3.IntegrityError as ex:
            messagebox.showerror("Error", f"Database error: {ex}", parent=self)
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)

    def _cart_to_json(self) -> str:
        parts: List[str] = []
        for pid, name, price, qty in self._cart:
            safe_name = name.replace("\\", "\\\\").replace('"', '\\"')
            parts.append(f'{{"pid":"{pid}","name":"{safe_name}","price":{float(price):.2f},"qty":{int(qty)}}}')
        return "[" + ",".join(parts) + "]"

    def _new_invoice(self) -> None:
        self._invoice_no.set(self._generate_invoice_no())
        self._cust_name.set("")
        self._cust_contact.set("")
        self._discount.set("0")
        self._selected_qty.set("1")
        self._product_search.set("")
        self._clear_cart()
        self._refresh_products()
        self._recalc_totals()


class BillViewerWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, service: InventoryService) -> None:
        super().__init__(master, "Bill Viewer")
        self._service = service

        tk.Label(self._top, text="Bill Viewer", font=("Arial", 16, "bold")).pack(side=tk.LEFT)

        self._search_invoice = tk.StringVar()

        tk.Label(self._top, text="Invoice No:").pack(side=tk.LEFT, padx=(20, 4))
        tk.Entry(self._top, textvariable=self._search_invoice, width=25).pack(side=tk.LEFT, padx=6)
        tk.Button(self._top, text="Search", width=10, command=self._search).pack(side=tk.LEFT, padx=4)
        tk.Button(self._top, text="Show All", width=10, command=self._refresh).pack(side=tk.LEFT, padx=4)
        tk.Button(self._top, text="Export Selected", width=14, command=self._export_selected).pack(side=tk.LEFT, padx=8)

        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        for w in self._left.winfo_children():
            w.destroy()
        for w in self._right.winfo_children():
            w.destroy()

        tk.Label(self._left, text="Bill Details", font=("Arial", 12, "bold")).pack(anchor="w")
        self._details = tk.Text(self._left, width=32, height=28)
        self._details.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        cols = ("invoice_no", "customer_name", "customer_contact", "date_time", "total", "discount", "net")
        self._tree = ttk.Treeview(self._right, columns=cols, show="headings")
        for c in cols:
            self._tree.heading(c, text=c)
            self._tree.column(c, width=140, anchor="w")
        self._tree.column("customer_name", width=180)
        self._tree.column("date_time", width=170)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb_y = ttk.Scrollbar(self._right, orient=tk.VERTICAL, command=self._tree.yview)
        sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.configure(yscrollcommand=sb_y.set)

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    def _on_select(self, _evt: Any) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        values = self._tree.item(sel[0], "values")
        invoice_no = str(values[0])
        b = self._service.bills.get(invoice_no)
        if not b:
            return
        self._details.delete("1.0", tk.END)
        self._details.insert(
            tk.END,
            f"Invoice: {b.invoice_no}\n"
            f"Customer: {b.customer_name}\n"
            f"Contact: {b.customer_contact}\n"
            f"Date/Time: {b.date_time}\n"
            f"Total: {b.total:.2f}\n"
            f"Discount: {b.discount:.2f}\n"
            f"Net: {b.net:.2f}\n\n"
            f"Items:\n{b.items_json}\n",
        )

    def _refresh(self) -> None:
        for i in self._tree.get_children():
            self._tree.delete(i)
        for b in self._service.bills.list_all():
            self._tree.insert("", tk.END, values=(b.invoice_no, b.customer_name, b.customer_contact, b.date_time, f"{b.total:.2f}", f"{b.discount:.2f}", f"{b.net:.2f}"))
        self._details.delete("1.0", tk.END)

    def _search(self) -> None:
        term = self._search_invoice.get().strip()
        rows = self._service.bills.search_by_invoice(term) if term else self._service.bills.list_all()
        for i in self._tree.get_children():
            self._tree.delete(i)
        for b in rows:
            self._tree.insert("", tk.END, values=(b.invoice_no, b.customer_name, b.customer_contact, b.date_time, f"{b.total:.2f}", f"{b.discount:.2f}", f"{b.net:.2f}"))
        self._details.delete("1.0", tk.END)

    def _export_selected(self) -> None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showerror("Error", "Select a bill to export", parent=self)
            return
        values = self._tree.item(sel[0], "values")
        invoice_no = str(values[0])
        b = self._service.bills.get(invoice_no)
        if not b:
            messagebox.showerror("Error", "Bill not found", parent=self)
            return

        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile=f"{invoice_no}.txt",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(
                    f"Invoice: {b.invoice_no}\n"
                    f"Customer: {b.customer_name}\n"
                    f"Contact: {b.customer_contact}\n"
                    f"Date/Time: {b.date_time}\n"
                    f"Total: {b.total:.2f}\n"
                    f"Discount: {b.discount:.2f}\n"
                    f"Net: {b.net:.2f}\n"
                    f"Items: {b.items_json}\n"
                )
            messagebox.showinfo("Success", f"Exported to {path}", parent=self)
        except Exception as ex:
            messagebox.showerror("Error", str(ex), parent=self)


class DashboardApp(tk.Tk):
    def __init__(self, service: InventoryService) -> None:
        super().__init__()
        self._service = service
        self.title("Inventory Management System")
        self.geometry("1100x650")
        self.minsize(1000, 600)

        self._header = tk.Frame(self, bd=2, relief=tk.RIDGE)
        self._header.pack(side=tk.TOP, fill=tk.X)

        self._content = tk.Frame(self)
        self._content.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self._left = tk.Frame(self._content, bd=2, relief=tk.RIDGE)
        self._left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        self._right = tk.Frame(self._content, bd=2, relief=tk.RIDGE)
        self._right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8), pady=8)

        self._time_var = tk.StringVar()
        self._build_header()
        self._build_left_menu()
        self._build_right_dashboard()
        self._update_time()
        self._refresh_counts()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_header(self) -> None:
        title = tk.Label(self._header, text="Inventory Management System", font=("Arial", 18, "bold"))
        title.pack(side=tk.LEFT, padx=10, pady=10)

        self._time_label = tk.Label(self._header, textvariable=self._time_var, font=("Arial", 12))
        self._time_label.pack(side=tk.RIGHT, padx=10)

    def _build_left_menu(self) -> None:
        tk.Label(self._left, text="Menu", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(10, 6))

        tk.Button(self._left, text="Employees", width=18, command=self._open_employees).pack(padx=10, pady=6)
        tk.Button(self._left, text="Suppliers", width=18, command=self._open_suppliers).pack(padx=10, pady=6)
        tk.Button(self._left, text="Categories", width=18, command=self._open_categories).pack(padx=10, pady=6)
        tk.Button(self._left, text="Products", width=18, command=self._open_products).pack(padx=10, pady=6)
        tk.Button(self._left, text="Billing", width=18, command=self._open_billing).pack(padx=10, pady=6)
        tk.Button(self._left, text="Bills", width=18, command=self._open_bills).pack(padx=10, pady=6)

        ttk.Separator(self._left, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)

        tk.Button(self._left, text="Refresh Dashboard", width=18, command=self._refresh_counts).pack(padx=10, pady=6)
        tk.Button(self._left, text="Exit", width=18, command=self._on_close).pack(padx=10, pady=6)

    def _build_right_dashboard(self) -> None:
        top = tk.Frame(self._right)
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self._img_label = tk.Label(top)
        self._img_label.pack(side=tk.RIGHT, padx=10)

        self._load_dashboard_image()

        tk.Label(top, text="Dashboard", font=("Arial", 16, "bold")).pack(side=tk.LEFT)

        self._cards = tk.Frame(self._right)
        self._cards.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._count_vars: Dict[str, tk.StringVar] = {
            "employees": tk.StringVar(value="0"),
            "suppliers": tk.StringVar(value="0"),
            "categories": tk.StringVar(value="0"),
            "products": tk.StringVar(value="0"),
            "bills": tk.StringVar(value="0"),
        }

        self._create_card("Employees", self._count_vars["employees"], 0, 0)
        self._create_card("Suppliers", self._count_vars["suppliers"], 0, 1)
        self._create_card("Categories", self._count_vars["categories"], 1, 0)
        self._create_card("Products", self._count_vars["products"], 1, 1)
        self._create_card("Bills", self._count_vars["bills"], 2, 0)

        self._cards.grid_columnconfigure(0, weight=1)
        self._cards.grid_columnconfigure(1, weight=1)
        self._cards.grid_rowconfigure(0, weight=1)
        self._cards.grid_rowconfigure(1, weight=1)
        self._cards.grid_rowconfigure(2, weight=1)

    def _create_card(self, title: str, var: tk.StringVar, r: int, c: int) -> None:
        card = tk.LabelFrame(self._cards, text=title, padx=10, pady=10)
        card.grid(row=r, column=c, sticky="nsew", padx=8, pady=8)
        tk.Label(card, textvariable=var, font=("Arial", 28, "bold")).pack(anchor="center", pady=10)

    def _load_dashboard_image(self) -> None:
        if Image is None or ImageTk is None:
            self._img_label.configure(text="")
            return
        candidates = [
            os.path.join(os.getcwd(), "dashboard.png"),
            os.path.join(os.getcwd(), "dashboard.jpg"),
            os.path.join(os.getcwd(), "logo.png"),
            os.path.join(os.getcwd(), "logo.jpg"),
        ]
        path = next((p for p in candidates if os.path.exists(p)), None)
        if not path:
            self._img_label.configure(text="")
            return
        try:
            img = Image.open(path)
            img = img.resize((120, 120))
            self._img = ImageTk.PhotoImage(img)
            self._img_label.configure(image=self._img)
        except Exception:
            self._img_label.configure(text="")

    def _update_time(self) -> None:
        self._time_var.set(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.after(1000, self._update_time)

    def _refresh_counts(self) -> None:
        try:
            counts = self._service.dashboard_counts()
            for k, v in counts.items():
                if k in self._count_vars:
                    self._count_vars[k].set(str(v))
        except Exception:
            pass

    def _open_employees(self) -> None:
        EmployeeManagerWindow(self, self._service)

    def _open_suppliers(self) -> None:
        SupplierManagerWindow(self, self._service)

    def _open_categories(self) -> None:
        CategoryManagerWindow(self, self._service)

    def _open_products(self) -> None:
        ProductManagerWindow(self, self._service)

    def _open_billing(self) -> None:
        BillingWindow(self, self._service)

    def _open_bills(self) -> None:
        BillViewerWindow(self, self._service)

    def _on_close(self) -> None:
        self.destroy()


def build_service(db_path: str) -> Tuple[InventoryService, Database]:
    db = Database(db_path)
    service = InventoryService(
        employees=EmployeeRepository(db),
        suppliers=SupplierRepository(db),
        categories=CategoryRepository(db),
        products=ProductRepository(db),
        bills=BillRepository(db),
    )
    return service, db


def main() -> None:
    db_path = os.path.join(os.getcwd(), "inventory.db")
    service, db = build_service(db_path)
    try:
        app = DashboardApp(service)
        app.mainloop()
    finally:
        db.close()


if __name__ == "__main__":
    main()