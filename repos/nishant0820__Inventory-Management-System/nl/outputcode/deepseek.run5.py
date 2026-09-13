import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import font
import sqlite3
import datetime
import os
from PIL import Image, ImageTk


class Database:
    def __init__(self, db_name="inventory.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                address TEXT
            )"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT,
                email TEXT,
                address TEXT
            )"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT
            )"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER,
                price REAL NOT NULL,
                stock_quantity INTEGER NOT NULL,
                supplier_id INTEGER,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            )"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT UNIQUE NOT NULL,
                date TEXT NOT NULL,
                employee_id INTEGER,
                total_amount REAL NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            )"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS bill_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER NOT NULL,
                product_id INTEGER,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                subtotal REAL NOT NULL,
                FOREIGN KEY (bill_id) REFERENCES bills(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )"""
        )
        self.conn.commit()

    # Employee methods
    def add_employee(self, name, phone, email, address):
        self.cursor.execute(
            "INSERT INTO employees (name, phone, email, address) VALUES (?,?,?,?)",
            (name, phone, email, address),
        )
        self.conn.commit()

    def get_all_employees(self):
        self.cursor.execute("SELECT * FROM employees")
        return self.cursor.fetchall()

    def update_employee(self, emp_id, name, phone, email, address):
        self.cursor.execute(
            "UPDATE employees SET name=?, phone=?, email=?, address=? WHERE id=?",
            (name, phone, email, address, emp_id),
        )
        self.conn.commit()

    def delete_employee(self, emp_id):
        self.cursor.execute("DELETE FROM employees WHERE id=?", (emp_id,))
        self.conn.commit()

    def search_employee(self, emp_id):
        self.cursor.execute("SELECT * FROM employees WHERE id=?", (emp_id,))
        return self.cursor.fetchone()

    # Supplier methods
    def add_supplier(self, name, contact, email, address):
        self.cursor.execute(
            "INSERT INTO suppliers (name, contact, email, address) VALUES (?,?,?,?)",
            (name, contact, email, address),
        )
        self.conn.commit()

    def get_all_suppliers(self):
        self.cursor.execute("SELECT * FROM suppliers")
        return self.cursor.fetchall()

    def update_supplier(self, sup_id, name, contact, email, address):
        self.cursor.execute(
            "UPDATE suppliers SET name=?, contact=?, email=?, address=? WHERE id=?",
            (name, contact, email, address, sup_id),
        )
        self.conn.commit()

    def delete_supplier(self, sup_id):
        self.cursor.execute("DELETE FROM suppliers WHERE id=?", (sup_id,))
        self.conn.commit()

    def search_supplier(self, sup_id):
        self.cursor.execute("SELECT * FROM suppliers WHERE id=?", (sup_id,))
        return self.cursor.fetchone()

    # Category methods
    def add_category(self, name, description):
        self.cursor.execute(
            "INSERT INTO categories (name, description) VALUES (?,?)",
            (name, description),
        )
        self.conn.commit()

    def get_all_categories(self):
        self.cursor.execute("SELECT * FROM categories")
        return self.cursor.fetchall()

    def update_category(self, cat_id, name, description):
        self.cursor.execute(
            "UPDATE categories SET name=?, description=? WHERE id=?",
            (name, description, cat_id),
        )
        self.conn.commit()

    def delete_category(self, cat_id):
        self.cursor.execute("DELETE FROM categories WHERE id=?", (cat_id,))
        self.conn.commit()

    def search_category(self, cat_id):
        self.cursor.execute("SELECT * FROM categories WHERE id=?", (cat_id,))
        return self.cursor.fetchone()

    # Product methods
    def add_product(self, name, category_id, price, stock, supplier_id):
        self.cursor.execute(
            "INSERT INTO products (name, category_id, price, stock_quantity, supplier_id) VALUES (?,?,?,?,?)",
            (name, category_id, price, stock, supplier_id),
        )
        self.conn.commit()

    def get_all_products(self):
        self.cursor.execute("SELECT * FROM products")
        return self.cursor.fetchall()

    def update_product(self, prod_id, name, category_id, price, stock, supplier_id):
        self.cursor.execute(
            "UPDATE products SET name=?, category_id=?, price=?, stock_quantity=?, supplier_id=? WHERE id=?",
            (name, category_id, price, stock, supplier_id, prod_id),
        )
        self.conn.commit()

    def delete_product(self, prod_id):
        self.cursor.execute("DELETE FROM products WHERE id=?", (prod_id,))
        self.conn.commit()

    def search_product(self, prod_id):
        self.cursor.execute("SELECT * FROM products WHERE id=?", (prod_id,))
        return self.cursor.fetchone()

    # Bill methods
    def add_bill(self, invoice_no, date, employee_id, total_amount, items):
        self.cursor.execute(
            "INSERT INTO bills (invoice_no, date, employee_id, total_amount) VALUES (?,?,?,?)",
            (invoice_no, date, employee_id, total_amount),
        )
        bill_id = self.cursor.lastrowid
        for item in items:
            self.cursor.execute(
                "INSERT INTO bill_items (bill_id, product_id, quantity, price, subtotal) VALUES (?,?,?,?,?)",
                (bill_id, item["product_id"], item["quantity"], item["price"], item["subtotal"]),
            )
            # Decrease stock
            self.cursor.execute(
                "UPDATE products SET stock_quantity = stock_quantity - ? WHERE id=?",
                (item["quantity"], item["product_id"]),
            )
        self.conn.commit()

    def get_all_bills(self):
        self.cursor.execute("SELECT * FROM bills")
        return self.cursor.fetchall()

    def search_bill_by_invoice(self, invoice_no):
        self.cursor.execute("SELECT * FROM bills WHERE invoice_no=?", (invoice_no,))
        bill = self.cursor.fetchone()
        if bill:
            bill_id = bill[0]
            self.cursor.execute("SELECT * FROM bill_items WHERE bill_id=?", (bill_id,))
            items = self.cursor.fetchall()
            return bill, items
        return None, []


class BaseForm(ttk.Frame):
    def __init__(self, parent, db, title, columns, table_name):
        super().__init__(parent)
        self.db = db
        self.title_text = title
        self.columns = columns
        self.table_name = table_name
        self.setup_ui()

    def setup_ui(self):
        # Title
        title_label = ttk.Label(self, text=self.title_text, font=("Arial", 14, "bold"))
        title_label.pack(pady=5)

        # Form fields (to be overridden by child if needed)
        self.create_form_fields()

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Add", command=self.add_record).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Update", command=self.update_record).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_record).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear", command=self.clear_form).pack(side="left", padx=5)

        # Treeview with scrollbar
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, pady=10)
        self.tree = ttk.Treeview(tree_frame, columns=tuple(range(len(self.columns))), show="headings")
        for i, col in enumerate(self.columns):
            self.tree.heading(i, text=col)
            self.tree.column(i, width=100)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<ButtonRelease-1>", self.on_tree_select)

        self.load_data()

    def create_form_fields(self):
        # To be overridden
        pass

    def add_record(self):
        raise NotImplementedError

    def update_record(self):
        raise NotImplementedError

    def delete_record(self):
        raise NotImplementedError

    def clear_form(self):
        # To be overridden
        pass

    def load_data(self):
        raise NotImplementedError

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0], "values")
            self.populate_form(values)

    def populate_form(self, values):
        # To be overridden
        pass


class EmployeeForm(BaseForm):
    def __init__(self, parent, db):
        super().__init__(parent, db, "Employee Management", ["ID", "Name", "Phone", "Email", "Address"], "employees")
        self.emp_id = None

    def create_form_fields(self):
        fields_frame = ttk.Frame(self)
        fields_frame.pack(pady=10)
        ttk.Label(fields_frame, text="Name:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.name_entry = ttk.Entry(fields_frame, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(fields_frame, text="Phone:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.phone_entry = ttk.Entry(fields_frame, width=30)
        self.phone_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(fields_frame, text="Email:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self.email_entry = ttk.Entry(fields_frame, width=30)
        self.email_entry.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(fields_frame, text="Address:").grid(row=3, column=0, sticky="e", padx=5, pady=2)
        self.address_entry = ttk.Entry(fields_frame, width=30)
        self.address_entry.grid(row=3, column=1, padx=5, pady=2)

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        for row in self.db.get_all_employees():
            self.tree.insert("", "end", values=row)

    def add_record(self):
        name = self.name_entry.get()
        phone = self.phone_entry.get()
        email = self.email_entry.get()
        address = self.address_entry.get()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        self.db.add_employee(name, phone, email, address)
        self.clear_form()
        self.load_data()
        messagebox.showinfo("Success", "Employee added")

    def update_record(self):
        if not self.emp_id:
            messagebox.showerror("Error", "Select an employee to update")
            return
        name = self.name_entry.get()
        phone = self.phone_entry.get()
        email = self.email_entry.get()
        address = self.address_entry.get()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        self.db.update_employee(self.emp_id, name, phone, email, address)
        self.clear_form()
        self.load_data()
        self.emp_id = None
        messagebox.showinfo("Success", "Employee updated")

    def delete_record(self):
        if not self.emp_id:
            messagebox.showerror("Error", "Select an employee to delete")
            return
        if messagebox.askyesno("Confirm", "Delete this employee?"):
            self.db.delete_employee(self.emp_id)
            self.clear_form()
            self.load_data()
            self.emp_id = None
            messagebox.showinfo("Success", "Employee deleted")

    def clear_form(self):
        self.name_entry.delete(0, "end")
        self.phone_entry.delete(0, "end")
        self.email_entry.delete(0, "end")
        self.address_entry.delete(0, "end")
        self.emp_id = None

    def populate_form(self, values):
        self.clear_form()
        self.emp_id = values[0]
        self.name_entry.insert(0, values[1])
        self.phone_entry.insert(0, values[2])
        self.email_entry.insert(0, values[3])
        self.address_entry.insert(0, values[4])


class SupplierForm(BaseForm):
    def __init__(self, parent, db):
        super().__init__(parent, db, "Supplier Management", ["ID", "Name", "Contact", "Email", "Address"], "suppliers")
        self.sup_id = None

    def create_form_fields(self):
        fields_frame = ttk.Frame(self)
        fields_frame.pack(pady=10)
        ttk.Label(fields_frame, text="Name:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.name_entry = ttk.Entry(fields_frame, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(fields_frame, text="Contact:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.contact_entry = ttk.Entry(fields_frame, width=30)
        self.contact_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(fields_frame, text="Email:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self.email_entry = ttk.Entry(fields_frame, width=30)
        self.email_entry.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(fields_frame, text="Address:").grid(row=3, column=0, sticky="e", padx=5, pady=2)
        self.address_entry = ttk.Entry(fields_frame, width=30)
        self.address_entry.grid(row=3, column=1, padx=5, pady=2)

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        for row in self.db.get_all_suppliers():
            self.tree.insert("", "end", values=row)

    def add_record(self):
        name = self.name_entry.get()
        contact = self.contact_entry.get()
        email = self.email_entry.get()
        address = self.address_entry.get()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        self.db.add_supplier(name, contact, email, address)
        self.clear_form()
        self.load_data()
        messagebox.showinfo("Success", "Supplier added")

    def update_record(self):
        if not self.sup_id:
            messagebox.showerror("Error", "Select a supplier to update")
            return
        name = self.name_entry.get()
        contact = self.contact_entry.get()
        email = self.email_entry.get()
        address = self.address_entry.get()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        self.db.update_supplier(self.sup_id, name, contact, email, address)
        self.clear_form()
        self.load_data()
        self.sup_id = None
        messagebox.showinfo("Success", "Supplier updated")

    def delete_record(self):
        if not self.sup_id:
            messagebox.showerror("Error", "Select a supplier to delete")
            return
        if messagebox.askyesno("Confirm", "Delete this supplier?"):
            self.db.delete_supplier(self.sup_id)
            self.clear_form()
            self.load_data()
            self.sup_id = None
            messagebox.showinfo("Success", "Supplier deleted")

    def clear_form(self):
        self.name_entry.delete(0, "end")
        self.contact_entry.delete(0, "end")
        self.email_entry.delete(0, "end")
        self.address_entry.delete(0, "end")
        self.sup_id = None

    def populate_form(self, values):
        self.clear_form()
        self.sup_id = values[0]
        self.name_entry.insert(0, values[1])
        self.contact_entry.insert(0, values[2])
        self.email_entry.insert(0, values[3])
        self.address_entry.insert(0, values[4])


class CategoryForm(BaseForm):
    def __init__(self, parent, db):
        super().__init__(parent, db, "Category Management", ["ID", "Name", "Description"], "categories")
        self.cat_id = None

    def create_form_fields(self):
        fields_frame = ttk.Frame(self)
        fields_frame.pack(pady=10)
        ttk.Label(fields_frame, text="Name:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.name_entry = ttk.Entry(fields_frame, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(fields_frame, text="Description:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.desc_entry = ttk.Entry(fields_frame, width=30)
        self.desc_entry.grid(row=1, column=1, padx=5, pady=2)

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        for row in self.db.get_all_categories():
            self.tree.insert("", "end", values=row)

    def add_record(self):
        name = self.name_entry.get()
        desc = self.desc_entry.get()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        self.db.add_category(name, desc)
        self.clear_form()
        self.load_data()
        messagebox.showinfo("Success", "Category added")

    def update_record(self):
        if not self.cat_id:
            messagebox.showerror("Error", "Select a category to update")
            return
        name = self.name_entry.get()
        desc = self.desc_entry.get()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        self.db.update_category(self.cat_id, name, desc)
        self.clear_form()
        self.load_data()
        self.cat_id = None
        messagebox.showinfo("Success", "Category updated")

    def delete_record(self):
        if not self.cat_id:
            messagebox.showerror("Error", "Select a category to delete")
            return
        if messagebox.askyesno("Confirm", "Delete this category?"):
            self.db.delete_category(self.cat_id)
            self.clear_form()
            self.load_data()
            self.cat_id = None
            messagebox.showinfo("Success", "Category deleted")

    def clear_form(self):
        self.name_entry.delete(0, "end")
        self.desc_entry.delete(0, "end")
        self.cat_id = None

    def populate_form(self, values):
        self.clear_form()
        self.cat_id = values[0]
        self.name_entry.insert(0, values[1])
        self.desc_entry.insert(0, values[2])


class ProductForm(BaseForm):
    def __init__(self, parent, db):
        super().__init__(parent, db, "Product Management", ["ID", "Name", "Category ID", "Price", "Stock", "Supplier ID"], "products")
        self.prod_id = None

    def create_form_fields(self):
        fields_frame = ttk.Frame(self)
        fields_frame.pack(pady=10)
        ttk.Label(fields_frame, text="Name:").grid(row=0, column=0, sticky="e", padx=5, pady=2)
        self.name_entry = ttk.Entry(fields_frame, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(fields_frame, text="Category ID:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.cat_id_entry = ttk.Entry(fields_frame, width=30)
        self.cat_id_entry.grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(fields_frame, text="Price:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self.price_entry = ttk.Entry(fields_frame, width=30)
        self.price_entry.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(fields_frame, text="Stock Qty:").grid(row=3, column=0, sticky="e", padx=5, pady=2)
        self.stock_entry = ttk.Entry(fields_frame, width=30)
        self.stock_entry.grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(fields_frame, text="Supplier ID:").grid(row=4, column=0, sticky="e", padx=5, pady=2)
        self.sup_id_entry = ttk.Entry(fields_frame, width=30)
        self.sup_id_entry.grid(row=4, column=1, padx=5, pady=2)

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        for row in self.db.get_all_products():
            self.tree.insert("", "end", values=row)

    def add_record(self):
        name = self.name_entry.get()
        cat_id = self.cat_id_entry.get()
        price = self.price_entry.get()
        stock = self.stock_entry.get()
        sup_id = self.sup_id_entry.get()
        if not name or not price or not stock:
            messagebox.showerror("Error", "Name, Price, Stock are required")
            return
        try:
            cat_id = int(cat_id) if cat_id else None
            price = float(price)
            stock = int(stock)
            sup_id = int(sup_id) if sup_id else None
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric values")
            return
        self.db.add_product(name, cat_id, price, stock, sup_id)
        self.clear_form()
        self.load_data()
        messagebox.showinfo("Success", "Product added")

    def update_record(self):
        if not self.prod_id:
            messagebox.showerror("Error", "Select a product to update")
            return
        name = self.name_entry.get()
        cat_id = self.cat_id_entry.get()
        price = self.price_entry.get()
        stock = self.stock_entry.get()
        sup_id = self.sup_id_entry.get()
        if not name or not price or not stock:
            messagebox.showerror("Error", "Name, Price, Stock are required")
            return
        try:
            cat_id = int(cat_id) if cat_id else None
            price = float(price)
            stock = int(stock)
            sup_id = int(sup_id) if sup_id else None
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric values")
            return
        self.db.update_product(self.prod_id, name, cat_id, price, stock, sup_id)
        self.clear_form()
        self.load_data()
        self.prod_id = None
        messagebox.showinfo("Success", "Product updated")

    def delete_record(self):
        if not self.prod_id:
            messagebox.showerror("Error", "Select a product to delete")
            return
        if messagebox.askyesno("Confirm", "Delete this product?"):
            self.db.delete_product(self.prod_id)
            self.clear_form()
            self.load_data()
            self.prod_id = None
            messagebox.showinfo("Success", "Product deleted")

    def clear_form(self):
        self.name_entry.delete(0, "end")
        self.cat_id_entry.delete(0, "end")
        self.price_entry.delete(0, "end")
        self.stock_entry.delete(0, "end")
        self.sup_id_entry.delete(0, "end")
        self.prod_id = None

    def populate_form(self, values):
        self.clear_form()
        self.prod_id = values[0]
        self.name_entry.insert(0, values[1])
        self.cat_id_entry.insert(0, values[2] if values[2] else "")
        self.price_entry.insert(0, values[3])
        self.stock_entry.insert(0, values[4])
        self.sup_id_entry.insert(0, values[5] if values[5] else "")


class BillingFrame(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.items = []  # list of dicts {'product_id':, 'product_name':, 'price':, 'quantity':, 'subtotal':}
        self.invoice_var = tk.StringVar()
        self.employee_var = tk.StringVar()
        self.total_amount = 0.0
        self.setup_ui()

    def setup_ui(self):
        # Header
        ttk.Label(self, text="Billing", font=("Arial", 14, "bold")).pack(pady=5)

        # Invoice number and date
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(header_frame, text="Invoice No:").grid(row=0, column=0, padx=5, sticky="w")
        self.invoice_entry = ttk.Entry(header_frame, textvariable=self.invoice_var, width=20)
        self.invoice_entry.grid(row=0, column=1, padx=5)
        ttk.Label(header_frame, text="Date:").grid(row=0, column=2, padx=5, sticky="w")
        self.date_entry = ttk.Entry(header_frame, width=15)
        self.date_entry.insert(0, datetime.date.today().strftime("%Y-%m-%d"))
        self.date_entry.grid(row=0, column=3, padx=5)
        ttk.Label(header_frame, text="Employee ID:").grid(row=0, column=4, padx=5, sticky="w")
        self.employee_entry = ttk.Entry(header_frame, width=10)
        self.employee_entry.grid(row=0, column=5, padx=5)

        # Product selection area
        prod_frame = ttk.LabelFrame(self, text="Add Product")
        prod_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(prod_frame, text="Product ID:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.product_id_entry = ttk.Entry(prod_frame, width=10)
        self.product_id_entry.grid(row=0, column=1, padx=5)

        ttk.Label(prod_frame, text="Quantity:").grid(row=0, column=2, padx=5, sticky="e")
        self.qty_entry = ttk.Entry(prod_frame, width=10)
        self.qty_entry.grid(row=0, column=3, padx=5)

        ttk.Button(prod_frame, text="Add to Cart", command=self.add_to_cart).grid(row=0, column=4, padx=10)

        # Cart treeview
        cart_frame = ttk.Frame(self)
        cart_frame.pack(fill="both", expand=True, padx=10, pady=5)
        columns = ("Product ID", "Product Name", "Price", "Quantity", "Subtotal")
        self.cart_tree = ttk.Treeview(cart_frame, columns=columns, show="headings", height=8)
        for col in columns:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=100)
        self.cart_tree.pack(side="left", fill="both", expand=True)
        cart_scroll = ttk.Scrollbar(cart_frame, orient="vertical", command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=cart_scroll.set)
        cart_scroll.pack(side="right", fill="y")

        # Total and buttons
        total_frame = ttk.Frame(self)
        total_frame.pack(fill="x", padx=10, pady=5)
        self.total_label = ttk.Label(total_frame, text="Total: $0.00", font=("Arial", 12, "bold"))
        self.total_label.pack(side="left", padx=10)
        ttk.Button(total_frame, text="Generate Bill", command=self.generate_bill).pack(side="right", padx=5)
        ttk.Button(total_frame, text="Clear Cart", command=self.clear_cart).pack(side="right", padx=5)

        # View bill section
        view_frame = ttk.LabelFrame(self, text="View Bill")
        view_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(view_frame, text="Invoice No:").pack(side="left", padx=5)
        self.search_invoice_entry = ttk.Entry(view_frame, width=15)
        self.search_invoice_entry.pack(side="left", padx=5)
        ttk.Button(view_frame, text="Search", command=self.view_bill).pack(side="left", padx=5)
        self.bill_display_text = tk.Text(view_frame, height=6, width=60)
        self.bill_display_text.pack(side="left", padx=5, pady=5)

    def add_to_cart(self):
        prod_id = self.product_id_entry.get().strip()
        qty = self.qty_entry.get().strip()
        if not prod_id or not qty:
            messagebox.showerror("Error", "Enter product ID and quantity")
            return
        try:
            prod_id = int(prod_id)
            qty = int(qty)
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric values")
            return
        product = self.db.search_product(prod_id)
        if not product:
            messagebox.showerror("Error", "Product not found")
            return
        if qty <= 0:
            messagebox.showerror("Error", "Quantity must be positive")
            return
        if product[4] < qty:
            messagebox.showerror("Error", f"Insufficient stock. Available: {product[4]}")
            return
        price = product[3]
        subtotal = price * qty
        # Check if product already in cart
        for item in self.items:
            if item["product_id"] == prod_id:
                # Update quantity and subtotal
                item["quantity"] += qty
                item["subtotal"] += subtotal
                self.refresh_cart_tree()
                self.update_total()
                return
        self.items.append({
            "product_id": prod_id,
            "product_name": product[1],
            "price": price,
            "quantity": qty,
            "subtotal": subtotal
        })
        self.refresh_cart_tree()
        self.update_total()

    def refresh_cart_tree(self):
        self.cart_tree.delete(*self.cart_tree.get_children())
        for item in self.items:
            self.cart_tree.insert("", "end", values=(
                item["product_id"],
                item["product_name"],
                f"{item['price']:.2f}",
                item["quantity"],
                f"{item['subtotal']:.2f}"
            ))

    def update_total(self):
        self.total_amount = sum(item["subtotal"] for item in self.items)
        self.total_label.config(text=f"Total: ${self.total_amount:.2f}")

    def clear_cart(self):
        self.items = []
        self.refresh_cart_tree()
        self.total_amount = 0.0
        self.total_label.config(text="Total: $0.00")

    def generate_bill(self):
        invoice_no = self.invoice_var.get().strip()
        if not invoice_no:
            messagebox.showerror("Error", "Enter invoice number")
            return
        if not self.items:
            messagebox.showerror("Error", "Cart is empty")
            return
        date = self.date_entry.get()
        employee_id = self.employee_entry.get().strip()
        employee_id = int(employee_id) if employee_id else None
        try:
            self.db.add_bill(invoice_no, date, employee_id, self.total_amount, self.items)
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Invoice number already exists")
            return
        messagebox.showinfo("Success", "Bill generated successfully")
        self.clear_cart()
        self.invoice_var.set("")

    def view_bill(self):
        invoice_no = self.search_invoice_entry.get().strip()
        if not invoice_no:
            messagebox.showerror("Error", "Enter invoice number")
            return
        bill, items = self.db.search_bill_by_invoice(invoice_no)
        if not bill:
            messagebox.showinfo("Not Found", "Bill not found")
            return
        self.bill_display_text.delete(1.0, "end")
        self.bill_display_text.insert("end", f"Invoice No: {bill[1]}\nDate: {bill[2]}\nEmployee ID: {bill[3] if bill[3] else 'N/A'}\n")
        self.bill_display_text.insert("end", f"Total: ${bill[4]:.2f}\n\nItems:\n")
        for item in items:
            product = self.db.search_product(item[2])
            name = product[1] if product else "Unknown"
            self.bill_display_text.insert("end", f"  {name} x{item[3]} @ {item[4]:.2f} = {item[5]:.2f}\n")


class Dashboard(ttk.Frame):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.setup_ui()
        self.update_clock()

    def setup_ui(self):
        # Load image if exists
        try:
            img_path = "logo.png"
            if os.path.exists(img_path):
                pil_image = Image.open(img_path)
                pil_image = pil_image.resize((150, 150), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(pil_image)
                logo_label = ttk.Label(self, image=self.logo_img)
                logo_label.pack(pady=20)
        except Exception:
            pass

        ttk.Label(self, text="Inventory Management System", font=("Arial", 18, "bold")).pack(pady=10)
        self.clock_label = ttk.Label(self, text="", font=("Arial", 12))
        self.clock_label.pack(pady=5)

        # Quick stats or buttons? Not required but can show employee count etc.
        stats_frame = ttk.Frame(self)
        stats_frame.pack(pady=20)
        self.emp_count_label = ttk.Label(stats_frame, text="Employees: 0")
        self.emp_count_label.pack(side="left", padx=10)
        self.prod_count_label = ttk.Label(stats_frame, text="Products: 0")
        self.prod_count_label.pack(side="left", padx=10)
        self.supplier_count_label = ttk.Label(stats_frame, text="Suppliers: 0")
        self.supplier_count_label.pack(side="left", padx=10)
        self.bill_count_label = ttk.Label(stats_frame, text="Bills: 0")
        self.bill_count_label.pack(side="left", padx=10)

        # Bind to update stats when tab is entered (optional)
        self.update_stats()

    def update_clock(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.config(text=now)
        self.after(1000, self.update_clock)

    def update_stats(self):
        try:
            # get counts from db
            emp_count = len(self.db.get_all_employees())
            prod_count = len(self.db.get_all_products())
            sup_count = len(self.db.get_all_suppliers())
            bill_count = len(self.db.get_all_bills())
        except Exception:
            emp_count = prod_count = sup_count = bill_count = 0
        self.emp_count_label.config(text=f"Employees: {emp_count}")
        self.prod_count_label.config(text=f"Products: {prod_count}")
        self.supplier_count_label.config(text=f"Suppliers: {sup_count}")
        self.bill_count_label.config(text=f"Bills: {bill_count}")
        self.after(5000, self.update_stats)  # refresh every 5 seconds


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Inventory Management System")
        self.root.geometry("900x650")
        self.db = Database()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        self.dashboard = Dashboard(self.notebook, self.db)
        self.notebook.add(self.dashboard, text="Dashboard")

        self.employee_form = EmployeeForm(self.notebook, self.db)
        self.notebook.add(self.employee_form, text="Employees")

        self.supplier_form = SupplierForm(self.notebook, self.db)
        self.notebook.add(self.supplier_form, text="Suppliers")

        self.category_form = CategoryForm(self.notebook, self.db)
        self.notebook.add(self.category_form, text="Categories")

        self.product_form = ProductForm(self.notebook, self.db)
        self.notebook.add(self.product_form, text="Products")

        self.billing_frame = BillingFrame(self.notebook, self.db)
        self.notebook.add(self.billing_frame, text="Billing")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = App()
    app.run()