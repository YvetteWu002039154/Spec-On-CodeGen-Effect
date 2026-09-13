import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import datetime
import sqlite3
import os

# ---------------------------- Database Setup ----------------------------
DB_NAME = "ims.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT NOT NULL,
        address TEXT,
        joining_date TEXT,
        role TEXT,
        salary REAL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT,
        email TEXT,
        address TEXT,
        city TEXT,
        state TEXT,
        zip_code TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category_id INTEGER,
        price REAL NOT NULL,
        qty INTEGER NOT NULL DEFAULT 0,
        supplier_id INTEGER,
        status TEXT DEFAULT 'active',
        FOREIGN KEY (category_id) REFERENCES categories(id),
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS bills (
        bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT,
        customer_phone TEXT,
        bill_date TEXT NOT NULL,
        total_amount REAL NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS bill_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id INTEGER NOT NULL,
        product_id INTEGER,
        product_name TEXT,
        qty INTEGER NOT NULL,
        price REAL NOT NULL,
        total REAL NOT NULL,
        FOREIGN KEY (bill_id) REFERENCES bills(bill_id)
    )''')
    conn.commit()
    conn.close()

create_tables()

# ---------------------------- Image Helper ----------------------------
def get_image(filename, size=(30, 30)):
    try:
        img = Image.open(os.path.join("images", filename)).resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    except:
        # fallback
        img = Image.new('RGB', size, color='gray')
        return ImageTk.PhotoImage(img)

# ---------------------------- Main Application ----------------------------
class InventoryManagementSystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("1350x700+0+0")
        self.root.configure(bg="white")

        # Current frame in content area
        self.content_frame = None

        # Dashboard images (placeholder)
        self.img_emp = get_image("employee.png")
        self.img_sup = get_image("supplier.png")
        self.img_cat = get_image("category.png")
        self.img_prod = get_image("product.png")
        self.img_bill = get_image("bill.png")
        self.img_logo = get_image("logo.png", size=(150, 150))

        self.create_dashboard()

    def create_dashboard(self):
        # Clear root for rebuilding
        for widget in self.root.winfo_children():
            widget.destroy()

        # Top bar
        top_frame = tk.Frame(self.root, bg="white")
        top_frame.pack(side=tk.TOP, fill=tk.X)

        lbl_title = tk.Label(top_frame, text="Inventory Management System Dashboard",
                             font=("Arial", 24, "bold"), bg="white", fg="blue")
        lbl_title.pack(side=tk.LEFT, padx=20, pady=10)

        self.clock_label = tk.Label(top_frame, text="",
                                    font=("Arial", 16), bg="white", fg="black")
        self.clock_label.pack(side=tk.RIGHT, padx=20, pady=10)
        self.update_clock()

        # Left dashboard panel
        self.dash_frame = tk.Frame(self.root, bg="light gray", width=200)
        self.dash_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.dash_frame.pack_propagate(False)

        # Logo
        tk.Label(self.dash_frame, image=self.img_logo, bg="light gray").pack(pady=20)

        # Buttons
        buttons = [
            ("Employee", self.img_emp, self.show_employee),
            ("Supplier", self.img_sup, self.show_supplier),
            ("Category", self.img_cat, self.show_category),
            ("Product", self.img_prod, self.show_product),
            ("Billing", self.img_bill, self.show_billing)
        ]
        for text, img, cmd in buttons:
            btn = tk.Button(self.dash_frame, text=text, image=img, compound=tk.LEFT,
                            command=cmd, padx=10, pady=10, bg="white",
                            font=("Arial", 12, "bold"))
            btn.image = img  # keep reference
            btn.pack(fill=tk.X, padx=20, pady=5)

        # Content area
        self.content_frame = tk.Frame(self.root, bg="white")
        self.content_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        # Welcome message
        tk.Label(self.content_frame,
                 text="Welcome to Inventory Management System\nPlease select a section from the left panel.",
                 font=("Arial", 18), bg="white").pack(expand=True)

    def update_clock(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        self.clock_label.config(text=now)
        self.root.after(1000, self.update_clock)

    def clear_content(self):
        if self.content_frame:
            self.content_frame.destroy()
        self.content_frame = tk.Frame(self.root, bg="white")
        self.content_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

    def show_employee(self):
        self.clear_content()
        EmployeeFrame(self.content_frame)

    def show_supplier(self):
        self.clear_content()
        SupplierFrame(self.content_frame)

    def show_category(self):
        self.clear_content()
        CategoryFrame(self.content_frame)

    def show_product(self):
        self.clear_content()
        ProductFrame(self.content_frame)

    def show_billing(self):
        self.clear_content()
        BillingFrame(self.content_frame)

# ---------------------------- Base CRUD Frame ----------------------------
class BaseCRUDFrame:
    """Mixin-like base for recurring CRUD layout: form left, treeview right."""
    def __init__(self, parent, title, columns, table_name, fields, fetch_query, insert_query, update_query, delete_query, search_fields=None):
        self.parent = parent
        self.table_name = table_name
        self.fields = fields  # list of (field_label, db_column, entry_width)
        self.columns = columns
        self.fetch_query = fetch_query
        self.insert_query = insert_query
        self.update_query = update_query
        self.delete_query = delete_query
        self.search_fields = search_fields or [fields[0][1]]  # default search by first field

        # Data variables for form
        self.entries = {}
        self.record_id = None

        # Layout
        self.main_frame = tk.Frame(self.parent, bg="white")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Title
        tk.Label(self.main_frame, text=title, font=("Arial", 20, "bold"),
                 bg="white", fg="dark blue").pack(anchor=tk.W, pady=5)

        # Left form frame
        form_frame = tk.LabelFrame(self.main_frame, text="Enter Details", bg="white",
                                   font=("Arial", 12, "bold"), padx=10, pady=10)
        form_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0,10), pady=5)

        row = 0
        for label_text, col_name, width in self.fields:
            tk.Label(form_frame, text=label_text + ":", bg="white",
                     font=("Arial", 10)).grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)
            ent = tk.Entry(form_frame, width=width, font=("Arial", 10))
            ent.grid(row=row, column=1, padx=5, pady=5)
            self.entries[col_name] = ent
            row += 1

        # Buttons
        btn_frame = tk.Frame(form_frame, bg="white")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)

        self.btn_add = tk.Button(btn_frame, text="Add", width=8, bg="green", fg="white",
                                 font=("Arial", 10, "bold"), command=self.add_record)
        self.btn_add.pack(side=tk.LEFT, padx=5)
        self.btn_update = tk.Button(btn_frame, text="Update", width=8, bg="orange",
                                    font=("Arial", 10, "bold"), command=self.update_record)
        self.btn_update.pack(side=tk.LEFT, padx=5)
        self.btn_delete = tk.Button(btn_frame, text="Delete", width=8, bg="red", fg="white",
                                    font=("Arial", 10, "bold"), command=self.delete_record)
        self.btn_delete.pack(side=tk.LEFT, padx=5)
        self.btn_clear = tk.Button(btn_frame, text="Clear", width=8, bg="yellow",
                                   font=("Arial", 10, "bold"), command=self.clear_form)
        self.btn_clear.pack(side=tk.LEFT, padx=5)

        # Search area
        search_frame = tk.LabelFrame(form_frame, text="Search", bg="white", font=("Arial", 10, "bold"))
        search_frame.grid(row=row+1, column=0, columnspan=2, pady=10, sticky="ew")
        self.search_entry = tk.Entry(search_frame, width=20, font=("Arial", 10))
        self.search_entry.pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(search_frame, text="Search", bg="blue", fg="white",
                  font=("Arial", 10, "bold"), command=self.search_records).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All", bg="purple", fg="white",
                  font=("Arial", 10, "bold"), command=self.fetch_all).pack(side=tk.LEFT, padx=5)

        # Right treeview
        tree_frame = tk.Frame(self.main_frame, bg="white")
        tree_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=(10,0), pady=5)

        tree_scroll = tk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                 yscrollcommand=tree_scroll.set, selectmode="browse")
        tree_scroll.config(command=self.tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(expand=True, fill=tk.BOTH)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor=tk.CENTER)

        self.tree.bind("<ButtonRelease-1>", self.on_tree_select)

        # Load data
        self.fetch_all()

    def add_record(self):
        try:
            values = tuple(self.entries[col].get() for _, col, _ in self.fields)
            conn = get_connection()
            c = conn.cursor()
            c.execute(self.insert_query, values)
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Record added successfully.")
            self.fetch_all()
            self.clear_form()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_record(self):
        if not self.record_id:
            messagebox.showwarning("Selection Required", "Please select a record to update.")
            return
        try:
            values = tuple(self.entries[col].get() for _, col, _ in self.fields) + (self.record_id,)
            conn = get_connection()
            c = conn.cursor()
            c.execute(self.update_query, values)
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Record updated.")
            self.fetch_all()
            self.clear_form()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_record(self):
        if not self.record_id:
            messagebox.showwarning("Selection Required", "Please select a record to delete.")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this record?"):
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute(self.delete_query, (self.record_id,))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Record deleted.")
                self.fetch_all()
                self.clear_form()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def clear_form(self):
        self.record_id = None
        for ent in self.entries.values():
            ent.delete(0, tk.END)

    def fetch_all(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = get_connection()
        c = conn.cursor()
        c.execute(self.fetch_query)
        records = c.fetchall()
        conn.close()
        for rec in records:
            self.tree.insert("", tk.END, values=tuple(rec))

    def search_records(self):
        keyword = self.search_entry.get().strip()
        if not keyword:
            self.fetch_all()
            return
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = get_connection()
        c = conn.cursor()
        # Build search condition for each search field using LIKE
        param = f"%{keyword}%"
        conditions = " OR ".join([f"{field} LIKE ?" for field in self.search_fields])
        query = self.fetch_query + f" WHERE {conditions}"
        c.execute(query, (param,) * len(self.search_fields))
        records = c.fetchall()
        conn.close()
        for rec in records:
            self.tree.insert("", tk.END, values=tuple(rec))

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0], 'values')
        if not values:
            return
        self.record_id = values[0]
        self.clear_form()
        # Populate entries according to column order (skip id column)
        for i, (_, col, _) in enumerate(self.fields):
            # values list length must match
            if i+1 < len(values):
                self.entries[col].insert(0, values[i+1])

# ---------------------------- Employee Frame ----------------------------
class EmployeeFrame(BaseCRUDFrame):
    def __init__(self, parent):
        columns = ("ID", "Name", "Email", "Phone", "Address", "Joining Date", "Role", "Salary")
        fields = [
            ("Name", "name", 20),
            ("Email", "email", 25),
            ("Phone", "phone", 15),
            ("Address", "address", 30),
            ("Joining Date (YYYY-MM-DD)", "joining_date", 15),
            ("Role", "role", 15),
            ("Salary", "salary", 10)
        ]
        fetch_query = "SELECT id, name, email, phone, address, joining_date, role, salary FROM employees"
        insert_query = "INSERT INTO employees (name, email, phone, address, joining_date, role, salary) VALUES (?, ?, ?, ?, ?, ?, ?)"
        update_query = "UPDATE employees SET name=?, email=?, phone=?, address=?, joining_date=?, role=?, salary=? WHERE id=?"
        delete_query = "DELETE FROM employees WHERE id=?"
        search_fields = ["name", "email", "phone"]
        super().__init__(parent, "Manage Employees", columns, "employees", fields,
                         fetch_query, insert_query, update_query, delete_query, search_fields)

# ---------------------------- Supplier Frame ----------------------------
class SupplierFrame(BaseCRUDFrame):
    def __init__(self, parent):
        columns = ("ID", "Name", "Contact", "Email", "Address", "City", "State", "Zip Code")
        fields = [
            ("Name", "name", 20),
            ("Contact", "contact", 15),
            ("Email", "email", 25),
            ("Address", "address", 30),
            ("City", "city", 15),
            ("State", "state", 15),
            ("Zip Code", "zip_code", 10)
        ]
        fetch_query = "SELECT id, name, contact, email, address, city, state, zip_code FROM suppliers"
        insert_query = "INSERT INTO suppliers (name, contact, email, address, city, state, zip_code) VALUES (?, ?, ?, ?, ?, ?, ?)"
        update_query = "UPDATE suppliers SET name=?, contact=?, email=?, address=?, city=?, state=?, zip_code=? WHERE id=?"
        delete_query = "DELETE FROM suppliers WHERE id=?"
        super().__init__(parent, "Manage Suppliers", columns, "suppliers", fields,
                         fetch_query, insert_query, update_query, delete_query, ["name"])

# ---------------------------- Category Frame ----------------------------
class CategoryFrame(BaseCRUDFrame):
    def __init__(self, parent):
        columns = ("ID", "Name")
        fields = [("Category Name", "name", 25)]
        fetch_query = "SELECT id, name FROM categories"
        insert_query = "INSERT INTO categories (name) VALUES (?)"
        update_query = "UPDATE categories SET name=? WHERE id=?"
        delete_query = "DELETE FROM categories WHERE id=?"
        super().__init__(parent, "Manage Categories", columns, "categories", fields,
                         fetch_query, insert_query, update_query, delete_query, ["name"])

# ---------------------------- Product Frame ----------------------------
class ProductFrame(BaseCRUDFrame):
    def __init__(self, parent):
        columns = ("ID", "Name", "Category", "Price", "Qty", "Supplier", "Status")
        fields = [
            ("Product Name", "name", 20),
            ("Category ID", "category_id", 10),
            ("Price", "price", 10),
            ("Quantity", "qty", 10),
            ("Supplier ID", "supplier_id", 10),
            ("Status (active/inactive)", "status", 12)
        ]
        # fetch with joins to show names
        fetch_query = '''SELECT p.id, p.name, c.name AS category, p.price, p.qty,
                        s.name AS supplier, p.status
                        FROM products p
                        LEFT JOIN categories c ON p.category_id = c.id
                        LEFT JOIN suppliers s ON p.supplier_id = s.id'''
        insert_query = "INSERT INTO products (name, category_id, price, qty, supplier_id, status) VALUES (?, ?, ?, ?, ?, ?)"
        update_query = "UPDATE products SET name=?, category_id=?, price=?, qty=?, supplier_id=?, status=? WHERE id=?"
        delete_query = "DELETE FROM products WHERE id=?"
        search_fields = ["p.name", "c.name", "s.name"]
        super().__init__(parent, "Manage Products", columns, "products", fields,
                         fetch_query, insert_query, update_query, delete_query, search_fields)
        # Override search to use join
        self.fetch_query = fetch_query  # needed for search override

    def search_records(self):
        # Override because self.fetch_query is a join query with aliases
        keyword = self.search_entry.get().strip()
        if not keyword:
            self.fetch_all()
            return
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = get_connection()
        c = conn.cursor()
        param = f"%{keyword}%"
        conditions = " OR ".join([f"{f} LIKE ?" for f in self.search_fields])
        query = self.fetch_query + f" WHERE {conditions}"
        c.execute(query, (param,) * len(self.search_fields))
        records = c.fetchall()
        conn.close()
        for rec in records:
            self.tree.insert("", tk.END, values=tuple(rec))

# ---------------------------- Billing Frame ----------------------------
class BillingFrame:
    def __init__(self, parent):
        self.parent = parent
        self.frame = tk.Frame(parent, bg="white")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Cart items
        self.cart = []  # list of tuples (product_id, name, price, qty, total)

        # Title
        tk.Label(self.frame, text="Billing System", font=("Arial", 20, "bold"),
                 bg="white", fg="dark blue").pack(anchor=tk.W, pady=10)

        # Customer area
        cust_frame = tk.LabelFrame(self.frame, text="Customer Details", bg="white",
                                   font=("Arial", 12, "bold"), padx=10, pady=10)
        cust_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(cust_frame, text="Name:", bg="white").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.cust_name = tk.Entry(cust_frame, width=25)
        self.cust_name.grid(row=0, column=1, padx=5)

        tk.Label(cust_frame, text="Phone:", bg="white").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.cust_phone = tk.Entry(cust_frame, width=20)
        self.cust_phone.grid(row=0, column=3, padx=5)

        # Product selection
        prod_frame = tk.LabelFrame(self.frame, text="Add Product to Bill", bg="white",
                                   font=("Arial", 12, "bold"), padx=10, pady=10)
        prod_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(prod_frame, text="Product:", bg="white").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.prod_combo = ttk.Combobox(prod_frame, width=30, state="readonly")
        self.prod_combo.grid(row=0, column=1, padx=5)
        self.load_product_list()

        tk.Label(prod_frame, text="Quantity:", bg="white").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.qty_entry = tk.Entry(prod_frame, width=10)
        self.qty_entry.grid(row=0, column=3, padx=5)

        btn_add_cart = tk.Button(prod_frame, text="Add to Cart", bg="blue", fg="white",
                                 font=("Arial", 10, "bold"), command=self.add_to_cart)
        btn_add_cart.grid(row=0, column=4, padx=10)

        # Cart treeview
        cart_frame = tk.LabelFrame(self.frame, text="Cart Items", bg="white",
                                   font=("Arial", 12, "bold"), padx=5, pady=5)
        cart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.cart_tree = ttk.Treeview(cart_frame, columns=("ID", "Product", "Price", "Qty", "Total"),
                                      show="headings", selectmode="browse")
        self.cart_tree.heading("ID", text="ID")
        self.cart_tree.heading("Product", text="Product")
        self.cart_tree.heading("Price", text="Price")
        self.cart_tree.heading("Qty", text="Qty")
        self.cart_tree.heading("Total", text="Total")
        self.cart_tree.column("ID", width=50)
        self.cart_tree.column("Product", width=200)
        self.cart_tree.column("Price", width=80)
        self.cart_tree.column("Qty", width=50)
        self.cart_tree.column("Total", width=100)
        self.cart_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(cart_frame, orient=tk.VERTICAL, command=self.cart_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.cart_tree.config(yscrollcommand=scrollbar.set)

        # Buttons for bill
        btn_frame = tk.Frame(self.frame, bg="white")
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        self.btn_generate = tk.Button(btn_frame, text="Generate Bill", bg="green", fg="white",
                                      font=("Arial", 12, "bold"), command=self.generate_bill)
        self.btn_generate.pack(side=tk.LEFT, padx=5)

        self.btn_clear_cart = tk.Button(btn_frame, text="Clear Cart", bg="orange",
                                        font=("Arial", 12, "bold"), command=self.clear_cart)
        self.btn_clear_cart.pack(side=tk.LEFT, padx=5)

        # Search bill by invoice no
        search_frame = tk.LabelFrame(self.frame, text="Search Bill by Invoice No", bg="white",
                                     font=("Arial", 12, "bold"), padx=10, pady=10)
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(search_frame, text="Invoice No:", bg="white").pack(side=tk.LEFT, padx=5)
        self.invoice_search = tk.Entry(search_frame, width=15)
        self.invoice_search.pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", bg="purple", fg="white",
                  font=("Arial", 10, "bold"), command=self.search_bill).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All Bills", bg="navy", fg="white",
                  font=("Arial", 10, "bold"), command=self.view_all_bills).pack(side=tk.LEFT, padx=5)

        # Area to display searched bill
        self.bill_display = ttk.Treeview(self.frame, columns=("Invoice", "Customer", "Date", "Total"),
                                         show="headings", height=3)
        self.bill_display.heading("Invoice", text="Invoice No")
        self.bill_display.heading("Customer", text="Customer")
        self.bill_display.heading("Date", text="Date")
        self.bill_display.heading("Total", text="Total")
        self.bill_display.pack(fill=tk.X, padx=10, pady=5)
        # Second tree for bill items when bill is clicked
        self.bill_items_tree = ttk.Treeview(self.frame, columns=("Product", "Qty", "Price", "Total"),
                                            show="headings")
        self.bill_items_tree.heading("Product", text="Product")
        self.bill_items_tree.heading("Qty", text="Qty")
        self.bill_items_tree.heading("Price", text="Price")
        self.bill_items_tree.heading("Total", text="Total")
        self.bill_items_tree.pack(fill=tk.X, padx=10, pady=5)
        self.bill_display.bind("<ButtonRelease-1>", self.on_bill_select)

    def load_product_list(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, name, price, qty FROM products WHERE status='active' AND qty > 0")
        products = c.fetchall()
        conn.close()
        self.products = products  # store for later
        self.prod_combo['values'] = [f"{p['id']} - {p['name']} (Stock:{p['qty']})" for p in products]
        if products:
            self.prod_combo.current(0)

    def add_to_cart(self):
        prod_str = self.prod_combo.get()
        if not prod_str:
            messagebox.showerror("Error", "Please select a product.")
            return
        prod_id = int(prod_str.split(" - ")[0])
        try:
            qty = int(self.qty_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Quantity must be number.")
            return

        # Get product details
        prod = next((p for p in self.products if p['id'] == prod_id), None)
        if not prod:
            messagebox.showerror("Error", "Product not found.")
            return
        if qty > prod['qty']:
            messagebox.showerror("Error", f"Insufficient stock. Available: {prod['qty']}")
            return

        price = prod['price']
        total = price * qty
        self.cart.append((prod_id, prod['name'], price, qty, total))
        self.update_cart_tree()
        self.qty_entry.delete(0, tk.END)

    def update_cart_tree(self):
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        for i, item in enumerate(self.cart):
            self.cart_tree.insert("", tk.END, iid=i, values=item)

    def clear_cart(self):
        self.cart = []
        self.update_cart_tree()

    def generate_bill(self):
        if not self.cart:
            messagebox.showwarning("Empty Cart", "Please add items to cart.")
            return
        cust_name = self.cust_name.get().strip()
        cust_phone = self.cust_phone.get().strip()
        if not cust_name or not cust_phone:
            messagebox.showwarning("Customer Info", "Please enter customer name and phone.")
            return

        total_amount = sum(item[4] for item in self.cart)
        bill_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = get_connection()
        c = conn.cursor()
        try:
            # Insert bill
            c.execute("INSERT INTO bills (customer_name, customer_phone, bill_date, total_amount) VALUES (?, ?, ?, ?)",
                      (cust_name, cust_phone, bill_date, total_amount))
            bill_id = c.lastrowid

            # Insert bill items and update stock
            for prod_id, name, price, qty, total in self.cart:
                c.execute("INSERT INTO bill_items (bill_id, product_id, product_name, qty, price, total) VALUES (?, ?, ?, ?, ?, ?)",
                          (bill_id, prod_id, name, qty, price, total))
                c.execute("UPDATE products SET qty = qty - ? WHERE id=?", (qty, prod_id))

            conn.commit()
            messagebox.showinfo("Success", f"Bill Generated. Invoice No: {bill_id}")
            self.clear_cart()
            self.cust_name.delete(0, tk.END)
            self.cust_phone.delete(0, tk.END)
            self.load_product_list()
            # Show the new bill
            self.show_bill_by_id(bill_id)
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", str(e))
        finally:
            conn.close()

    def show_bill_by_id(self, bill_id):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT bill_id, customer_name, bill_date, total_amount FROM bills WHERE bill_id=?", (bill_id,))
        bill = c.fetchone()
        if bill:
            self.bill_display.delete(*self.bill_display.get_children())
            self.bill_display.insert("", tk.END, values=tuple(bill))
            self.display_bill_items(bill_id)
        conn.close()

    def display_bill_items(self, bill_id):
        for row in self.bill_items_tree.get_children():
            self.bill_items_tree.delete(row)
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT product_name, qty, price, total FROM bill_items WHERE bill_id=?", (bill_id,))
        items = c.fetchall()
        for item in items:
            self.bill_items_tree.insert("", tk.END, values=tuple(item))
        conn.close()

    def search_bill(self):
        invoice = self.invoice_search.get().strip()
        if not invoice:
            messagebox.showwarning("Input", "Enter invoice number.")
            return
        try:
            bill_id = int(invoice)
        except ValueError:
            messagebox.showerror("Error", "Invoice number must be integer.")
            return
        self.show_bill_by_id(bill_id)

    def view_all_bills(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT bill_id, customer_name, bill_date, total_amount FROM bills ORDER BY bill_id DESC")
        bills = c.fetchall()
        conn.close()
        self.bill_display.delete(*self.bill_display.get_children())
        for b in bills:
            self.bill_display.insert("", tk.END, values=tuple(b))
        # clear items tree
        for row in self.bill_items_tree.get_children():
            self.bill_items_tree.delete(row)

    def on_bill_select(self, event):
        selected = self.bill_display.selection()
        if not selected:
            return
        values = self.bill_display.item(selected[0], 'values')
        if values:
            bill_id = values[0]
            self.display_bill_items(bill_id)

# ---------------------------- Run Application ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryManagementSystem(root)
    root.mainloop()