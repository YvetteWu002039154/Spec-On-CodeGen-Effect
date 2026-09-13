import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont
from PIL import Image, ImageTk
import sqlite3
import os
import datetime
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Employee:
    id: Optional[int] = None
    name: str = ""
    contact: str = ""
    email: str = ""
    address: str = ""
    join_date: str = ""

    def validate(self) -> Tuple[bool, str]:
        if not self.name.strip():
            return False, "Name is required"
        if not self.contact.strip():
            return False, "Contact is required"
        if self.contact.strip() and not self.contact.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            return False, "Contact must be numeric"
        if self.email.strip() and "@" not in self.email:
            return False, "Invalid email"
        if not self.join_date.strip():
            self.join_date = datetime.date.today().isoformat()
        return True, ""


@dataclass
class Supplier:
    id: Optional[int] = None
    name: str = ""
    contact: str = ""
    email: str = ""
    address: str = ""
    gst: str = ""

    def validate(self) -> Tuple[bool, str]:
        if not self.name.strip():
            return False, "Name is required"
        if not self.contact.strip():
            return False, "Contact is required"
        if self.contact.strip() and not self.contact.replace("+", "").replace("-", "").replace(" ", "").isdigit():
            return False, "Contact must be numeric"
        if self.email.strip() and "@" not in self.email:
            return False, "Invalid email"
        return True, ""


@dataclass
class Category:
    id: Optional[int] = None
    name: str = ""

    def validate(self) -> Tuple[bool, str]:
        if not self.name.strip():
            return False, "Category name is required"
        return True, ""


@dataclass
class Product:
    id: Optional[int] = None
    name: str = ""
    category_id: Optional[int] = None
    price: float = 0.0
    quantity: int = 0
    supplier_id: Optional[int] = None

    def validate(self) -> Tuple[bool, str]:
        if not self.name.strip():
            return False, "Product name is required"
        if self.price < 0:
            return False, "Price must be non-negative"
        if self.quantity < 0:
            return False, "Quantity must be non-negative"
        if self.category_id is None:
            return False, "Category is required"
        if self.supplier_id is None:
            return False, "Supplier is required"
        return True, ""


@dataclass
class BillItem:
    product_id: int
    quantity: int
    price: float
    total: float


