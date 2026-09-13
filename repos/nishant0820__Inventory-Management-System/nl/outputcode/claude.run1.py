import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
from datetime import datetime
from PIL import Image, ImageTk
import random
import string


# Database Setup
def create_database():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        dob TEXT,
        email TEXT,
        phone TEXT,
        address TEXT,
        department TEXT,
        designation TEXT,
        salary REAL,
        join_date TEXT,
        photo TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        contact TEXT,
        email TEXT,
        phone TEXT,
        address TEXT,
        company TEXT,
        product_type TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT,
        supplier TEXT,
        price REAL,
        quantity INTEGER,
        description TEXT,
        status TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT UNIQUE NOT NULL,
        customer_name TEXT,
        customer_phone TEXT,
        customer_email TEXT,
        bill_date TEXT,
        total_amount REAL,
        tax REAL,
        discount REAL,
        net_amount REAL,
        bill_details TEXT
    )''')

    conn.commit()
    conn.close()


# Main Application
class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1400x800")
        self.resizable(True, True)
        self.configure(bg="#1a1a2e")
        create_database()
        self.current_frame = None
        self.setup_main_layout()
        self.show_dashboard()

    def setup_main_layout(self):
        # Header
        self.header_frame = tk.Frame(self, bg="#16213e", height=70)
        self.header_frame.pack(fill=tk.X, side=tk.TOP)
        self.header_frame.pack_propagate(False)

        title_label = tk.Label(
            self.header_frame,
            text="📦 Inventory Management System",
            font=("Arial", 22, "bold"),
            bg="#16213e",
            fg="#e94560"
        )
        title_label.pack(side=tk.LEFT, padx=20, pady=15)

        self.time_label = tk.Label(
            self.header_frame,
            text="",
            font=("Arial", 12),
            bg="#16213e",
            fg="#a8dadc"
        )
        self.time_label.pack(side=tk.RIGHT, padx=20)
        self.update_time()

        # Sidebar
        self.sidebar_frame = tk.Frame(self, bg="#0f3460", width=200)
        self.sidebar_frame.pack(fill=tk.Y, side=tk.LEFT)
        self.sidebar_frame.pack_propagate(False)

        nav_buttons = [
            ("🏠 Dashboard", self.show_dashboard),
            ("👤 Employees", self.show_employees),
            ("🏭 Suppliers", self.show_suppliers),
            ("📦 Products", self.show_products),
            ("📂 Categories", self.show_categories),
            ("🧾 Billing", self.show_billing),
            ("📋 Bills", self.show_bills),
        ]

        tk.Label(
            self.sidebar_frame,
            text="Navigation",
            font=("Arial", 13, "bold"),
            bg="#0f3460",
            fg="#e94560"
        ).pack(pady=(20, 10))

        for text, command in nav_buttons:
            btn = tk.Button(
                self.sidebar_frame,
                text=text,
                font=("Arial", 11),
                bg="#16213e",
                fg="white",
                activebackground="#e94560",
                activeforeground="white",
                relief=tk.FLAT,
                cursor="hand2",
                command=command,
                width=20,
                pady=8
            )
            btn.pack(pady=3, padx=10)

        # Main Content Area
        self.content_frame = tk.Frame(self, bg="#1a1a2e")
        self.content_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

    def update_time(self):
        now = datetime.now().strftime("%A, %d %B %Y  |  %H:%M:%S")
        self.time_label.config(text=now)
        self.after(1000, self.update_time)

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_dashboard(self):
        self.clear_content()
        DashboardFrame(self.content_frame)

    def show_employees(self):
        self.clear_content()
        EmployeeFrame(self.content_frame)

    def show_suppliers(self):
        self.clear_content()
        SupplierFrame(self.content_frame)

    def show_products(self):
        self.clear_content()
        ProductFrame(self.content_frame)

    def show_categories(self):
        self.clear_content()
        CategoryFrame(self.content_frame)

    def show_billing(self):
        self.clear_content()
        BillingFrame(self.content_frame)

    def show_bills(self):
        self.clear_content()
        BillsFrame(self.content_frame)


# Dashboard Frame
class DashboardFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.pack(fill=tk.BOTH, expand=True)
        self.create_widgets()

    def create_widgets(self):
        tk.Label(
            self,
            text="Dashboard Overview",
            font=("Arial", 20, "bold"),
            bg="#1a1a2e",
            fg="#e94560"
        ).pack(pady=20)

        stats_frame = tk.Frame(self, bg="#1a1a2e")
        stats_frame.pack(fill=tk.X, padx=20, pady=10)

        stats = self.get_stats()
        cards = [
            ("👤 Employees", stats['employees'], "#e94560"),
            ("🏭 Suppliers", stats['suppliers'], "#0f3460"),
            ("📦 Products", stats['products'], "#16213e"),
            ("📂 Categories", stats['categories'], "#533483"),
            ("🧾 Bills", stats['bills'], "#e94560"),
        ]

        for i, (title, count, color) in enumerate(cards):
            card = tk.Frame(stats_frame, bg=color, width=200, height=120, relief=tk.RAISED, bd=2)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            card.pack_propagate(False)
            stats_frame.columnconfigure(i, weight=1)

            tk.Label(card, text=title, font=("Arial", 13, "bold"), bg=color, fg="white").pack(pady=(20, 5))
            tk.Label(card, text=str(count), font=("Arial", 24, "bold"), bg=color, fg="white").pack()

        # Recent Bills
        recent_frame = tk.LabelFrame(
            self,
            text="Recent Bills",
            font=("Arial", 13, "bold"),
            bg="#1a1a2e",
            fg="#a8dadc",
            bd=2
        )
        recent_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        columns = ("Invoice No", "Customer", "Date", "Net Amount")
        tree = ttk.Treeview(recent_frame, columns=columns, show="headings", height=8)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor=tk.CENTER)

        style = ttk.Style()
        style.configure("Treeview", background="#16213e", foreground="white", fieldbackground="#16213e", rowheight=28)
        style.configure("Treeview.Heading", background="#0f3460", foreground="white", font=("Arial", 10, "bold"))

        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT invoice_no, customer_name, bill_date, net_amount FROM bills ORDER BY id DESC LIMIT 10")
        for row in cursor.fetchall():
            tree.insert("", tk.END, values=row)
        conn.close()

        scrollbar = ttk.Scrollbar(recent_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def get_stats(self):
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        stats = {}
        for table in ['employees', 'suppliers', 'products', 'categories', 'bills']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        conn.close()
        return stats


# Employee Frame
class EmployeeFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.pack(fill=tk.BOTH, expand=True)
        self.photo_path = tk.StringVar()
        self.photo_label = None
        self.selected_id = None
        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        tk.Label(self, text="Employee Management", font=("Arial", 18, "bold"), bg="#1a1a2e", fg="#e94560").pack(pady=10)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10)

        # Form
        form_frame = tk.LabelFrame(main, text="Employee Details", font=("Arial", 11, "bold"),
                                   bg="#16213e", fg="#a8dadc", bd=2)
        form_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        fields = [
            ("Employee ID", "emp_id"),
            ("Name", "name"),
            ("Age", "age"),
            ("Gender", "gender"),
            ("Date of Birth", "dob"),
            ("Email", "email"),
            ("Phone", "phone"),
            ("Address", "address"),
            ("Department", "department"),
            ("Designation", "designation"),
            ("Salary", "salary"),
            ("Join Date", "join_date"),
        ]

        self.vars = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label + ":", font=("Arial", 10), bg="#16213e", fg="white").grid(
                row=i, column=0, sticky="w", padx=10, pady=3)
            if key == "gender":
                var = tk.StringVar(value="Male")
                combo = ttk.Combobox(form_frame, textvariable=var, values=["Male", "Female", "Other"], width=20)
                combo.grid(row=i, column=1, padx=10, pady=3, sticky="w")
                self.vars[key] = var
            else:
                var = tk.StringVar()
                entry = tk.Entry(form_frame, textvariable=var, font=("Arial", 10), bg="#0f3460", fg="white",
                                 insertbackground="white", width=22)
                entry.grid(row=i, column=1, padx=10, pady=3, sticky="w")
                self.vars[key] = var

        # Photo
        photo_frame = tk.Frame(form_frame, bg="#16213e")
        photo_frame.grid(row=len(fields), column=0, columnspan=2, pady=5)

        self.photo_label = tk.Label(photo_frame, text="No Photo", bg="#0f3460", fg="white", width=15, height=7)
        self.photo_label.pack(side=tk.LEFT, padx=5)

        tk.Button(photo_frame, text="Browse Photo", command=self.browse_photo,
                  bg="#e94560", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)

        # Buttons
        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=len(fields) + 1, column=0, columnspan=2, pady=10)

        for text, cmd, color in [
            ("Add", self.add_employee, "#28a745"),
            ("Update", self.update_employee, "#ffc107"),
            ("Delete", self.delete_employee, "#dc3545"),
            ("Clear", self.clear_form, "#6c757d"),
        ]:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)

        # Table
        table_frame = tk.LabelFrame(main, text="Employee List", font=("Arial", 11, "bold"),
                                    bg="#16213e", fg="#a8dadc", bd=2)
        table_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Search
        search_frame = tk.Frame(table_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, bg="#0f3460", fg="white",
                 insertbackground="white", width=25).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Emp ID", "Name", "Department", "Designation", "Phone", "Salary")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor=tk.CENTER)

        style = ttk.Style()
        style.configure("Treeview", background="#16213e", foreground="white",
                        fieldbackground="#16213e", rowheight=25)
        style.configure("Treeview.Heading", background="#0f3460", foreground="white",
                        font=("Arial", 9, "bold"))

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<ButtonRelease-1>", self.select_row)

    def browse_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if path:
            self.photo_path.set(path)
            img = Image.open(path).resize((100, 80))
            photo = ImageTk.PhotoImage(img)
            self.photo_label.config(image=photo, text="")
            self.photo_label.image = photo

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, emp_id, name, department, designation, phone, salary FROM employees")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, emp_id, name, department, designation, phone, salary FROM employees")
        for row in cursor.fetchall():
            if any(query in str(val).lower() for val in row):
                self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_row(self, event):
        selected = self.tree.focus()
        if not selected:
            return
        values = self.tree.item(selected, 'values')
        if not values:
            return
        self.selected_id = values[0]
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE id=?", (self.selected_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            keys = ["emp_id", "name", "age", "gender", "dob", "email", "phone",
                    "address", "department", "designation", "salary", "join_date"]
            for i, key in enumerate(keys):
                self.vars[key].set(row[i + 1])
            if row[14]:
                self.photo_path.set(row[14])
                try:
                    img = Image.open(row[14]).resize((100, 80))
                    photo = ImageTk.PhotoImage(img)
                    self.photo_label.config(image=photo, text="")
                    self.photo_label.image = photo
                except:
                    pass

    def add_employee(self):
        data = {k: v.get() for k, v in self.vars.items()}
        if not data['emp_id'] or not data['name']:
            messagebox.showerror("Error", "Employee ID and Name are required!")
            return
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO employees (emp_id, name, age, gender, dob, email, phone,
                address, department, designation, salary, join_date, photo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (data['emp_id'], data['name'], data['age'], data['gender'], data['dob'],
                            data['email'], data['phone'], data['address'], data['department'],
                            data['designation'], data['salary'], data['join_date'], self.photo_path.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee added successfully!")
            self.load_data()
            self.clear_form()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Employee ID already exists!")

    def update_employee(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select an employee to update!")
            return
        data = {k: v.get() for k, v in self.vars.items()}
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE employees SET emp_id=?, name=?, age=?, gender=?, dob=?, email=?,
            phone=?, address=?, department=?, designation=?, salary=?, join_date=?, photo=?
            WHERE id=?''',
                       (data['emp_id'], data['name'], data['age'], data['gender'], data['dob'],
                        data['email'], data['phone'], data['address'], data['department'],
                        data['designation'], data['salary'], data['join_date'],
                        self.photo_path.get(), self.selected_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Employee updated successfully!")
        self.load_data()
        self.clear_form()

    def delete_employee(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select an employee to delete!")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this employee?"):
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM employees WHERE id=?", (self.selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee deleted successfully!")
            self.load_data()
            self.clear_form()

    def clear_form(self):
        for var in self.vars.values():
            var.set("")
        self.photo_path.set("")
        self.photo_label.config(image="", text="No Photo")
        self.photo_label.image = None
        self.selected_id = None


