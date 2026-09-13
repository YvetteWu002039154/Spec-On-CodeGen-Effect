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
    user_type: str
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
class Bill:
    invoice: str
    customer_name: str
    customer_contact: str
    total: float
    discount: float
    net_pay: float
    paid: float
    balance: float
    created_at: str
    content: str


class Database:
    def __init__(self, path: str = "ims.db") -> None:
        self._path = path
        self._conn = sqlite3.connect(self._path)
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
            CREATE TABLE IF NOT EXISTS employee(
                emp_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                gender TEXT NOT NULL,
                contact TEXT NOT NULL,
                dob TEXT NOT NULL,
                doj TEXT NOT NULL,
                password TEXT NOT NULL,
                user_type TEXT NOT NULL,
                address TEXT NOT NULL,
                salary REAL NOT NULL CHECK(salary >= 0)
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
                name TEXT PRIMARY KEY
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS product(
                name TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                supplier TEXT NOT NULL,
                price REAL NOT NULL CHECK(price >= 0),
                qty INTEGER NOT NULL CHECK(qty >= 0),
                status TEXT NOT NULL,
                FOREIGN KEY(category) REFERENCES category(name) ON UPDATE CASCADE ON DELETE RESTRICT,
                FOREIGN KEY(supplier) REFERENCES supplier(invoice) ON UPDATE CASCADE ON DELETE RESTRICT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bill(
                invoice TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                customer_contact TEXT NOT NULL,
                total REAL NOT NULL CHECK(total >= 0),
                discount REAL NOT NULL CHECK(discount >= 0),
                net_pay REAL NOT NULL CHECK(net_pay >= 0),
                paid REAL NOT NULL CHECK(paid >= 0),
                balance REAL NOT NULL,
                created_at TEXT NOT NULL,
                content TEXT NOT NULL
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
        if not e.emp_id.strip():
            raise ValueError("Employee ID is required")
        self._db.execute(
            """
            INSERT INTO employee(emp_id,name,email,gender,contact,dob,doj,password,user_type,address,salary)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
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
                e.user_type.strip(),
                e.address.strip(),
                float(e.salary),
            ),
        )

    def update(self, e: Employee) -> None:
        self._db.execute(
            """
            UPDATE employee
            SET name=?,email=?,gender=?,contact=?,dob=?,doj=?,password=?,user_type=?,address=?,salary=?
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
                e.user_type.strip(),
                e.address.strip(),
                float(e.salary),
                e.emp_id.strip(),
            ),
        )

    def delete(self, emp_id: str) -> None:
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
            user_type=r["user_type"],
            address=r["address"],
            salary=float(r["salary"]),
        )

    def list_all(self) -> List[Employee]:
        rows = self._db.query("SELECT * FROM employee ORDER BY emp_id")
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
                    user_type=r["user_type"],
                    address=r["address"],
                    salary=float(r["salary"]),
                )
            )
        return out

    def search(self, field: str, value: str) -> List[Employee]:
        allowed = {"emp_id", "name", "email", "contact", "user_type"}
        if field not in allowed:
            raise ValueError("Invalid search field")
        rows = self._db.query(
            f"SELECT * FROM employee WHERE {field} LIKE ? ORDER BY emp_id",
            (f"%{value.strip()}%",),
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
                user_type=r["user_type"],
                address=r["address"],
                salary=float(r["salary"]),
            )
            for r in rows
        ]


class SupplierRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, s: Supplier) -> None:
        if not s.invoice.strip():
            raise ValueError("Supplier invoice is required")
        self._db.execute(
            "INSERT INTO supplier(invoice,name,contact,desc) VALUES(?,?,?,?)",
            (s.invoice.strip(), s.name.strip(), s.contact.strip(), s.desc.strip()),
        )

    def update(self, s: Supplier) -> None:
        self._db.execute(
            "UPDATE supplier SET name=?,contact=?,desc=? WHERE invoice=?",
            (s.name.strip(), s.contact.strip(), s.desc.strip(), s.invoice.strip()),
        )

    def delete(self, invoice: str) -> None:
        self._db.execute("DELETE FROM supplier WHERE invoice=?", (invoice.strip(),))

    def get(self, invoice: str) -> Optional[Supplier]:
        rows = self._db.query("SELECT * FROM supplier WHERE invoice=?", (invoice.strip(),))
        if not rows:
            return None
        r = rows[0]
        return Supplier(invoice=r["invoice"], name=r["name"], contact=r["contact"], desc=r["desc"])

    def list_all(self) -> List[Supplier]:
        rows = self._db.query("SELECT * FROM supplier ORDER BY invoice")
        return [Supplier(invoice=r["invoice"], name=r["name"], contact=r["contact"], desc=r["desc"]) for r in rows]

    def search(self, field: str, value: str) -> List[Supplier]:
        allowed = {"invoice", "name", "contact"}
        if field not in allowed:
            raise ValueError("Invalid search field")
        rows = self._db.query(
            f"SELECT * FROM supplier WHERE {field} LIKE ? ORDER BY invoice",
            (f"%{value.strip()}%",),
        )
        return [Supplier(invoice=r["invoice"], name=r["name"], contact=r["contact"], desc=r["desc"]) for r in rows]


class CategoryRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, c: Category) -> None:
        name = c.name.strip()
        if not name:
            raise ValueError("Category name is required")
        self._db.execute("INSERT INTO category(name) VALUES(?)", (name,))

    def delete(self, name: str) -> None:
        self._db.execute("DELETE FROM category WHERE name=?", (name.strip(),))

    def list_all(self) -> List[Category]:
        rows = self._db.query("SELECT * FROM category ORDER BY name")
        return [Category(name=r["name"]) for r in rows]

    def exists(self, name: str) -> bool:
        rows = self._db.query("SELECT 1 FROM category WHERE name=?", (name.strip(),))
        return bool(rows)


class ProductRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, p: Product) -> None:
        if not p.name.strip():
            raise ValueError("Product name is required")
        if p.qty < 0:
            raise ValueError("Quantity cannot be negative")
        if p.price < 0:
            raise ValueError("Price cannot be negative")
        self._db.execute(
            "INSERT INTO product(name,category,supplier,price,qty,status) VALUES(?,?,?,?,?,?)",
            (
                p.name.strip(),
                p.category.strip(),
                p.supplier.strip(),
                float(p.price),
                int(p.qty),
                p.status.strip(),
            ),
        )

    def update(self, p: Product) -> None:
        if p.qty < 0:
            raise ValueError("Quantity cannot be negative")
        if p.price < 0:
            raise ValueError("Price cannot be negative")
        self._db.execute(
            "UPDATE product SET category=?,supplier=?,price=?,qty=?,status=? WHERE name=?",
            (
                p.category.strip(),
                p.supplier.strip(),
                float(p.price),
                int(p.qty),
                p.status.strip(),
                p.name.strip(),
            ),
        )

    def delete(self, name: str) -> None:
        self._db.execute("DELETE FROM product WHERE name=?", (name.strip(),))

    def get(self, name: str) -> Optional[Product]:
        rows = self._db.query("SELECT * FROM product WHERE name=?", (name.strip(),))
        if not rows:
            return None
        r = rows[0]
        return Product(
            name=r["name"],
            category=r["category"],
            supplier=r["supplier"],
            price=float(r["price"]),
            qty=int(r["qty"]),
            status=r["status"],
        )

    def list_all(self) -> List[Product]:
        rows = self._db.query("SELECT * FROM product ORDER BY name")
        return [
            Product(
                name=r["name"],
                category=r["category"],
                supplier=r["supplier"],
                price=float(r["price"]),
                qty=int(r["qty"]),
                status=r["status"],
            )
            for r in rows
        ]

    def search(self, field: str, value: str) -> List[Product]:
        allowed = {"name", "category", "supplier", "status"}
        if field not in allowed:
            raise ValueError("Invalid search field")
        rows = self._db.query(
            f"SELECT * FROM product WHERE {field} LIKE ? ORDER BY name",
            (f"%{value.strip()}%",),
        )
        return [
            Product(
                name=r["name"],
                category=r["category"],
                supplier=r["supplier"],
                price=float(r["price"]),
                qty=int(r["qty"]),
                status=r["status"],
            )
            for r in rows
        ]

    def adjust_stock(self, name: str, delta_qty: int) -> None:
        p = self.get(name)
        if not p:
            raise ValueError("Product not found")
        new_qty = p.qty + int(delta_qty)
        if new_qty < 0:
            raise ValueError("Insufficient stock")
        self._db.execute("UPDATE product SET qty=? WHERE name=?", (new_qty, name.strip()))


class BillRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, b: Bill) -> None:
        if not b.invoice.strip():
            raise ValueError("Invoice number is required")
        self._db.execute(
            """
            INSERT INTO bill(invoice,customer_name,customer_contact,total,discount,net_pay,paid,balance,created_at,content)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                b.invoice.strip(),
                b.customer_name.strip(),
                b.customer_contact.strip(),
                float(b.total),
                float(b.discount),
                float(b.net_pay),
                float(b.paid),
                float(b.balance),
                b.created_at,
                b.content,
            ),
        )

    def get(self, invoice: str) -> Optional[Bill]:
        rows = self._db.query("SELECT * FROM bill WHERE invoice=?", (invoice.strip(),))
        if not rows:
            return None
        r = rows[0]
        return Bill(
            invoice=r["invoice"],
            customer_name=r["customer_name"],
            customer_contact=r["customer_contact"],
            total=float(r["total"]),
            discount=float(r["discount"]),
            net_pay=float(r["net_pay"]),
            paid=float(r["paid"]),
            balance=float(r["balance"]),
            created_at=r["created_at"],
            content=r["content"],
        )

    def list_all(self) -> List[Bill]:
        rows = self._db.query("SELECT * FROM bill ORDER BY created_at DESC")
        return [
            Bill(
                invoice=r["invoice"],
                customer_name=r["customer_name"],
                customer_contact=r["customer_contact"],
                total=float(r["total"]),
                discount=float(r["discount"]),
                net_pay=float(r["net_pay"]),
                paid=float(r["paid"]),
                balance=float(r["balance"]),
                created_at=r["created_at"],
                content=r["content"],
            )
            for r in rows
        ]

    def search_by_invoice(self, invoice_part: str) -> List[Bill]:
        rows = self._db.query(
            "SELECT * FROM bill WHERE invoice LIKE ? ORDER BY created_at DESC",
            (f"%{invoice_part.strip()}%",),
        )
        return [
            Bill(
                invoice=r["invoice"],
                customer_name=r["customer_name"],
                customer_contact=r["customer_contact"],
                total=float(r["total"]),
                discount=float(r["discount"]),
                net_pay=float(r["net_pay"]),
                paid=float(r["paid"]),
                balance=float(r["balance"]),
                created_at=r["created_at"],
                content=r["content"],
            )
            for r in rows
        ]


class ImageManager:
    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, int, int], Any] = {}

    def load(self, path: str, size: Tuple[int, int]) -> Optional[Any]:
        if not Image or not ImageTk:
            return None
        key = (path, size[0], size[1])
        if key in self._cache:
            return self._cache[key]
        if not os.path.exists(path):
            return None
        try:
            img = Image.open(path)
            img = img.resize(size)
            tk_img = ImageTk.PhotoImage(img)
            self._cache[key] = tk_img
            return tk_img
        except Exception:
            return None


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


class EmployeeManagerWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, repo: EmployeeRepository) -> None:
        super().__init__(master, "Employee Management")
        self._repo = repo

        self.var_search_by = tk.StringVar(value="emp_id")
        self.var_search_txt = tk.StringVar()

        self.var_emp_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_gender = tk.StringVar(value="Select")
        self.var_contact = tk.StringVar()
        self.var_dob = tk.StringVar()
        self.var_doj = tk.StringVar()
        self.var_password = tk.StringVar()
        self.var_user_type = tk.StringVar(value="Employee")
        self.var_salary = tk.StringVar(value="0")
        self.txt_address: Optional[tk.Text] = None

        self._build()
        self._refresh_table()
        self._center()

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(top, text="Search By:").pack(side="left")
        cb = ttk.Combobox(top, textvariable=self.var_search_by, values=["emp_id", "name", "email", "contact", "user_type"], state="readonly", width=12)
        cb.pack(side="left", padx=5)
        ttk.Entry(top, textvariable=self.var_search_txt, width=30).pack(side="left", padx=5)
        ttk.Button(top, text="Search", command=self._search).pack(side="left", padx=5)
        ttk.Button(top, text="Show All", command=self._refresh_table).pack(side="left", padx=5)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        form = ttk.LabelFrame(body, text="Employee Details")
        form.pack(side="left", fill="y", padx=(0, 10))

        def row(label: str, widget: tk.Widget, r: int) -> None:
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w", padx=8, pady=6)
            widget.grid(row=r, column=1, sticky="ew", padx=8, pady=6)

        form.columnconfigure(1, weight=1)

        row("Employee ID", ttk.Entry(form, textvariable=self.var_emp_id), 0)
        row("Name", ttk.Entry(form, textvariable=self.var_name), 1)
        row("Email", ttk.Entry(form, textvariable=self.var_email), 2)
        row("Gender", ttk.Combobox(form, textvariable=self.var_gender, values=["Select", "Male", "Female", "Other"], state="readonly"), 3)
        row("Contact", ttk.Entry(form, textvariable=self.var_contact), 4)
        row("DOB (YYYY-MM-DD)", ttk.Entry(form, textvariable=self.var_dob), 5)
        row("DOJ (YYYY-MM-DD)", ttk.Entry(form, textvariable=self.var_doj), 6)
        row("Password", ttk.Entry(form, textvariable=self.var_password, show="*"), 7)
        row("User Type", ttk.Combobox(form, textvariable=self.var_user_type, values=["Admin", "Employee"], state="readonly"), 8)
        row("Salary", ttk.Entry(form, textvariable=self.var_salary), 9)

        ttk.Label(form, text="Address").grid(row=10, column=0, sticky="nw", padx=8, pady=6)
        self.txt_address = tk.Text(form, width=28, height=4)
        self.txt_address.grid(row=10, column=1, sticky="ew", padx=8, pady=6)

        btns = ttk.Frame(form)
        btns.grid(row=11, column=0, columnspan=2, sticky="ew", padx=8, pady=10)
        for i in range(4):
            btns.columnconfigure(i, weight=1)
        ttk.Button(btns, text="Save", command=self._save).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(btns, text="Update", command=self._update).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(btns, text="Delete", command=self._delete).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(btns, text="Clear", command=self._clear).grid(row=0, column=3, sticky="ew", padx=4)

        table_frame = ttk.LabelFrame(body, text="Employees")
        table_frame.pack(side="left", fill="both", expand=True)

        cols = ("emp_id", "name", "email", "gender", "contact", "dob", "doj", "user_type", "salary")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=110, anchor="w")
        self.tree.column("email", width=160)
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        ysb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        ysb.place(relx=1.0, rely=0.0, relheight=1.0, anchor="ne")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _validate_date(self, s: str) -> None:
        s = s.strip()
        if not s:
            raise ValueError("Date is required")
        datetime.strptime(s, "%Y-%m-%d")

    def _get_address(self) -> str:
        if not self.txt_address:
            return ""
        return self.txt_address.get("1.0", "end").strip()

    def _set_address(self, value: str) -> None:
        if not self.txt_address:
            return
        self.txt_address.delete("1.0", "end")
        self.txt_address.insert("1.0", value or "")

    def _read_form(self) -> Employee:
        emp_id = self.var_emp_id.get().strip()
        name = self.var_name.get().strip()
        email = self.var_email.get().strip()
        gender = self.var_gender.get().strip()
        contact = self.var_contact.get().strip()
        dob = self.var_dob.get().strip()
        doj = self.var_doj.get().strip()
        password = self.var_password.get()
        user_type = self.var_user_type.get().strip()
        address = self._get_address()
        salary_str = self.var_salary.get().strip()

        if not emp_id or not name or not email or not contact or not password or not address:
            raise ValueError("All fields are required")
        if gender == "Select" or not gender:
            raise ValueError("Select gender")
        self._validate_date(dob)
        self._validate_date(doj)
        try:
            salary = float(salary_str)
        except Exception:
            raise ValueError("Invalid salary")
        if salary < 0:
            raise ValueError("Salary cannot be negative")

        return Employee(
            emp_id=emp_id,
            name=name,
            email=email,
            gender=gender,
            contact=contact,
            dob=dob,
            doj=doj,
            password=password,
            user_type=user_type or "Employee",
            address=address,
            salary=salary,
        )

    def _save(self) -> None:
        try:
            e = self._read_form()
            if self._repo.get(e.emp_id):
                raise ValueError("Employee ID already exists")
            self._repo.add(e)
            messagebox.showinfo("Success", "Employee added")
            self._refresh_table()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _update(self) -> None:
        try:
            e = self._read_form()
            if not self._repo.get(e.emp_id):
                raise ValueError("Employee not found")
            self._repo.update(e)
            messagebox.showinfo("Success", "Employee updated")
            self._refresh_table()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _delete(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        if not emp_id:
            messagebox.showerror("Error", "Employee ID is required")
            return
        if not messagebox.askyesno("Confirm", "Delete this employee?"):
            return
        try:
            self._repo.delete(emp_id)
            messagebox.showinfo("Success", "Employee deleted")
            self._refresh_table()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _clear(self) -> None:
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_email.set("")
        self.var_gender.set("Select")
        self.var_contact.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_password.set("")
        self.var_user_type.set("Employee")
        self.var_salary.set("0")
        self._set_address("")
        self.tree.selection_remove(self.tree.selection())

    def _refresh_table(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for e in self._repo.list_all():
            self.tree.insert("", "end", values=(e.emp_id, e.name, e.email, e.gender, e.contact, e.dob, e.doj, e.user_type, f"{e.salary:.2f}"))

    def _search(self) -> None:
        try:
            field = self.var_search_by.get().strip()
            txt = self.var_search_txt.get().strip()
            for i in self.tree.get_children():
                self.tree.delete(i)
            for e in self._repo.search(field, txt):
                self.tree.insert("", "end", values=(e.emp_id, e.name, e.email, e.gender, e.contact, e.dob, e.doj, e.user_type, f"{e.salary:.2f}"))
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _on_select(self, _evt: Any) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        emp_id = str(vals[0])
        e = self._repo.get(emp_id)
        if not e:
            return
        self.var_emp_id.set(e.emp_id)
        self.var_name.set(e.name)
        self.var_email.set(e.email)
        self.var_gender.set(e.gender)
        self.var_contact.set(e.contact)
        self.var_dob.set(e.dob)
        self.var_doj.set(e.doj)
        self.var_password.set(e.password)
        self.var_user_type.set(e.user_type)
        self.var_salary.set(str(e.salary))
        self._set_address(e.address)


class SupplierManagerWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, repo: SupplierRepository) -> None:
        super().__init__(master, "Supplier Management")
        self._repo = repo

        self.var_search_by = tk.StringVar(value="invoice")
        self.var_search_txt = tk.StringVar()

        self.var_invoice = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.txt_desc: Optional[tk.Text] = None

        self._build()
        self._refresh_table()
        self._center()

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(top, text="Search By:").pack(side="left")
        cb = ttk.Combobox(top, textvariable=self.var_search_by, values=["invoice", "name", "contact"], state="readonly", width=12)
        cb.pack(side="left", padx=5)
        ttk.Entry(top, textvariable=self.var_search_txt, width=30).pack(side="left", padx=5)
        ttk.Button(top, text="Search", command=self._search).pack(side="left", padx=5)
        ttk.Button(top, text="Show All", command=self._refresh_table).pack(side="left", padx=5)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        form = ttk.LabelFrame(body, text="Supplier Details")
        form.pack(side="left", fill="y", padx=(0, 10))
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Invoice No").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(form, textvariable=self.var_invoice).grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        ttk.Label(form, text="Name").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(form, textvariable=self.var_name).grid(row=1, column=1, sticky="ew", padx=8, pady=6)

        ttk.Label(form, text="Contact").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(form, textvariable=self.var_contact).grid(row=2, column=1, sticky="ew", padx=8, pady=6)

        ttk.Label(form, text="Description").grid(row=3, column=0, sticky="nw", padx=8, pady=6)
        self.txt_desc = tk.Text(form, width=28, height=6)
        self.txt_desc.grid(row=3, column=1, sticky="ew", padx=8, pady=6)

        btns = ttk.Frame(form)
        btns.grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=10)
        for i in range(4):
            btns.columnconfigure(i, weight=1)
        ttk.Button(btns, text="Save", command=self._save).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(btns, text="Update", command=self._update).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(btns, text="Delete", command=self._delete).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(btns, text="Clear", command=self._clear).grid(row=0, column=3, sticky="ew", padx=4)

        table_frame = ttk.LabelFrame(body, text="Suppliers")
        table_frame.pack(side="left", fill="both", expand=True)

        cols = ("invoice", "name", "contact", "desc")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=140, anchor="w")
        self.tree.column("desc", width=260)
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        ysb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        ysb.place(relx=1.0, rely=0.0, relheight=1.0, anchor="ne")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _get_desc(self) -> str:
        if not self.txt_desc:
            return ""
        return self.txt_desc.get("1.0", "end").strip()

    def _set_desc(self, value: str) -> None:
        if not self.txt_desc:
            return
        self.txt_desc.delete("1.0", "end")
        self.txt_desc.insert("1.0", value or "")

    def _read_form(self) -> Supplier:
        invoice = self.var_invoice.get().strip()
        name = self.var_name.get().strip()
        contact = self.var_contact.get().strip()
        desc = self._get_desc()
        if not invoice or not name or not contact or not desc:
            raise ValueError("All fields are required")
        return Supplier(invoice=invoice, name=name, contact=contact, desc=desc)

    def _save(self) -> None:
        try:
            s = self._read_form()
            if self._repo.get(s.invoice):
                raise ValueError("Invoice already exists")
            self._repo.add(s)
            messagebox.showinfo("Success", "Supplier added")
            self._refresh_table()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _update(self) -> None:
        try:
            s = self._read_form()
            if not self._repo.get(s.invoice):
                raise ValueError("Supplier not found")
            self._repo.update(s)
            messagebox.showinfo("Success", "Supplier updated")
            self._refresh_table()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _delete(self) -> None:
        invoice = self.var_invoice.get().strip()
        if not invoice:
            messagebox.showerror("Error", "Invoice is required")
            return
        if not messagebox.askyesno("Confirm", "Delete this supplier?"):
            return
        try:
            self._repo.delete(invoice)
            messagebox.showinfo("Success", "Supplier deleted")
            self._refresh_table()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _clear(self) -> None:
        self.var_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self._set_desc("")
        self.tree.selection_remove(self.tree.selection())

    def _refresh_table(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for s in self._repo.list_all():
            self.tree.insert("", "end", values=(s.invoice, s.name, s.contact, s.desc))

    def _search(self) -> None:
        try:
            field = self.var_search_by.get().strip()
            txt = self.var_search_txt.get().strip()
            for i in self.tree.get_children():
                self.tree.delete(i)
            for s in self._repo.search(field, txt):
                self.tree.insert("", "end", values=(s.invoice, s.name, s.contact, s.desc))
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _on_select(self, _evt: Any) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        invoice = str(vals[0])
        s = self._repo.get(invoice)
        if not s:
            return
        self.var_invoice.set(s.invoice)
        self.var_name.set(s.name)
        self.var_contact.set(s.contact)
        self._set_desc(s.desc)


class CategoryManagerWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, repo: CategoryRepository) -> None:
        super().__init__(master, "Category Management")
        self._repo = repo
        self.var_name = tk.StringVar()
        self._build()
        self._refresh()
        self._center()

    def _build(self) -> None:
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.LabelFrame(frm, text="Category")
        left.pack(side="left", fill="y", padx=(0, 10))
        left.columnconfigure(1, weight=1)

        ttk.Label(left, text="Name").grid(row=0, column=0, sticky="w", padx=8, pady=8)
        ttk.Entry(left, textvariable=self.var_name, width=25).grid(row=0, column=1, sticky="ew", padx=8, pady=8)

        btns = ttk.Frame(left)
        btns.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)
        btns.columnconfigure(2, weight=1)
        ttk.Button(btns, text="Add", command=self._add).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(btns, text="Delete", command=self._delete).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(btns, text="Clear", command=self._clear).grid(row=0, column=2, sticky="ew", padx=4)

        right = ttk.LabelFrame(frm, text="Categories")
        right.pack(side="left", fill="both", expand=True)

        self.listbox = tk.Listbox(right)
        self.listbox.pack(fill="both", expand=True, padx=6, pady=6)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

    def _refresh(self) -> None:
        self.listbox.delete(0, "end")
        for c in self._repo.list_all():
            self.listbox.insert("end", c.name)

    def _add(self) -> None:
        try:
            name = self.var_name.get().strip()
            if not name:
                raise ValueError("Name is required")
            if self._repo.exists(name):
                raise ValueError("Category already exists")
            self._repo.add(Category(name=name))
            messagebox.showinfo("Success", "Category added")
            self._refresh()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _delete(self) -> None:
        name = self.var_name.get().strip()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        if not messagebox.askyesno("Confirm", "Delete this category?"):
            return
        try:
            self._repo.delete(name)
            messagebox.showinfo("Success", "Category deleted")
            self._refresh()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _clear(self) -> None:
        self.var_name.set("")
        self.listbox.selection_clear(0, "end")

    def _on_select(self, _evt: Any) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        self.var_name.set(self.listbox.get(sel[0]))


class ProductManagerWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, repo: ProductRepository, cat_repo: CategoryRepository, sup_repo: SupplierRepository) -> None:
        super().__init__(master, "Product Management")
        self._repo = repo
        self._cat_repo = cat_repo
        self._sup_repo = sup_repo

        self.var_search_by = tk.StringVar(value="name")
        self.var_search_txt = tk.StringVar()

        self.var_name = tk.StringVar()
        self.var_category = tk.StringVar(value="Select")
        self.var_supplier = tk.StringVar(value="Select")
        self.var_price = tk.StringVar(value="0")
        self.var_qty = tk.StringVar(value="0")
        self.var_status = tk.StringVar(value="Active")

        self._build()
        self._reload_dropdowns()
        self._refresh_table()
        self._center()

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(top, text="Search By:").pack(side="left")
        cb = ttk.Combobox(top, textvariable=self.var_search_by, values=["name", "category", "supplier", "status"], state="readonly", width=12)
        cb.pack(side="left", padx=5)
        ttk.Entry(top, textvariable=self.var_search_txt, width=30).pack(side="left", padx=5)
        ttk.Button(top, text="Search", command=self._search).pack(side="left", padx=5)
        ttk.Button(top, text="Show All", command=self._refresh_table).pack(side="left", padx=5)
        ttk.Button(top, text="Reload Lists", command=self._reload_dropdowns).pack(side="left", padx=5)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=10)

        form = ttk.LabelFrame(body, text="Product Details")
        form.pack(side="left", fill="y", padx=(0, 10))
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Name").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(form, textvariable=self.var_name).grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        ttk.Label(form, text="Category").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.cb_category = ttk.Combobox(form, textvariable=self.var_category, values=["Select"], state="readonly")
        self.cb_category.grid(row=1, column=1, sticky="ew", padx=8, pady=6)

        ttk.Label(form, text="Supplier (Invoice)").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        self.cb_supplier = ttk.Combobox(form, textvariable=self.var_supplier, values=["Select"], state="readonly")
        self.cb_supplier.grid(row=2, column=1, sticky="ew", padx=8, pady=6)

        ttk.Label(form, text="Price").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(form, textvariable=self.var_price).grid(row=3, column=1, sticky="ew", padx=8, pady=6)

        ttk.Label(form, text="Quantity").grid(row=4, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(form, textvariable=self.var_qty).grid(row=4, column=1, sticky="ew", padx=8, pady=6)

        ttk.Label(form, text="Status").grid(row=5, column=0, sticky="w", padx=8, pady=6)
        ttk.Combobox(form, textvariable=self.var_status, values=["Active", "Inactive"], state="readonly").grid(row=5, column=1, sticky="ew", padx=8, pady=6)

        btns = ttk.Frame(form)
        btns.grid(row=6, column=0, columnspan=2, sticky="ew", padx=8, pady=10)
        for i in range(4):
            btns.columnconfigure(i, weight=1)
        ttk.Button(btns, text="Save", command=self._save).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(btns, text="Update", command=self._update).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(btns, text="Delete", command=self._delete).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(btns, text="Clear", command=self._clear).grid(row=0, column=3, sticky="ew", padx=4)

        table_frame = ttk.LabelFrame(body, text="Products")
        table_frame.pack(side="left", fill="both", expand=True)

        cols = ("name", "category", "supplier", "price", "qty", "status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=130, anchor="w")
        self.tree.column("price", width=90, anchor="e")
        self.tree.column("qty", width=70, anchor="e")
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        ysb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        ysb.place(relx=1.0, rely=0.0, relheight=1.0, anchor="ne")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _reload_dropdowns(self) -> None:
        cats = ["Select"] + [c.name for c in self._cat_repo.list_all()]
        sups = ["Select"] + [s.invoice for s in self._sup_repo.list_all()]
        self.cb_category["values"] = cats
        self.cb_supplier["values"] = sups
        if self.var_category.get() not in cats:
            self.var_category.set("Select")
        if self.var_supplier.get() not in sups:
            self.var_supplier.set("Select")

    def _read_form(self) -> Product:
        name = self.var_name.get().strip()
        category = self.var_category.get().strip()
        supplier = self.var_supplier.get().strip()
        status = self.var_status.get().strip() or "Active"
        if not name:
            raise ValueError("Name is required")
        if category == "Select" or not category:
            raise ValueError("Select category")
        if supplier == "Select" or not supplier:
            raise ValueError("Select supplier")
        try:
            price = float(self.var_price.get().strip())
        except Exception:
            raise ValueError("Invalid price")
        try:
            qty = int(float(self.var_qty.get().strip()))
        except Exception:
            raise ValueError("Invalid quantity")
        if price < 0:
            raise ValueError("Price cannot be negative")
        if qty < 0:
            raise ValueError("Quantity cannot be negative")
        return Product(name=name, category=category, supplier=supplier, price=price, qty=qty, status=status)

    def _save(self) -> None:
        try:
            p = self._read_form()
            if self._repo.get(p.name):
                raise ValueError("Product already exists")
            self._repo.add(p)
            messagebox.showinfo("Success", "Product added")
            self._refresh_table()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _update(self) -> None:
        try:
            p = self._read_form()
            if not self._repo.get(p.name):
                raise ValueError("Product not found")
            self._repo.update(p)
            messagebox.showinfo("Success", "Product updated")
            self._refresh_table()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _delete(self) -> None:
        name = self.var_name.get().strip()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        if not messagebox.askyesno("Confirm", "Delete this product?"):
            return
        try:
            self._repo.delete(name)
            messagebox.showinfo("Success", "Product deleted")
            self._refresh_table()
            self._clear()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _clear(self) -> None:
        self.var_name.set("")
        self.var_category.set("Select")
        self.var_supplier.set("Select")
        self.var_price.set("0")
        self.var_qty.set("0")
        self.var_status.set("Active")
        self.tree.selection_remove(self.tree.selection())

    def _refresh_table(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for p in self._repo.list_all():
            self.tree.insert("", "end", values=(p.name, p.category, p.supplier, f"{p.price:.2f}", p.qty, p.status))

    def _search(self) -> None:
        try:
            field = self.var_search_by.get().strip()
            txt = self.var_search_txt.get().strip()
            for i in self.tree.get_children():
                self.tree.delete(i)
            for p in self._repo.search(field, txt):
                self.tree.insert("", "end", values=(p.name, p.category, p.supplier, f"{p.price:.2f}", p.qty, p.status))
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _on_select(self, _evt: Any) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        name = str(vals[0])
        p = self._repo.get(name)
        if not p:
            return
        self.var_name.set(p.name)
        self.var_category.set(p.category)
        self.var_supplier.set(p.supplier)
        self.var_price.set(str(p.price))
        self.var_qty.set(str(p.qty))
        self.var_status.set(p.status)


class BillingWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, prod_repo: ProductRepository, bill_repo: BillRepository) -> None:
        super().__init__(master, "Billing")
        self._prod_repo = prod_repo
        self._bill_repo = bill_repo

        self.var_invoice = tk.StringVar(value=self._generate_invoice())
        self.var_cust_name = tk.StringVar()
        self.var_cust_contact = tk.StringVar()

        self.var_search_product = tk.StringVar()
        self.var_selected_product = tk.StringVar(value="Select")
        self.var_price = tk.StringVar(value="0")
        self.var_qty = tk.StringVar(value="1")

        self.var_total = tk.StringVar(value="0.00")
        self.var_discount = tk.StringVar(value="0.00")
        self.var_net = tk.StringVar(value="0.00")
        self.var_paid = tk.StringVar(value="0.00")
        self.var_balance = tk.StringVar(value="0.00")

        self._cart: List[Tuple[str, float, int, float]] = []

        self._build()
        self._reload_products()
        self._recalc()
        self._center()

    def _generate_invoice(self) -> str:
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def _build(self) -> None:
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.Frame(root)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        cust = ttk.LabelFrame(left, text="Customer")
        cust.pack(fill="x", pady=(0, 10))
        cust.columnconfigure(1, weight=1)
        ttk.Label(cust, text="Invoice No").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(cust, textvariable=self.var_invoice, state="readonly").grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(cust, text="New", command=self._new_invoice).grid(row=0, column=2, sticky="ew", padx=8, pady=6)

        ttk.Label(cust, text="Name").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(cust, textvariable=self.var_cust_name).grid(row=1, column=1, columnspan=2, sticky="ew", padx=8, pady=6)
        ttk.Label(cust, text="Contact").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(cust, textvariable=self.var_cust_contact).grid(row=2, column=1, columnspan=2, sticky="ew", padx=8, pady=6)

        prod = ttk.LabelFrame(left, text="Add Product")
        prod.pack(fill="x", pady=(0, 10))
        prod.columnconfigure(1, weight=1)

        ttk.Label(prod, text="Search").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(prod, textvariable=self.var_search_product).grid(row=0, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(prod, text="Find", command=self._reload_products).grid(row=0, column=2, sticky="ew", padx=8, pady=6)

        ttk.Label(prod, text="Product").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        self.cb_products = ttk.Combobox(prod, textvariable=self.var_selected_product, values=["Select"], state="readonly")
        self.cb_products.grid(row=1, column=1, sticky="ew", padx=8, pady=6)
        self.cb_products.bind("<<ComboboxSelected>>", self._on_product_selected)

        ttk.Label(prod, text="Price").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(prod, textvariable=self.var_price, state="readonly").grid(row=2, column=1, sticky="ew", padx=8, pady=6)

        ttk.Label(prod, text="Qty").grid(row=3, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(prod, textvariable=self.var_qty).grid(row=3, column=1, sticky="ew", padx=8, pady=6)
        ttk.Button(prod, text="Add to Cart", command=self._add_to_cart).grid(row=3, column=2, sticky="ew", padx=8, pady=6)

        cart = ttk.LabelFrame(left, text="Cart")
        cart.pack(fill="both", expand=True)
        cols = ("name", "price", "qty", "amount")
        self.tree = ttk.Treeview(cart, columns=cols, show="headings", height=10)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120, anchor="w")
        self.tree.column("price", width=90, anchor="e")
        self.tree.column("qty", width=70, anchor="e")
        self.tree.column("amount", width=110, anchor="e")
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)
        self.tree.bind("<Delete>", self._remove_selected)

        btn_cart = ttk.Frame(cart)
        btn_cart.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(btn_cart, text="Remove Selected (Del)", command=self._remove_selected).pack(side="left")
        ttk.Button(btn_cart, text="Clear Cart", command=self._clear_cart).pack(side="left", padx=6)

        right = ttk.Frame(root)
        right.pack(side="left", fill="y")

        summary = ttk.LabelFrame(right, text="Summary")
        summary.pack(fill="x", pady=(0, 10))
        summary.columnconfigure(1, weight=1)

        def srow(r: int, label: str, var: tk.StringVar, readonly: bool = True) -> None:
            ttk.Label(summary, text=label).grid(row=r, column=0, sticky="w", padx=8, pady=6)
            state = "readonly" if readonly else "normal"
            ttk.Entry(summary, textvariable=var, state=state, width=18).grid(row=r, column=1, sticky="ew", padx=8, pady=6)

        srow(0, "Total", self.var_total, True)
        srow(1, "Discount", self.var_discount, False)
        srow(2, "Net Pay", self.var_net, True)
        srow(3, "Paid", self.var_paid, False)
        srow(4, "Balance", self.var_balance, True)

        self.var_discount.trace_add("write", lambda *_: self._recalc())
        self.var_paid.trace_add("write", lambda *_: self._recalc())

        actions = ttk.LabelFrame(right, text="Actions")
        actions.pack(fill="x")
        ttk.Button(actions, text="Generate Bill", command=self._generate_bill).pack(fill="x", padx=8, pady=6)
        ttk.Button(actions, text="Save Bill", command=self._save_bill).pack(fill="x", padx=8, pady=6)
        ttk.Button(actions, text="Print/Export Bill", command=self._export_bill).pack(fill="x", padx=8, pady=6)

        bill_view = ttk.LabelFrame(right, text="Bill Preview")
        bill_view.pack(fill="both", expand=True, pady=(10, 0))
        self.txt_bill = tk.Text(bill_view, width=40, height=18)
        self.txt_bill.pack(fill="both", expand=True, padx=6, pady=6)

    def _reload_products(self) -> None:
        q = self.var_search_product.get().strip()
        products = self._prod_repo.search("name", q) if q else self._prod_repo.list_all()
        names = ["Select"] + [p.name for p in products if p.status.lower() == "active"]
        self.cb_products["values"] = names
        if self.var_selected_product.get() not in names:
            self.var_selected_product.set("Select")
            self.var_price.set("0")

    def _on_product_selected(self, _evt: Any) -> None:
        name = self.var_selected_product.get().strip()
        if not name or name == "Select":
            self.var_price.set("0")
            return
        p = self._prod_repo.get(name)
        if not p:
            self.var_price.set("0")
            return
        self.var_price.set(f"{p.price:.2f}")

    def _add_to_cart(self) -> None:
        try:
            name = self.var_selected_product.get().strip()
            if not name or name == "Select":
                raise ValueError("Select a product")
            p = self._prod_repo.get(name)
            if not p:
                raise ValueError("Product not found")
            if p.status.lower() != "active":
                raise ValueError("Product is inactive")
            try:
                qty = int(float(self.var_qty.get().strip()))
            except Exception:
                raise ValueError("Invalid quantity")
            if qty <= 0:
                raise ValueError("Quantity must be positive")
            if qty > p.qty:
                raise ValueError("Insufficient stock")
            price = float(p.price)
            amount = price * qty

            for idx, (n, pr, q, am) in enumerate(self._cart):
                if n == name:
                    new_qty = q + qty
                    if new_qty > p.qty:
                        raise ValueError("Insufficient stock")
                    new_amount = pr * new_qty
                    self._cart[idx] = (n, pr, new_qty, new_amount)
                    self._render_cart()
                    self._recalc()
                    return

            self._cart.append((name, price, qty, amount))
            self._render_cart()
            self._recalc()
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _render_cart(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for n, pr, q, am in self._cart:
            self.tree.insert("", "end", values=(n, f"{pr:.2f}", q, f"{am:.2f}"))

    def _remove_selected(self, _evt: Any = None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], "values")
        name = str(vals[0])
        self._cart = [x for x in self._cart if x[0] != name]
        self._render_cart()
        self._recalc()

    def _clear_cart(self) -> None:
        self._cart.clear()
        self._render_cart()
        self._recalc()

    def _recalc(self) -> None:
        total = sum(am for *_rest, am in self._cart)
        try:
            discount = float(self.var_discount.get().strip() or "0")
        except Exception:
            discount = 0.0
        if discount < 0:
            discount = 0.0
        net = max(0.0, total - discount)
        try:
            paid = float(self.var_paid.get().strip() or "0")
        except Exception:
            paid = 0.0
        if paid < 0:
            paid = 0.0
        balance = net - paid
        self.var_total.set(f"{total:.2f}")
        self.var_discount.set(f"{discount:.2f}")
        self.var_net.set(f"{net:.2f}")
        self.var_paid.set(f"{paid:.2f}")
        self.var_balance.set(f"{balance:.2f}")

    def _new_invoice(self) -> None:
        self.var_invoice.set(self._generate_invoice())
        self.var_cust_name.set("")
        self.var_cust_contact.set("")
        self.var_search_product.set("")
        self.var_selected_product.set("Select")
        self.var_price.set("0")
        self.var_qty.set("1")
        self.var_discount.set("0.00")
        self.var_paid.set("0.00")
        self._clear_cart()
        self.txt_bill.delete("1.0", "end")

    def _bill_text(self) -> str:
        inv = self.var_invoice.get().strip()
        cust = self.var_cust_name.get().strip()
        contact = self.var_cust_contact.get().strip()
        created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines: List[str] = []
        lines.append("INVENTORY MANAGEMENT SYSTEM - BILL")
        lines.append(f"Invoice: {inv}")
        lines.append(f"Date: {created}")
        lines.append(f"Customer: {cust}")
        lines.append(f"Contact: {contact}")
        lines.append("-" * 44)
        lines.append(f"{'Item':20} {'Price':>8} {'Qty':>5} {'Amt':>8}")
        lines.append("-" * 44)
        for n, pr, q, am in self._cart:
            item = (n[:20]).ljust(20)
            lines.append(f"{item} {pr:>8.2f} {q:>5d} {am:>8.2f}")
        lines.append("-" * 44)
        total = float(self.var_total.get())
        discount = float(self.var_discount.get())
        net = float(self.var_net.get())
        paid = float(self.var_paid.get())
        balance = float(self.var_balance.get())
        lines.append(f"{'Total':>34} {total:>8.2f}")
        lines.append(f"{'Discount':>34} {discount:>8.2f}")
        lines.append(f"{'Net Pay':>34} {net:>8.2f}")
        lines.append(f"{'Paid':>34} {paid:>8.2f}")
        lines.append(f"{'Balance':>34} {balance:>8.2f}")
        lines.append("-" * 44)
        lines.append("Thank you!")
        return "\n".join(lines)

    def _generate_bill(self) -> None:
        try:
            if not self._cart:
                raise ValueError("Cart is empty")
            if not self.var_cust_name.get().strip() or not self.var_cust_contact.get().strip():
                raise ValueError("Customer details are required")
            self._recalc()
            txt = self._bill_text()
            self.txt_bill.delete("1.0", "end")
            self.txt_bill.insert("1.0", txt)
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _save_bill(self) -> None:
        try:
            inv = self.var_invoice.get().strip()
            if not inv:
                raise ValueError("Invoice is required")
            if self._bill_repo.get(inv):
                raise ValueError("Invoice already saved")
            if not self._cart:
                raise ValueError("Cart is empty")
            if not self.var_cust_name.get().strip() or not self.var_cust_contact.get().strip():
                raise ValueError("Customer details are required")

            for n, _pr, q, _am in self._cart:
                self._prod_repo.adjust_stock(n, -q)

            self._recalc()
            created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            content = self.txt_bill.get("1.0", "end").strip()
            if not content:
                content = self._bill_text()
                self.txt_bill.delete("1.0", "end")
                self.txt_bill.insert("1.0", content)

            b = Bill(
                invoice=inv,
                customer_name=self.var_cust_name.get().strip(),
                customer_contact=self.var_cust_contact.get().strip(),
                total=float(self.var_total.get()),
                discount=float(self.var_discount.get()),
                net_pay=float(self.var_net.get()),
                paid=float(self.var_paid.get()),
                balance=float(self.var_balance.get()),
                created_at=created,
                content=content,
            )
            self._bill_repo.add(b)
            messagebox.showinfo("Success", "Bill saved")
        except Exception as ex:
            messagebox.showerror("Error", str(ex))

    def _export_bill(self) -> None:
        try:
            content = self.txt_bill.get("1.0", "end").strip()
            if not content:
                raise ValueError("Generate bill first")
            initial = f"bill_{self.var_invoice.get().strip() or 'invoice'}.txt"
            path = filedialog.asksaveasfilename(
                title="Save Bill",
                defaultextension=".txt",
                initialfile=initial,
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            )
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Success", f"Bill saved to:\n{path}")
        except Exception as ex:
            messagebox.showerror("Error", str(ex))


class BillViewerWindow(BaseManagerWindow):
    def __init__(self, master: tk.Tk, repo: BillRepository) -> None:
        super().__init__(master, "Bill Viewer")
        self._repo = repo
        self.var_invoice = tk.StringVar()
        self._build()
        self._refresh_list()
        self._center()

    def _build(self) -> None:
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.LabelFrame(root, text="Bills (by Invoice No)")
        left.pack(side="left", fill="y", padx=(0, 10))

        top = ttk.Frame(left)
        top.pack(fill="x", padx=6, pady=6)
        ttk.Entry(top, textvariable=self.var_invoice, width=18).pack(side="left")
        ttk.Button(top, text="Search", command=self._search).pack(side="left", padx=6)
        ttk.Button(top, text="Show All", command=self._refresh_list).pack(side="left")

        self.listbox = tk.Listbox(left, width=28, height=25)
        self.listbox.pack(fill="both", expand=True, padx=6, pady=6)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        right = ttk.LabelFrame(root, text="Bill")
        right.pack(side="left", fill="both", expand=True)
        self.txt = tk.Text(right)
        self.txt.pack(fill="both", expand=True, padx=6, pady=6)

    def _refresh_list(self) -> None:
        self.listbox.delete(0, "end")
        for b in self._repo.list_all():
            self.listbox.insert("end", b.invoice)

    def _search(self) -> None:
        self.listbox.delete(0, "end")
        for b in self._repo.search_by_invoice(self.var_invoice.get().strip()):
            self.listbox.insert("end", b.invoice)

    def _on_select(self, _evt: Any) -> None:
        sel = self.listbox.curselection()
        if not sel:
            return
        inv = self.listbox.get(sel[0])
        b = self._repo.get(inv)
        if not b:
            return
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", b.content)


class Dashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1100x650")
        self.minsize(1000, 600)

        self._db = Database("ims.db")
        self._emp_repo = EmployeeRepository(self._db)
        self._sup_repo = SupplierRepository(self._db)
        self._cat_repo = CategoryRepository(self._db)
        self._prod_repo = ProductRepository(self._db)
        self._bill_repo = BillRepository(self._db)

        self._img = ImageManager()
        self._header_img_ref: Optional[Any] = None

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()
        self._tick()
        self._refresh_counts()

    def _build(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x")

        title = ttk.Label(header, text="Inventory Management System", font=("Arial", 20, "bold"))
        title.pack(side="left", padx=12, pady=12)

        self.lbl_time = ttk.Label(header, text="", font=("Arial", 11))
        self.lbl_time.pack(side="right", padx=12)

        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=12, pady=12)

        left = ttk.Frame(main)
        left.pack(side="left", fill="y", padx=(0, 12))

        btn_style = {"width": 22}
        ttk.Button(left, text="Employees", command=self._open_employees, **btn_style).pack(fill="x", pady=6)
        ttk.Button(left, text="Suppliers", command=self._open_suppliers, **btn_style).pack(fill="x", pady=6)
        ttk.Button(left, text="Categories", command=self._open_categories, **btn_style).pack(fill="x", pady=6)
        ttk.Button(left, text="Products", command=self._open_products, **btn_style).pack(fill="x", pady=6)
        ttk.Button(left, text="Billing", command=self._open_billing, **btn_style).pack(fill="x", pady=6)
        ttk.Button(left, text="Bill Viewer", command=self._open_bill_viewer, **btn_style).pack(fill="x", pady=6)
        ttk.Button(left, text="Refresh Dashboard", command=self._refresh_counts, **btn_style).pack(fill="x", pady=6)

        right = ttk.Frame(main)
        right.pack(side="left", fill="both", expand=True)

        banner = ttk.LabelFrame(right, text="Dashboard")
        banner.pack(fill="both", expand=True)

        self.lbl_banner = ttk.Label(banner, text="Welcome", font=("Arial", 16, "bold"))
        self.lbl_banner.pack(anchor="w", padx=10, pady=(10, 0))

        self.lbl_counts = ttk.Label(banner, text="", font=("Arial", 12))
        self.lbl_counts.pack(anchor="w", padx=10, pady=10)

        img_frame = ttk.Frame(banner)
        img_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(img_frame, bg="white", highlightthickness=1, highlightbackground="#ccc")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._draw_placeholder)

    def _draw_placeholder(self, _evt: Any = None) -> None:
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        self.canvas.create_rectangle(10, 10, max(11, w - 10), max(11, h - 10), outline="#999")
        self.canvas.create_text(w // 2, h // 2, text="Dashboard Image Area", fill="#666", font=("Arial", 14))

    def _tick(self) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_time.config(text=now)
        self.after(1000, self._tick)

    def _refresh_counts(self) -> None:
        try:
            emp = len(self._emp_repo.list_all())
            sup = len(self._sup_repo.list_all())
            cat = len(self._cat_repo.list_all())
            prod = len(self._prod_repo.list_all())
            bills = len(self._bill_repo.list_all())
            self.lbl_counts.config(
                text=f"Employees: {emp}\nSuppliers: {sup}\nCategories: {cat}\nProducts: {prod}\nBills: {bills}"
            )
        except Exception as ex:
            self.lbl_counts.config(text=f"Error loading counts: {ex}")

    def _open_employees(self) -> None:
        EmployeeManagerWindow(self, self._emp_repo)

    def _open_suppliers(self) -> None:
        SupplierManagerWindow(self, self._sup_repo)

    def _open_categories(self) -> None:
        CategoryManagerWindow(self, self._cat_repo)

    def _open_products(self) -> None:
        ProductManagerWindow(self, self._prod_repo, self._cat_repo, self._sup_repo)

    def _open_billing(self) -> None:
        BillingWindow(self, self._prod_repo, self._bill_repo)

    def _open_bill_viewer(self) -> None:
        BillViewerWindow(self, self._bill_repo)

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