class Database:
    def __init__(self, db_name: str = "inventory.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                email TEXT,
                address TEXT,
                join_date TEXT
            )
        """)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                email TEXT,
                address TEXT,
                gst TEXT
            )
        """)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER,
                price REAL DEFAULT 0,
                quantity INTEGER DEFAULT 0,
                supplier_id INTEGER,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            )
        """)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT UNIQUE NOT NULL,
                date TEXT NOT NULL,
                customer_name TEXT,
                total_amount REAL DEFAULT 0,
                tax REAL DEFAULT 0,
                grand_total REAL DEFAULT 0
            )
        """)
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS bill_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                price REAL,
                total REAL,
                FOREIGN KEY (bill_id) REFERENCES bills(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        self.conn.commit()

    # Employee CRUD
    def insert_employee(self, emp: Employee) -> int:
        self.cur.execute(
            "INSERT INTO employees (name, contact, email, address, join_date) VALUES (?, ?, ?, ?, ?)",
            (emp.name, emp.contact, emp.email, emp.address, emp.join_date)
        )
        self.conn.commit()
        return self.cur.lastrowid

    def update_employee(self, emp: Employee):
        self.cur.execute(
            "UPDATE employees SET name=?, contact=?, email=?, address=?, join_date=? WHERE id=?",
            (emp.name, emp.contact, emp.email, emp.address, emp.join_date, emp.id)
        )
        self.conn.commit()

    def delete_employee(self, emp_id: int):
        self.cur.execute("DELETE FROM employees WHERE id=?", (emp_id,))
        self.conn.commit()

    def fetch_employees(self, search: str = "") -> List[Dict[str, Any]]:
        if search:
            self.cur.execute("SELECT * FROM employees WHERE name LIKE ? OR contact LIKE ?",
                             (f'%{search}%', f'%{search}%'))
        else:
            self.cur.execute("SELECT * FROM employees")
        return [dict(row) for row in self.cur.fetchall()]

    def get_employee(self, emp_id: int) -> Optional[Dict[str, Any]]:
        self.cur.execute("SELECT * FROM employees WHERE id=?", (emp_id,))
        row = self.cur.fetchone()
        return dict(row) if row else None

    # Supplier CRUD
    def insert_supplier(self, sup: Supplier) -> int:
        self.cur.execute(
            "INSERT INTO suppliers (name, contact, email, address, gst) VALUES (?, ?, ?, ?, ?)",
            (sup.name, sup.contact, sup.email, sup.address, sup.gst)
        )
        self.conn.commit()
        return self.cur.lastrowid

    def update_supplier(self, sup: Supplier):
        self.cur.execute(
            "UPDATE suppliers SET name=?, contact=?, email=?, address=?, gst=? WHERE id=?",
            (sup.name, sup.contact, sup.email, sup.address, sup.gst, sup.id)
        )
        self.conn.commit()

    def delete_supplier(self, sup_id: int):
        self.cur.execute("DELETE FROM suppliers WHERE id=?", (sup_id,))
        self.conn.commit()

    def fetch_suppliers(self, search: str = "") -> List[Dict[str, Any]]:
        if search:
            self.cur.execute("SELECT * FROM suppliers WHERE name LIKE ? OR contact LIKE ?",
                             (f'%{search}%', f'%{search}%'))
        else:
            self.cur.execute("SELECT * FROM suppliers")
        return [dict(row) for row in self.cur.fetchall()]

    def get_supplier(self, sup_id: int) -> Optional[Dict[str, Any]]:
        self.cur.execute("SELECT * FROM suppliers WHERE id=?", (sup_id,))
        row = self.cur.fetchone()
        return dict(row) if row else None

    # Category CRUD
    def insert_category(self, cat: Category) -> int:
        try:
            self.cur.execute("INSERT INTO categories (name) VALUES (?)", (cat.name,))
            self.conn.commit()
            return self.cur.lastrowid
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Category already exists")
            return -1

    def update_category(self, cat: Category):
        try:
            self.cur.execute("UPDATE categories SET name=? WHERE id=?", (cat.name, cat.id))
            self.conn.commit()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Category name must be unique")

    def delete_category(self, cat_id: int):
        # Check if category is in use
        self.cur.execute("SELECT COUNT(*) FROM products WHERE category_id=?", (cat_id,))
        if self.cur.fetchone()[0] > 0:
            messagebox.showerror("Error", "Cannot delete category used by products")
            return
        self.cur.execute("DELETE FROM categories WHERE id=?", (cat_id,))
        self.conn.commit()

    def fetch_categories(self) -> List[Dict[str, Any]]:
        self.cur.execute("SELECT * FROM categories")
        return [dict(row) for row in self.cur.fetchall()]

    def get_category(self, cat_id: int) -> Optional[Dict[str, Any]]:
        self.cur.execute("SELECT * FROM categories WHERE id=?", (cat_id,))
        row = self.cur.fetchone()
        return dict(row) if row else None

    # Product CRUD
    def insert_product(self, prod: Product) -> int:
        self.cur.execute(
            "INSERT INTO products (name, category_id, price, quantity, supplier_id) VALUES (?, ?, ?, ?, ?)",
            (prod.name, prod.category_id, prod.price, prod.quantity, prod.supplier_id)
        )
        self.conn.commit()
        return self.cur.lastrowid

    def update_product(self, prod: Product):
        self.cur.execute(
            "UPDATE products SET name=?, category_id=?, price=?, quantity=?, supplier_id=? WHERE id=?",
            (prod.name, prod.category_id, prod.price, prod.quantity, prod.supplier_id, prod.id)
        )
        self.conn.commit()

    def delete_product(self, prod_id: int):
        self.cur.execute("DELETE FROM products WHERE id=?", (prod_id,))
        self.conn.commit()

    def fetch_products(self, search: str = "") -> List[Dict[str, Any]]:
        if search:
            self.cur.execute("SELECT * FROM products WHERE name LIKE ? OR id LIKE ?",
                             (f'%{search}%', f'%{search}%'))
        else:
            self.cur.execute("SELECT * FROM products")
        return [dict(row) for row in self.cur.fetchall()]

    def get_product(self, prod_id: int) -> Optional[Dict[str, Any]]:
        self.cur.execute("SELECT * FROM products WHERE id=?", (prod_id,))
        row = self.cur.fetchone()
        return dict(row) if row else None

    # Bill generation
    def generate_invoice_no(self) -> str:
        today = datetime.date.today().strftime("%Y%m%d")
        self.cur.execute("SELECT COUNT(*) FROM bills WHERE date LIKE ?", (f'{today}%',))
        count = self.cur.fetchone()[0] + 1
        return f"INV-{today}-{count:04d}"

    def create_bill(self, customer_name: str, items: List[BillItem]) -> str:
        invoice_no = self.generate_invoice_no()
        date = datetime.date.today().isoformat()
        total = sum(item.total for item in items)
        tax = total * 0.1  # 10% tax
        grand_total = total + tax
        self.cur.execute(
            "INSERT INTO bills (invoice_no, date, customer_name, total_amount, tax, grand_total) VALUES (?, ?, ?, ?, ?, ?)",
            (invoice_no, date, customer_name, total, tax, grand_total)
        )
        bill_id = self.cur.lastrowid
        for item in items:
            self.cur.execute(
                "INSERT INTO bill_items (bill_id, product_id, quantity, price, total) VALUES (?, ?, ?, ?, ?)",
                (bill_id, item.product_id, item.quantity, item.price, item.total)
            )
            # Update stock
            self.cur.execute("UPDATE products SET quantity = quantity - ? WHERE id=?", (item.quantity, item.product_id))
        self.conn.commit()
        return invoice_no

    def fetch_bills(self, search: str = "") -> List[Dict[str, Any]]:
        if search:
            self.cur.execute("SELECT * FROM bills WHERE invoice_no LIKE ? OR customer_name LIKE ?",
                             (f'%{search}%', f'%{search}%'))
        else:
            self.cur.execute("SELECT * FROM bills ORDER BY date DESC")
        return [dict(row) for row in self.cur.fetchall()]

    def get_bill_details(self, bill_id: int) -> Optional[Dict[str, Any]]:
        self.cur.execute("SELECT * FROM bills WHERE id=?", (bill_id,))
        bill = self.cur.fetchone()
        if not bill:
            return None
        bill = dict(bill)
        self.cur.execute("SELECT * FROM bill_items WHERE bill_id=?", (bill_id,))
        bill['items'] = [dict(row) for row in self.cur.fetchall()]
        return bill

    def close(self):
        self.conn.close()


class BaseManagementWindow(tk.Toplevel):
    """Base class for entity management windows (Employee, Supplier, Product, Category)."""
    def __init__(self, parent, db: Database, title: str):
        super().__init__(parent)
        self.db = db
        self.title(title)
        self.geometry("900x550")
        self.configure(bg="#f0f0f0")
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        raise NotImplementedError

    def load_data(self):
        raise NotImplementedError

    def clear_form(self):
        raise NotImplementedError

    def save(self):
        raise NotImplementedError

    def edit(self):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError


class EmployeeWindow(BaseManagementWindow):
    def __init__(self, parent, db: Database):
        super().__init__(parent, db, "Employee Management")

    def create_widgets(self):
        # Form Frame
        form_frame = tk.LabelFrame(self, text="Employee Details", bg="#f0f0f0", font=('Arial', 11, 'bold'))
        form_frame.pack(pady=10, padx=10, fill="x")

        tk.Label(form_frame, text="Name:", bg="#f0f0f0").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.name_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Contact:", bg="#f0f0f0").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.contact_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.contact_var, width=30).grid(row=1, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Email:", bg="#f0f0f0").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.email_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.email_var, width=30).grid(row=2, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Address:", bg="#f0f0f0").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.address_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.address_var, width=30).grid(row=3, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Join Date (YYYY-MM-DD):", bg="#f0f0f0").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        self.date_var = tk.StringVar(value=datetime.date.today().isoformat())
        tk.Entry(form_frame, textvariable=self.date_var, width=30).grid(row=4, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(form_frame, bg="#f0f0f0")
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        self.add_btn = tk.Button(btn_frame, text="Add", command=self.save, bg="#4CAF50", fg="white", width=8)
        self.add_btn.pack(side=tk.LEFT, padx=5)
        self.edit_btn = tk.Button(btn_frame, text="Update", command=self.edit, bg="#2196F3", fg="white", width=8)
        self.edit_btn.pack(side=tk.LEFT, padx=5)
        self.del_btn = tk.Button(btn_frame, text="Delete", command=self.delete, bg="#f44336", fg="white", width=8)
        self.del_btn.pack(side=tk.LEFT, padx=5)
        self.clear_btn = tk.Button(btn_frame, text="Clear", command=self.clear_form, bg="#FF9800", fg="white", width=8)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # Search and List
        list_frame = tk.LabelFrame(self, text="Employee List", bg="#f0f0f0", font=('Arial', 11, 'bold'))
        list_frame.pack(pady=10, padx=10, fill="both", expand=True)

        search_frame = tk.Frame(list_frame, bg="#f0f0f0")
        search_frame.pack(pady=5, fill="x")

        tk.Label(search_frame, text="Search:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.load_data())
        tk.Entry(search_frame, textvariable=self.search_var, width=20).pack(side=tk.LEFT, padx=5)

        columns = ("id", "name", "contact", "email", "address", "join_date")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("contact", text="Contact")
        self.tree.heading("email", text="Email")
        self.tree.heading("address", text="Address")
        self.tree.heading("join_date", text="Join Date")
        self.tree.column("id", width=30)
        self.tree.column("name", width=150)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<Double-1>", self.on_select)

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])['values']
            self.name_var.set(values[1])
            self.contact_var.set(values[2])
            self.email_var.set(values[3])
            self.address_var.set(values[4])
            self.date_var.set(values[5])
            self.selected_id = values[0]
            self.add_btn.config(state="disabled")
            self.edit_btn.config(state="normal")
            self.del_btn.config(state="normal")

    def clear_form(self):
        self.name_var.set("")
        self.contact_var.set("")
        self.email_var.set("")
        self.address_var.set("")
        self.date_var.set(datetime.date.today().isoformat())
        self.selected_id = None
        self.add_btn.config(state="normal")
        self.edit_btn.config(state="disabled")
        self.del_btn.config(state="disabled")

    def load_data(self, *args):
        search = self.search_var.get()
        employees = self.db.fetch_employees(search)
        for row in self.tree.get_children():
            self.tree.delete(row)
        for emp in employees:
            self.tree.insert("", "end",
                             values=(emp['id'], emp['name'], emp['contact'], emp['email'], emp['address'], emp['join_date']))

    def save(self):
        emp = Employee(
            name=self.name_var.get(),
            contact=self.contact_var.get(),
            email=self.email_var.get(),
            address=self.address_var.get(),
            join_date=self.date_var.get()
        )
        valid, msg = emp.validate()
        if not valid:
            messagebox.showerror("Validation Error", msg)
            return
        self.db.insert_employee(emp)
        messagebox.showinfo("Success", "Employee added")
        self.clear_form()
        self.load_data()

    def edit(self):
        if not hasattr(self, 'selected_id') or not self.selected_id:
            messagebox.showerror("Error", "Select an employee to edit")
            return
        emp = Employee(
            id=self.selected_id,
            name=self.name_var.get(),
            contact=self.contact_var.get(),
            email=self.email_var.get(),
            address=self.address_var.get(),
            join_date=self.date_var.get()
        )
        valid, msg = emp.validate()
        if not valid:
            messagebox.showerror("Validation Error", msg)
            return
        self.db.update_employee(emp)
        messagebox.showinfo("Success", "Employee updated")
        self.clear_form()
        self.load_data()

    def delete(self):
        if not hasattr(self, 'selected_id') or not self.selected_id:
            messagebox.showerror("Error", "Select an employee to delete")
            return
        if messagebox.askyesno("Confirm", "Delete this employee?"):
            self.db.delete_employee(self.selected_id)
            messagebox.showinfo("Success", "Employee deleted")
            self.clear_form()
            self.load_data()


class SupplierWindow(BaseManagementWindow):
    def __init__(self, parent, db: Database):
        super().__init__(parent, db, "Supplier Management")

    def create_widgets(self):
        form_frame = tk.LabelFrame(self, text="Supplier Details", bg="#f0f0f0", font=('Arial', 11, 'bold'))
        form_frame.pack(pady=10, padx=10, fill="x")

        tk.Label(form_frame, text="Name:", bg="#f0f0f0").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.name_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Contact:", bg="#f0f0f0").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.contact_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.contact_var, width=30).grid(row=1, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Email:", bg="#f0f0f0").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.email_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.email_var, width=30).grid(row=2, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Address:", bg="#f0f0f0").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.address_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.address_var, width=30).grid(row=3, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="GST:", bg="#f0f0f0").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        self.gst_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.gst_var, width=30).grid(row=4, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(form_frame, bg="#f0f0f0")
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        self.add_btn = tk.Button(btn_frame, text="Add", command=self.save, bg="#4CAF50", fg="white", width=8)
        self.add_btn.pack(side=tk.LEFT, padx=5)
        self.edit_btn = tk.Button(btn_frame, text="Update", command=self.edit, bg="#2196F3", fg="white", width=8)
        self.edit_btn.pack(side=tk.LEFT, padx=5)
        self.del_btn = tk.Button(btn_frame, text="Delete", command=self.delete, bg="#f44336", fg="white", width=8)
        self.del_btn.pack(side=tk.LEFT, padx=5)
        self.clear_btn = tk.Button(btn_frame, text="Clear", command=self.clear_form, bg="#FF9800", fg="white", width=8)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        list_frame = tk.LabelFrame(self, text="Supplier List", bg="#f0f0f0", font=('Arial', 11, 'bold'))
        list_frame.pack(pady=10, padx=10, fill="both", expand=True)

        search_frame = tk.Frame(list_frame, bg="#f0f0f0")
        search_frame.pack(pady=5, fill="x")
        tk.Label(search_frame, text="Search:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.load_data())
        tk.Entry(search_frame, textvariable=self.search_var, width=20).pack(side=tk.LEFT, padx=5)

        columns = ("id", "name", "contact", "email", "address", "gst")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=col.capitalize())
        self.tree.column("id", width=30)
        self.tree.column("name", width=150)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<Double-1>", self.on_select)

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])['values']
            self.name_var.set(values[1])
            self.contact_var.set(values[2])
            self.email_var.set(values[3])
            self.address_var.set(values[4])
            self.gst_var.set(values[5])
            self.selected_id = values[0]
            self.add_btn.config(state="disabled")
            self.edit_btn.config(state="normal")
            self.del_btn.config(state="normal")

    def clear_form(self):
        self.name_var.set("")
        self.contact_var.set("")
        self.email_var.set("")
        self.address_var.set("")
        self.gst_var.set("")
        self.selected_id = None
        self.add_btn.config(state="normal")
        self.edit_btn.config(state="disabled")
        self.del_btn.config(state="disabled")

    def load_data(self, *args):
        search = self.search_var.get()
        suppliers = self.db.fetch_suppliers(search)
        for row in self.tree.get_children():
            self.tree.delete(row)
        for sup in suppliers:
            self.tree.insert("", "end",
                             values=(sup['id'], sup['name'], sup['contact'], sup['email'], sup['address'], sup['gst']))

    def save(self):
        sup = Supplier(
            name=self.name_var.get(),
            contact=self.contact_var.get(),
            email=self.email_var.get(),
            address=self.address_var.get(),
            gst=self.gst_var.get()
        )
        valid, msg = sup.validate()
        if not valid:
            messagebox.showerror("Validation Error", msg)
            return
        self.db.insert_supplier(sup)
        messagebox.showinfo("Success", "Supplier added")
        self.clear_form()
        self.load_data()

    def edit(self):
        if not hasattr(self, 'selected_id') or not self.selected_id:
            messagebox.showerror("Error", "Select a supplier to edit")
            return
        sup = Supplier(
            id=self.selected_id,
            name=self.name_var.get(),
            contact=self.contact_var.get(),
            email=self.email_var.get(),
            address=self.address_var.get(),
            gst=self.gst_var.get()
        )
        valid, msg = sup.validate()
        if not valid:
            messagebox.showerror("Validation Error", msg)
            return
        self.db.update_supplier(sup)
        messagebox.showinfo("Success", "Supplier updated")
        self.clear_form()
        self.load_data()

    def delete(self):
        if not hasattr(self, 'selected_id') or not self.selected_id:
            messagebox.showerror("Error", "Select a supplier to delete")
            return
        if messagebox.askyesno("Confirm", "Delete this supplier?"):
            self.db.delete_supplier(self.selected_id)
            messagebox.showinfo("Success", "Supplier deleted")
            self.clear_form()
            self.load_data()