# Supplier Frame
class SupplierFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.pack(fill=tk.BOTH, expand=True)
        self.selected_id = None
        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        tk.Label(self, text="Supplier Management", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(pady=10)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        form_frame = tk.LabelFrame(main, text="Supplier Details", font=("Arial", 11, "bold"),
                                   bg="#16213e", fg="#a8dadc", bd=2)
        form_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        fields = [
            ("Supplier ID", "supplier_id"),
            ("Name", "name"),
            ("Contact Person", "contact"),
            ("Email", "email"),
            ("Phone", "phone"),
            ("Address", "address"),
            ("Company", "company"),
            ("Product Type", "product_type"),
        ]

        self.vars = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label + ":", font=("Arial", 10), bg="#16213e", fg="white").grid(
                row=i, column=0, sticky="w", padx=10, pady=5)
            var = tk.StringVar()
            tk.Entry(form_frame, textvariable=var, font=("Arial", 10), bg="#0f3460", fg="white",
                     insertbackground="white", width=25).grid(row=i, column=1, padx=10, pady=5, sticky="w")
            self.vars[key] = var

        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=15)

        for text, cmd, color in [
            ("Add", self.add_supplier, "#28a745"),
            ("Update", self.update_supplier, "#ffc107"),
            ("Delete", self.delete_supplier, "#dc3545"),
            ("Clear", self.clear_form, "#6c757d"),
        ]:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)

        table_frame = tk.LabelFrame(main, text="Supplier List", font=("Arial", 11, "bold"),
                                    bg="#16213e", fg="#a8dadc", bd=2)
        table_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        search_frame = tk.Frame(table_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, bg="#0f3460", fg="white",
                 insertbackground="white", width=25).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Supplier ID", "Name", "Company", "Phone", "Email", "Product Type")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=22)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<ButtonRelease-1>", self.select_row)

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, supplier_id, name, company, phone, email, product_type FROM suppliers")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, supplier_id, name, company, phone, email, product_type FROM suppliers")
        for row in cursor.fetchall():
            if any(query in str(val).lower() for val in row):
                self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_row(self, event):
        selected = self.tree.focus()
        if not selected:
            return
        values = self.tree.item(selected, 'values')
        if not values:
            return
        self.selected_id = values[0]
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM suppliers WHERE id=?", (self.selected_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            keys = ["supplier_id", "name", "contact", "email", "phone", "address", "company", "product_type"]
            for i, key in enumerate(keys):
                self.vars[key].set(row[i + 1])

    def add_supplier(self):
        data = {k: v.get() for k, v in self.vars.items()}
        if not data['supplier_id'] or not data['name']:
            messagebox.showerror("Error", "Supplier ID and Name are required!")
            return
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO suppliers (supplier_id, name, contact, email, phone, address, company, product_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                           (data['supplier_id'], data['name'], data['contact'], data['email'],
                            data['phone'], data['address'], data['company'], data['product_type']))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier added successfully!")
            self.load_data()
            self.clear_form()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Supplier ID already exists!")

    def update_supplier(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a supplier to update!")
            return
        data = {k: v.get() for k, v in self.vars.items()}
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE suppliers SET supplier_id=?, name=?, contact=?, email=?, phone=?,
            address=?, company=?, product_type=? WHERE id=?''',
                       (data['supplier_id'], data['name'], data['contact'], data['email'],
                        data['phone'], data['address'], data['company'], data['product_type'],
                        self.selected_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Supplier updated successfully!")
        self.load_data()
        self.clear_form()

    def delete_supplier(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a supplier to delete!")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this supplier?"):
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM suppliers WHERE id=?", (self.selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier deleted successfully!")
            self.load_data()
            self.clear_form()

    def clear_form(self):
        for var in self.vars.values():
            var.set("")
        self.selected_id = None


# Category Frame
class CategoryFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.pack(fill=tk.BOTH, expand=True)
        self.selected_id = None
        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        tk.Label(self, text="Category Management", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(pady=10)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        form_frame = tk.LabelFrame(main, text="Category Details", font=("Arial", 11, "bold"),
                                   bg="#16213e", fg="#a8dadc", bd=2)
        form_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        fields = [
            ("Category ID", "category_id"),
            ("Name", "name"),
            ("Description", "description"),
        ]

        self.vars = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label + ":", font=("Arial", 10), bg="#16213e", fg="white").grid(
                row=i, column=0, sticky="w", padx=10, pady=10)
            var = tk.StringVar()
            tk.Entry(form_frame, textvariable=var, font=("Arial", 10), bg="#0f3460", fg="white",
                     insertbackground="white", width=25).grid(row=i, column=1, padx=10, pady=10, sticky="w")
            self.vars[key] = var

        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=20)

        for text, cmd, color in [
            ("Add", self.add_category, "#28a745"),
            ("Update", self.update_category, "#ffc107"),
            ("Delete", self.delete_category, "#dc3545"),
            ("Clear", self.clear_form, "#6c757d"),
        ]:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)

        table_frame = tk.LabelFrame(main, text="Category List", font=("Arial", 11, "bold"),
                                    bg="#16213e", fg="#a8dadc", bd=2)
        table_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        search_frame = tk.Frame(table_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, bg="#0f3460", fg="white",
                 insertbackground="white", width=25).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Category ID", "Name", "Description")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=22)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<ButtonRelease-1>", self.select_row)

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, category_id, name, description FROM categories")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, category_id, name, description FROM categories")
        for row in cursor.fetchall():
            if any(query in str(val).lower() for val in row):
                self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_row(self, event):
        selected = self.tree.focus()
        if not selected:
            return
        values = self.tree.item(selected, 'values')
        if not values:
            return
        self.selected_id = values[0]
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE id=?", (self.selected_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            keys = ["category_id", "name", "description"]
            for i, key in enumerate(keys):
                self.vars[key].set(row[i + 1])

    def add_category(self):
        data = {k: v.get() for k, v in self.vars.items()}
        if not data['category_id'] or not data['name']:
            messagebox.showerror("Error", "Category ID and Name are required!")
            return
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO categories (category_id, name, description) VALUES (?, ?, ?)",
                           (data['category_id'], data['name'], data['description']))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category added successfully!")
            self.load_data()
            self.clear_form()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Category ID already exists!")

    def update_category(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a category to update!")
            return
        data = {k: v.get() for k, v in self.vars.items()}
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE categories SET category_id=?, name=?, description=? WHERE id=?",
                       (data['category_id'], data['name'], data['description'], self.selected_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Category updated successfully!")
        self.load_data()
        self.clear_form()

    def delete_category(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a category to delete!")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this category?"):
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM categories WHERE id=?", (self.selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category deleted successfully!")
            self.load_data()
            self.clear_form()

    def clear_form(self):
        for var in self.vars.values():
            var.set("")
        self.selected_id = None


# Product Frame
class ProductFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.pack(fill=tk.BOTH, expand=True)
        self.selected_id = None
        self.create_widgets()
        self.load_data()

    def get_categories(self):
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories")
        cats = [row[0] for row in cursor.fetchall()]
        conn.close()
        return cats if cats else ["General"]

    def get_suppliers(self):
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM suppliers")
        sups = [row[0] for row in cursor.fetchall()]
        conn.close()
        return sups if sups else ["Default"]

    def create_widgets(self):
        tk.Label(self, text="Product Management", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(pady=10)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        form_frame = tk.LabelFrame(main, text="Product Details", font=("Arial", 11, "bold"),
                                   bg="#16213e", fg="#a8dadc", bd=2)
        form_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.vars = {}

        fields_simple = [
            ("Product ID", "product_id"),
            ("Name", "name"),
            ("Price", "price"),
            ("Quantity", "quantity"),
            ("Description", "description"),
        ]

        row_idx = 0
        for label, key in fields_simple:
            tk.Label(form_frame, text=label + ":", font=("Arial", 10), bg="#16213e", fg="white").grid(
                row=row_idx, column=0, sticky="w", padx=10, pady=5)
            var = tk.StringVar()
            tk.Entry(form_frame, textvariable=var, font=("Arial", 10), bg="#0f3460", fg="white",
                     insertbackground="white", width=25).grid(row=row_idx, column=1, padx=10, pady=5, sticky="w")
            self.vars[key] = var
            row_idx += 1

        # Category dropdown
        tk.Label(form_frame, text="Category:", font=("Arial", 10), bg="#16213e", fg="white").grid(
            row=row_idx, column=0, sticky="w", padx=10, pady=5)
        self.vars['category'] = tk.StringVar()
        self.cat_combo = ttk.Combobox(form_frame, textvariable=self.vars['category'],
                                      values=self.get_categories(), width=22)
        self.cat_combo.grid(row=row_idx, column=1, padx=10, pady=5, sticky="w")
        row_idx += 1

        # Supplier dropdown
        tk.Label(form_frame, text="Supplier:", font=("Arial", 10), bg="#16213e", fg="white").grid(
            row=row_idx, column=0, sticky="w", padx=10, pady=5)
        self.vars['supplier'] = tk.StringVar()
        self.sup_combo = ttk.Combobox(form_frame, textvariable=self.vars['supplier'],
                                      values=self.get_suppliers(), width=22)
        self.sup_combo.grid(row=row_idx, column=1, padx=10, pady=5, sticky="w")
        row_idx += 1

        # Status dropdown
        tk.Label(form_frame, text="Status:", font=("Arial", 10), bg="#16213e", fg="white").grid(
            row=row_idx, column=0, sticky="w", padx=10, pady=5)
        self.vars['status'] = tk.StringVar(value="Available")
        ttk.Combobox(form_frame, textvariable=self.vars['status'],
                     values=["Available", "Out of Stock", "Discontinued"], width=22).grid(
            row=row_idx, column=1, padx=10, pady=5, sticky="w")
        row_idx += 1

        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=row_idx, column=0, columnspan=2, pady=15)

        for text, cmd, color in [
            ("Add", self.add_product, "#28a745"),
            ("Update", self.update_product, "#ffc107"),
            ("Delete", self.delete_product, "#dc3545"),
            ("Clear", self.clear_form, "#6c757d"),
        ]:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)

        table_frame = tk.LabelFrame(main, text="Product List", font=("Arial", 11, "bold"),
                                    bg="#16213e", fg="#a8dadc", bd=2)
        table_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        search_frame = tk.Frame(table_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, bg="#0f3460", fg="white",
                 insertbackground="white", width=25).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Product ID", "Name", "Category", "Supplier", "Price", "Quantity", "Status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=22)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<ButtonRelease-1>", self.select_row)

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, product_id, name, category, supplier, price, quantity, status FROM products")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, product_id, name, category, supplier, price, quantity, status FROM products")
        for row in cursor.fetchall():
            if any(query in str(val).lower() for val in row):
                self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_row(self, event):
        selected = self.tree.focus()
        if not selected:
            return
        values = self.tree.item(selected, 'values')
        if not values:
            return
        self.selected_id = values[0]
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id=?", (self.selected_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            keys = ["product_id", "name", "category", "supplier", "price", "quantity", "description", "status"]
            for i, key in enumerate(keys):
                self.vars[key].set(row[i + 1])

    def add_product(self):
        data = {k: v.get() for k, v in self.vars.items()}
        if not data['product_id'] or not data['name']:
            messagebox.showerror("Error", "Product ID and Name are required!")
            return
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO products (product_id, name, category, supplier, price, quantity, description, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                           (data['product_id'], data['name'], data['category'], data['supplier'],
                            data['price'], data['quantity'], data['description'], data['status']))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product added successfully!")
            self.load_data()
            self.clear_form()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Product ID already exists!")

    def update_product(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a product to update!")
            return
        data = {k: v.get() for k, v in self.vars.items()}
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE products SET product_id=?, name=?, category=?, supplier=?, price=?,
            quantity=?, description=?, status=? WHERE id=?''',
                       (data['product_id'], data['name'], data['category'], data['supplier'],
                        data['price'], data['quantity'], data['description'], data['status'],
                        self.selected_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Product updated successfully!")
        self.load_data()
        self.clear_form()

    def delete_product(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a product to delete!")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this product?"):
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id=?", (self.selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product deleted successfully!")
            self.load_data()
            self.clear_form()

    def clear_form(self):
        for var in self.vars.values():
            var.set("")
        self.selected_id = None


# Billing Frame
class BillingFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.pack(fill=tk.BOTH, expand=True)
        self.cart_items = []
        self.create_widgets()

    def get_products(self):
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, name, price FROM products WHERE status='Available'")
        products = cursor.fetchall()
        conn.close()
        return products

    def generate_invoice(self):
        return "INV-" + ''.join(random.choices(string.digits, k=8))

    def create_widgets(self):
        tk.Label(self, text="Billing / Invoice", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(pady=10)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        # Left - Customer & Product Selection
        left_frame = tk.Frame(main, bg="#1a1a2e")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Customer Info
        cust_frame = tk.LabelFrame(left_frame, text="Customer Information", font=("Arial", 11, "bold"),
                                   bg="#16213e", fg="#a8dadc", bd=2)
        cust_frame.pack(fill=tk.X, pady=5)

        self.invoice_var = tk.StringVar(value=self.generate_invoice())
        cust_fields = [
            ("Invoice No", self.invoice_var),
            ("Customer Name", tk.StringVar()),
            ("Phone", tk.StringVar()),
            ("Email", tk.StringVar()),
        ]
        self.cust_vars = {}
        cust_keys = ["invoice_no", "customer_name", "customer_phone", "customer_email"]
        for i, ((label, var), key) in enumerate(zip(cust_fields, cust_keys)):
            tk.Label(cust_frame, text=label + ":", font=("Arial", 10), bg="#16213e", fg="white").grid(
                row=i, column=0, sticky="w", padx=10, pady=4)
            entry = tk.Entry(cust_frame, textvariable=var, font=("Arial", 10), bg="#0f3460", fg="white",
                             insertbackground="white", width=25)
            entry.grid(row=i, column=1, padx=10, pady=4, sticky="w")
            self.cust_vars[key] = var

        # Product Selection
        prod_frame = tk.LabelFrame(left_frame, text="Add Product", font=("Arial", 11, "bold"),
                                   bg="#16213e", fg="#a8dadc", bd=2)
        prod_frame.pack(fill=tk.X, pady=5)

        products = self.get_products()
        product_names = [f"{p[0]} - {p[1]}" for p in products]
        self.product_data = {f"{p[0]} - {p[1]}": p[2] for p in products}

        tk.Label(prod_frame, text="Product:", font=("Arial", 10), bg="#16213e", fg="white").grid(
            row=0, column=0, sticky="w", padx=10, pady=5)
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(prod_frame, textvariable=self.product_var,
                                          values=product_names, width=28)
        self.product_combo.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.product_combo.bind("<<ComboboxSelected>>", self.on_product_select)

        tk.Label(prod_frame, text="Price:", font=("Arial", 10), bg="#16213e", fg="white").grid(
            row=1, column=0, sticky="w", padx=10, pady=5)
        self.price_var = tk.StringVar()
        tk.Entry(prod_frame, textvariable=self.price_var, font=("Arial", 10), bg="#0f3460", fg="white",
                 insertbackground="white", width=15, state="readonly").grid(row=1, column=1, padx=10, pady=5, sticky="w")

        tk.Label(prod_frame, text="Quantity:", font=("Arial", 10), bg="#16213e", fg="white").grid(
            row=2, column=0, sticky="w", padx=10, pady=5)
        self.qty_var = tk.StringVar(value="1")
        tk.Entry(prod_frame, textvariable=self.qty_var, font=("Arial", 10), bg="#0f3460", fg="white",
                 insertbackground="white", width=15).grid(row=2, column=1, padx=10, pady=5, sticky="w")

        tk.Button(prod_frame, text="Add to Cart", command=self.add_to_cart,
                  bg="#28a745", fg="white", font=("Arial", 10, "bold"), width=15).grid(
            row=3, column=0, columnspan=2, pady=10)

        # Discount & Tax
        calc_frame = tk.LabelFrame(left_frame, text="Discount & Tax", font=("Arial", 11, "bold"),
                                   bg="#16213e", fg="#a8dadc", bd=2)
        calc_frame.pack(fill=tk.X, pady=5)

        tk.Label(calc_frame, text="Discount (%):", font=("Arial", 10), bg="#16213e", fg="white").grid(
            row=0, column=0, sticky="w", padx=10, pady=5)
        self.discount_var = tk.StringVar(value="0")
        tk.Entry(calc_frame, textvariable=self.discount_var, font=("Arial", 10), bg="#0f3460", fg="white",
                 insertbackground="white", width=15).grid(row=0, column=1, padx=10, pady=5, sticky="w")

        tk.Label(calc_frame, text="Tax (%):", font=("Arial", 10), bg="#16213e", fg="white").grid(
            row=1, column=0, sticky="w", padx=10, pady=5)
        self.tax_var = tk.StringVar(value="0")
        tk.Entry(calc_frame, textvariable=self.tax_var, font=("Arial", 10), bg="#0f3460", fg="white",
                 insertbackground="white", width=15).grid(row=1, column=1, padx=10, pady=5, sticky="w")

        tk.Button(calc_frame, text="Calculate", command=self.calculate_total,
                  bg="#0f3460", fg="white", font=("Arial", 10, "bold"), width=12).grid(
            row=2, column=0, columnspan=2, pady=8)

        # Right - Bill Preview
        right_frame = tk.LabelFrame(main, text="Bill Preview", font=("Arial", 11, "bold"),
                                    bg="#16213e", fg="#a8dadc", bd=2)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Cart Table
        cart_columns = ("Product", "Price", "Qty", "Total")
        self.cart_tree = ttk.Treeview(right_frame, columns=cart_columns, show="headings", height=12)
        for col in cart_columns:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=130, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.cart_tree.pack(fill=tk.X, padx=5, pady=5)

        # Remove from cart
        tk.Button(right_frame, text="Remove Selected", command=self.remove_from_cart,
                  bg="#dc3545", fg="white", font=("Arial", 9)).pack(pady=3)

        # Totals
        totals_frame = tk.Frame(right_frame, bg="#16213e")
        totals_frame.pack(fill=tk.X, padx=10, pady=5)

        self.total_label = tk.Label(totals_frame, text="Subtotal: $0.00", font=("Arial", 11),
                                    bg="#16213e", fg="white")
        self.total_label.pack(anchor="e")
        self.discount_label = tk.Label(totals_frame, text="Discount: $0.00", font=("Arial", 11),
                                       bg="#16213e", fg="#ffc107")
        self.discount_label.pack(anchor="e")
        self.tax_label = tk.Label(totals_frame, text="Tax: $0.00", font=("Arial", 11),
                                  bg="#16213e", fg="#a8dadc")
        self.tax_label.pack(anchor="e")
        self.net_label = tk.Label(totals_frame, text="Net Amount: $0.00", font=("Arial", 14, "bold"),
                                  bg="#16213e", fg="#e94560")
        self.net_label.pack(anchor="e")

        # Bill Text
        self.bill_text = tk.Text(right_frame, height=8, bg="#0f3460", fg="white",
                                 font=("Courier", 9), state=tk.DISABLED)
        self.bill_text.pack(fill=tk.X, padx=5, pady=5)

        # Action Buttons
        action_frame = tk.Frame(right_frame, bg="#16213e")
        action_frame.pack(pady=10)

        for text, cmd, color in [
            ("Generate Bill", self.generate_bill, "#28a745"),
            ("Print Bill", self.print_bill, "#0f3460"),
            ("Clear All", self.clear_all, "#dc3545"),
        ]:
            tk.Button(action_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 10, "bold"), width=12).pack(side=tk.LEFT, padx=5)

    def on_product_select(self, event):
        selected = self.product_var.get()
        if selected in self.product_data:
            self.price_var.set(str(self.product_data[selected]))

    def add_to_cart(self):
        product = self.product_var.get()
        if not product:
            messagebox.showerror("Error", "Please select a product!")
            return
        try:
            qty = int(self.qty_var.get())
            price = float(self.price_var.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity or price!")
            return
        total = price * qty
        self.cart_items.append((product, price, qty, total))
        self.cart_tree.insert("", tk.END, values=(product, f"${price:.2f}", qty, f"${total:.2f}"))
        self.calculate_total()

    def remove_from_cart(self):
        selected = self.cart_tree.focus()
        if not selected:
            return
        idx = self.cart_tree.index(selected)
        self.cart_tree.delete(selected)
        if 0 <= idx < len(self.cart_items):
            self.cart_items.pop(idx)
        self.calculate_total()

    def calculate_total(self):
        subtotal = sum(item[3] for item in self.cart_items)
        try:
            discount_pct = float(self.discount_var.get())
            tax_pct = float(self.tax_var.get())
        except ValueError:
            discount_pct = 0
            tax_pct = 0
        discount_amt = subtotal * discount_pct / 100
        tax_amt = (subtotal - discount_amt) * tax_pct / 100
        net = subtotal - discount_amt + tax_amt

        self.total_label.config(text=f"Subtotal: ${subtotal:.2f}")
        self.discount_label.config(text=f"Discount ({discount_pct}%): -${discount_amt:.2f}")
        self.tax_label.config(text=f"Tax ({tax_pct}%): +${tax_amt:.2f}")
        self.net_label.config(text=f"Net Amount: ${net:.2f}")

        self._subtotal = subtotal
        self._discount_amt = discount_amt
        self._tax_amt = tax_amt
        self._net = net

    def generate_bill(self):
        if not self.cart_items:
            messagebox.showerror("Error", "Cart is empty!")
            return
        self.calculate_total()
        invoice = self.cust_vars['invoice_no'].get()
        cust_name = self.cust_vars['customer_name'].get() or "Walk-in Customer"
        cust_phone = self.cust_vars['customer_phone'].get()
        cust_email = self.cust_vars['customer_email'].get()
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        bill_details = "\n".join([f"{item[0]} x{item[2]} @ ${item[1]:.2f} = ${item[3]:.2f}"
                                  for item in self.cart_items])

        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO bills (invoice_no, customer_name, customer_phone, customer_email,
                bill_date, total_amount, tax, discount, net_amount, bill_details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (invoice, cust_name, cust_phone, cust_email, date,
                            self._subtotal, self._tax_amt, self._discount_amt,
                            self._net, bill_details))
            conn.commit()
            conn.close()

            # Show bill in text area
            bill_text = f"""
{'='*50}
        INVENTORY MANAGEMENT SYSTEM
              INVOICE / BILL
{'='*50}
Invoice No : {invoice}
Date       : {date}
Customer   : {cust_name}
Phone      : {cust_phone}
Email      : {cust_email}
{'='*50}
{'Product':<30} {'Qty':>5} {'Price':>8} {'Total':>8}
{'-'*50}
"""
            for item in self.cart_items:
                bill_text += f"{item[0][:28]:<30} {item[2]:>5} {item[1]:>8.2f} {item[3]:>8.2f}\n"

            bill_text += f"""
{'-'*50}
{'Subtotal':>40} : ${self._subtotal:.2f}
{'Discount':>40} : -${self._discount_amt:.2f}
{'Tax':>40} : +${self._tax_amt:.2f}
{'NET AMOUNT':>40} : ${self._net:.2f}
{'='*50}
        Thank you for your purchase!
{'='*50}
"""
            self.bill_text.config(state=tk.NORMAL)
            self.bill_text.delete(1.0, tk.END)
            self.bill_text.insert(tk.END, bill_text)
            self.bill_text.config(state=tk.DISABLED)
            self._bill_text_content = bill_text

            messagebox.showinfo("Success", f"Bill generated successfully!\nInvoice: {invoice}")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Invoice number already exists! Please generate a new one.")

    def print_bill(self):
        if not hasattr(self, '_bill_text_content'):
            messagebox.showerror("Error", "Please generate a bill first!")
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile=f"Bill_{self.cust_vars['invoice_no'].get()}.txt"
        )
        if save_path:
            with open(save_path, 'w') as f:
                f.write(self._bill_text_content)
            messagebox.showinfo("Success", f"Bill saved to {save_path}")

    def clear_all(self):
        self.cart_items.clear()
        self.cart_tree.delete(*self.cart_tree.get_children())
        for var in self.cust_vars.values():
            var.set("")
        self.cust_vars['invoice_no'].set(self.generate_invoice())
        self.product_var.set("")
        self.price_var.set("")
        self.qty_var.set("1")
        self.discount_var.set("0")
        self.tax_var.set("0")
        self.total_label.config(text="Subtotal: $0.00")
        self.discount_label.config(text="Discount: $0.00")
        self.tax_label.config(text="Tax: $0.00")
        self.net_label.config(text="Net Amount: $0.00")
        self.bill_text.config(state=tk.NORMAL)
        self.bill_text.delete(1.0, tk.END)
        self.bill_text.config(state=tk.DISABLED)
        if hasattr(self, '_bill_text_content'):
            del self._bill_text_content


# Bills Frame
class BillsFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.pack(fill=tk.BOTH, expand=True)
        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        tk.Label(self, text="Bills / Invoices", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(pady=10)

        # Search
        search_frame = tk.Frame(self, bg="#1a1a2e")
        search_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(search_frame, text="Search:", bg="#1a1a2e", fg="white", font=("Arial", 11)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, bg="#0f3460", fg="white",
                 insertbackground="white", width=30, font=("Arial", 11)).pack(side=tk.LEFT, padx=10)

        tk.Button(search_frame, text="Delete Selected", command=self.delete_bill,
                  bg="#dc3545", fg="white", font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=5)
        tk.Button(search_frame, text="View Details", command=self.view_details,
                  bg="#0f3460", fg="white", font=("Arial", 10, "bold")).pack(side=tk.RIGHT, padx=5)

        # Table
        table_frame = tk.LabelFrame(self, text="All Bills", font=("Arial", 11, "bold"),
                                    bg="#16213e", fg="#a8dadc", bd=2)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        columns = ("ID", "Invoice No", "Customer", "Phone", "Date", "Subtotal", "Tax", "Discount", "Net Amount")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=18)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<Double-1>", lambda e: self.view_details())

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT id, invoice_no, customer_name, customer_phone, bill_date,
            total_amount, tax, discount, net_amount FROM bills ORDER BY id DESC''')
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT id, invoice_no, customer_name, customer_phone, bill_date,
            total_amount, tax, discount, net_amount FROM bills ORDER BY id DESC''')
        for row in cursor.fetchall():
            if any(query in str(val).lower() for val in row):
                self.tree.insert("", tk.END, values=row)
        conn.close()

    def view_details(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showerror("Error", "Please select a bill to view!")
            return
        values = self.tree.item(selected, 'values')
        bill_id = values[0]

        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bills WHERE id=?", (bill_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            detail_win = tk.Toplevel(self)
            detail_win.title(f"Bill Details - {row[1]}")
            detail_win.geometry("600x500")
            detail_win.configure(bg="#1a1a2e")

            tk.Label(detail_win, text="Bill Details", font=("Arial", 16, "bold"),
                     bg="#1a1a2e", fg="#e94560").pack(pady=10)

            text = tk.Text(detail_win, bg="#0f3460", fg="white", font=("Courier", 10))
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            bill_info = f"""
{'='*55}
           INVENTORY MANAGEMENT SYSTEM
                 INVOICE / BILL
{'='*55}
Invoice No    : {row[1]}
Customer      : {row[2]}
Phone         : {row[3]}
Email         : {row[4]}
Date          : {row[5]}
{'='*55}
ITEMS:
{row[10]}
{'='*55}
Subtotal      : ${row[6]:.2f}
Tax           : ${row[7]:.2f}
Discount      : ${row[8]:.2f}
NET AMOUNT    : ${row[9]:.2f}
{'='*55}
"""
            text.insert(tk.END, bill_info)
            text.config(state=tk.DISABLED)

            tk.Button(detail_win, text="Close", command=detail_win.destroy,
                      bg="#dc3545", fg="white", font=("Arial", 10, "bold")).pack(pady=5)

    def delete_bill(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showerror("Error", "Please select a bill to delete!")
            return
        values = self.tree.item(selected, 'values')
        if messagebox.askyesno("Confirm", f"Delete bill {values[1]}?"):
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bills WHERE id=?", (values[0],))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Bill deleted successfully!")
            self.load_data()


if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()