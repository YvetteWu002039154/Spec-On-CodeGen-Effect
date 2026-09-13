import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import datetime
import os
from typing import List, Tuple, Optional
from PIL import Image, ImageTk

class Database:
    def __init__(self, db_name: str = "inventory.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT,
                email TEXT,
                role TEXT,
                salary REAL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT,
                email TEXT,
                address TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                category_id INTEGER,
                FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_no INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                customer_name TEXT,
                total REAL NOT NULL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no INTEGER,
                product_id INTEGER,
                product_name TEXT,
                price REAL,
                quantity INTEGER,
                total REAL,
                FOREIGN KEY (invoice_no) REFERENCES invoices(invoice_no),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        self.conn.commit()

    def execute(self, query: str, params: tuple = ()):
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", str(e))
            raise

    def fetch_all(self, query: str, params: tuple = ()) -> List[Tuple]:
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[Tuple]:
        self.cursor.execute(query, params)
        return self.cursor.fetchone()

    def close(self):
        self.conn.close()


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("1000x700")
        self.db = Database()
        self.create_widgets()

    def create_widgets(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill='both')

        self.dashboard_frame = DashboardFrame(notebook, self.db)
        self.employee_frame = EmployeeFrame(notebook, self.db)
        self.supplier_frame = SupplierFrame(notebook, self.db)
        self.category_frame = CategoryFrame(notebook, self.db)
        self.product_frame = ProductFrame(notebook, self.db)
        self.billing_frame = BillingFrame(notebook, self.db)
        self.invoice_frame = InvoiceFrame(notebook, self.db)

        notebook.add(self.dashboard_frame, text="Dashboard")
        notebook.add(self.employee_frame, text="Employees")
        notebook.add(self.supplier_frame, text="Suppliers")
        notebook.add(self.product_frame, text="Products")
        notebook.add(self.category_frame, text="Categories")
        notebook.add(self.billing_frame, text="Billing")
        notebook.add(self.invoice_frame, text="Invoices")

    def on_close(self):
        self.db.close()
        self.root.destroy()


class DashboardFrame(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, db: Database):
        super().__init__(parent)
        self.db = db
        self.create_widgets()
        self.update_clock()

    def create_widgets(self):
        container = ttk.Frame(self)
        container.pack(expand=True, fill='both', padx=20, pady=20)

        try:
            img = Image.open("inventory_logo.png")
            img = img.resize((150, 150), Image.LANCZOS)
            self.logo = ImageTk.PhotoImage(img)
            logo_label = ttk.Label(container, image=self.logo)
            logo_label.pack(pady=10)
        except:
            logo_label = ttk.Label(container, text="Inventory System", font=("Arial", 24, "bold"))
            logo_label.pack(pady=10)

        welcome = ttk.Label(container, text="Welcome to Inventory Management System", font=("Arial", 16))
        welcome.pack()

        self.clock_label = ttk.Label(container, font=("Arial", 12))
        self.clock_label.pack(pady=10)

        buttons_frame = ttk.Frame(container)
        buttons_frame.pack(pady=20)

        ttk.Button(buttons_frame, text="Employees", command=lambda: self.navigate(1)).grid(row=0, column=0, padx=5)
        ttk.Button(buttons_frame, text="Suppliers", command=lambda: self.navigate(2)).grid(row=0, column=1, padx=5)
        ttk.Button(buttons_frame, text="Products", command=lambda: self.navigate(3)).grid(row=0, column=2, padx=5)
        ttk.Button(buttons_frame, text="Categories", command=lambda: self.navigate(4)).grid(row=0, column=3, padx=5)
        ttk.Button(buttons_frame, text="Billing", command=lambda: self.navigate(5)).grid(row=0, column=4, padx=5)
        ttk.Button(buttons_frame, text="Invoices", command=lambda: self.navigate(6)).grid(row=0, column=5, padx=5)

        info = ttk.Label(container, text="Manage your inventory with ease.", font=("Arial", 12))
        info.pack()

    def update_clock(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.config(text=now)
        self.after(1000, self.update_clock)

    def navigate(self, index: int):
        self.master.select(index)


class EmployeeFrame(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, db: Database):
        super().__init__(parent)
        self.db = db
        self.create_widgets()
        self.load_employees()

    def create_widgets(self):
        input_frame = ttk.LabelFrame(self, text="Employee Details")
        input_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(input_frame, text="Name:").grid(row=0, column=0, sticky='e', padx=5, pady=2)
        self.name_entry = ttk.Entry(input_frame)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(input_frame, text="Contact:").grid(row=0, column=2, sticky='e', padx=5, pady=2)
        self.contact_entry = ttk.Entry(input_frame)
        self.contact_entry.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(input_frame, text="Email:").grid(row=1, column=0, sticky='e', padx=5, pady=2)
        self.email_entry = ttk.Entry(input_frame)
        self.email_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(input_frame, text="Role:").grid(row=1, column=2, sticky='e', padx=5, pady=2)
        self.role_entry = ttk.Entry(input_frame)
        self.role_entry.grid(row=1, column=3, padx=5, pady=2)

        ttk.Label(input_frame, text="Salary:").grid(row=2, column=0, sticky='e', padx=5, pady=2)
        self.salary_entry = ttk.Entry(input_frame)
        self.salary_entry.grid(row=2, column=1, padx=5, pady=2)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(button_frame, text="Add", command=self.add_employee).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Update", command=self.update_employee).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Delete", command=self.delete_employee).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Clear", command=self.clear_entries).pack(side='left', padx=5)

        self.tree = ttk.Treeview(self, columns=("ID", "Name", "Contact", "Email", "Role", "Salary"), show='headings')
        for col in self.tree['columns']:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        self.tree.pack(fill='both', expand=True, padx=10, pady=5)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.selected_id = None

    def load_employees(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = self.db.fetch_all("SELECT * FROM employees")
        for r in rows:
            self.tree.insert('', 'end', values=r)

    def clear_entries(self):
        self.name_entry.delete(0, tk.END)
        self.contact_entry.delete(0, tk.END)
        self.email_entry.delete(0, tk.END)
        self.role_entry.delete(0, tk.END)
        self.salary_entry.delete(0, tk.END)
        self.selected_id = None

    def add_employee(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required")
            return
        contact = self.contact_entry.get().strip()
        email = self.email_entry.get().strip()
        role = self.role_entry.get().strip()
        salary_str = self.salary_entry.get().strip()
        salary = 0.0
        if salary_str:
            try:
                salary = float(salary_str)
            except ValueError:
                messagebox.showerror("Error", "Salary must be a number")
                return
        self.db.execute("INSERT INTO employees (name, contact, email, role, salary) VALUES (?,?,?,?,?)",
                       (name, contact, email, role, salary))
        self.load_employees()
        self.clear_entries()
        messagebox.showinfo("Success", "Employee added")

    def update_employee(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Select an employee to update")
            return
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required")
            return
        contact = self.contact_entry.get().strip()
        email = self.email_entry.get().strip()
        role = self.role_entry.get().strip()
        salary_str = self.salary_entry.get().strip()
        salary = 0.0
        if salary_str:
            try:
                salary = float(salary_str)
            except ValueError:
                messagebox.showerror("Error", "Salary must be a number")
                return
        self.db.execute("UPDATE employees SET name=?, contact=?, email=?, role=?, salary=? WHERE id=?",
                       (name, contact, email, role, salary, self.selected_id))
        self.load_employees()
        self.clear_entries()
        messagebox.showinfo("Success", "Employee updated")

    def delete_employee(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Select an employee to delete")
            return
        if messagebox.askyesno("Confirm", "Delete selected employee?"):
            self.db.execute("DELETE FROM employees WHERE id=?", (self.selected_id,))
            self.load_employees()
            self.clear_entries()
            messagebox.showinfo("Success", "Employee deleted")

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
            self.selected_id = values[0]
            self.name_entry.delete(0, tk.END); self.name_entry.insert(0, values[1])
            self.contact_entry.delete(0, tk.END); self.contact_entry.insert(0, values[2])
            self.email_entry.delete(0, tk.END); self.email_entry.insert(0, values[3])
            self.role_entry.delete(0, tk.END); self.role_entry.insert(0, values[4])
            self.salary_entry.delete(0, tk.END); self.salary_entry.insert(0, values[5])


class SupplierFrame(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, db: Database):
        super().__init__(parent)
        self.db = db
        self.create_widgets()
        self.load_suppliers()

    def create_widgets(self):
        input_frame = ttk.LabelFrame(self, text="Supplier Details")
        input_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(input_frame, text="Name:").grid(row=0, column=0, sticky='e', padx=5, pady=2)
        self.name_entry = ttk.Entry(input_frame)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(input_frame, text="Contact:").grid(row=0, column=2, sticky='e', padx=5, pady=2)
        self.contact_entry = ttk.Entry(input_frame)
        self.contact_entry.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(input_frame, text="Email:").grid(row=1, column=0, sticky='e', padx=5, pady=2)
        self.email_entry = ttk.Entry(input_frame)
        self.email_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(input_frame, text="Address:").grid(row=1, column=2, sticky='e', padx=5, pady=2)
        self.address_entry = ttk.Entry(input_frame)
        self.address_entry.grid(row=1, column=3, padx=5, pady=2)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(button_frame, text="Add", command=self.add_supplier).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Update", command=self.update_supplier).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Delete", command=self.delete_supplier).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Clear", command=self.clear_entries).pack(side='left', padx=5)

        self.tree = ttk.Treeview(self, columns=("ID", "Name", "Contact", "Email", "Address"), show='headings')
        for col in self.tree['columns']:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        self.tree.pack(fill='both', expand=True, padx=10, pady=5)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.selected_id = None

    def load_suppliers(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = self.db.fetch_all("SELECT * FROM suppliers")
        for r in rows:
            self.tree.insert('', 'end', values=r)

    def clear_entries(self):
        self.name_entry.delete(0, tk.END)
        self.contact_entry.delete(0, tk.END)
        self.email_entry.delete(0, tk.END)
        self.address_entry.delete(0, tk.END)
        self.selected_id = None

    def add_supplier(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required")
            return
        contact = self.contact_entry.get().strip()
        email = self.email_entry.get().strip()
        address = self.address_entry.get().strip()
        self.db.execute("INSERT INTO suppliers (name, contact, email, address) VALUES (?,?,?,?)",
                       (name, contact, email, address))
        self.load_suppliers()
        self.clear_entries()
        messagebox.showinfo("Success", "Supplier added")

    def update_supplier(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Select a supplier")
            return
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required")
            return
        contact = self.contact_entry.get().strip()
        email = self.email_entry.get().strip()
        address = self.address_entry.get().strip()
        self.db.execute("UPDATE suppliers SET name=?, contact=?, email=?, address=? WHERE id=?",
                       (name, contact, email, address, self.selected_id))
        self.load_suppliers()
        self.clear_entries()
        messagebox.showinfo("Success", "Supplier updated")

    def delete_supplier(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Select a supplier")
            return
        if messagebox.askyesno("Confirm", "Delete supplier?"):
            self.db.execute("DELETE FROM suppliers WHERE id=?", (self.selected_id,))
            self.load_suppliers()
            self.clear_entries()
            messagebox.showinfo("Success", "Supplier deleted")

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
            self.selected_id = values[0]
            self.name_entry.delete(0, tk.END); self.name_entry.insert(0, values[1])
            self.contact_entry.delete(0, tk.END); self.contact_entry.insert(0, values[2])
            self.email_entry.delete(0, tk.END); self.email_entry.insert(0, values[3])
            self.address_entry.delete(0, tk.END); self.address_entry.insert(0, values[4])


class CategoryFrame(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, db: Database):
        super().__init__(parent)
        self.db = db
        self.create_widgets()
        self.load_categories()

    def create_widgets(self):
        input_frame = ttk.Frame(self)
        input_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(input_frame, text="Category Name:").pack(side='left', padx=5)
        self.name_entry = ttk.Entry(input_frame, width=30)
        self.name_entry.pack(side='left', padx=5)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(button_frame, text="Add", command=self.add_category).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Delete", command=self.delete_category).pack(side='left', padx=5)

        self.tree = ttk.Treeview(self, columns=("ID", "Name"), show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Category Name")
        self.tree.column("ID", width=50)
        self.tree.column("Name", width=200)
        self.tree.pack(fill='both', expand=True, padx=10, pady=5)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.selected_id = None

    def load_categories(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = self.db.fetch_all("SELECT * FROM categories")
        for r in rows:
            self.tree.insert('', 'end', values=r)

    def add_category(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Category name required")
            return
        try:
            self.db.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            self.load_categories()
            self.name_entry.delete(0, tk.END)
            messagebox.showinfo("Success", "Category added")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Category already exists")

    def delete_category(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Select a category")
            return
        if messagebox.askyesno("Confirm", "Delete category?"):
            self.db.execute("DELETE FROM categories WHERE id=?", (self.selected_id,))
            self.load_categories()
            self.name_entry.delete(0, tk.END)
            self.selected_id = None
            messagebox.showinfo("Success", "Category deleted")

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
            self.selected_id = values[0]
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, values[1])


class ProductFrame(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, db: Database):
        super().__init__(parent)
        self.db = db
        self.create_widgets()
        self.load_categories_combobox()
        self.load_products()

    def create_widgets(self):
        input_frame = ttk.LabelFrame(self, text="Product Details")
        input_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(input_frame, text="Name:").grid(row=0, column=0, sticky='e')
        self.name_entry = ttk.Entry(input_frame)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(input_frame, text="Description:").grid(row=0, column=2, sticky='e')
        self.desc_entry = ttk.Entry(input_frame)
        self.desc_entry.grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(input_frame, text="Price:").grid(row=1, column=0, sticky='e')
        self.price_entry = ttk.Entry(input_frame)
        self.price_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(input_frame, text="Stock:").grid(row=1, column=2, sticky='e')
        self.stock_entry = ttk.Entry(input_frame)
        self.stock_entry.grid(row=1, column=3, padx=5, pady=2)

        ttk.Label(input_frame, text="Category:").grid(row=2, column=0, sticky='e')
        self.category_combo = ttk.Combobox(input_frame, state='readonly')
        self.category_combo.grid(row=2, column=1, padx=5, pady=2)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(button_frame, text="Add", command=self.add_product).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Update", command=self.update_product).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Delete", command=self.delete_product).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Clear", command=self.clear_entries).pack(side='left', padx=5)

        self.tree = ttk.Treeview(self, columns=("ID", "Name", "Description", "Price", "Stock", "Category"), show='headings')
        cols = ["ID", "Name", "Description", "Price", "Stock", "Category"]
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        self.tree.pack(fill='both', expand=True, padx=10, pady=5)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        self.selected_id = None

    def load_categories_combobox(self):
        cats = self.db.fetch_all("SELECT id, name FROM categories")
        self.category_dict = {name: id for id, name in cats}
        self.category_combo['values'] = list(self.category_dict.keys())
        if self.category_combo['values']:
            self.category_combo.current(0)

    def load_products(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = self.db.fetch_all("""
            SELECT p.id, p.name, p.description, p.price, p.stock, c.name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
        """)
        for r in rows:
            self.tree.insert('', 'end', values=r)

    def clear_entries(self):
        self.name_entry.delete(0, tk.END)
        self.desc_entry.delete(0, tk.END)
        self.price_entry.delete(0, tk.END)
        self.stock_entry.delete(0, tk.END)
        if self.category_combo['values']:
            self.category_combo.current(0)
        self.selected_id = None

    def get_form_data(self):
        name = self.name_entry.get().strip()
        if not name:
            raise ValueError("Product name required")
        desc = self.desc_entry.get().strip()
        price_str = self.price_entry.get().strip()
        try:
            price = float(price_str)
        except ValueError:
            raise ValueError("Price must be a number")
        stock_str = self.stock_entry.get().strip()
        try:
            stock = int(stock_str) if stock_str else 0
        except ValueError:
            raise ValueError("Stock must be an integer")
        cat_name = self.category_combo.get()
        if not cat_name:
            raise ValueError("Please select a category")
        cat_id = self.category_dict.get(cat_name)
        if cat_id is None:
            raise ValueError("Invalid category")
        return name, desc, price, stock, cat_id

    def add_product(self):
        try:
            name, desc, price, stock, cat_id = self.get_form_data()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        self.db.execute("INSERT INTO products (name, description, price, stock, category_id) VALUES (?,?,?,?,?)",
                       (name, desc, price, stock, cat_id))
        self.load_products()
        self.clear_entries()
        messagebox.showinfo("Success", "Product added")

    def update_product(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Select a product")
            return
        try:
            name, desc, price, stock, cat_id = self.get_form_data()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        self.db.execute("UPDATE products SET name=?, description=?, price=?, stock=?, category_id=? WHERE id=?",
                       (name, desc, price, stock, cat_id, self.selected_id))
        self.load_products()
        self.clear_entries()
        messagebox.showinfo("Success", "Product updated")

    def delete_product(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Select a product")
            return
        if messagebox.askyesno("Confirm", "Delete product?"):
            self.db.execute("DELETE FROM products WHERE id=?", (self.selected_id,))
            self.load_products()
            self.clear_entries()
            messagebox.showinfo("Success", "Product deleted")

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
            self.selected_id = values[0]
            self.name_entry.delete(0, tk.END); self.name_entry.insert(0, values[1])
            self.desc_entry.delete(0, tk.END); self.desc_entry.insert(0, values[2])
            self.price_entry.delete(0, tk.END); self.price_entry.insert(0, values[3])
            self.stock_entry.delete(0, tk.END); self.stock_entry.insert(0, values[4])
            cat_name = values[5] if values[5] else ''
            if cat_name in self.category_dict:
                self.category_combo.set(cat_name)


class BillingFrame(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, db: Database):
        super().__init__(parent)
        self.db = db
        self.cart: List[Tuple[int, str, float, int, float]] = []  # (product_id, name, price, qty, total)
        self.create_widgets()
        self.load_products_combobox()
        self.generate_invoice_number()

    def create_widgets(self):
        customer_frame = ttk.LabelFrame(self, text="Customer Details")
        customer_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(customer_frame, text="Customer Name:").pack(side='left', padx=5)
        self.customer_entry = ttk.Entry(customer_frame)
        self.customer_entry.pack(side='left', fill='x', expand=True, padx=5)

        ttk.Label(customer_frame, text="Invoice No:").pack(side='left', padx=5)
        self.invoice_label = ttk.Label(customer_frame, text="---", width=10)
        self.invoice_label.pack(side='left', padx=5)

        cart_input_frame = ttk.Frame(self)
        cart_input_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(cart_input_frame, text="Product:").pack(side='left', padx=5)
        self.product_combo = ttk.Combobox(cart_input_frame, state='readonly', width=30)
        self.product_combo.pack(side='left', padx=5)
        ttk.Label(cart_input_frame, text="Quantity:").pack(side='left', padx=5)
        self.qty_entry = ttk.Entry(cart_input_frame, width=10)
        self.qty_entry.pack(side='left', padx=5)
        ttk.Button(cart_input_frame, text="Add to Cart", command=self.add_to_cart).pack(side='left', padx=10)

        self.cart_tree = ttk.Treeview(self, columns=("Product", "Price", "Qty", "Total"), show='headings')
        self.cart_tree.heading("Product", text="Product")
        self.cart_tree.heading("Price", text="Price")
        self.cart_tree.heading("Qty", text="Qty")
        self.cart_tree.heading("Total", text="Total")
        self.cart_tree.column("Product", width=200)
        self.cart_tree.column("Price", width=80)
        self.cart_tree.column("Qty", width=80)
        self.cart_tree.column("Total", width=100)
        self.cart_tree.pack(fill='both', expand=True, padx=10, pady=5)

        self.total_label = ttk.Label(self, text="Total: 0.00", font=("Arial", 12, "bold"))
        self.total_label.pack(anchor='e', padx=20, pady=5)

        ttk.Button(self, text="Generate Invoice", command=self.generate_invoice).pack(pady=10)

    def load_products_combobox(self):
        products = self.db.fetch_all("SELECT id, name, price, stock FROM products")
        self.products_dict = {}
        self.product_stock = {}
        values = []
        for pid, name, price, stock in products:
            display = f"{name} (Stock: {stock})"
            self.products_dict[display] = (pid, price, stock)
            self.product_stock[pid] = stock
            values.append(display)
        self.product_combo['values'] = values
        if values:
            self.product_combo.current(0)

    def generate_invoice_number(self):
        row = self.db.fetch_one("SELECT MAX(invoice_no) FROM invoices")
        self.next_invoice = (row[0] + 1) if row[0] else 1
        self.invoice_label.config(text=str(self.next_invoice))

    def add_to_cart(self):
        selection = self.product_combo.get()
        if not selection:
            messagebox.showerror("Error", "Select a product")
            return
        pid, price, stock = self.products_dict[selection]
        qty_str = self.qty_entry.get().strip()
        try:
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Quantity must be positive integer")
            return
        if qty > stock:
            messagebox.showerror("Error", f"Insufficient stock. Available: {stock}")
            return
        name = selection.split(" (")[0]
        # Check if product already in cart, update quantity
        for i, (cpid, cname, cprice, cqty, ctotal) in enumerate(self.cart):
            if cpid == pid:
                new_qty = cqty + qty
                if new_qty > stock:
                    messagebox.showerror("Error", f"Total quantity exceeds stock ({stock})")
                    return
                new_total = new_qty * price
                self.cart[i] = (pid, name, price, new_qty, new_total)
                self.refresh_cart()
                return
        total = qty * price
        self.cart.append((pid, name, price, qty, total))
        self.refresh_cart()

    def refresh_cart(self):
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        cart_total = 0.0
        for item in self.cart:
            _, name, price, qty, total = item
            self.cart_tree.insert('', 'end', values=(name, f"{price:.2f}", qty, f"{total:.2f}"))
            cart_total += total
        self.total_label.config(text=f"Total: {cart_total:.2f}")

    def generate_invoice(self):
        if not self.cart:
            messagebox.showerror("Error", "Cart is empty")
            return
        customer = self.customer_entry.get().strip()
        date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = sum(item[4] for item in self.cart)
        inv_no = self.next_invoice
        try:
            self.db.execute("INSERT INTO invoices (invoice_no, date, customer_name, total) VALUES (?,?,?,?)",
                           (inv_no, date, customer, total))
            for pid, name, price, qty, item_total in self.cart:
                self.db.execute("INSERT INTO invoice_items (invoice_no, product_id, product_name, price, quantity, total) VALUES (?,?,?,?,?,?)",
                               (inv_no, pid, name, price, qty, item_total))
                # Update stock
                self.db.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (qty, pid))
            self.db.conn.commit()
            messagebox.showinfo("Success", f"Invoice {inv_no} generated successfully")
            # Reset
            self.cart.clear()
            self.refresh_cart()
            self.customer_entry.delete(0, tk.END)
            self.generate_invoice_number()
            self.load_products_combobox()  # refresh stock displays
        except Exception as e:
            self.db.conn.rollback()
            messagebox.showerror("Error", f"Failed to generate invoice: {e}")


class InvoiceFrame(ttk.Frame):
    def __init__(self, parent: ttk.Notebook, db: Database):
        super().__init__(parent)
        self.db = db
        self.create_widgets()
        self.load_invoices()

    def create_widgets(self):
        self.tree = ttk.Treeview(self, columns=("Invoice No", "Date", "Customer", "Total"), show='headings')
        cols = ["Invoice No", "Date", "Customer", "Total"]
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        self.tree.pack(fill='both', expand=True, padx=10, pady=5)
        self.tree.bind('<Double-1>', self.view_invoice_details)

    def load_invoices(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        invoices = self.db.fetch_all("SELECT invoice_no, date, customer_name, total FROM invoices ORDER BY invoice_no DESC")
        for inv in invoices:
            self.tree.insert('', 'end', values=inv)

    def view_invoice_details(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        inv_no = item['values'][0]
        details = self.db.fetch_all("""
            SELECT product_name, price, quantity, total 
            FROM invoice_items 
            WHERE invoice_no = ?
        """, (inv_no,))
        if not details:
            return
        top = tk.Toplevel(self)
        top.title(f"Invoice #{inv_no}")
        top.geometry("500x300")
        tree = ttk.Treeview(top, columns=("Product", "Price", "Qty", "Total"), show='headings')
        for col in tree['columns']:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        tree.pack(fill='both', expand=True)
        for d in details:
            tree.insert('', 'end', values=d)
        grand_total = sum(d[3] for d in details)
        ttk.Label(top, text=f"Grand Total: {grand_total:.2f}", font=("Arial", 12, "bold")).pack(pady=10)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()