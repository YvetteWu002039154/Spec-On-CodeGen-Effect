import sqlite3
import os
import random
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from PIL import Image, ImageTk
from typing import Optional, List, Dict, Any


class DatabaseManager:
    """Manages SQLite database operations."""
    def __init__(self, db_name: str = "inventory.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                designation TEXT,
                salary REAL,
                address TEXT,
                date_joined TEXT
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
                name TEXT NOT NULL UNIQUE,
                description TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER,
                supplier_id INTEGER,
                price REAL NOT NULL,
                stock_quantity INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (category_id) REFERENCES categories (id),
                FOREIGN KEY (supplier_id) REFERENCES suppliers (id)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT UNIQUE NOT NULL,
                customer_name TEXT,
                date TEXT NOT NULL,
                total_amount REAL NOT NULL
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                product_id INTEGER,
                product_name TEXT,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                subtotal REAL NOT NULL,
                FOREIGN KEY (invoice_id) REFERENCES invoices (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        self.conn.commit()

    def execute_query(self, query: str, params: tuple = ()) -> Any:
        self.cursor.execute(query, params)
        self.conn.commit()
        return self.cursor

    def fetch_all(self, query: str, params: tuple = ()) -> List[tuple]:
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[tuple]:
        self.cursor.execute(query, params)
        return self.cursor.fetchone()

    def close(self):
        self.conn.close()


class InventoryManagementApp:
    """Main application class for the Inventory Management System."""
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("1200x700")
        self.root.configure(bg="#f0f0f0")
        self.db = DatabaseManager()

        # Load and place the logo/background image
        self.setup_images()
        self.create_dashboard()

    def setup_images(self):
        """Initialize images if available, else use placeholders."""
        try:
            self.logo_image = Image.open("logo.png")
            self.logo_image = self.logo_image.resize((150, 150), Image.LANCZO`S)
            self.logo_photo = ImageTk.PhotoImage(self.logo_image)
        except Exception:
            self.logo_photo = None
        try:
            self.bg_image = Image.open("bg.png")
            self.bg_image = self.bg_image.resize((1200, 700), Image.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(self.bg_image)
        except Exception:
            self.bg_photo = None

    def create_dashboard(self):
        dashboard_frame = tk.Frame(self.root, bg="#ffffff", bd=2, relief=tk.RIDGE)
        dashboard_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Background canvas
        canvas = tk.Canvas(dashboard_frame, highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        if self.bg_photo:
            canvas.create_image(0, 0, image=self.bg_photo, anchor=tk.NW)
        canvas.configure(bg="#ffffff")

        # Title label
        title_label = tk.Label(canvas, text="Inventory Management System", font=("Helvetica", 26, "bold"),
                               bg="#ffffff", fg="#333333")
        canvas.create_window(600, 50, window=title_label)

        # Date and time label
        self.clock_label = tk.Label(canvas, text="", font=("Helvetica", 14), bg="#ffffff", fg="#555555")
        canvas.create_window(600, 100, window=self.clock_label)
        self.update_clock()

        # Logo
        if self.logo_photo:
            canvas.create_image(600, 200, image=self.logo_photo, anchor=tk.CENTER)

        # Button frame
        btn_frame = tk.Frame(canvas, bg="#ffffff", bd=0)
        canvas.create_window(600, 400, window=btn_frame)

        buttons = [
            ("Manage Employees", self.open_employee_window),
            ("Manage Suppliers", self.open_supplier_window),
            ("Manage Categories", self.open_category_window),
            ("Manage Products", self.open_product_window),
            ("Billing", self.open_billing_window),
            ("Invoice List", self.open_invoice_list_window),
        ]
        for i, (text, command) in enumerate(buttons):
            btn = tk.Button(btn_frame, text=text, command=command, width=20, height=2,
                            font=("Helvetica", 12), bg="#4a7a8c", fg="white",
                            activebackground="#3a5a6c", activeforeground="white", bd=2)
            btn.grid(row=i//3, column=i%3, padx=10, pady=10)

    def update_clock(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.config(text=now)
        self.root.after(1000, self.update_clock)

    # ------------------------- Employee Management -------------------------
    def open_employee_window(self):
        self.create_management_window(
            "Employee Management",
            ("name", "email", "phone", "designation", "salary", "address", "date_joined"),
            ["Name", "Email", "Phone", "Designation", "Salary", "Address", "Date Joined"],
            "employees",
            id_col="id",
            listbox_cols=["id", "name", "designation", "phone"],
            listbox_headers=["ID", "Name", "Designation", "Phone"]
        )

    # ------------------------- Supplier Management -------------------------
    def open_supplier_window(self):
        self.create_management_window(
            "Supplier Management",
            ("name", "contact", "email", "address"),
            ["Name", "Contact", "Email", "Address"],
            "suppliers",
            id_col="id",
            listbox_cols=["id", "name", "contact"],
            listbox_headers=["ID", "Name", "Contact"]
        )

    # ------------------------- Category Management -------------------------
    def open_category_window(self):
        self.create_management_window(
            "Category Management",
            ("name", "description"),
            ["Name", "Description"],
            "categories",
            id_col="id",
            listbox_cols=["id", "name", "description"],
            listbox_headers=["ID", "Name", "Description"]
        )

    # ------------------------- Product Management -------------------------
    def open_product_window(self):
        # Product management is more complex because of foreign keys.
        product_win = tk.Toplevel(self.root)
        product_win.title("Product Management")
        product_win.geometry("900x600")
        product_win.configure(bg="#ffffff")

        # Form frame
        form_frame = tk.LabelFrame(product_win, text="Product Details", font=("Helvetica", 12, "bold"), bg="#ffffff")
        form_frame.pack(fill=tk.X, padx=10, pady=10)

        fields = ["Name", "Category", "Supplier", "Price", "Stock Quantity"]
        entries = {}

        for i, field in enumerate(fields):
            tk.Label(form_frame, text=field + ":", bg="#ffffff").grid(row=i//3, column=(i%3)*2, padx=5, pady=5, sticky=tk.W)
            if field == "Category":
                combo = ttk.Combobox(form_frame, values=self.get_category_names(), state="readonly")
                combo.grid(row=i//3, column=(i%3)*2+1, padx=5, pady=5, sticky=tk.W)
                entries[field] = combo
            elif field == "Supplier":
                combo = ttk.Combobox(form_frame, values=self.get_supplier_names(), state="readonly")
                combo.grid(row=i//3, column=(i%3)*2+1, padx=5, pady=5, sticky=tk.W)
                entries[field] = combo
            else:
                entry = tk.Entry(form_frame)
                entry.grid(row=i//3, column=(i%3)*2+1, padx=5, pady=5, sticky=tk.W)
                entries[field] = entry

        # Buttons
        btn_frame = tk.Frame(product_win, bg="#ffffff")
        btn_frame.pack(pady=5)

        selected_id = tk.StringVar()
        tk.Button(btn_frame, text="Add", bg="#4a7a8c", fg="white",
                  command=lambda: self.save_product(entries, product_tree, selected_id)).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Update", bg="#4a7a8c", fg="white",
                  command=lambda: self.update_product(entries, product_tree, selected_id)).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Delete", bg="#4a7a8c", fg="white",
                  command=lambda: self.delete_product(product_tree, selected_id)).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="Clear", bg="#4a7a8c", fg="white",
                  command=lambda: self.clear_product_entries(entries, selected_id)).grid(row=0, column=3, padx=5)

        # Treeview list
        list_frame = tk.Frame(product_win, bg="#ffffff")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = ("ID", "Name", "Category", "Supplier", "Price", "Stock")
        product_tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=12)
        for col in cols:
            product_tree.heading(col, text=col)
            product_tree.column(col, width=130, anchor=tk.CENTER)
        product_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=product_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        product_tree.configure(yscrollcommand=scrollbar.set)

        product_tree.bind("<<TreeviewSelect>>", lambda e: self.on_product_select(e, entries, selected_id))
        self.load_product_tree(product_tree)

    def get_category_names(self) -> list:
        rows = self.db.fetch_all("SELECT name FROM categories")
        return [row[0] for row in rows]

    def get_supplier_names(self) -> list:
        rows = self.db.fetch_all("SELECT name FROM suppliers")
        return [row[0] for row in rows]

    def save_product(self, entries, tree, selected_id):
        name = entries["Name"].get().strip()
        category = entries["Category"].get()
        supplier = entries["Supplier"].get()
        price = entries["Price"].get()
        stock = entries["Stock Quantity"].get()

        if not name or not price:
            messagebox.showerror("Error", "Name and Price are required.")
            return
        try:
            price = float(price)
            stock = int(stock) if stock else 0
        except ValueError:
            messagebox.showerror("Error", "Price must be a number and stock quantity an integer.")
            return

        # get ids
        cat_id = self.db.fetch_one("SELECT id FROM categories WHERE name=?", (category,))[0] if category else None
        sup_id = self.db.fetch_one("SELECT id FROM suppliers WHERE name=?", (supplier,))[0] if supplier else None

        self.db.execute_query("INSERT INTO products (name, category_id, supplier_id, price, stock_quantity) VALUES (?,?,?,?,?)",
                              (name, cat_id, sup_id, price, stock))
        self.load_product_tree(tree)
        self.clear_product_entries(entries, selected_id)
        messagebox.showinfo("Success", "Product added successfully.")

    def update_product(self, entries, tree, selected_id):
        if not selected_id.get():
            messagebox.showerror("Error", "Please select a product to update.")
            return
        name = entries["Name"].get().strip()
        category = entries["Category"].get()
        supplier = entries["Supplier"].get()
        price = entries["Price"].get()
        stock = entries["Stock Quantity"].get()
        try:
            price = float(price)
            stock = int(stock) if stock else 0
        except ValueError:
            messagebox.showerror("Error", "Invalid numbers.")
            return
        cat_id = self.db.fetch_one("SELECT id FROM categories WHERE name=?", (category,))[0] if category else None
        sup_id = self.db.fetch_one("SELECT id FROM suppliers WHERE name=?", (supplier,))[0] if supplier else None
        self.db.execute_query("UPDATE products SET name=?, category_id=?, supplier_id=?, price=?, stock_quantity=? WHERE id=?",
                              (name, cat_id, sup_id, price, stock, selected_id.get()))
        self.load_product_tree(tree)
        self.clear_product_entries(entries, selected_id)
        messagebox.showinfo("Success", "Product updated.")

    def delete_product(self, tree, selected_id):
        if not selected_id.get():
            messagebox.showerror("Error", "Please select a product to delete.")
            return
        self.db.execute_query("DELETE FROM products WHERE id=?", (selected_id.get(),))
        self.load_product_tree(tree)
        self.clear_product_entries(tree, selected_id)
        messagebox.showinfo("Success", "Product deleted.")

    def clear_product_entries(self, entries, selected_id):
        for e in entries.values():
            if isinstance(e, tk.Entry):
                e.delete(0, tk.END)
            elif isinstance(e, ttk.Combobox):
                e.set('')
        selected_id.set('')

    def on_product_select(self, event, entries, selected_id):
        tree = event.widget
        selected = tree.focus()
        if not selected:
            return
        values = tree.item(selected, 'values')
        if not values:
            return
        selected_id.set(values[0])
        entries["Name"].delete(0, tk.END)
        entries["Name"].insert(0, values[1])
        entries["Category"].set(values[2])
        entries["Supplier"].set(values[3])
        entries["Price"].delete(0, tk.END)
        entries["Price"].insert(0, values[4])
        entries["Stock Quantity"].delete(0, tk.END)
        entries["Stock Quantity"].insert(0, values[5])

    def load_product_tree(self, tree):
        for item in tree.get_children():
            tree.delete(item)
        query = '''
            SELECT p.id, p.name, c.name, s.name, p.price, p.stock_quantity
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
        '''
        for row in self.db.fetch_all(query):
            tree.insert("", tk.END, values=row)

    # ------------------------- Billing Window -------------------------
    def open_billing_window(self):
        bill_win = tk.Toplevel(self.root)
        bill_win.title("Billing")
        bill_win.geometry("1000x650")
        bill_win.configure(bg="#ffffff")

        # Customer info
        cust_frame = tk.LabelFrame(bill_win, text="Customer Details", font=("Helvetica", 12, "bold"), bg="#ffffff")
        cust_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(cust_frame, text="Customer Name:", bg="#ffffff").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        cust_name_entry = tk.Entry(cust_frame, width=30)
        cust_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        tk.Label(cust_frame, text="Date:", bg="#ffffff").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        date_entry = tk.Entry(cust_frame, textvariable=date_var, width=15, state="readonly")
        date_entry.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        # Product selection
        prod_frame = tk.LabelFrame(bill_win, text="Add Product", font=("Helvetica", 12, "bold"), bg="#ffffff")
        prod_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(prod_frame, text="Product:", bg="#ffffff").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        product_combo = ttk.Combobox(prod_frame, values=self.get_product_names(), state="readonly", width=25)
        product_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        tk.Label(prod_frame, text="Quantity:", bg="#ffffff").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        qty_entry = tk.Entry(prod_frame, width=10)
        qty_entry.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        add_to_cart_btn = tk.Button(prod_frame, text="Add to Cart", bg="#4a7a8c", fg="white",
                                    command=lambda: self.add_to_cart(product_combo, qty_entry, cart_tree, total_var))
        add_to_cart_btn.grid(row=0, column=4, padx=10, pady=5)

        # Cart Treeview
        cart_frame = tk.LabelFrame(bill_win, text="Cart Items", font=("Helvetica", 12, "bold"), bg="#ffffff")
        cart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cart_cols = ("Product", "Qty", "Unit Price", "Subtotal")
        cart_tree = ttk.Treeview(cart_frame, columns=cart_cols, show="headings", height=8)
        for col in cart_cols:
            cart_tree.heading(col, text=col)
            cart_tree.column(col, anchor=tk.CENTER, width=150)
        cart_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cart_scroll = ttk.Scrollbar(cart_frame, orient=tk.VERTICAL, command=cart_tree.yview)
        cart_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        cart_tree.configure(yscrollcommand=cart_scroll.set)

        # Total and bill button
        total_frame = tk.Frame(bill_win, bg="#ffffff")
        total_frame.pack(fill=tk.X, padx=10, pady=5)

        total_var = tk.StringVar(value="Total: $0.00")
        total_label = tk.Label(total_frame, textvariable=total_var, font=("Helvetica", 14, "bold"), bg="#ffffff", fg="#333333")
        total_label.pack(side=tk.LEFT, padx=10)

        generate_btn = tk.Button(total_frame, text="Generate Invoice", bg="#4a7a8c", fg="white", font=("Helvetica", 12),
                                 command=lambda: self.generate_invoice(cust_name_entry, date_var, cart_tree, total_var, bill_win))
        generate_btn.pack(side=tk.RIGHT, padx=20)

        # Delete selected item from cart
        delete_cart_btn = tk.Button(total_frame, text="Remove Selected", bg="#d9534f", fg="white",
                                    command=lambda: self.remove_cart_item(cart_tree, total_var))
        delete_cart_btn.pack(side=tk.RIGHT, padx=5)

    def get_product_names(self) -> list:
        rows = self.db.fetch_all("SELECT name FROM products WHERE stock_quantity > 0")
        return [row[0] for row in rows]

    def add_to_cart(self, product_combo, qty_entry, cart_tree, total_var):
        product_name = product_combo.get()
        if not product_name:
            messagebox.showerror("Error", "Please select a product.")
            return
        try:
            quantity = int(qty_entry.get())
            if quantity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity.")
            return

        product = self.db.fetch_one("SELECT id, price, stock_quantity FROM products WHERE name=?", (product_name,))
        if not product:
            messagebox.showerror("Error", "Product not found.")
            return
        prod_id, price, stock = product
        if quantity > stock:
            messagebox.showerror("Error", f"Insufficient stock. Only {stock} available.")
            return

        subtotal = price * quantity
        # Add to cart tree
        cart_tree.insert("", tk.END, values=(product_name, quantity, f"${price:.2f}", f"${subtotal:.2f}"))
        # Update total
        self.update_cart_total(cart_tree, total_var)
        qty_entry.delete(0, tk.END)

    def remove_cart_item(self, cart_tree, total_var):
        selected = cart_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Select an item to remove.")
            return
        cart_tree.delete(selected)
        self.update_cart_total(cart_tree, total_var)

    def update_cart_total(self, cart_tree, total_var):
        total = 0.0
        for child in cart_tree.get_children():
            values = cart_tree.item(child, 'values')
            if len(values) >= 4:
                try:
                    sub = float(values[3].replace('$', ''))
                    total += sub
                except:
                    pass
        total_var.set(f"Total: ${total:.2f}")

    def generate_invoice(self, cust_entry, date_var, cart_tree, total_var, window):
        customer_name = cust_entry.get().strip()
        if not customer_name:
            messagebox.showerror("Error", "Customer name is required.")
            return
        date = date_var.get()
        cart_items = []
        for child in cart_tree.get_children():
            values = cart_tree.item(child, 'values')
            if len(values) >= 4:
                product_name = values[0]
                qty = int(values[1])
                unit_price = float(values[2].replace('$', ''))
                subtotal = float(values[3].replace('$', ''))
                cart_items.append((product_name, qty, unit_price, subtotal))
        if not cart_items:
            messagebox.showerror("Error", "Cart is empty.")
            return
        total = sum(item[3] for item in cart_items)
        # Generate invoice number
        invoice_no = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100,999)}"
        # Insert invoice
        self.db.execute_query("INSERT INTO invoices (invoice_no, customer_name, date, total_amount) VALUES (?,?,?,?)",
                              (invoice_no, customer_name, date, total))
        invoice_id = self.db.cursor.lastrowid
        # Insert invoice items and update stock
        for product_name, qty, unit_price, subtotal in cart_items:
            prod = self.db.fetch_one("SELECT id, stock_quantity FROM products WHERE name=?", (product_name,))
            if prod:
                prod_id, stock = prod
                new_stock = stock - qty
                self.db.execute_query("UPDATE products SET stock_quantity=? WHERE id=?", (new_stock, prod_id))
                self.db.execute_query("INSERT INTO invoice_items (invoice_id, product_id, product_name, quantity, unit_price, subtotal) VALUES (?,?,?,?,?,?)",
                                      (invoice_id, prod_id, product_name, qty, unit_price, subtotal))
            else:
                # product no longer exists, maybe still insert item
                self.db.execute_query("INSERT INTO invoice_items (invoice_id, product_id, product_name, quantity, unit_price, subtotal) VALUES (?,?,?,?,?,?)",
                                      (invoice_id, None, product_name, qty, unit_price, subtotal))
        messagebox.showinfo("Success", f"Invoice {invoice_no} generated successfully.")
        # Clear cart
        for child in cart_tree.get_children():
            cart_tree.delete(child)
        total_var.set("Total: $0.00")
        cust_entry.delete(0, tk.END)

    # ------------------------- Invoice List Window -------------------------
    def open_invoice_list_window(self):
        inv_win = tk.Toplevel(self.root)
        inv_win.title("Invoice List")
        inv_win.geometry("800x500")
        inv_win.configure(bg="#ffffff")

        tree_frame = tk.Frame(inv_win, bg="#ffffff")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("Invoice No", "Customer", "Date", "Total")
        inv_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=15)
        for col in cols:
            inv_tree.heading(col, text=col)
            inv_tree.column(col, width=150, anchor=tk.CENTER)
        inv_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=inv_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        inv_tree.configure(yscrollcommand=scrollbar.set)

        self.load_invoice_list(inv_tree)

        # View details button
        btn = tk.Button(inv_win, text="View Details", bg="#4a7a8c", fg="white",
                        command=lambda: self.view_invoice_details(inv_tree))
        btn.pack(pady=5)

    def load_invoice_list(self, tree):
        for item in tree.get_children():
            tree.delete(item)
        for row in self.db.fetch_all("SELECT invoice_no, customer_name, date, total_amount FROM invoices"):
            tree.insert("", tk.END, values=row)

    def view_invoice_details(self, inv_tree):
        selected = inv_tree.focus()
        if not selected:
            messagebox.showerror("Error", "Select an invoice to view.")
            return
        values = inv_tree.item(selected, 'values')
        invoice_no = values[0]
        details_win = tk.Toplevel(self.root)
        details_win.title(f"Details for {invoice_no}")
        details_win.geometry("700x400")
        details_win.configure(bg="#ffffff")

        # Invoice header
        cust = values[1]
        date = values[2]
        total = values[3]
        header_frame = tk.Frame(details_win, bg="#ffffff")
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(header_frame, text=f"Invoice: {invoice_no}", font=("Helvetica", 14, "bold"), bg="#ffffff").pack(anchor=tk.W)
        tk.Label(header_frame, text=f"Customer: {cust}", bg="#ffffff").pack(anchor=tk.W)
        tk.Label(header_frame, text=f"Date: {date}", bg="#ffffff").pack(anchor=tk.W)
        tk.Label(header_frame, text=f"Total: ${total}", font=("Helvetica", 12, "bold"), bg="#ffffff").pack(anchor=tk.W)

        # Items
        items_tree = ttk.Treeview(details_win, columns=("Product", "Qty", "Unit Price", "Subtotal"), show="headings", height=8)
        for col in items_tree["columns"]:
            items_tree.heading(col, text=col)
            items_tree.column(col, width=140, anchor=tk.CENTER)
        items_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        invoice_id = self.db.fetch_one("SELECT id FROM invoices WHERE invoice_no=?", (invoice_no,))[0]
        for row in self.db.fetch_all("SELECT product_name, quantity, unit_price, subtotal FROM invoice_items WHERE invoice_id=?", (invoice_id,)):
            items_tree.insert("", tk.END, values=row)

    # ------------------------- Generic Management Window -------------------------
    def create_management_window(self, title: str, fields: tuple, labels: list, table: str,
                                 id_col: str, listbox_cols: list, listbox_headers: list):
        """Create a generic CRUD window for employees, suppliers, categories."""
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("900x600")
        win.configure(bg="#ffffff")

        # Form
        form_frame = tk.LabelFrame(win, text="Details", font=("Helvetica", 12, "bold"), bg="#ffffff")
        form_frame.pack(fill=tk.X, padx=10, pady=5)

        entries = {}
        for i, field in enumerate(fields):
            tk.Label(form_frame, text=labels[i] + ":", bg="#ffffff").grid(row=i//3, column=(i%3)*2, padx=5, pady=5, sticky=tk.W)
            entry = tk.Entry(form_frame, width=25)
            entry.grid(row=i//3, column=(i%3)*2+1, padx=5, pady=5, sticky=tk.W)
            entries[field] = entry

        btn_frame = tk.Frame(win, bg="#ffffff")
        btn_frame.pack(pady=5)

        selected_id = tk.StringVar()

        tk.Button(btn_frame, text="Add", bg="#4a7a8c", fg="white",
                  command=lambda: self.add_record(entries, table, listbox_cols, listbox_headers, tree, selected_id)).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Update", bg="#4a7a8c", fg="white",
                  command=lambda: self.update_record(entries, table, id_col, listbox_cols, listbox_headers, tree, selected_id)).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Delete", bg="#4a7a8c", fg="white",
                  command=lambda: self.delete_record(table, id_col, tree, selected_id)).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="Clear", bg="#4a7a8c", fg="white",
                  command=lambda: self.clear_entries(entries, selected_id)).grid(row=0, column=3, padx=5)

        # Treeview
        list_frame = tk.Frame(win, bg="#ffffff")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        tree = ttk.Treeview(list_frame, columns=listbox_headers, show="headings", height=12)
        for header in listbox_headers:
            tree.heading(header, text=header)
            tree.column(header, width=150, anchor=tk.CENTER)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.bind("<<TreeviewSelect>>",
                  lambda e: self.on_generic_select(e, entries, fields, id_col, selected_id))
        self.load_tree(tree, table, listbox_cols)

    def load_tree(self, tree, table, columns):
        for item in tree.get_children():
            tree.delete(item)
        cols = ", ".join(columns)
        for row in self.db.fetch_all(f"SELECT {cols} FROM {table}"):
            tree.insert("", tk.END, values=row)

    def on_generic_select(self, event, entries, fields, id_col, selected_id):
        tree = event.widget
        selected = tree.focus()
        if not selected:
            return
        values = tree.item(selected, 'values')
        if not values:
            return
        selected_id.set(values[0])
        # Populate entries; assume values order matches fields except id_col is first in listbox but not in fields.
        # listbox_cols includes id as first, fields are the rest.
        for i, field in enumerate(fields):
            entries[field].delete(0, tk.END)
            if i+1 < len(values):
                entries[field].insert(0, values[i+1])

    def clear_entries(self, entries, selected_id):
        for entry in entries.values():
            entry.delete(0, tk.END)
        selected_id.set('')

    def add_record(self, entries, table, listbox_cols, listbox_headers, tree, selected_id):
        values = [entry.get() for entry in entries.values()]
        # Basic validation: none empty? could be improved.
        placeholders = ", ".join(['?'] * len(values))
        fields = ", ".join(entries.keys())
        self.db.execute_query(f"INSERT INTO {table} ({fields}) VALUES ({placeholders})", tuple(values))
        self.load_tree(tree, table, listbox_cols)
        self.clear_entries(entries, selected_id)
        messagebox.showinfo("Success", "Record added successfully.")

    def update_record(self, entries, table, id_col, listbox_cols, listbox_headers, tree, selected_id):
        if not selected_id.get():
            messagebox.showerror("Error", "Please select a record to update.")
            return
        values = [entry.get() for entry in entries.values()]
        set_clause = ", ".join([f"{field}=?" for field in entries.keys()])
        self.db.execute_query(f"UPDATE {table} SET {set_clause} WHERE {id_col}=?",
                              tuple(values) + (selected_id.get(),))
        self.load_tree(tree, table, listbox_cols)
        self.clear_entries(entries, selected_id)
        messagebox.showinfo("Success", "Record updated.")

    def delete_record(self, table, id_col, tree, selected_id):
        if not selected_id.get():
            messagebox.showerror("Error", "Please select a record to delete.")
            return
        self.db.execute_query(f"DELETE FROM {table} WHERE {id_col}=?", (selected_id.get(),))
        self.load_tree(tree, table, [id_col])  # will need columns, but we can reload with default listbox_cols somehow. Actually better to pass listbox_cols again. We'll store them as attribute maybe. Simplified: we can just fetch all columns again. We'll call load_tree again with same parameters as used in create_management_window. We can store listbox_cols in win for later. Let's adjust.
        self.clear_entries(None, selected_id)
        messagebox.showinfo("Success", "Record deleted.")
        # Need access to listbox_cols. We'll modify delete_record signature to pass them.
        # Let's adjust the lambda to include listbox_cols.

    # Override delete button in create_management_window: need to store listbox_cols and table in closure.
    # We'll modify create_management_window to pass them directly.
    # But the lambda we used doesn't have listbox_cols available. Let's restructure create_management_window to store them in the window's namespace (e.g., win.listbox_cols = listbox_cols, win.table = table) and reference them in delete.
    # For brevity, I'll redesign create_management_window to define inner functions that capture the needed variables. Let's rewrite that part.

    def create_management_window(self, title, fields, labels, table, id_col, listbox_cols, listbox_headers):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("900x600")
        win.configure(bg="#ffffff")

        form_frame = tk.LabelFrame(win, text="Details", font=("Helvetica", 12, "bold"), bg="#ffffff")
        form_frame.pack(fill=tk.X, padx=10, pady=5)

        entries = {}
        for i, field in enumerate(fields):
            tk.Label(form_frame, text=labels[i] + ":", bg="#ffffff").grid(row=i//3, column=(i%3)*2, padx=5, pady=5, sticky=tk.W)
            entry = tk.Entry(form_frame, width=25)
            entry.grid(row=i//3, column=(i%3)*2+1, padx=5, pady=5, sticky=tk.W)
            entries[field] = entry

        btn_frame = tk.Frame(win, bg="#ffffff")
        btn_frame.pack(pady=5)

        selected_id = tk.StringVar()

        def add():
            values = [entry.get() for entry in entries.values()]
            placeholders = ", ".join(['?'] * len(values))
            fields_str = ", ".join(entries.keys())
            self.db.execute_query(f"INSERT INTO {table} ({fields_str}) VALUES ({placeholders})", tuple(values))
            self.load_tree(tree, table, listbox_cols)
            self.clear_entries(entries, selected_id)
            messagebox.showinfo("Success", "Record added.")

        def update():
            if not selected_id.get():
                messagebox.showerror("Error", "Select a record to update.")
                return
            values = [entry.get() for entry in entries.values()]
            set_clause = ", ".join([f"{field}=?" for field in entries.keys()])
            self.db.execute_query(f"UPDATE {table} SET {set_clause} WHERE {id_col}=?",
                                  tuple(values) + (selected_id.get(),))
            self.load_tree(tree, table, listbox_cols)
            self.clear_entries(entries, selected_id)
            messagebox.showinfo("Success", "Record updated.")

        def delete():
            if not selected_id.get():
                messagebox.showerror("Error", "Select a record to delete.")
                return
            self.db.execute_query(f"DELETE FROM {table} WHERE {id_col}=?", (selected_id.get(),))
            self.load_tree(tree, table, listbox_cols)
            self.clear_entries(entries, selected_id)
            messagebox.showinfo("Success", "Record deleted.")

        tk.Button(btn_frame, text="Add", bg="#4a7a8c", fg="white", command=add).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Update", bg="#4a7a8c", fg="white", command=update).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Delete", bg="#4a7a8c", fg="white", command=delete).grid(row=0, column=2, padx=5)
        tk.Button(btn_frame, text="Clear", bg="#4a7a8c", fg="white",
                  command=lambda: self.clear_entries(entries, selected_id)).grid(row=0, column=3, padx=5)

        list_frame = tk.Frame(win, bg="#ffffff")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        tree = ttk.Treeview(list_frame, columns=listbox_headers, show="headings", height=12)
        for header in listbox_headers:
            tree.heading(header, text=header)
            tree.column(header, width=150, anchor=tk.CENTER)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.bind("<<TreeviewSelect>>",
                  lambda e: self.on_generic_select(e, entries, fields, id_col, selected_id))
        self.load_tree(tree, table, listbox_cols)


# ------------------------- Run the App -------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryManagementApp(root)
    root.mainloop()