import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
from datetime import datetime
from PIL import Image, ImageTk
import random
import string


# Database Setup
def init_db():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT,
            gender TEXT,
            dob TEXT,
            department TEXT,
            designation TEXT,
            salary REAL,
            join_date TEXT,
            photo TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT,
            company TEXT,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            supplier TEXT,
            price REAL,
            quantity INTEGER,
            description TEXT,
            status TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            customer_name TEXT,
            customer_phone TEXT,
            customer_email TEXT,
            bill_date TEXT,
            total REAL,
            tax REAL,
            grand_total REAL,
            bill_data TEXT
        )
    """)

    conn.commit()
    conn.close()


# Color Scheme
BG_COLOR = "#1a1a2e"
SIDEBAR_COLOR = "#16213e"
CARD_COLOR = "#0f3460"
ACCENT_COLOR = "#e94560"
TEXT_COLOR = "#ffffff"
ENTRY_BG = "#16213e"
BUTTON_COLOR = "#e94560"
BUTTON_HOVER = "#c73652"
GREEN_COLOR = "#00b894"
YELLOW_COLOR = "#fdcb6e"
BLUE_COLOR = "#0984e3"


class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1400x800")
        self.configure(bg=BG_COLOR)
        self.resizable(True, True)
        init_db()
        self.current_frame = None
        self.create_layout()
        self.show_dashboard()

    def create_layout(self):
        # Sidebar
        self.sidebar = tk.Frame(self, bg=SIDEBAR_COLOR, width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # Logo area
        logo_frame = tk.Frame(self.sidebar, bg=ACCENT_COLOR, height=80)
        logo_frame.pack(fill=tk.X)
        logo_frame.pack_propagate(False)
        tk.Label(logo_frame, text="📦 IMS", font=("Arial", 22, "bold"),
                 bg=ACCENT_COLOR, fg=TEXT_COLOR).pack(expand=True)

        # Navigation buttons
        nav_items = [
            ("🏠  Dashboard", self.show_dashboard),
            ("👤  Employees", self.show_employees),
            ("🚚  Suppliers", self.show_suppliers),
            ("📦  Products", self.show_products),
            ("🏷️  Categories", self.show_categories),
            ("🧾  Billing", self.show_billing),
            ("📋  Bills", self.show_bills),
        ]

        self.nav_buttons = []
        for text, command in nav_items:
            btn = tk.Button(self.sidebar, text=text, font=("Arial", 12),
                            bg=SIDEBAR_COLOR, fg=TEXT_COLOR,
                            bd=0, padx=20, pady=15, anchor="w",
                            activebackground=ACCENT_COLOR,
                            activeforeground=TEXT_COLOR,
                            cursor="hand2", command=command)
            btn.pack(fill=tk.X)
            self.nav_buttons.append(btn)

        # Main content area
        self.main_frame = tk.Frame(self, bg=BG_COLOR)
        self.main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Top bar
        self.topbar = tk.Frame(self.main_frame, bg=CARD_COLOR, height=60)
        self.topbar.pack(fill=tk.X)
        self.topbar.pack_propagate(False)

        self.page_title = tk.Label(self.topbar, text="Dashboard",
                                   font=("Arial", 16, "bold"),
                                   bg=CARD_COLOR, fg=TEXT_COLOR)
        self.page_title.pack(side=tk.LEFT, padx=20, pady=15)

        self.time_label = tk.Label(self.topbar, text="",
                                   font=("Arial", 11),
                                   bg=CARD_COLOR, fg=YELLOW_COLOR)
        self.time_label.pack(side=tk.RIGHT, padx=20)
        self.update_time()

        # Content frame
        self.content_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def update_time(self):
        now = datetime.now().strftime("%A, %d %B %Y  |  %I:%M:%S %p")
        self.time_label.config(text=now)
        self.after(1000, self.update_time)

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_dashboard(self):
        self.page_title.config(text="Dashboard")
        self.clear_content()
        DashboardFrame(self.content_frame)

    def show_employees(self):
        self.page_title.config(text="Employee Management")
        self.clear_content()
        EmployeeFrame(self.content_frame)

    def show_suppliers(self):
        self.page_title.config(text="Supplier Management")
        self.clear_content()
        SupplierFrame(self.content_frame)

    def show_products(self):
        self.page_title.config(text="Product Management")
        self.clear_content()
        ProductFrame(self.content_frame)

    def show_categories(self):
        self.page_title.config(text="Category Management")
        self.clear_content()
        CategoryFrame(self.content_frame)

    def show_billing(self):
        self.page_title.config(text="Billing")
        self.clear_content()
        BillingFrame(self.content_frame)

    def show_bills(self):
        self.page_title.config(text="Bills / Invoices")
        self.clear_content()
        BillsFrame(self.content_frame)


class DashboardFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.pack(fill=tk.BOTH, expand=True)
        self.create_widgets()

    def get_counts(self):
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM employees")
        emp = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM suppliers")
        sup = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM products")
        prod = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM categories")
        cat = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM bills")
        bills = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(grand_total) FROM bills")
        revenue = cursor.fetchone()[0] or 0
        conn.close()
        return emp, sup, prod, cat, bills, revenue

    def create_widgets(self):
        emp, sup, prod, cat, bills, revenue = self.get_counts()

        # Welcome label
        tk.Label(self, text="Welcome to Inventory Management System",
                 font=("Arial", 18, "bold"), bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=(10, 5))
        tk.Label(self, text=f"Today: {datetime.now().strftime('%A, %d %B %Y')}",
                 font=("Arial", 12), bg=BG_COLOR, fg=YELLOW_COLOR).pack(pady=(0, 20))

        # Stats cards
        cards_frame = tk.Frame(self, bg=BG_COLOR)
        cards_frame.pack(fill=tk.X, padx=20)

        cards_data = [
            ("👤 Employees", emp, GREEN_COLOR),
            ("🚚 Suppliers", sup, BLUE_COLOR),
            ("📦 Products", prod, ACCENT_COLOR),
            ("🏷️ Categories", cat, YELLOW_COLOR),
            ("🧾 Bills", bills, "#a29bfe"),
            (f"💰 Revenue", f"${revenue:.2f}", "#00cec9"),
        ]

        for i, (title, value, color) in enumerate(cards_data):
            card = tk.Frame(cards_frame, bg=color, width=180, height=120)
            card.grid(row=0, column=i, padx=8, pady=8, sticky="nsew")
            card.pack_propagate(False)
            cards_frame.columnconfigure(i, weight=1)
            tk.Label(card, text=str(value), font=("Arial", 26, "bold"),
                     bg=color, fg=TEXT_COLOR).pack(expand=True)
            tk.Label(card, text=title, font=("Arial", 11, "bold"),
                     bg=color, fg=TEXT_COLOR).pack(pady=(0, 10))

        # Recent bills table
        tk.Label(self, text="Recent Bills", font=("Arial", 14, "bold"),
                 bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=(20, 5), anchor="w", padx=20)

        table_frame = tk.Frame(self, bg=CARD_COLOR)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        cols = ("Invoice No", "Customer", "Date", "Grand Total")
        tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=8)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=CARD_COLOR, foreground=TEXT_COLOR,
                         fieldbackground=CARD_COLOR, rowheight=28)
        style.configure("Treeview.Heading", background=ACCENT_COLOR,
                         foreground=TEXT_COLOR, font=("Arial", 10, "bold"))

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor="center")

        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT invoice_no, customer_name, bill_date, grand_total FROM bills ORDER BY id DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            tree.insert("", tk.END, values=row)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)


class EmployeeFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.pack(fill=tk.BOTH, expand=True)
        self.photo_path = tk.StringVar()
        self.photo_image = None
        self.selected_id = None
        self.create_widgets()
        self.load_data()

    def generate_id(self):
        return "EMP" + "".join(random.choices(string.digits, k=5))

    def create_widgets(self):
        # Left form
        left = tk.Frame(self, bg=CARD_COLOR, width=380)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left.pack_propagate(False)

        tk.Label(left, text="Employee Details", font=("Arial", 14, "bold"),
                 bg=CARD_COLOR, fg=ACCENT_COLOR).pack(pady=10)

        # Photo
        self.photo_label = tk.Label(left, bg=CARD_COLOR, width=120, height=120,
                                    relief="solid", bd=1, fg=TEXT_COLOR,
                                    text="No Photo")
        self.photo_label.pack(pady=5)

        tk.Button(left, text="Browse Photo", bg=BLUE_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 9), bd=0, padx=10, pady=5,
                  command=self.browse_photo).pack(pady=3)

        form_frame = tk.Frame(left, bg=CARD_COLOR)
        form_frame.pack(fill=tk.X, padx=15)

        fields = [
            ("Employee ID", "emp_id"),
            ("Full Name", "name"),
            ("Email", "email"),
            ("Phone", "phone"),
            ("Address", "address"),
            ("Date of Birth", "dob"),
            ("Department", "department"),
            ("Designation", "designation"),
            ("Salary", "salary"),
            ("Join Date", "join_date"),
        ]

        self.entries = {}
        for label, key in fields:
            tk.Label(form_frame, text=label, bg=CARD_COLOR, fg=TEXT_COLOR,
                     font=("Arial", 9)).pack(anchor="w", pady=(5, 0))
            entry = tk.Entry(form_frame, bg=ENTRY_BG, fg=TEXT_COLOR,
                             insertbackground=TEXT_COLOR, font=("Arial", 10),
                             relief="flat", bd=5)
            entry.pack(fill=tk.X, pady=2)
            self.entries[key] = entry

        # Gender
        tk.Label(form_frame, text="Gender", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 9)).pack(anchor="w", pady=(5, 0))
        self.gender_var = tk.StringVar(value="Male")
        gender_frame = tk.Frame(form_frame, bg=CARD_COLOR)
        gender_frame.pack(fill=tk.X)
        for g in ["Male", "Female", "Other"]:
            tk.Radiobutton(gender_frame, text=g, variable=self.gender_var,
                           value=g, bg=CARD_COLOR, fg=TEXT_COLOR,
                           selectcolor=ENTRY_BG, activebackground=CARD_COLOR,
                           activeforeground=TEXT_COLOR).pack(side=tk.LEFT)

        # Buttons
        btn_frame = tk.Frame(left, bg=CARD_COLOR)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Add", bg=GREEN_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.add_employee).grid(row=0, column=0, padx=3)
        tk.Button(btn_frame, text="Update", bg=BLUE_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.update_employee).grid(row=0, column=1, padx=3)
        tk.Button(btn_frame, text="Delete", bg=ACCENT_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.delete_employee).grid(row=0, column=2, padx=3)
        tk.Button(btn_frame, text="Clear", bg=YELLOW_COLOR, fg="#000",
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.clear_form).grid(row=0, column=3, padx=3)

        # Right table
        right = tk.Frame(self, bg=BG_COLOR)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Search
        search_frame = tk.Frame(right, bg=BG_COLOR)
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search:", bg=BG_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, bg=ENTRY_BG,
                 fg=TEXT_COLOR, insertbackground=TEXT_COLOR, font=("Arial", 10),
                 relief="flat", bd=5, width=30).pack(side=tk.LEFT, padx=5)

        # Table
        cols = ("EMP ID", "Name", "Email", "Phone", "Department", "Designation", "Salary", "Gender")
        self.tree = ttk.Treeview(right, columns=cols, show="headings")
        style = ttk.Style()
        style.configure("Treeview", background=CARD_COLOR, foreground=TEXT_COLOR,
                         fieldbackground=CARD_COLOR, rowheight=28)
        style.configure("Treeview.Heading", background=ACCENT_COLOR,
                         foreground=TEXT_COLOR, font=("Arial", 10, "bold"))

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")

        scrollbar_y = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(right, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<ButtonRelease-1>", self.select_row)

        # Auto-generate ID
        self.entries["emp_id"].insert(0, self.generate_id())
        self.entries["join_date"].insert(0, datetime.now().strftime("%Y-%m-%d"))

    def browse_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif")])
        if path:
            self.photo_path.set(path)
            img = Image.open(path).resize((120, 120))
            self.photo_image = ImageTk.PhotoImage(img)
            self.photo_label.config(image=self.photo_image, text="")

    def get_form_data(self):
        return {
            "emp_id": self.entries["emp_id"].get().strip(),
            "name": self.entries["name"].get().strip(),
            "email": self.entries["email"].get().strip(),
            "phone": self.entries["phone"].get().strip(),
            "address": self.entries["address"].get().strip(),
            "gender": self.gender_var.get(),
            "dob": self.entries["dob"].get().strip(),
            "department": self.entries["department"].get().strip(),
            "designation": self.entries["designation"].get().strip(),
            "salary": self.entries["salary"].get().strip(),
            "join_date": self.entries["join_date"].get().strip(),
            "photo": self.photo_path.get(),
        }

    def add_employee(self):
        data = self.get_form_data()
        if not data["emp_id"] or not data["name"]:
            messagebox.showerror("Error", "Employee ID and Name are required!")
            return
        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO employees (emp_id, name, email, phone, address, gender, dob,
                department, designation, salary, join_date, photo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data["emp_id"], data["name"], data["email"], data["phone"],
                  data["address"], data["gender"], data["dob"], data["department"],
                  data["designation"], data["salary"], data["join_date"], data["photo"]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee added successfully!")
            self.clear_form()
            self.load_data()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Employee ID already exists!")

    def update_employee(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select an employee to update!")
            return
        data = self.get_form_data()
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE employees SET emp_id=?, name=?, email=?, phone=?, address=?, gender=?,
            dob=?, department=?, designation=?, salary=?, join_date=?, photo=?
            WHERE id=?
        """, (data["emp_id"], data["name"], data["email"], data["phone"],
              data["address"], data["gender"], data["dob"], data["department"],
              data["designation"], data["salary"], data["join_date"], data["photo"],
              self.selected_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Employee updated successfully!")
        self.clear_form()
        self.load_data()

    def delete_employee(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select an employee to delete!")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this employee?"):
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM employees WHERE id=?", (self.selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee deleted successfully!")
            self.clear_form()
            self.load_data()

    def clear_form(self):
        for key, entry in self.entries.items():
            entry.delete(0, tk.END)
        self.entries["emp_id"].insert(0, self.generate_id())
        self.entries["join_date"].insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.gender_var.set("Male")
        self.photo_path.set("")
        self.photo_label.config(image="", text="No Photo")
        self.photo_image = None
        self.selected_id = None

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, emp_id, name, email, phone, department, designation, salary, gender FROM employees")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, iid=row[0], values=row[1:])

    def search_data(self):
        query = self.search_var.get().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, emp_id, name, email, phone, department, designation, salary, gender
            FROM employees WHERE LOWER(name) LIKE ? OR LOWER(emp_id) LIKE ?
        """, (f"%{query}%", f"%{query}%"))
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, iid=row[0], values=row[1:])

    def select_row(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        self.selected_id = selected[0]
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE id=?", (self.selected_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            keys = ["emp_id", "name", "email", "phone", "address", "dob",
                    "department", "designation", "salary", "join_date"]
            db_keys = [1, 2, 3, 4, 5, 7, 8, 9, 10, 11]
            for key, idx in zip(keys, db_keys):
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, row[idx] or "")
            self.gender_var.set(row[6] or "Male")
            photo = row[12]
            if photo and os.path.exists(photo):
                self.photo_path.set(photo)
                img = Image.open(photo).resize((120, 120))
                self.photo_image = ImageTk.PhotoImage(img)
                self.photo_label.config(image=self.photo_image, text="")
            else:
                self.photo_label.config(image="", text="No Photo")


class SupplierFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.pack(fill=tk.BOTH, expand=True)
        self.selected_id = None
        self.create_widgets()
        self.load_data()

    def generate_id(self):
        return "SUP" + "".join(random.choices(string.digits, k=5))

    def create_widgets(self):
        left = tk.Frame(self, bg=CARD_COLOR, width=350)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left.pack_propagate(False)

        tk.Label(left, text="Supplier Details", font=("Arial", 14, "bold"),
                 bg=CARD_COLOR, fg=ACCENT_COLOR).pack(pady=10)

        form_frame = tk.Frame(left, bg=CARD_COLOR)
        form_frame.pack(fill=tk.X, padx=15)

        fields = [
            ("Supplier ID", "supplier_id"),
            ("Name", "name"),
            ("Email", "email"),
            ("Phone", "phone"),
            ("Address", "address"),
            ("Company", "company"),
            ("Description", "description"),
        ]

        self.entries = {}
        for label, key in fields:
            tk.Label(form_frame, text=label, bg=CARD_COLOR, fg=TEXT_COLOR,
                     font=("Arial", 9)).pack(anchor="w", pady=(5, 0))
            entry = tk.Entry(form_frame, bg=ENTRY_BG, fg=TEXT_COLOR,
                             insertbackground=TEXT_COLOR, font=("Arial", 10),
                             relief="flat", bd=5)
            entry.pack(fill=tk.X, pady=2)
            self.entries[key] = entry

        btn_frame = tk.Frame(left, bg=CARD_COLOR)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Add", bg=GREEN_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.add_supplier).grid(row=0, column=0, padx=3)
        tk.Button(btn_frame, text="Update", bg=BLUE_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.update_supplier).grid(row=0, column=1, padx=3)
        tk.Button(btn_frame, text="Delete", bg=ACCENT_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.delete_supplier).grid(row=0, column=2, padx=3)
        tk.Button(btn_frame, text="Clear", bg=YELLOW_COLOR, fg="#000",
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.clear_form).grid(row=0, column=3, padx=3)

        right = tk.Frame(self, bg=BG_COLOR)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        search_frame = tk.Frame(right, bg=BG_COLOR)
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search:", bg=BG_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, bg=ENTRY_BG,
                 fg=TEXT_COLOR, insertbackground=TEXT_COLOR, font=("Arial", 10),
                 relief="flat", bd=5, width=30).pack(side=tk.LEFT, padx=5)

        cols = ("Supplier ID", "Name", "Email", "Phone", "Company", "Address")
        self.tree = ttk.Treeview(right, columns=cols, show="headings")
        style = ttk.Style()
        style.configure("Treeview", background=CARD_COLOR, foreground=TEXT_COLOR,
                         fieldbackground=CARD_COLOR, rowheight=28)
        style.configure("Treeview.Heading", background=ACCENT_COLOR,
                         foreground=TEXT_COLOR, font=("Arial", 10, "bold"))

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=130, anchor="center")

        scrollbar_y = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<ButtonRelease-1>", self.select_row)

        self.entries["supplier_id"].insert(0, self.generate_id())

    def add_supplier(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        if not data["supplier_id"] or not data["name"]:
            messagebox.showerror("Error", "Supplier ID and Name are required!")
            return
        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO suppliers (supplier_id, name, email, phone, address, company, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data["supplier_id"], data["name"], data["email"], data["phone"],
                  data["address"], data["company"], data["description"]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier added successfully!")
            self.clear_form()
            self.load_data()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Supplier ID already exists!")

    def update_supplier(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a supplier to update!")
            return
        data = {k: v.get().strip() for k, v in self.entries.items()}
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE suppliers SET supplier_id=?, name=?, email=?, phone=?, address=?, company=?, description=?
            WHERE id=?
        """, (data["supplier_id"], data["name"], data["email"], data["phone"],
              data["address"], data["company"], data["description"], self.selected_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Supplier updated successfully!")
        self.clear_form()
        self.load_data()

    def delete_supplier(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a supplier to delete!")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this supplier?"):
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM suppliers WHERE id=?", (self.selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier deleted successfully!")
            self.clear_form()
            self.load_data()

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.entries["supplier_id"].insert(0, self.generate_id())
        self.selected_id = None

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, supplier_id, name, email, phone, company, address FROM suppliers")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, iid=row[0], values=row[1:])

    def search_data(self):
        query = self.search_var.get().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, supplier_id, name, email, phone, company, address
            FROM suppliers WHERE LOWER(name) LIKE ? OR LOWER(supplier_id) LIKE ?
        """, (f"%{query}%", f"%{query}%"))
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, iid=row[0], values=row[1:])

    def select_row(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        self.selected_id = selected[0]
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM suppliers WHERE id=?", (self.selected_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            keys = ["supplier_id", "name", "email", "phone", "address", "company", "description"]
            for i, key in enumerate(keys):
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, row[i + 1] or "")


class CategoryFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.pack(fill=tk.BOTH, expand=True)
        self.selected_id = None
        self.create_widgets()
        self.load_data()

    def generate_id(self):
        return "CAT" + "".join(random.choices(string.digits, k=4))

    def create_widgets(self):
        left = tk.Frame(self, bg=CARD_COLOR, width=350)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left.pack_propagate(False)

        tk.Label(left, text="Category Details", font=("Arial", 14, "bold"),
                 bg=CARD_COLOR, fg=ACCENT_COLOR).pack(pady=10)

        form_frame = tk.Frame(left, bg=CARD_COLOR)
        form_frame.pack(fill=tk.X, padx=15)

        fields = [
            ("Category ID", "category_id"),
            ("Category Name", "name"),
            ("Description", "description"),
        ]

        self.entries = {}
        for label, key in fields:
            tk.Label(form_frame, text=label, bg=CARD_COLOR, fg=TEXT_COLOR,
                     font=("Arial", 9)).pack(anchor="w", pady=(5, 0))
            entry = tk.Entry(form_frame, bg=ENTRY_BG, fg=TEXT_COLOR,
                             insertbackground=TEXT_COLOR, font=("Arial", 10),
                             relief="flat", bd=5)
            entry.pack(fill=tk.X, pady=2)
            self.entries[key] = entry

        btn_frame = tk.Frame(left, bg=CARD_COLOR)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Add", bg=GREEN_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.add_category).grid(row=0, column=0, padx=3)
        tk.Button(btn_frame, text="Update", bg=BLUE_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.update_category).grid(row=0, column=1, padx=3)
        tk.Button(btn_frame, text="Delete", bg=ACCENT_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.delete_category).grid(row=0, column=2, padx=3)
        tk.Button(btn_frame, text="Clear", bg=YELLOW_COLOR, fg="#000",
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.clear_form).grid(row=0, column=3, padx=3)

        right = tk.Frame(self, bg=BG_COLOR)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        search_frame = tk.Frame(right, bg=BG_COLOR)
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search:", bg=BG_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, bg=ENTRY_BG,
                 fg=TEXT_COLOR, insertbackground=TEXT_COLOR, font=("Arial", 10),
                 relief="flat", bd=5, width=30).pack(side=tk.LEFT, padx=5)

        cols = ("Category ID", "Name", "Description")
        self.tree = ttk.Treeview(right, columns=cols, show="headings")
        style = ttk.Style()
        style.configure("Treeview", background=CARD_COLOR, foreground=TEXT_COLOR,
                         fieldbackground=CARD_COLOR, rowheight=28)
        style.configure("Treeview.Heading", background=ACCENT_COLOR,
                         foreground=TEXT_COLOR, font=("Arial", 10, "bold"))

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200, anchor="center")

        scrollbar_y = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<ButtonRelease-1>", self.select_row)

        self.entries["category_id"].insert(0, self.generate_id())

    def add_category(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        if not data["category_id"] or not data["name"]:
            messagebox.showerror("Error", "Category ID and Name are required!")
            return
        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO categories (category_id, name, description) VALUES (?, ?, ?)",
                           (data["category_id"], data["name"], data["description"]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category added successfully!")
            self.clear_form()
            self.load_data()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Category ID already exists!")

    def update_category(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a category to update!")
            return
        data = {k: v.get().strip() for k, v in self.entries.items()}
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE categories SET category_id=?, name=?, description=? WHERE id=?",
                       (data["category_id"], data["name"], data["description"], self.selected_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Category updated successfully!")
        self.clear_form()
        self.load_data()

    def delete_category(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a category to delete!")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this category?"):
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM categories WHERE id=?", (self.selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category deleted successfully!")
            self.clear_form()
            self.load_data()

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.entries["category_id"].insert(0, self.generate_id())
        self.selected_id = None

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, category_id, name, description FROM categories")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, iid=row[0], values=row[1:])

    def search_data(self):
        query = self.search_var.get().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, category_id, name, description
            FROM categories WHERE LOWER(name) LIKE ? OR LOWER(category_id) LIKE ?
        """, (f"%{query}%", f"%{query}%"))
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, iid=row[0], values=row[1:])

    def select_row(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        self.selected_id = selected[0]
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE id=?", (self.selected_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            keys = ["category_id", "name", "description"]
            for i, key in enumerate(keys):
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, row[i + 1] or "")


class ProductFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.pack(fill=tk.BOTH, expand=True)
        self.selected_id = None
        self.create_widgets()
        self.load_data()

    def generate_id(self):
        return "PRD" + "".join(random.choices(string.digits, k=5))

    def get_categories(self):
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories")
        cats = [row[0] for row in cursor.fetchall()]
        conn.close()
        return cats or ["General"]

    def get_suppliers(self):
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM suppliers")
        sups = [row[0] for row in cursor.fetchall()]
        conn.close()
        return sups or ["Default"]

    def create_widgets(self):
        left = tk.Frame(self, bg=CARD_COLOR, width=380)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left.pack_propagate(False)

        tk.Label(left, text="Product Details", font=("Arial", 14, "bold"),
                 bg=CARD_COLOR, fg=ACCENT_COLOR).pack(pady=10)

        form_frame = tk.Frame(left, bg=CARD_COLOR)
        form_frame.pack(fill=tk.X, padx=15)

        self.entries = {}

        # Product ID
        tk.Label(form_frame, text="Product ID", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 9)).pack(anchor="w", pady=(5, 0))
        self.entries["product_id"] = tk.Entry(form_frame, bg=ENTRY_BG, fg=TEXT_COLOR,
                                               insertbackground=TEXT_COLOR, font=("Arial", 10),
                                               relief="flat", bd=5)
        self.entries["product_id"].pack(fill=tk.X, pady=2)

        # Name
        tk.Label(form_frame, text="Product Name", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 9)).pack(anchor="w", pady=(5, 0))
        self.entries["name"] = tk.Entry(form_frame, bg=ENTRY_BG, fg=TEXT_COLOR,
                                         insertbackground=TEXT_COLOR, font=("Arial", 10),
                                         relief="flat", bd=5)
        self.entries["name"].pack(fill=tk.X, pady=2)

        # Category
        tk.Label(form_frame, text="Category", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 9)).pack(anchor="w", pady=(5, 0))
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(form_frame, textvariable=self.category_var,
                                            values=self.get_categories(), state="readonly")
        self.category_combo.pack(fill=tk.X, pady=2)

        # Supplier
        tk.Label(form_frame, text="Supplier", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 9)).pack(anchor="w", pady=(5, 0))
        self.supplier_var = tk.StringVar()
        self.supplier_combo = ttk.Combobox(form_frame, textvariable=self.supplier_var,
                                            values=self.get_suppliers(), state="readonly")
        self.supplier_combo.pack(fill=tk.X, pady=2)

        # Price
        tk.Label(form_frame, text="Price", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 9)).pack(anchor="w", pady=(5, 0))
        self.entries["price"] = tk.Entry(form_frame, bg=ENTRY_BG, fg=TEXT_COLOR,
                                          insertbackground=TEXT_COLOR, font=("Arial", 10),
                                          relief="flat", bd=5)
        self.entries["price"].pack(fill=tk.X, pady=2)

        # Quantity
        tk.Label(form_frame, text="Quantity", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 9)).pack(anchor="w", pady=(5, 0))
        self.entries["quantity"] = tk.Entry(form_frame, bg=ENTRY_BG, fg=TEXT_COLOR,
                                             insertbackground=TEXT_COLOR, font=("Arial", 10),
                                             relief="flat", bd=5)
        self.entries["quantity"].pack(fill=tk.X, pady=2)

        # Description
        tk.Label(form_frame, text="Description", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 9)).pack(anchor="w", pady=(5, 0))
        self.entries["description"] = tk.Entry(form_frame, bg=ENTRY_BG, fg=TEXT_COLOR,
                                                insertbackground=TEXT_COLOR, font=("Arial", 10),
                                                relief="flat", bd=5)
        self.entries["description"].pack(fill=tk.X, pady=2)

        # Status
        tk.Label(form_frame, text="Status", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 9)).pack(anchor="w", pady=(5, 0))
        self.status_var = tk.StringVar(value="Active")
        status_frame = tk.Frame(form_frame, bg=CARD_COLOR)
        status_frame.pack(fill=tk.X)
        for s in ["Active", "Inactive"]:
            tk.Radiobutton(status_frame, text=s, variable=self.status_var,
                           value=s, bg=CARD_COLOR, fg=TEXT_COLOR,
                           selectcolor=ENTRY_BG, activebackground=CARD_COLOR,
                           activeforeground=TEXT_COLOR).pack(side=tk.LEFT)

        btn_frame = tk.Frame(left, bg=CARD_COLOR)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Add", bg=GREEN_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.add_product).grid(row=0, column=0, padx=3)
        tk.Button(btn_frame, text="Update", bg=BLUE_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.update_product).grid(row=0, column=1, padx=3)
        tk.Button(btn_frame, text="Delete", bg=ACCENT_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.delete_product).grid(row=0, column=2, padx=3)
        tk.Button(btn_frame, text="Clear", bg=YELLOW_COLOR, fg="#000",
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=6,
                  command=self.clear_form).grid(row=0, column=3, padx=3)

        right = tk.Frame(self, bg=BG_COLOR)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        search_frame = tk.Frame(right, bg=BG_COLOR)
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search:", bg=BG_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, bg=ENTRY_BG,
                 fg=TEXT_COLOR, insertbackground=TEXT_COLOR, font=("Arial", 10),
                 relief="flat", bd=5, width=30).pack(side=tk.LEFT, padx=5)

        cols = ("Product ID", "Name", "Category", "Supplier", "Price", "Quantity", "Status")
        self.tree = ttk.Treeview(right, columns=cols, show="headings")
        style = ttk.Style()
        style.configure("Treeview", background=CARD_COLOR, foreground=TEXT_COLOR,
                         fieldbackground=CARD_COLOR, rowheight=28)
        style.configure("Treeview.Heading", background=ACCENT_COLOR,
                         foreground=TEXT_COLOR, font=("Arial", 10, "bold"))

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor="center")

        scrollbar_y = ttk.Scrollbar(right, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(right, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.bind("<ButtonRelease-1>", self.select_row)

        self.entries["product_id"].insert(0, self.generate_id())

    def add_product(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        data["category"] = self.category_var.get()
        data["supplier"] = self.supplier_var.get()
        data["status"] = self.status_var.get()

        if not data["product_id"] or not data["name"]:
            messagebox.showerror("Error", "Product ID and Name are required!")
            return
        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (product_id, name, category, supplier, price, quantity, description, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (data["product_id"], data["name"], data["category"], data["supplier"],
                  data["price"], data["quantity"], data["description"], data["status"]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product added successfully!")
            self.clear_form()
            self.load_data()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Product ID already exists!")

    def update_product(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a product to update!")
            return
        data = {k: v.get().strip() for k, v in self.entries.items()}
        data["category"] = self.category_var.get()
        data["supplier"] = self.supplier_var.get()
        data["status"] = self.status_var.get()
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE products SET product_id=?, name=?, category=?, supplier=?, price=?,
            quantity=?, description=?, status=? WHERE id=?
        """, (data["product_id"], data["name"], data["category"], data["supplier"],
              data["price"], data["quantity"], data["description"], data["status"],
              self.selected_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Product updated successfully!")
        self.clear_form()
        self.load_data()

    def delete_product(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a product to delete!")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this product?"):
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id=?", (self.selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product deleted successfully!")
            self.clear_form()
            self.load_data()

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.entries["product_id"].insert(0, self.generate_id())
        self.category_var.set("")
        self.supplier_var.set("")
        self.status_var.set("Active")
        self.selected_id = None
        self.category_combo["values"] = self.get_categories()
        self.supplier_combo["values"] = self.get_suppliers()

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, product_id, name, category, supplier, price, quantity, status FROM products")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, iid=row[0], values=row[1:])

    def search_data(self):
        query = self.search_var.get().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, product_id, name, category, supplier, price, quantity, status
            FROM products WHERE LOWER(name) LIKE ? OR LOWER(product_id) LIKE ?
        """, (f"%{query}%", f"%{query}%"))
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, iid=row[0], values=row[1:])

    def select_row(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        self.selected_id = selected[0]
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id=?", (self.selected_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            keys = ["product_id", "name", "price", "quantity", "description"]
            db_idx = [1, 2, 5, 6, 7]
            for key, idx in zip(keys, db_idx):
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, row[idx] or "")
            self.category_var.set(row[3] or "")
            self.supplier_var.set(row[4] or "")
            self.status_var.set(row[8] or "Active")


class BillingFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.pack(fill=tk.BOTH, expand=True)
        self.cart_items = []
        self.create_widgets()

    def generate_invoice(self):
        return "INV" + "".join(random.choices(string.digits, k=8))

    def get_products(self):
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name, price FROM products WHERE status='Active'")
        products = cursor.fetchall()
        conn.close()
        return products

    def create_widgets(self):
        # Top: Customer info
        top_frame = tk.Frame(self, bg=CARD_COLOR)
        top_frame.pack(fill=tk.X, pady=(0, 5))

        tk.Label(top_frame, text="Invoice No:", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 10)).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.invoice_var = tk.StringVar(value=self.generate_invoice())
        tk.Entry(top_frame, textvariable=self.invoice_var, bg=ENTRY_BG, fg=TEXT_COLOR,
                 insertbackground=TEXT_COLOR, font=("Arial", 10), relief="flat", bd=5,
                 width=20).grid(row=0, column=1, padx=5, pady=8)

        tk.Label(top_frame, text="Customer Name:", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 10)).grid(row=0, column=2, padx=10, pady=8, sticky="w")
        self.cust_name = tk.Entry(top_frame, bg=ENTRY_BG, fg=TEXT_COLOR,
                                   insertbackground=TEXT_COLOR, font=("Arial", 10),
                                   relief="flat", bd=5, width=20)
        self.cust_name.grid(row=0, column=3, padx=5, pady=8)

        tk.Label(top_frame, text="Phone:", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 10)).grid(row=0, column=4, padx=10, pady=8, sticky="w")
        self.cust_phone = tk.Entry(top_frame, bg=ENTRY_BG, fg=TEXT_COLOR,
                                    insertbackground=TEXT_COLOR, font=("Arial", 10),
                                    relief="flat", bd=5, width=15)
        self.cust_phone.grid(row=0, column=5, padx=5, pady=8)

        tk.Label(top_frame, text="Email:", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 10)).grid(row=0, column=6, padx=10, pady=8, sticky="w")
        self.cust_email = tk.Entry(top_frame, bg=ENTRY_BG, fg=TEXT_COLOR,
                                    insertbackground=TEXT_COLOR, font=("Arial", 10),
                                    relief="flat", bd=5, width=20)
        self.cust_email.grid(row=0, column=7, padx=5, pady=8)

        # Middle: Product selection + Cart
        mid_frame = tk.Frame(self, bg=BG_COLOR)
        mid_frame.pack(fill=tk.BOTH, expand=True)

        # Left: Product selection
        prod_frame = tk.Frame(mid_frame, bg=CARD_COLOR, width=350)
        prod_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        prod_frame.pack_propagate(False)

        tk.Label(prod_frame, text="Add Product", font=("Arial", 12, "bold"),
                 bg=CARD_COLOR, fg=ACCENT_COLOR).pack(pady=10)

        tk.Label(prod_frame, text="Select Product:", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 10)).pack(anchor="w", padx=15)
        self.product_var = tk.StringVar()
        products = self.get_products()
        product_names = [p[0] for p in products]
        self.product_prices = {p[0]: p[1] for p in products}
        self.product_combo = ttk.Combobox(prod_frame, textvariable=self.product_var,
                                           values=product_names, state="readonly", width=30)
        self.product_combo.pack(padx=15, pady=5, fill=tk.X)
        self.product_combo.bind("<<ComboboxSelected>>", self.on_product_select)

        tk.Label(prod_frame, text="Price:", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 10)).pack(anchor="w", padx=15)
        self.price_var = tk.StringVar(value="0.00")
        tk.Entry(prod_frame, textvariable=self.price_var, bg=ENTRY_BG, fg=TEXT_COLOR,
                 insertbackground=TEXT_COLOR, font=("Arial", 10), relief="flat", bd=5).pack(
            padx=15, pady=5, fill=tk.X)

        tk.Label(prod_frame, text="Quantity:", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 10)).pack(anchor="w", padx=15)
        self.qty_var = tk.StringVar(value="1")
        tk.Entry(prod_frame, textvariable=self.qty_var, bg=ENTRY_BG, fg=TEXT_COLOR,
                 insertbackground=TEXT_COLOR, font=("Arial", 10), relief="flat", bd=5).pack(
            padx=15, pady=5, fill=tk.X)

        tk.Button(prod_frame, text="Add to Cart", bg=GREEN_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 11, "bold"), bd=0, padx=20, pady=8,
                  command=self.add_to_cart).pack(pady=10)

        tk.Button(prod_frame, text="Remove Selected", bg=ACCENT_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 11, "bold"), bd=0, padx=20, pady=8,
                  command=self.remove_from_cart).pack(pady=5)

        # Right: Cart + Bill
        right_frame = tk.Frame(mid_frame, bg=BG_COLOR)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(right_frame, text="Cart", font=("Arial", 12, "bold"),
                 bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w", padx=5)

        cols = ("Product", "Price", "Quantity", "Total")
        self.cart_tree = ttk.Treeview(right_frame, columns=cols, show="headings", height=10)
        style = ttk.Style()
        style.configure("Treeview", background=CARD_COLOR, foreground=TEXT_COLOR,
                         fieldbackground=CARD_COLOR, rowheight=28)
        style.configure("Treeview.Heading", background=ACCENT_COLOR,
                         foreground=TEXT_COLOR, font=("Arial", 10, "bold"))

        for col in cols:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=150, anchor="center")

        self.cart_tree.pack(fill=tk.BOTH, expand=True, padx=5)

        # Summary
        summary_frame = tk.Frame(right_frame, bg=CARD_COLOR)
        summary_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(summary_frame, text="Subtotal:", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 11)).grid(row=0, column=0, padx=20, pady=5, sticky="w")
        self.subtotal_var = tk.StringVar(value="$0.00")
        tk.Label(summary_frame, textvariable=self.subtotal_var, bg=CARD_COLOR,
                 fg=GREEN_COLOR, font=("Arial", 11, "bold")).grid(row=0, column=1, padx=20)

        tk.Label(summary_frame, text="Tax (10%):", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 11)).grid(row=0, column=2, padx=20, pady=5, sticky="w")
        self.tax_var = tk.StringVar(value="$0.00")
        tk.Label(summary_frame, textvariable=self.tax_var, bg=CARD_COLOR,
                 fg=YELLOW_COLOR, font=("Arial", 11, "bold")).grid(row=0, column=3, padx=20)

        tk.Label(summary_frame, text="Grand Total:", bg=CARD_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 13, "bold")).grid(row=0, column=4, padx=20, pady=5, sticky="w")
        self.grand_total_var = tk.StringVar(value="$0.00")
        tk.Label(summary_frame, textvariable=self.grand_total_var, bg=CARD_COLOR,
                 fg=ACCENT_COLOR, font=("Arial", 13, "bold")).grid(row=0, column=5, padx=20)

        # Buttons
        bill_btn_frame = tk.Frame(right_frame, bg=BG_COLOR)
        bill_btn_frame.pack(pady=5)

        tk.Button(bill_btn_frame, text="Generate Bill", bg=GREEN_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 12, "bold"), bd=0, padx=20, pady=8,
                  command=self.generate_bill).pack(side=tk.LEFT, padx=5)
        tk.Button(bill_btn_frame, text="Clear All", bg=ACCENT_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 12, "bold"), bd=0, padx=20, pady=8,
                  command=self.clear_all).pack(side=tk.LEFT, padx=5)
        tk.Button(bill_btn_frame, text="Print Bill", bg=BLUE_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 12, "bold"), bd=0, padx=20, pady=8,
                  command=self.print_bill).pack(side=tk.LEFT, padx=5)

    def on_product_select(self, event):
        product = self.product_var.get()
        if product in self.product_prices:
            self.price_var.set(str(self.product_prices[product]))

    def add_to_cart(self):
        product = self.product_var.get()
        if not product:
            messagebox.showerror("Error", "Please select a product!")
            return
        try:
            price = float(self.price_var.get())
            qty = int(self.qty_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid price or quantity!")
            return

        total = price * qty
        self.cart_items.append({"product": product, "price": price, "qty": qty, "total": total})
        self.cart_tree.insert("", tk.END, values=(product, f"${price:.2f}", qty, f"${total:.2f}"))
        self.update_totals()

    def remove_from_cart(self):
        selected = self.cart_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select an item to remove!")
            return
        idx = self.cart_tree.index(selected[0])
        self.cart_tree.delete(selected[0])
        self.cart_items.pop(idx)
        self.update_totals()

    def update_totals(self):
        subtotal = sum(item["total"] for item in self.cart_items)
        tax = subtotal * 0.10
        grand_total = subtotal + tax
        self.subtotal_var.set(f"${subtotal:.2f}")
        self.tax_var.set(f"${tax:.2f}")
        self.grand_total_var.set(f"${grand_total:.2f}")

    def generate_bill(self):
        if not self.cart_items:
            messagebox.showerror("Error", "Cart is empty!")
            return
        invoice_no = self.invoice_var.get()
        cust_name = self.cust_name.get().strip()
        cust_phone = self.cust_phone.get().strip()
        cust_email = self.cust_email.get().strip()

        if not cust_name:
            messagebox.showerror("Error", "Customer name is required!")
            return

        subtotal = sum(item["total"] for item in self.cart_items)
        tax = subtotal * 0.10
        grand_total = subtotal + tax
        bill_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        import json
        bill_data = json.dumps(self.cart_items)

        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bills (invoice_no, customer_name, customer_phone, customer_email,
                bill_date, total, tax, grand_total, bill_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (invoice_no, cust_name, cust_phone, cust_email,
                  bill_date, subtotal, tax, grand_total, bill_data))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Bill generated successfully!\nInvoice No: {invoice_no}")
            self.clear_all()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Invoice number already exists!")

    def print_bill(self):
        if not self.cart_items:
            messagebox.showerror("Error", "Cart is empty!")
            return
        invoice_no = self.invoice_var.get()
        cust_name = self.cust_name.get().strip() or "Walk-in Customer"
        subtotal = sum(item["total"] for item in self.cart_items)
        tax = subtotal * 0.10
        grand_total = subtotal + tax

        bill_text = f"""
{'='*50}
        INVENTORY MANAGEMENT SYSTEM
              SALES INVOICE
{'='*50}
Invoice No : {invoice_no}
Date       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Customer   : {cust_name}
Phone      : {self.cust_phone.get()}
Email      : {self.cust_email.get()}
{'='*50}
{'Product':<20} {'Price':>8} {'Qty':>5} {'Total':>10}
{'-'*50}
"""
        for item in self.cart_items:
            bill_text += f"{item['product']:<20} ${item['price']:>7.2f} {item['qty']:>5} ${item['total']:>9.2f}\n"

        bill_text += f"""
{'-'*50}
{'Subtotal:':<35} ${subtotal:>9.2f}
{'Tax (10%):':<35} ${tax:>9.2f}
{'Grand Total:':<35} ${grand_total:>9.2f}
{'='*50}
        Thank you for your purchase!
{'='*50}
"""
        # Show in popup
        popup = tk.Toplevel()
        popup.title("Bill Preview")
        popup.geometry("500x600")
        popup.configure(bg=BG_COLOR)

        tk.Label(popup, text="Bill Preview", font=("Arial", 14, "bold"),
                 bg=BG_COLOR, fg=ACCENT_COLOR).pack(pady=10)

        text_widget = tk.Text(popup, bg=CARD_COLOR, fg=TEXT_COLOR,
                               font=("Courier", 10), relief="flat")
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        text_widget.insert(tk.END, bill_text)
        text_widget.config(state=tk.DISABLED)

        tk.Button(popup, text="Close", bg=ACCENT_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 11, "bold"), bd=0, padx=20, pady=6,
                  command=popup.destroy).pack(pady=10)

    def clear_all(self):
        self.cart_items.clear()
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        self.cust_name.delete(0, tk.END)
        self.cust_phone.delete(0, tk.END)
        self.cust_email.delete(0, tk.END)
        self.invoice_var.set(self.generate_invoice())
        self.product_var.set("")
        self.price_var.set("0.00")
        self.qty_var.set("1")
        self.update_totals()


class BillsFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.pack(fill=tk.BOTH, expand=True)
        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        # Search
        search_frame = tk.Frame(self, bg=BG_COLOR)
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search:", bg=BG_COLOR, fg=TEXT_COLOR,
                 font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, bg=ENTRY_BG,
                 fg=TEXT_COLOR, insertbackground=TEXT_COLOR, font=("Arial", 10),
                 relief="flat", bd=5, width=30).pack(side=tk.LEFT, padx=5)

        tk.Button(search_frame, text="View Bill", bg=BLUE_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=5,
                  command=self.view_bill).pack(side=tk.LEFT, padx=10)
        tk.Button(search_frame, text="Delete Bill", bg=ACCENT_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 10, "bold"), bd=0, padx=15, pady=5,
                  command=self.delete_bill).pack(side=tk.LEFT, padx=5)

        # Table
        cols = ("Invoice No", "Customer", "Phone", "Email", "Date", "Subtotal", "Tax", "Grand Total")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        style = ttk.Style()
        style.configure("Treeview", background=CARD_COLOR, foreground=TEXT_COLOR,
                         fieldbackground=CARD_COLOR, rowheight=28)
        style.configure("Treeview.Heading", background=ACCENT_COLOR,
                         foreground=TEXT_COLOR, font=("Arial", 10, "bold"))

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=130, anchor="center")

        scrollbar_y = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, invoice_no, customer_name, customer_phone, customer_email,
            bill_date, total, tax, grand_total FROM bills ORDER BY id DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, iid=row[0],
                             values=(row[1], row[2], row[3], row[4], row[5],
                                     f"${row[6]:.2f}", f"${row[7]:.2f}", f"${row[8]:.2f}"))

    def search_data(self):
        query = self.search_var.get().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, invoice_no, customer_name, customer_phone, customer_email,
            bill_date, total, tax, grand_total FROM bills
            WHERE LOWER(invoice_no) LIKE ? OR LOWER(customer_name) LIKE ?
            ORDER BY id DESC
        """, (f"%{query}%", f"%{query}%"))
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, iid=row[0],
                             values=(row[1], row[2], row[3], row[4], row[5],
                                     f"${row[6]:.2f}", f"${row[7]:.2f}", f"${row[8]:.2f}"))

    def view_bill(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a bill to view!")
            return
        bill_id = selected[0]
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bills WHERE id=?", (bill_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return

        import json
        try:
            items = json.loads(row[9])
        except Exception:
            items = []

        popup = tk.Toplevel()
        popup.title(f"Bill - {row[1]}")
        popup.geometry("550x650")
        popup.configure(bg=BG_COLOR)

        bill_text = f"""
{'='*55}
         INVENTORY MANAGEMENT SYSTEM
               SALES INVOICE
{'='*55}
Invoice No  : {row[1]}
Date        : {row[5]}
Customer    : {row[2]}
Phone       : {row[3]}
Email       : {row[4]}
{'='*55}
{'Product':<22} {'Price':>8} {'Qty':>5} {'Total':>12}
{'-'*55}
"""
        for item in items:
            bill_text += f"{item['product']:<22} ${item['price']:>7.2f} {item['qty']:>5} ${item['total']:>11.2f}\n"

        bill_text += f"""
{'-'*55}
{'Subtotal:':<40} ${row[6]:>9.2f}
{'Tax (10%):':<40} ${row[7]:>9.2f}
{'Grand Total:':<40} ${row[8]:>9.2f}
{'='*55}
          Thank you for your purchase!
{'='*55}
"""
        tk.Label(popup, text=f"Invoice: {row[1]}", font=("Arial", 14, "bold"),
                 bg=BG_COLOR, fg=ACCENT_COLOR).pack(pady=10)

        text_widget = tk.Text(popup, bg=CARD_COLOR, fg=TEXT_COLOR,
                               font=("Courier", 10), relief="flat")
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        text_widget.insert(tk.END, bill_text)
        text_widget.config(state=tk.DISABLED)

        tk.Button(popup, text="Close", bg=ACCENT_COLOR, fg=TEXT_COLOR,
                  font=("Arial", 11, "bold"), bd=0, padx=20, pady=6,
                  command=popup.destroy).pack(pady=10)

    def delete_bill(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a bill to delete!")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this bill?"):
            bill_id = selected[0]
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bills WHERE id=?", (bill_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Bill deleted successfully!")
            self.load_data()


if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()