class CategoryWindow(BaseManagementWindow):
    def __init__(self, parent, db: Database):
        super().__init__(parent, db, "Category Management")

    def create_widgets(self):
        form_frame = tk.LabelFrame(self, text="Category Details", bg="#f0f0f0", font=('Arial', 11, 'bold'))
        form_frame.pack(pady=10, padx=10, fill="x")

        tk.Label(form_frame, text="Name:", bg="#f0f0f0").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.name_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(form_frame, bg="#f0f0f0")
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10)

        self.add_btn = tk.Button(btn_frame, text="Add", command=self.save, bg="#4CAF50", fg="white", width=8)
        self.add_btn.pack(side=tk.LEFT, padx=5)
        self.edit_btn = tk.Button(btn_frame, text="Update", command=self.edit, bg="#2196F3", fg="white", width=8)
        self.edit_btn.pack(side=tk.LEFT, padx=5)
        self.del_btn = tk.Button(btn_frame, text="Delete", command=self.delete, bg="#f44336", fg="white", width=8)
        self.del_btn.pack(side=tk.LEFT, padx=5)
        self.clear_btn = tk.Button(btn_frame, text="Clear", command=self.clear_form, bg="#FF9800", fg="white", width=8)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        list_frame = tk.LabelFrame(self, text="Category List", bg="#f0f0f0", font=('Arial', 11, 'bold'))
        list_frame.pack(pady=10, padx=10, fill="both", expand=True)

        columns = ("id", "name")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Name")
        self.tree.column("id", width=30)
        self.tree.column("name", width=200)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<Double-1>", self.on_select)

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])['values']
            self.name_var.set(values[1])
            self.selected_id = values[0]
            self.add_btn.config(state="disabled")
            self.edit_btn.config(state="normal")
            self.del_btn.config(state="normal")

    def clear_form(self):
        self.name_var.set("")
        self.selected_id = None
        self.add_btn.config(state="normal")
        self.edit_btn.config(state="disabled")
        self.del_btn.config(state="disabled")

    def load_data(self, *args):
        categories = self.db.fetch_categories()
        for row in self.tree.get_children():
            self.tree.delete(row)
        for cat in categories:
            self.tree.insert("", "end", values=(cat['id'], cat['name']))

    def save(self):
        cat = Category(name=self.name_var.get())
        valid, msg = cat.validate()
        if not valid:
            messagebox.showerror("Validation Error", msg)
            return
        result = self.db.insert_category(cat)
        if result != -1:
            messagebox.showinfo("Success", "Category added")
            self.clear_form()
            self.load_data()

    def edit(self):
        if not hasattr(self, 'selected_id') or not self.selected_id:
            messagebox.showerror("Error", "Select a category to edit")
            return
        cat = Category(id=self.selected_id, name=self.name_var.get())
        valid, msg = cat.validate()
        if not valid:
            messagebox.showerror("Validation Error", msg)
            return
        self.db.update_category(cat)
        messagebox.showinfo("Success", "Category updated")
        self.clear_form()
        self.load_data()

    def delete(self):
        if not hasattr(self, 'selected_id') or not self.selected_id:
            messagebox.showerror("Error", "Select a category to delete")
            return
        if messagebox.askyesno("Confirm", "Delete this category?"):
            self.db.delete_category(self.selected_id)
            self.clear_form()
            self.load_data()


