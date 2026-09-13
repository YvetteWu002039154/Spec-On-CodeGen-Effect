import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkinter import filedialog
from datetime import datetime
import sqlite3
import os
from PIL import Image, ImageTk

# ---------------------- Database Setup ----------------------
DB_NAME = "inventory.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            position TEXT,
            email TEXT,
            phone TEXT,
            salary REAL,
            joining_date TEXT
        );
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_person TEXT,
            phone TEXT,
            email TEXT,
            address TEXT
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            supplier_id INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        );
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT NOT NULL UNIQUE,
            customer_name TEXT,
            date TEXT NOT NULL,
            total_amount REAL NOT NULL DEFAULT 0.0
        );
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    ''')
    conn.commit()
    conn.close()

# ---------------------- Helper Functions ----------------------
def validate_float(value):
    try:
        return float(value)
    except ValueError:
        return None

def validate_int(value):
    try:
        return int(value)
    except ValueError:
        return None

# ---------------------- Dashboard Frame ----------------------
class Dashboard(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.time_label = ttk.Label(self, font=('Arial', 24))
        self.time_label.pack(pady=20)
        self.update_clock()

        # Title
        ttk.Label(self, text="Inventory Management System", font=('Arial', 18, 'bold')).pack(pady=10)

        # Buttons for navigation
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20, expand=True, fill='both')

        ttk.Button(btn_frame, text="Employee Management",
                   command=lambda: controller.show_frame("EmployeeFrame")).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Supplier Management",
                   command=lambda: controller.show_frame("SupplierFrame")).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Product Management",
                   command=lambda: controller.show_frame("ProductFrame")).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Category Management",
                   command=lambda: controller.show_frame("CategoryFrame")).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="Billing & Invoices",
                   command=lambda: controller.show_frame("BillingFrame")).pack(side='left', padx=10)

        # Image (placeholder)
        try:
            image = Image.open("logo.png")  # if exists
            photo = ImageTk.PhotoImage(image.resize((100, 100)))
            lbl_img = ttk.Label(self, image=photo)
            lbl_img.image = photo
            lbl_img.pack(side='bottom', pady=10)
        except Exception:
            ttk.Label(self, text="(No Logo Image)").pack(side='bottom', pady=10)

    def update_clock(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=now)
        self.after(1000, self.update_clock)

# ---------------------- Employee Management Frame ----------------------
class EmployeeFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text="Employee Management", font=('Arial', 16)).pack(pady=10)

        # Entry form
        form = ttk.Frame(self)
        form.pack(pady=10, padx=10, fill='x')
        ttk.Label(form, text="Name").grid(row=0, column=0, sticky='w')
        self.name_entry = ttk.Entry(form)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(form, text="Position").grid(row=1, column=0, sticky='w')
        self.pos_entry = ttk.Entry(form)
        self.pos_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(form, text="Email").grid(row=2, column=0, sticky='w')
        self.email_entry = ttk.Entry(form)
        self.email_entry.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(form, text="Phone").grid(row=3, column=0, sticky='w')
        self.phone_entry = ttk.Entry(form)
        self.phone_entry.grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(form, text="Salary").grid(row=4, column=0, sticky='w')
        self.salary_entry = ttk.Entry(form)
        self.salary_entry.grid(row=4, column=1, padx=5, pady=2)

        ttk.Label(form, text="Joining Date (YYYY-MM-DD)").grid(row=5, column=0, sticky='w')
        self.jdate_entry = ttk.Entry(form)
        self.jdate_entry.grid(row=5, column=1, padx=5, pady=2)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Add Employee", command=self.add_employee).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Update Selected", command=self.update_employee).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_employee).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear Fields", command=self.clear_fields).pack(side='left', padx=5)

        # Treeview
        self.tree = ttk.Treeview(self, columns=("ID", "Name", "Position", "Email", "Phone", "Salary", "Joining Date"), show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Position", text="Position")
        self.tree.heading("Email", text="Email")
        self.tree.heading("Phone", text="Phone")
        self.tree.heading("Salary", text="Salary")
        self.tree.heading("Joining Date", text="Joining Date")
        self.tree.column("ID", width=30)
        self.tree.pack(fill='both', expand=True, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.load_data()

    def load_data(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees")
        rows = cursor.fetchall()
        for row in rows:
            self.tree.insert("", "end", values=(row["id"], row["name"], row["position"], row["email"], row["phone"], row["salary"], row["joining_date"]))
        conn.close()

    def clear_fields(self):
        self.name_entry.delete(0, 'end')
        self.pos_entry.delete(0, 'end')
        self.email_entry.delete(0, 'end')
        self.phone_entry.delete(0, 'end')
        self.salary_entry.delete(0, 'end')
        self.jdate_entry.delete(0, 'end')

    def on_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        item = self.tree.item(selection[0])['values']
        self.clear_fields()
        self.name_entry.insert(0, item[1] if item[1] else "")
        self.pos_entry.insert(0, item[2] if item[2] else "")
        self.email_entry.insert(0, item[3] if item[3] else "")
        self.phone_entry.insert(0, item[4] if item[4] else "")
        self.salary_entry.insert(0, str(item[5]) if item[5] else "")
        self.jdate_entry.insert(0, item[6] if item[6] else "")

    def add_employee(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        pos = self.pos_entry.get().strip()
        email = self.email_entry.get().strip()
        phone = self.phone_entry.get().strip()
        salary_str = self.salary_entry.get().strip()
        salary = validate_float(salary_str) if salary_str else 0.0
        jdate = self.jdate_entry.get().strip()
        try:
            datetime.strptime(jdate, "%Y-%m-%d") if jdate else None
        except ValueError:
            messagebox.showerror("Error", "Date format must be YYYY-MM-DD")
            return
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO employees (name, position, email, phone, salary, joining_date) VALUES (?, ?, ?, ?, ?, ?)",
                       (name, pos, email, phone, salary, jdate))
        conn.commit()
        conn.close()
        self.load_data()
        self.clear_fields()
        messagebox.showinfo("Success", "Employee added")

    def update_employee(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showerror("Error", "Select an employee to update")
            return
        emp_id = self.tree.item(selection[0])['values'][0]
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        pos = self.pos_entry.get().strip()
        email = self.email_entry.get().strip()
        phone = self.phone_entry.get().strip()
        salary_str = self.salary_entry.get().strip()
        salary = validate_float(salary_str) if salary_str else 0.0
        jdate = self.jdate_entry.get().strip()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE employees SET name=?, position=?, email=?, phone=?, salary=?, joining_date=? WHERE id=?",
                       (name, pos, email, phone, salary, jdate, emp_id))
        conn.commit()
        conn.close()
        self.load_data()
        self.clear_fields()
        messagebox.showinfo("Success", "Employee updated")

    def delete_employee(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showerror("Error", "Select an employee to delete")
            return
        if not messagebox.askyesno("Confirm", "Delete selected employee?"):
            return
        emp_id = self.tree.item(selection[0])['values'][0]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM employees WHERE id=?", (emp_id,))
        conn.commit()
        conn.close()
        self.load_data()
        self.clear_fields()
        messagebox.showinfo("Success", "Employee deleted")

# ---------------------- Supplier Management Frame ----------------------
class SupplierFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text="Supplier Management", font=('Arial', 16)).pack(pady=10)

        form = ttk.Frame(self)
        form.pack(pady=10, padx=10, fill='x')
        ttk.Label(form, text="Name").grid(row=0, column=0, sticky='w')
        self.name_entry = ttk.Entry(form)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(form, text="Contact Person").grid(row=1, column=0, sticky='w')
        self.contact_entry = ttk.Entry(form)
        self.contact_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(form, text="Phone").grid(row=2, column=0, sticky='w')
        self.phone_entry = ttk.Entry(form)
        self.phone_entry.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(form, text="Email").grid(row=3, column=0, sticky='w')
        self.email_entry = ttk.Entry(form)
        self.email_entry.grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(form, text="Address").grid(row=4, column=0, sticky='w')
        self.addr_entry = ttk.Entry(form)
        self.addr_entry.grid(row=4, column=1, padx=5, pady=2)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Add", command=self.add_supplier).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Update Selected", command=self.update_supplier).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_supplier).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear", command=self.clear_fields).pack(side='left', padx=5)

        self.tree = ttk.Treeview(self, columns=("ID", "Name", "Contact", "Phone", "Email", "Address"), show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Contact", text="Contact Person")
        self.tree.heading("Phone", text="Phone")
        self.tree.heading("Email", text="Email")
        self.tree.heading("Address", text="Address")
        self.tree.column("ID", width=30)
        self.tree.pack(fill='both', expand=True, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.load_data()

    def load_data(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM suppliers")
        for row in cursor.fetchall():
            self.tree.insert("", "end", values=(row["id"], row["name"], row["contact_person"], row["phone"], row["email"], row["address"]))
        conn.close()

    def clear_fields(self):
        self.name_entry.delete(0, 'end')
        self.contact_entry.delete(0, 'end')
        self.phone_entry.delete(0, 'end')
        self.email_entry.delete(0, 'end')
        self.addr_entry.delete(0, 'end')

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])['values']
        self.clear_fields()
        self.name_entry.insert(0, item[1])
        self.contact_entry.insert(0, item[2] if item[2] else "")
        self.phone_entry.insert(0, item[3] if item[3] else "")
        self.email_entry.insert(0, item[4] if item[4] else "")
        self.addr_entry.insert(0, item[5] if item[5] else "")

    def add_supplier(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required")
            return
        contact = self.contact_entry.get().strip()
        phone = self.phone_entry.get().strip()
        email = self.email_entry.get().strip()
        addr = self.addr_entry.get().strip()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO suppliers (name, contact_person, phone, email, address) VALUES (?,?,?,?,?)",
                       (name, contact, phone, email, addr))
        conn.commit()
        conn.close()
        self.load_data()
        self.clear_fields()
        messagebox.showinfo("Success", "Supplier added")

    def update_supplier(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Select a supplier")
            return
        sid = self.tree.item(sel[0])['values'][0]
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required")
            return
        contact = self.contact_entry.get().strip()
        phone = self.phone_entry.get().strip()
        email = self.email_entry.get().strip()
        addr = self.addr_entry.get().strip()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE suppliers SET name=?, contact_person=?, phone=?, email=?, address=? WHERE id=?",
                       (name, contact, phone, email, addr, sid))
        conn.commit()
        conn.close()
        self.load_data()
        self.clear_fields()
        messagebox.showinfo("Success", "Supplier updated")

    def delete_supplier(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Select a supplier")
            return
        if not messagebox.askyesno("Confirm", "Delete this supplier?"):
            return
        sid = self.tree.item(sel[0])['values'][0]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM suppliers WHERE id=?", (sid,))
        conn.commit()
        conn.close()
        self.load_data()
        self.clear_fields()
        messagebox.showinfo("Success", "Supplier deleted")

# ---------------------- Category Management Frame ----------------------
class CategoryFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text="Category Management", font=('Arial', 16)).pack(pady=10)

        form = ttk.Frame(self)
        form.pack(pady=10, padx=10, fill='x')
        ttk.Label(form, text="Category Name").grid(row=0, column=0, sticky='w')
        self.name_entry = ttk.Entry(form)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(form, text="Description").grid(row=1, column=0, sticky='w')
        self.desc_entry = ttk.Entry(form)
        self.desc_entry.grid(row=1, column=1, padx=5, pady=2)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Add", command=self.add_category).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Update Selected", command=self.update_category).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_category).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear", command=self.clear_fields).pack(side='left', padx=5)

        self.tree = ttk.Treeview(self, columns=("ID", "Name", "Description"), show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Description", text="Description")
        self.tree.column("ID", width=30)
        self.tree.pack(fill='both', expand=True, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.load_data()

    def load_data(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories")
        for row in cursor.fetchall():
            self.tree.insert("", "end", values=(row["id"], row["name"], row["description"]))
        conn.close()

    def clear_fields(self):
        self.name_entry.delete(0, 'end')
        self.desc_entry.delete(0, 'end')

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])['values']
        self.clear_fields()
        self.name_entry.insert(0, item[1])
        self.desc_entry.insert(0, item[2] if item[2] else "")

    def add_category(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required")
            return
        desc = self.desc_entry.get().strip()
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO categories (name, description) VALUES (?,?)", (name, desc))
            conn.commit()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Category already exists")
            conn.close()
            return
        conn.close()
        self.load_data()
        self.clear_fields()
        messagebox.showinfo("Success", "Category added")

    def update_category(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Select a category")
            return
        cid = self.tree.item(sel[0])['values'][0]
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required")
            return
        desc = self.desc_entry.get().strip()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE categories SET name=?, description=? WHERE id=?", (name, desc, cid))
        conn.commit()
        conn.close()
        self.load_data()
        self.clear_fields()
        messagebox.showinfo("Success", "Category updated")

    def delete_category(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Select a category")
            return
        if not messagebox.askyesno("Confirm", "Delete category?"):
            return
        cid = self.tree.item(sel[0])['values'][0]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM categories WHERE id=?", (cid,))
        conn.commit()
        conn.close()
        self.load_data()
        self.clear_fields()
        messagebox.showinfo("Success", "Category deleted")

# ---------------------- Product Management Frame ----------------------
class ProductFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text="Product Management", font=('Arial', 16)).pack(pady=10)

        form = ttk.Frame(self)
        form.pack(pady=10, padx=10, fill='x')

        ttk.Label(form, text="Name").grid(row=0, column=0, sticky='w')
        self.name_entry = ttk.Entry(form)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(form, text="Category").grid(row=1, column=0, sticky='w')
        self.cat_combo = ttk.Combobox(form, state="readonly")
        self.cat_combo.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(form, text="Price").grid(row=2, column=0, sticky='w')
        self.price_entry = ttk.Entry(form)
        self.price_entry.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(form, text="Quantity").grid(row=3, column=0, sticky='w')
        self.qty_entry = ttk.Entry(form)
        self.qty_entry.grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(form, text="Supplier").grid(row=4, column=0, sticky='w')
        self.sup_combo = ttk.Combobox(form, state="readonly")
        self.sup_combo.grid(row=4, column=1, padx=5, pady=2)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Add", command=self.add_product).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Update Selected", command=self.update_product).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_product).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear", command=self.clear_fields).pack(side='left', padx=5)

        self.tree = ttk.Treeview(self, columns=("ID", "Name", "Category", "Price", "Qty", "Supplier"), show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Category", text="Category")
        self.tree.heading("Price", text="Price")
        self.tree.heading("Qty", text="Qty")
        self.tree.heading("Supplier", text="Supplier")
        self.tree.column("ID", width=30)
        self.tree.pack(fill='both', expand=True, padx=10, pady=10)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        self.populate_combos()
        self.load_data()

    def populate_combos(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM categories")
        cats = [f"{row['id']}: {row['name']}" for row in cursor.fetchall()]
        self.cat_combo['values'] = cats
        cursor.execute("SELECT id, name FROM suppliers")
        sups = [f"{row['id']}: {row['name']}" for row in cursor.fetchall()]
        self.sup_combo['values'] = sups
        conn.close()

    def load_data(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.id, p.name, c.name as cat_name, p.price, p.quantity, s.name as sup_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
        ''')
        for row in cursor.fetchall():
            self.tree.insert("", "end", values=(row["id"], row["name"], row["cat_name"] or "-", row["price"], row["quantity"], row["sup_name"] or "-"))
        conn.close()

    def clear_fields(self):
        self.name_entry.delete(0, 'end')
        self.cat_combo.set('')
        self.price_entry.delete(0, 'end')
        self.qty_entry.delete(0, 'end')
        self.sup_combo.set('')

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        item = self.tree.item(sel[0])['values']
        self.clear_fields()
        self.name_entry.insert(0, item[1])
        # find combo values
        cat_name = item[2] if item[2] != '-' else ''
        sup_name = item[5] if item[5] != '-' else ''
        # set combo by searching for matching id:name
        for val in self.cat_combo['values']:
            if val.endswith(f": {cat_name}"):
                self.cat_combo.set(val)
                break
        for val in self.sup_combo['values']:
            if val.endswith(f": {sup_name}"):
                self.sup_combo.set(val)
                break
        self.price_entry.insert(0, str(item[3]))
        self.qty_entry.insert(0, str(item[4]))

    def get_combo_ids(self):
        cat_id = None
        sup_id = None
        cat_val = self.cat_combo.get()
        if cat_val and ': ' in cat_val:
            cat_id = int(cat_val.split(':')[0])
        sup_val = self.sup_combo.get()
        if sup_val and ': ' in sup_val:
            sup_id = int(sup_val.split(':')[0])
        return cat_id, sup_id

    def add_product(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required")
            return
        price_str = self.price_entry.get().strip()
        if not price_str:
            messagebox.showerror("Error", "Price required")
            return
        price = validate_float(price_str)
        if price is None:
            messagebox.showerror("Error", "Invalid price")
            return
        qty_str = self.qty_entry.get().strip()
        qty = validate_int(qty_str) if qty_str else 0
        if qty is None:
            messagebox.showerror("Error", "Invalid quantity")
            return
        cat_id, sup_id = self.get_combo_ids()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO products (name, category_id, price, quantity, supplier_id) VALUES (?,?,?,?,?)",
                       (name, cat_id, price, qty, sup_id))
        conn.commit()
        conn.close()
        self.load_data()
        self.clear_fields()
        messagebox.showinfo("Success", "Product added")

    def update_product(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Select a product")
            return
        pid = self.tree.item(sel[0])['values'][0]
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required")
            return
        price_str = self.price_entry.get().strip()
        if not price_str:
            messagebox.showerror("Error", "Price required")
            return
        price = validate_float(price_str)
        if price is None:
            messagebox.showerror("Error", "Invalid price")
            return
        qty_str = self.qty_entry.get().strip()
        qty = validate_int(qty_str) if qty_str else 0
        if qty is None:
            messagebox.showerror("Error", "Invalid quantity")
            return
        cat_id, sup_id = self.get_combo_ids()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET name=?, category_id=?, price=?, quantity=?, supplier_id=? WHERE id=?",
                       (name, cat_id, price, qty, sup_id, pid))
        conn.commit()
        conn.close()
        self.load_data()
        self.clear_fields()
        messagebox.showinfo("Success", "Product updated")

    def delete_product(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Select a product")
            return
        if not messagebox.askyesno("Confirm", "Delete product?"):
            return
        pid = self.tree.item(sel[0])['values'][0]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id=?", (pid,))
        conn.commit()
        conn.close()
        self.load_data()
        self.clear_fields()
        messagebox.showinfo("Success", "Product deleted")

# ---------------------- Billing & Invoices Frame ----------------------
class BillingFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ttk.Label(self, text="Billing & Invoices", font=('Arial', 16)).pack(pady=10)

        # Billing form
        bill_frame = ttk.LabelFrame(self, text="Create New Invoice")
        bill_frame.pack(pady=10, padx=10, fill='x')

        ttk.Label(bill_frame, text="Invoice Number").grid(row=0, column=0, sticky='w')
        self.inv_no_entry = ttk.Entry(bill_frame)
        self.inv_no_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(bill_frame, text="Customer Name").grid(row=1, column=0, sticky='w')
        self.cust_entry = ttk.Entry(bill_frame)
        self.cust_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(bill_frame, text="Date (YYYY-MM-DD)").grid(row=2, column=0, sticky='w')
        self.date_entry = ttk.Entry(bill_frame)
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.date_entry.grid(row=2, column=1, padx=5, pady=2)

        # Product selection and adding to list
        add_item_frame = ttk.LabelFrame(self, text="Add Item")
        add_item_frame.pack(pady=10, padx=10, fill='x')

        ttk.Label(add_item_frame, text="Product").grid(row=0, column=0, sticky='w')
        self.prod_combo = ttk.Combobox(add_item_frame, state="readonly")
        self.prod_combo.grid(row=0, column=1, padx=5, pady=2)
        self.prod_combo.bind("<<ComboboxSelected>>", self.load_product_details)

        ttk.Label(add_item_frame, text="Available Qty").grid(row=1, column=0, sticky='w')
        self.avail_label = ttk.Label(add_item_frame, text="0")
        self.avail_label.grid(row=1, column=1, sticky='w')

        ttk.Label(add_item_frame, text="Price").grid(row=2, column=0, sticky='w')
        self.price_label = ttk.Label(add_item_frame, text="0.00")
        self.price_label.grid(row=2, column=1, sticky='w')

        ttk.Label(add_item_frame, text="Quantity").grid(row=3, column=0, sticky='w')
        self.qty_spin = ttk.Spinbox(add_item_frame, from_=1, to=1000, width=10)
        self.qty_spin.grid(row=3, column=1, padx=5, pady=2)

        ttk.Button(add_item_frame, text="Add to Invoice", command=self.add_item_to_invoice).grid(row=4, column=0, columnspan=2, pady=5)

        # Items list
        self.items_tree = ttk.Treeview(self, columns=("Product", "Qty", "Price", "Total"), show='headings')
        self.items_tree.heading("Product", text="Product")
        self.items_tree.heading("Qty", text="Qty")
        self.items_tree.heading("Price", text="Unit Price")
        self.items_tree.heading("Total", text="Total")
        self.items_tree.pack(pady=10, padx=10, fill='both', expand=True)

        self.total_label = ttk.Label(self, text="Total: 0.00", font=('Arial', 14, 'bold'))
        self.total_label.pack()

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Generate Invoice", command=self.generate_invoice).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear Invoice", command=self.clear_invoice).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="View Invoices", command=self.show_invoices_window).pack(side='left', padx=5)

        self.populate_product_combo()

        # Storage for current invoice items (list of dicts)
        self.current_items = []

    def populate_product_combo(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, quantity, price FROM products")
        self.products = {f"{row['id']}: {row['name']}": (row['id'], row['quantity'], row['price']) for row in cursor.fetchall()}
        conn.close()
        self.prod_combo['values'] = list(self.products.keys())

    def load_product_details(self, event=None):
        prod_name = self.prod_combo.get()
        if prod_name in self.products:
            pid, qty, price = self.products[prod_name]
            self.avail_label.config(text=str(qty))
            self.price_label.config(text=f"{price:.2f}")
        else:
            self.avail_label.config(text="0")
            self.price_label.config(text="0.00")

    def add_item_to_invoice(self):
        prod_name = self.prod_combo.get()
        if not prod_name:
            messagebox.showerror("Error", "Select a product")
            return
        try:
            qty = int(self.qty_spin.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity")
            return
        pid, avail, price = self.products[prod_name]
        if qty > avail:
            messagebox.showerror("Error", f"Only {avail} available")
            return
        # Check if product already in items, then update quantity
        for item in self.current_items:
            if item['pid'] == pid:
                if item['qty'] + qty > avail:
                    messagebox.showerror("Error", f"Total exceeds available qty ({avail})")
                    return
                item['qty'] += qty
                self.refresh_items_tree()
                self.update_total()
                return
        self.current_items.append({'pid': pid, 'name': prod_name.split(': ',1)[1], 'qty': qty, 'price': price})
        self.refresh_items_tree()
        self.update_total()

    def refresh_items_tree(self):
        for i in self.items_tree.get_children():
            self.items_tree.delete(i)
        for item in self.current_items:
            total = item['qty'] * item['price']
            self.items_tree.insert("", "end", values=(item['name'], item['qty'], f"{item['price']:.2f}", f"{total:.2f}"))

    def update_total(self):
        total = sum(item['qty'] * item['price'] for item in self.current_items)
        self.total_label.config(text=f"Total: {total:.2f}")

    def clear_invoice(self):
        self.current_items = []
        self.refresh_items_tree()
        self.update_total()
        self.inv_no_entry.delete(0, 'end')
        self.cust_entry.delete(0, 'end')
        self.date_entry.delete(0, 'end')
        self.date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

    def generate_invoice(self):
        inv_no = self.inv_no_entry.get().strip()
        if not inv_no:
            messagebox.showerror("Error", "Invoice number required")
            return
        customer = self.cust_entry.get().strip()
        date_str = self.date_entry.get().strip()
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Date format YYYY-MM-DD")
            return
        if not self.current_items:
            messagebox.showerror("Error", "No items in invoice")
            return
        total = sum(item['qty'] * item['price'] for item in self.current_items)

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO invoices (invoice_number, customer_name, date, total_amount) VALUES (?,?,?,?)",
                           (inv_no, customer, date_str, total))
            inv_id = cursor.lastrowid
            for item in self.current_items:
                cursor.execute("INSERT INTO invoice_items (invoice_id, product_id, quantity, price) VALUES (?,?,?,?)",
                               (inv_id, item['pid'], item['qty'], item['price']))
                # reduce product quantity
                cursor.execute("UPDATE products SET quantity = quantity - ? WHERE id=?", (item['qty'], item['pid']))
            conn.commit()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Invoice number already exists")
            conn.close()
            return
        conn.close()
        messagebox.showinfo("Success", "Invoice generated")
        # update product combo after stock change
        self.populate_product_combo()
        self.clear_invoice()

    def show_invoices_window(self):
        InvoicesView(self)

# ---------------------- Invoices View ----------------------
class InvoicesView(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Invoices")
        self.geometry("800x500")

        self.tree = ttk.Treeview(self, columns=("ID", "Invoice No", "Customer", "Date", "Total"), show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Invoice No", text="Invoice No")
        self.tree.heading("Customer", text="Customer")
        self.tree.heading("Date", text="Date")
        self.tree.heading("Total", text="Total")
        self.tree.column("ID", width=30)
        self.tree.pack(fill='both', expand=True, padx=10, pady=10)

        ttk.Button(self, text="View Details", command=self.view_details).pack(pady=5)
        ttk.Button(self, text="Delete Invoice", command=self.delete_invoice).pack(pady=5)

        self.load_invoices()

    def load_invoices(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices ORDER BY date DESC")
        for row in cursor.fetchall():
            self.tree.insert("", "end", values=(row["id"], row["invoice_number"], row["customer_name"], row["date"], row["total_amount"]))
        conn.close()

    def view_details(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Select an invoice")
            return
        inv_id = self.tree.item(sel[0])['values'][0]
        InvoiceDetails(self, inv_id)

    def delete_invoice(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Error", "Select an invoice")
            return
        if not messagebox.askyesno("Confirm", "Delete invoice and restock items?"):
            return
        inv_id = self.tree.item(sel[0])['values'][0]
        conn = get_db()
        cursor = conn.cursor()
        # restore quantities
        cursor.execute("SELECT product_id, quantity FROM invoice_items WHERE invoice_id=?", (inv_id,))
        for row in cursor.fetchall():
            cursor.execute("UPDATE products SET quantity = quantity + ? WHERE id=?", (row["quantity"], row["product_id"]))
        cursor.execute("DELETE FROM invoice_items WHERE invoice_id=?", (inv_id,))
        cursor.execute("DELETE FROM invoices WHERE id=?", (inv_id,))
        conn.commit()
        conn.close()
        self.load_invoices()
        messagebox.showinfo("Success", "Invoice deleted")

# ---------------------- Invoice Details ----------------------
class InvoiceDetails(tk.Toplevel):
    def __init__(self, parent, inv_id):
        super().__init__(parent)
        self.title(f"Invoice #{inv_id}")
        self.geometry("600x400")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invoices WHERE id=?", (inv_id,))
        inv = cursor.fetchone()
        if inv:
            ttk.Label(self, text=f"Invoice No: {inv['invoice_number']}", font=('Arial', 12, 'bold')).pack(pady=5)
            ttk.Label(self, text=f"Customer: {inv['customer_name']}").pack()
            ttk.Label(self, text=f"Date: {inv['date']}").pack()
            ttk.Label(self, text=f"Total: {inv['total_amount']:.2f}").pack()

        # items
        tree = ttk.Treeview(self, columns=("Product", "Qty", "Price", "Total"), show='headings')
        tree.heading("Product", text="Product")
        tree.heading("Qty", text="Qty")
        tree.heading("Price", text="Unit Price")
        tree.heading("Total", text="Total")
        tree.pack(fill='both', expand=True, padx=10, pady=10)

        cursor.execute('''
            SELECT p.name, ii.quantity, ii.price, (ii.quantity * ii.price) as total
            FROM invoice_items ii
            JOIN products p ON ii.product_id = p.id
            WHERE ii.invoice_id=?
        ''', (inv_id,))
        for row in cursor.fetchall():
            tree.insert("", "end", values=(row["name"], row["quantity"], f"{row['price']:.2f}", f"{row['total']:.2f}"))
        conn.close()

# ---------------------- Main Application ----------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("900x600")

        container = ttk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (Dashboard, EmployeeFrame, SupplierFrame, ProductFrame, CategoryFrame, BillingFrame):
            frame = F(container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("Dashboard")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()

# ---------------------- Entry Point ----------------------
if __name__ == "__main__":
    init_db()
    app = App()
    app.mainloop()