class ProductWindow(BaseManagementWindow):
    def __init__(self, parent, db: Database):
        super().__init__(parent, db, "Product Management")

    def create_widgets(self):
        form_frame = tk.LabelFrame(self, text="Product Details", bg="#f0f0f0", font=('Arial', 11, 'bold'))
        form_frame.pack(pady=10, padx=10, fill="x")

        tk.Label(form_frame, text="Name:", bg="#f0f0f0").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.name_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.name_var, width=30).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Category:", bg="#f0f0f0").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.category_var = tk.StringVar()
        self.category_cb = ttk.Combobox(form_frame, textvariable=self.category_var, state="readonly", width=28)
        self.category_cb.grid(row=1, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Price:", bg="#f0f0f0").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.price_var = tk.StringVar(value="0.0")
        tk.Entry(form_frame, textvariable=self.price_var, width=30).grid(row=2, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Quantity:", bg="#f0f0f0").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.qty_var = tk.StringVar(value="0")
        tk.Entry(form_frame, textvariable=self.qty_var, width=30).grid(row=3, column=1, padx=5, pady=5)

        tk.Label(form_frame, text="Supplier:", bg="#f0f0f0").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        self.supplier_var = tk.StringVar()
        self.supplier_cb = ttk.Combobox(form_frame, textvariable=self.supplier_var, state="readonly", width=28)
        self.supplier_cb.grid(row=4, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(form_frame, bg="#f0f0f0")
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        self.add_btn = tk.Button(btn_frame, text="Add", command=self.save, bg="#4CAF50", fg="white", width=8)
        self.add_btn.pack(side=tk.LEFT, padx=5)
        self.edit_btn = tk.Button(btn_frame, text="Update", command=self.edit, bg="#2196F3", fg="white", width=8)
        self.edit_btn.pack(side=tk.LEFT, padx=5)
        self.del_btn = tk.Button(btn_frame, text="Delete", command=self.delete, bg="#f44336", fg="white", width=8)
        self.del_btn.pack(side=tk.LEFT, padx=5)
        self.clear_btn = tk.Button(btn_frame, text="Clear", command=self.clear_form, bg="#FF9800", fg="white", width=8)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        list_frame = tk.LabelFrame(self, text="Product List", bg="#f0f0f0", font=('Arial', 11, 'bold'))
        list_frame.pack(pady=10, padx=10, fill="both", expand=True)

        search_frame = tk.Frame(list_frame, bg="#f0f0f0")
        search_frame.pack(pady=5, fill="x")
        tk.Label(search_frame, text="Search:", bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.load_data())
        tk.Entry(search_frame, textvariable=self.search_var, width=20).pack(side=tk.LEFT, padx=5)

        columns = ("id", "name", "category", "price", "quantity", "supplier")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=col.capitalize())
        self.tree.column("id", width=30)
        self.tree.column("name", width=150)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)
        self.tree.bind("<Double-1>", self.on_select)

        # Load drop-down data
        self.load_dropdowns()

    def load_dropdowns(self):
        # Load categories
        cats = self.db.fetch_categories()
        cat_names = [c['name'] for c in cats]
        self.category_cb['values'] = cat_names
        self.cat_dict = {c['name']: c['id'] for c in cats}

        # Load suppliers
        sups = self.db.fetch_suppliers()
        sup_names = [s['name'] for s in sups]
        self.supplier_cb['values'] = sup_names
        self.sup_dict = {s['name']: s['id'] for s in sups}

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])['values']
            self.name_var.set(values[1])
            self.category_var.set(values[2])
            self.price_var.set(values[3])
            self.qty_var.set(values[4])
            self.supplier_var.set(values[5])
            self.selected_id = values[0]
            self.add_btn.config(state="disabled")
            self.edit_btn.config(state="normal")
            self.del_btn.config(state="normal")

    def clear_form(self):
        self.name_var.set("")
        self.category_var.set("")
        self.price_var.set("0.0")
        self.qty_var.set("0")
        self.supplier_var.set("")
        self.selected_id = None
        self.add_btn.config(state="normal")
        self.edit_btn.config(state="disabled")
        self.del_btn.config(state="disabled")

    def load_data(self, *args):
        search = self.search_var.get()
        products = self.db.fetch_products(search)
        for row in self.tree.get_children():
            self.tree.delete(row)
        for prod in products:
            # Resolve foreign keys for display
            cat = self.db.get_category(prod['category_id'])
            sup = self.db.get_supplier(prod['supplier_id'])
            cat_name = cat['name'] if cat else "N/A"
            sup_name = sup['name'] if sup else "N/A"
            self.tree.insert("", "end",
                             values=(prod['id'], prod['name'], cat_name, prod['price'], prod['quantity'], sup_name))
        self.load_dropdowns()

    def save(self):
        cat_name = self.category_var.get()
        sup_name = self.supplier_var.get()
        if cat_name not in self.cat_dict:
            messagebox.showerror("Error", "Invalid category")
            return
        if sup_name not in self.sup_dict:
            messagebox.showerror("Error", "Invalid supplier")
            return
        try:
            price = float(self.price_var.get())
            qty = int(self.qty_var.get())
        except ValueError:
            messagebox.showerror("Error", "Price and Quantity must be numbers")
            return
        prod = Product(
            name=self.name_var.get(),
            category_id=self.cat_dict[cat_name],
            price=price,
            quantity=qty,
            supplier_id=self.sup_dict[sup_name]
        )
        valid, msg = prod.validate()
        if not valid:
            messagebox.showerror("Validation Error", msg)
            return
        self.db.insert_product(prod)
        messagebox.showinfo("Success", "Product added")
        self.clear_form()
        self.load_data()

    def edit(self):
        if not hasattr(self, 'selected_id') or not self.selected_id:
            messagebox.showerror("Error", "Select a product to edit")
            return
        cat_name = self.category_var.get()
        sup_name = self.supplier_var.get()
        if cat_name not in self.cat_dict:
            messagebox.showerror("Error", "Invalid category")
            return
        if sup_name not in self.sup_dict:
            messagebox.showerror("Error", "Invalid supplier")
            return
        try:
            price = float(self.price_var.get())
            qty = int(self.qty_var.get())
        except ValueError:
            messagebox.showerror("Error", "Price and Quantity must be numbers")
            return
        prod = Product(
            id=self.selected_id,
            name=self.name_var.get(),
            category_id=self.cat_dict[cat_name],
            price=price,
            quantity=qty,
            supplier_id=self.sup_dict[sup_name]
        )
        valid, msg = prod.validate()
        if not valid:
            messagebox.showerror("Validation Error", msg)
            return
        self.db.update_product(prod)
        messagebox.showinfo("Success", "Product updated")
        self.clear_form()
        self.load_data()

    def delete(self):
        if not hasattr(self, 'selected_id') or not self.selected_id:
            messagebox.showerror("Error", "Select a product to delete")
            return
        if messagebox.askyesno("Confirm", "Delete this product?"):
            self.db.delete_product(self.selected_id)
            messagebox.showinfo("Success", "Product deleted")
            self.clear_form()
            self.load_data()


class BillingWindow(tk.Toplevel):
    def __init__(self, parent, db: Database):
        super().__init__(parent)
        self.db = db
        self.title("Billing System")
        self.geometry("1000x650")
        self.configure(bg="#f0f0f0")
        self.cart: List[BillItem] = []

        self.create_widgets()
        self.load_products()

    def create_widgets(self):
        # Top frame for customer and invoice details
        top = tk.Frame(self, bg="#f0f0f0")
        top.pack(pady=10, padx=10, fill="x")

        tk.Label(top, text="Customer Name:", bg="#f0f0f0").grid(row=0, column=0, padx=5, sticky="e")
        self.cust_var = tk.StringVar()
        tk.Entry(top, textvariable=self.cust_var, width=30).grid(row=0, column=1, padx=5)

        tk.Label(top, text="Date:", bg="#f0f0f0").grid(row=0, column=2, padx=5, sticky="e")
        self.date_var = tk.StringVar(value=datetime.date.today().isoformat())
        tk.Entry(top, textvariable=self.date_var, state="readonly", width=15).grid(row=0, column=3, padx=5)

        # Product selection frame
        select_frame = tk.LabelFrame(self, text="Select Product", bg="#f0f0f0", font=('Arial', 11, 'bold'))
        select_frame.pack(pady=10, padx=10, fill="x")

        tk.Label(select_frame, text="Product:", bg="#f0f0f0").grid(row=0, column=0, padx=5, sticky="e")
        self.prod_var = tk.StringVar()
        self.prod_combo = ttk.Combobox(select_frame, textvariable=self.prod_var, state="readonly", width=20)
        self.prod_combo.grid(row=0, column=1, padx=5)
        self.prod_combo.bind("<<ComboboxSelected>>", self.update_price_qty)

        tk.Label(select_frame, text="Price:", bg="#f0f0f0").grid(row=0, column=2, padx=5, sticky="e")
        self.price_var = tk.StringVar(value="0.00")
        tk.Entry(select_frame, textvariable=self.price_var, state="readonly", width=10).grid(row=0, column=3, padx=5)

        tk.Label(select_frame, text="Available:", bg="#f0f0f0").grid(row=0, column=4, padx=5, sticky="e")
        self.avail_var = tk.StringVar(value="0")
        tk.Entry(select_frame, textvariable=self.avail_var, state="readonly", width=10).grid(row=0, column=5, padx=5)

        tk.Label(select_frame, text="Quantity:", bg="#f0f0f0").grid(row=1, column=0, padx=5, sticky="e")
        self.qty_var = tk.StringVar(value="1")
        tk.Entry(select_frame, textvariable=self.qty_var, width=10).grid(row=1, column=1, padx=5)

        self.add_cart_btn = tk.Button(select_frame, text="Add to Cart", command=self.add_to_cart, bg="#4CAF50", fg="white")
        self.add_cart_btn.grid(row=1, column=2, columnspan=2, pady=10)

        # Cart display
        cart_frame = tk.LabelFrame(self, text="Cart", bg="#f0f0f0", font=('Arial', 11, 'bold'))
        cart_frame.pack(pady=10, padx=10, fill="both", expand=True)

        columns = ("product_id", "name", "price", "qty", "total")
        self.cart_tree = ttk.Treeview(cart_frame, columns=columns, show="headings", selectmode="browse")
        self.cart_tree.heading("product_id", text="Prod ID")
        self.cart_tree.heading("name", text="Product Name")
        self.cart_tree.heading("price", text="Price")
        self.cart_tree.heading("qty", text="Qty")
        self.cart_tree.heading("total", text="Total")
        self.cart_tree.column("product_id", width=50)
        self.cart_tree.column("name", width=200)
        self.cart_tree.pack(fill="both", expand=True, padx=5, pady=5)

        # Bottom: totals and generate bill
        bottom = tk.Frame(self, bg="#f0f0f0")
        bottom.pack(pady=10, padx=10, fill="x")

        self.total_label = tk.Label(bottom, text="Total: 0.00", font=('Arial', 12, 'bold'), bg="#f0f0f0")
        self.total_label.pack(side=tk.LEFT, padx=20)
        self.tax_label = tk.Label(bottom, text="Tax (10%): 0.00", font=('Arial', 12, 'bold'), bg="#f0f0f0")
        self.tax_label.pack(side=tk.LEFT, padx=20)
        self.grand_label = tk.Label(bottom, text="Grand Total: 0.00", font=('Arial', 12, 'bold'), fg="red", bg="#f0f0f0")
        self.grand_label.pack(side=tk.LEFT, padx=20)

        self.gen_btn = tk.Button(bottom, text="Generate Invoice", command=self.generate_invoice, bg="#2196F3", fg="white", width=15)
        self.gen_btn.pack(side=tk.RIGHT, padx=10)

    def load_products(self):
        products = self.db.fetch_products()
        self.products_map: Dict[str, Dict[str, Any]] = {}
        names = []
        for p in products:
            name = f"{p['id']} - {p['name']}"
            self.products_map[name] = p
            names.append(name)
        self.prod_combo['values'] = names
        if names:
            self.prod_combo.current(0)
            self.update_price_qty()

    def update_price_qty(self, event=None):
        selected = self.prod_var.get()
        if selected in self.products_map:
            p = self.products_map[selected]
            self.price_var.set(f"{p['price']:.2f}")
            self.avail_var.set(str(p['quantity']))
        else:
            self.price_var.set("0.00")
            self.avail_var.set("0")

    def add_to_cart(self):
        selected = self.prod_var.get()
        if not selected or selected not in self.products_map:
            messagebox.showerror("Error", "Select a valid product")
            return
        try:
            qty = int(self.qty_var.get())
        except ValueError:
            messagebox.showerror("Error", "Quantity must be integer")
            return
        if qty <= 0:
            messagebox.showerror("Error", "Quantity must be positive")
            return
        product = self.products_map[selected]
        if qty > product['quantity']:
            messagebox.showerror("Error", f"Only {product['quantity']} available")
            return
        price = product['price']
        total = round(price * qty, 2)
        item = BillItem(product_id=product['id'], quantity=qty, price=price, total=total)
        # Check if already in cart, update quantity
        existing_found = False
        for child in self.cart_tree.get_children():
            values = self.cart_tree.item(child)['values']
            if int(values[0]) == product['id']:
                # update
                existing_qty = int(values[3])
                new_qty = existing_qty + qty
                if new_qty > product['quantity']:
                    messagebox.showerror("Error", f"Cannot add more, only {product['quantity']} total available")
                    return
                new_total = round(price * new_qty, 2)
                self.cart_tree.item(child, values=(product['id'], product['name'], f"{price:.2f}", new_qty, f"{new_total:.2f}"))
                # update BillItem list
                for i, cart_item in enumerate(self.cart):
                    if cart_item.product_id == product['id']:
                        self.cart[i] = BillItem(product_id=product['id'], quantity=new_qty, price=price, total=new_total)
                        break
                existing_found = True
                break
        if not existing_found:
            self.cart_tree.insert("", "end", values=(product['id'], product['name'], f"{price:.2f}", qty, f"{total:.2f}"))
            self.cart.append(item)
        self.update_totals()
        self.qty_var.set("1")

    def update_totals(self):
        total = sum(item.total for item in self.cart)
        tax = round(total * 0.1, 2)
        grand = total + tax
        self.total_label.config(text=f"Total: {total:.2f}")
        self.tax_label.config(text=f"Tax (10%): {tax:.2f}")
        self.grand_label.config(text=f"Grand Total: {grand:.2f}")

    def generate_invoice(self):
        if not self.cart:
            messagebox.showerror("Error", "Cart is empty")
            return
        customer = self.cust_var.get().strip()
        if not customer:
            customer = "Walk-in Customer"
        try:
            invoice_no = self.db.create_bill(customer, self.cart)
            messagebox.showinfo("Success", f"Invoice {invoice_no} generated successfully.")
            # Clear cart and reload products
            self.cart.clear()
            for child in self.cart_tree.get_children():
                self.cart_tree.delete(child)
            self.update_totals()
            self.load_products()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate invoice: {str(e)}")


class InventoryApp:
    def __init__(self):
        self.db = Database()
        self.root = tk.Tk()
        self.root.title("Inventory Management System")
        self.root.geometry("800x600")
        self.root.configure(bg="#2E4057")
        self.clock_label = None
        self.load_images()
        self.create_dashboard()
        self.update_clock()

    def load_images(self):
        # Try to load a default image, if not available use a placeholder
        self.images = {}
        img_path = os.path.join(os.path.dirname(__file__), "inventory.png")
        if os.path.exists(img_path):
            try:
                pil_img = Image.open(img_path)
                pil_img = pil_img.resize((200, 200), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(pil_img)
            except:
                self.logo_img = None
        else:
            self.logo_img = None

    def create_dashboard(self):
        # Header
        header = tk.Frame(self.root, bg="#1B2A3A", height=100)
        header.pack(fill="x")
        tk.Label(header, text="INVENTORY MANAGEMENT SYSTEM", font=('Arial', 24, 'bold'), bg="#1B2A3A", fg="white").pack(pady=20)
        # Clock
        self.clock_label = tk.Label(header, font=('Arial', 12), bg="#1B2A3A", fg="lightgray")
        self.clock_label.pack(pady=(0, 10))

        # Main content
        content = tk.Frame(self.root, bg="#2E4057")
        content.pack(expand=True, fill="both", padx=20, pady=20)

        # If image available, show it
        if self.logo_img:
            img_label = tk.Label(content, image=self.logo_img, bg="#2E4057")
            img_label.grid(row=0, column=0, rowspan=5, padx=20, pady=10)

        # Buttons
        button_config = {"bg": "#4CAF50", "fg": "white", "font": ('Arial', 12, 'bold'), "width": 20, "height": 2}
        tk.Button(content, text="Manage Employees", command=self.open_employees, **button_config).grid(row=0, column=1, padx=10, pady=10)
        tk.Button(content, text="Manage Suppliers", command=self.open_suppliers, **button_config).grid(row=1, column=1, padx=10, pady=10)
        tk.Button(content, text="Manage Categories", command=self.open_categories, **button_config).grid(row=2, column=1, padx=10, pady=10)
        tk.Button(content, text="Manage Products", command=self.open_products, **button_config).grid(row=3, column=1, padx=10, pady=10)
        tk.Button(content, text="Billing", command=self.open_billing, bg="#2196F3", fg="white", font=('Arial', 12, 'bold'), width=20, height=2).grid(row=4, column=1, padx=10, pady=10)

        # Author/version
        tk.Label(self.root, text="v1.0 | Developed with Python & Tkinter", bg="#2E4057", fg="white").pack(side="bottom", pady=5)

    def update_clock(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.config(text=now)
        self.root.after(1000, self.update_clock)

    def open_employees(self):
        EmployeeWindow(self.root, self.db)

    def open_suppliers(self):
        SupplierWindow(self.root, self.db)

    def open_categories(self):
        CategoryWindow(self.root, self.db)

    def open_products(self):
        ProductWindow(self.root, self.db)

    def open_billing(self):
        BillingWindow(self.root, self.db)

    def run(self):
        self.root.mainloop()
        self.db.close()


if __name__ == "__main__":
    app = InventoryApp()
    app.run()