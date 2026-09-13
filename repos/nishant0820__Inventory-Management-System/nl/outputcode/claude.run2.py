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
            position TEXT,
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
            category_id TEXT,
            supplier_id TEXT,
            price REAL,
            quantity INTEGER,
            description TEXT,
            photo TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(category_id),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            customer_name TEXT,
            customer_phone TEXT,
            customer_email TEXT,
            total_amount REAL,
            bill_date TEXT,
            bill_details TEXT
        )
    """)

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
        self.sidebar_buttons = {}

        self.setup_ui()
        self.show_dashboard()
        self.update_time()

    def setup_ui(self):
        # Header
        self.header_frame = tk.Frame(self, bg="#16213e", height=70)
        self.header_frame.pack(side=tk.TOP, fill=tk.X)
        self.header_frame.pack_propagate(False)

        tk.Label(
            self.header_frame,
            text="📦 Inventory Management System",
            font=("Arial", 22, "bold"),
            bg="#16213e",
            fg="#e94560"
        ).pack(side=tk.LEFT, padx=20, pady=15)

        self.time_label = tk.Label(
            self.header_frame,
            text="",
            font=("Arial", 13),
            bg="#16213e",
            fg="#a8dadc"
        )
        self.time_label.pack(side=tk.RIGHT, padx=20, pady=15)

        # Main container
        self.main_container = tk.Frame(self, bg="#1a1a2e")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Sidebar
        self.sidebar = tk.Frame(self.main_container, bg="#16213e", width=220)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        tk.Label(
            self.sidebar,
            text="MENU",
            font=("Arial", 12, "bold"),
            bg="#16213e",
            fg="#e94560"
        ).pack(pady=(20, 10))

        menu_items = [
            ("🏠 Dashboard", self.show_dashboard),
            ("👤 Employees", self.show_employees),
            ("🏭 Suppliers", self.show_suppliers),
            ("📦 Products", self.show_products),
            ("🗂️ Categories", self.show_categories),
            ("🧾 Billing", self.show_billing),
            ("📋 Bills", self.show_bills),
        ]

        for text, command in menu_items:
            btn = tk.Button(
                self.sidebar,
                text=text,
                font=("Arial", 12),
                bg="#0f3460",
                fg="white",
                bd=0,
                padx=10,
                pady=12,
                anchor="w",
                width=20,
                cursor="hand2",
                command=command
            )
            btn.pack(fill=tk.X, padx=10, pady=3)
            self.sidebar_buttons[text] = btn

        # Content area
        self.content_area = tk.Frame(self.main_container, bg="#1a1a2e")
        self.content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def update_time(self):
        now = datetime.now().strftime("%A, %d %B %Y  |  %H:%M:%S")
        self.time_label.config(text=now)
        self.after(1000, self.update_time)

    def clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    def show_dashboard(self):
        self.clear_content()
        DashboardFrame(self.content_area)

    def show_employees(self):
        self.clear_content()
        EmployeeFrame(self.content_area)

    def show_suppliers(self):
        self.clear_content()
        SupplierFrame(self.content_area)

    def show_products(self):
        self.clear_content()
        ProductFrame(self.content_area)

    def show_categories(self):
        self.clear_content()
        CategoryFrame(self.content_area)

    def show_billing(self):
        self.clear_content()
        BillingFrame(self.content_area)

    def show_bills(self):
        self.clear_content()
        BillsFrame(self.content_area)


# Dashboard Frame
class DashboardFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.pack(fill=tk.BOTH, expand=True)
        self.setup_ui()

    def setup_ui(self):
        tk.Label(
            self,
            text="Dashboard",
            font=("Arial", 20, "bold"),
            bg="#1a1a2e",
            fg="white"
        ).pack(pady=(20, 10))

        stats_frame = tk.Frame(self, bg="#1a1a2e")
        stats_frame.pack(fill=tk.X, padx=20, pady=10)

        stats = self.get_stats()
        colors = ["#e94560", "#0f3460", "#533483", "#2b9348"]
        icons = ["👤", "🏭", "📦", "🗂️"]
        labels = ["Employees", "Suppliers", "Products", "Categories"]

        for i, (label, icon, color, count) in enumerate(zip(labels, icons, colors, stats)):
            card = tk.Frame(stats_frame, bg=color, width=200, height=120)
            card.grid(row=0, column=i, padx=15, pady=10, sticky="nsew")
            card.pack_propagate(False)
            stats_frame.columnconfigure(i, weight=1)

            tk.Label(card, text=icon, font=("Arial", 30), bg=color, fg="white").pack(pady=(15, 5))
            tk.Label(card, text=str(count), font=("Arial", 22, "bold"), bg=color, fg="white").pack()
            tk.Label(card, text=label, font=("Arial", 12), bg=color, fg="white").pack()

        # Recent Bills
        recent_frame = tk.LabelFrame(
            self, text="Recent Bills", font=("Arial", 13, "bold"),
            bg="#1a1a2e", fg="#e94560", bd=2
        )
        recent_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        cols = ("Invoice No", "Customer", "Phone", "Total", "Date")
        tree = ttk.Treeview(recent_frame, columns=cols, show="headings", height=8)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=150, anchor="center")

        scrollbar = ttk.Scrollbar(recent_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT invoice_no, customer_name, customer_phone, total_amount, bill_date FROM bills ORDER BY id DESC LIMIT 10")
        for row in cursor.fetchall():
            tree.insert("", tk.END, values=row)
        conn.close()

    def get_stats(self):
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        counts = []
        for table in ["employees", "suppliers", "products", "categories"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            counts.append(cursor.fetchone()[0])
        conn.close()
        return counts


# Employee Frame
class EmployeeFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.pack(fill=tk.BOTH, expand=True)
        self.photo_path = tk.StringVar()
        self.photo_image = None
        self.selected_id = None
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        tk.Label(self, text="Employee Management", font=("Arial", 18, "bold"), bg="#1a1a2e", fg="white").pack(pady=(10, 5))

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Form
        form_frame = tk.LabelFrame(main, text="Employee Details", font=("Arial", 12, "bold"), bg="#16213e", fg="#e94560", bd=2)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=5)

        fields = [
            ("Employee ID", "emp_id"),
            ("Name", "name"),
            ("Email", "email"),
            ("Phone", "phone"),
            ("Address", "address"),
            ("Position", "position"),
            ("Salary", "salary"),
            ("Join Date (YYYY-MM-DD)", "join_date"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label + ":", font=("Arial", 10), bg="#16213e", fg="white").grid(row=i, column=0, padx=10, pady=5, sticky="w")
            entry = tk.Entry(form_frame, font=("Arial", 10), width=22, bg="#0f3460", fg="white", insertbackground="white")
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.entries[key] = entry

        # Photo
        tk.Label(form_frame, text="Photo:", font=("Arial", 10), bg="#16213e", fg="white").grid(row=len(fields), column=0, padx=10, pady=5, sticky="w")
        tk.Button(form_frame, text="Browse", command=self.browse_photo, bg="#0f3460", fg="white", font=("Arial", 9)).grid(row=len(fields), column=1, padx=10, pady=5, sticky="w")

        self.photo_label = tk.Label(form_frame, bg="#16213e", text="No Photo", fg="gray")
        self.photo_label.grid(row=len(fields)+1, column=0, columnspan=2, pady=5)

        # Buttons
        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=len(fields)+2, column=0, columnspan=2, pady=10)

        for text, cmd, color in [
            ("Add", self.add_employee, "#2b9348"),
            ("Update", self.update_employee, "#e9c46a"),
            ("Delete", self.delete_employee, "#e94560"),
            ("Clear", self.clear_form, "#533483"),
        ]:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white", font=("Arial", 10, "bold"), width=8, cursor="hand2").pack(side=tk.LEFT, padx=4)

        # Search
        right_frame = tk.Frame(main, bg="#1a1a2e")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        search_frame = tk.Frame(right_frame, bg="#1a1a2e")
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search:", bg="#1a1a2e", fg="white", font=("Arial", 11)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 11), bg="#0f3460", fg="white", insertbackground="white", width=30).pack(side=tk.LEFT, padx=5)

        # Table
        cols = ("ID", "Emp ID", "Name", "Email", "Phone", "Position", "Salary", "Join Date")
        self.tree = ttk.Treeview(right_frame, columns=cols, show="headings", height=20)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")
        self.tree.column("ID", width=40)

        vsb = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def browse_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if path:
            self.photo_path.set(path)
            img = Image.open(path).resize((80, 80))
            self.photo_image = ImageTk.PhotoImage(img)
            self.photo_label.config(image=self.photo_image, text="")

    def add_employee(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        if not data["emp_id"] or not data["name"]:
            messagebox.showerror("Error", "Employee ID and Name are required!")
            return
        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO employees (emp_id, name, email, phone, address, position, salary, join_date, photo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data["emp_id"], data["name"], data["email"], data["phone"],
                  data["address"], data["position"], data["salary"], data["join_date"], self.photo_path.get()))
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
        data = {k: v.get().strip() for k, v in self.entries.items()}
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE employees SET emp_id=?, name=?, email=?, phone=?, address=?, position=?, salary=?, join_date=?, photo=?
            WHERE id=?
        """, (data["emp_id"], data["name"], data["email"], data["phone"],
              data["address"], data["position"], data["salary"], data["join_date"], self.photo_path.get(), self.selected_id))
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
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.photo_path.set("")
        self.photo_label.config(image="", text="No Photo")
        self.photo_image = None
        self.selected_id = None

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, emp_id, name, email, phone, position, salary, join_date FROM employees")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get().strip()
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, emp_id, name, email, phone, position, salary, join_date FROM employees
            WHERE name LIKE ? OR emp_id LIKE ? OR phone LIKE ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])["values"]
        self.selected_id = values[0]
        keys = ["emp_id", "name", "email", "phone", "position", "salary", "join_date"]
        for i, key in enumerate(keys):
            self.entries[key].delete(0, tk.END)
            self.entries[key].insert(0, values[i+1] if values[i+1] else "")
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT address, photo FROM employees WHERE id=?", (self.selected_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            self.entries["address"].delete(0, tk.END)
            self.entries["address"].insert(0, row[0] if row[0] else "")
            if row[1] and os.path.exists(row[1]):
                self.photo_path.set(row[1])
                img = Image.open(row[1]).resize((80, 80))
                self.photo_image = ImageTk.PhotoImage(img)
                self.photo_label.config(image=self.photo_image, text="")


# Supplier Frame
class SupplierFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.pack(fill=tk.BOTH, expand=True)
        self.selected_id = None
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        tk.Label(self, text="Supplier Management", font=("Arial", 18, "bold"), bg="#1a1a2e", fg="white").pack(pady=(10, 5))

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        form_frame = tk.LabelFrame(main, text="Supplier Details", font=("Arial", 12, "bold"), bg="#16213e", fg="#e94560", bd=2)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=5)

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
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label + ":", font=("Arial", 10), bg="#16213e", fg="white").grid(row=i, column=0, padx=10, pady=5, sticky="w")
            entry = tk.Entry(form_frame, font=("Arial", 10), width=22, bg="#0f3460", fg="white", insertbackground="white")
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.entries[key] = entry

        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)

        for text, cmd, color in [
            ("Add", self.add_supplier, "#2b9348"),
            ("Update", self.update_supplier, "#e9c46a"),
            ("Delete", self.delete_supplier, "#e94560"),
            ("Clear", self.clear_form, "#533483"),
        ]:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white", font=("Arial", 10, "bold"), width=8, cursor="hand2").pack(side=tk.LEFT, padx=4)

        right_frame = tk.Frame(main, bg="#1a1a2e")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        search_frame = tk.Frame(right_frame, bg="#1a1a2e")
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search:", bg="#1a1a2e", fg="white", font=("Arial", 11)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 11), bg="#0f3460", fg="white", insertbackground="white", width=30).pack(side=tk.LEFT, padx=5)

        cols = ("ID", "Supplier ID", "Name", "Email", "Phone", "Company")
        self.tree = ttk.Treeview(right_frame, columns=cols, show="headings", height=20)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")
        self.tree.column("ID", width=40)

        vsb = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

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
        self.selected_id = None

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, supplier_id, name, email, phone, company FROM suppliers")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get().strip()
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, supplier_id, name, email, phone, company FROM suppliers
            WHERE name LIKE ? OR supplier_id LIKE ? OR company LIKE ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])["values"]
        self.selected_id = values[0]
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT supplier_id, name, email, phone, address, company, description FROM suppliers WHERE id=?", (self.selected_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            keys = ["supplier_id", "name", "email", "phone", "address", "company", "description"]
            for key, val in zip(keys, row):
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, val if val else "")


# Category Frame
class CategoryFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.pack(fill=tk.BOTH, expand=True)
        self.selected_id = None
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        tk.Label(self, text="Category Management", font=("Arial", 18, "bold"), bg="#1a1a2e", fg="white").pack(pady=(10, 5))

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        form_frame = tk.LabelFrame(main, text="Category Details", font=("Arial", 12, "bold"), bg="#16213e", fg="#e94560", bd=2)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=5)

        fields = [
            ("Category ID", "category_id"),
            ("Name", "name"),
            ("Description", "description"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label + ":", font=("Arial", 10), bg="#16213e", fg="white").grid(row=i, column=0, padx=10, pady=8, sticky="w")
            entry = tk.Entry(form_frame, font=("Arial", 10), width=22, bg="#0f3460", fg="white", insertbackground="white")
            entry.grid(row=i, column=1, padx=10, pady=8)
            self.entries[key] = entry

        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)

        for text, cmd, color in [
            ("Add", self.add_category, "#2b9348"),
            ("Update", self.update_category, "#e9c46a"),
            ("Delete", self.delete_category, "#e94560"),
            ("Clear", self.clear_form, "#533483"),
        ]:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white", font=("Arial", 10, "bold"), width=8, cursor="hand2").pack(side=tk.LEFT, padx=4)

        right_frame = tk.Frame(main, bg="#1a1a2e")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        search_frame = tk.Frame(right_frame, bg="#1a1a2e")
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search:", bg="#1a1a2e", fg="white", font=("Arial", 11)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 11), bg="#0f3460", fg="white", insertbackground="white", width=30).pack(side=tk.LEFT, padx=5)

        cols = ("ID", "Category ID", "Name", "Description")
        self.tree = ttk.Treeview(right_frame, columns=cols, show="headings", height=20)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor="center")
        self.tree.column("ID", width=40)

        vsb = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

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
        self.selected_id = None

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, category_id, name, description FROM categories")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get().strip()
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, category_id, name, description FROM categories WHERE name LIKE ? OR category_id LIKE ?",
                       (f"%{query}%", f"%{query}%"))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])["values"]
        self.selected_id = values[0]
        keys = ["category_id", "name", "description"]
        for key, val in zip(keys, values[1:]):
            self.entries[key].delete(0, tk.END)
            self.entries[key].insert(0, val if val else "")


# Product Frame
class ProductFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.pack(fill=tk.BOTH, expand=True)
        self.photo_path = tk.StringVar()
        self.photo_image = None
        self.selected_id = None
        self.setup_ui()
        self.load_data()

    def get_categories(self):
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT category_id FROM categories")
        cats = [row[0] for row in cursor.fetchall()]
        conn.close()
        return cats

    def get_suppliers(self):
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT supplier_id FROM suppliers")
        sups = [row[0] for row in cursor.fetchall()]
        conn.close()
        return sups

    def setup_ui(self):
        tk.Label(self, text="Product Management", font=("Arial", 18, "bold"), bg="#1a1a2e", fg="white").pack(pady=(10, 5))

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        form_frame = tk.LabelFrame(main, text="Product Details", font=("Arial", 12, "bold"), bg="#16213e", fg="#e94560", bd=2)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=5)

        tk.Label(form_frame, text="Product ID:", font=("Arial", 10), bg="#16213e", fg="white").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.product_id_entry = tk.Entry(form_frame, font=("Arial", 10), width=22, bg="#0f3460", fg="white", insertbackground="white")
        self.product_id_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(form_frame, text="Name:", font=("Arial", 10), bg="#16213e", fg="white").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.name_entry = tk.Entry(form_frame, font=("Arial", 10), width=22, bg="#0f3460", fg="white", insertbackground="white")
        self.name_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(form_frame, text="Category:", font=("Arial", 10), bg="#16213e", fg="white").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(form_frame, textvariable=self.category_var, width=20, font=("Arial", 10))
        self.category_combo["values"] = self.get_categories()
        self.category_combo.grid(row=2, column=1, padx=10, pady=5)

        tk.Label(form_frame, text="Supplier:", font=("Arial", 10), bg="#16213e", fg="white").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.supplier_var = tk.StringVar()
        self.supplier_combo = ttk.Combobox(form_frame, textvariable=self.supplier_var, width=20, font=("Arial", 10))
        self.supplier_combo["values"] = self.get_suppliers()
        self.supplier_combo.grid(row=3, column=1, padx=10, pady=5)

        tk.Label(form_frame, text="Price:", font=("Arial", 10), bg="#16213e", fg="white").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.price_entry = tk.Entry(form_frame, font=("Arial", 10), width=22, bg="#0f3460", fg="white", insertbackground="white")
        self.price_entry.grid(row=4, column=1, padx=10, pady=5)

        tk.Label(form_frame, text="Quantity:", font=("Arial", 10), bg="#16213e", fg="white").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.quantity_entry = tk.Entry(form_frame, font=("Arial", 10), width=22, bg="#0f3460", fg="white", insertbackground="white")
        self.quantity_entry.grid(row=5, column=1, padx=10, pady=5)

        tk.Label(form_frame, text="Description:", font=("Arial", 10), bg="#16213e", fg="white").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.desc_entry = tk.Entry(form_frame, font=("Arial", 10), width=22, bg="#0f3460", fg="white", insertbackground="white")
        self.desc_entry.grid(row=6, column=1, padx=10, pady=5)

        tk.Label(form_frame, text="Photo:", font=("Arial", 10), bg="#16213e", fg="white").grid(row=7, column=0, padx=10, pady=5, sticky="w")
        tk.Button(form_frame, text="Browse", command=self.browse_photo, bg="#0f3460", fg="white", font=("Arial", 9)).grid(row=7, column=1, padx=10, pady=5, sticky="w")

        self.photo_label = tk.Label(form_frame, bg="#16213e", text="No Photo", fg="gray")
        self.photo_label.grid(row=8, column=0, columnspan=2, pady=5)

        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=9, column=0, columnspan=2, pady=10)

        for text, cmd, color in [
            ("Add", self.add_product, "#2b9348"),
            ("Update", self.update_product, "#e9c46a"),
            ("Delete", self.delete_product, "#e94560"),
            ("Clear", self.clear_form, "#533483"),
        ]:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white", font=("Arial", 10, "bold"), width=8, cursor="hand2").pack(side=tk.LEFT, padx=4)

        right_frame = tk.Frame(main, bg="#1a1a2e")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        search_frame = tk.Frame(right_frame, bg="#1a1a2e")
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search:", bg="#1a1a2e", fg="white", font=("Arial", 11)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 11), bg="#0f3460", fg="white", insertbackground="white", width=30).pack(side=tk.LEFT, padx=5)

        cols = ("ID", "Product ID", "Name", "Category", "Supplier", "Price", "Quantity")
        self.tree = ttk.Treeview(right_frame, columns=cols, show="headings", height=20)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor="center")
        self.tree.column("ID", width=40)

        vsb = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

    def browse_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if path:
            self.photo_path.set(path)
            img = Image.open(path).resize((80, 80))
            self.photo_image = ImageTk.PhotoImage(img)
            self.photo_label.config(image=self.photo_image, text="")

    def add_product(self):
        pid = self.product_id_entry.get().strip()
        name = self.name_entry.get().strip()
        if not pid or not name:
            messagebox.showerror("Error", "Product ID and Name are required!")
            return
        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (product_id, name, category_id, supplier_id, price, quantity, description, photo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (pid, name, self.category_var.get(), self.supplier_var.get(),
                  self.price_entry.get(), self.quantity_entry.get(),
                  self.desc_entry.get(), self.photo_path.get()))
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
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE products SET product_id=?, name=?, category_id=?, supplier_id=?, price=?, quantity=?, description=?, photo=?
            WHERE id=?
        """, (self.product_id_entry.get(), self.name_entry.get(), self.category_var.get(),
              self.supplier_var.get(), self.price_entry.get(), self.quantity_entry.get(),
              self.desc_entry.get(), self.photo_path.get(), self.selected_id))
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
        self.product_id_entry.delete(0, tk.END)
        self.name_entry.delete(0, tk.END)
        self.category_var.set("")
        self.supplier_var.set("")
        self.price_entry.delete(0, tk.END)
        self.quantity_entry.delete(0, tk.END)
        self.desc_entry.delete(0, tk.END)
        self.photo_path.set("")
        self.photo_label.config(image="", text="No Photo")
        self.photo_image = None
        self.selected_id = None

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, product_id, name, category_id, supplier_id, price, quantity FROM products")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get().strip()
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, product_id, name, category_id, supplier_id, price, quantity FROM products
            WHERE name LIKE ? OR product_id LIKE ?
        """, (f"%{query}%", f"%{query}%"))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])["values"]
        self.selected_id = values[0]
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, name, category_id, supplier_id, price, quantity, description, photo FROM products WHERE id=?", (self.selected_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            self.product_id_entry.delete(0, tk.END)
            self.product_id_entry.insert(0, row[0] if row[0] else "")
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, row[1] if row[1] else "")
            self.category_var.set(row[2] if row[2] else "")
            self.supplier_var.set(row[3] if row[3] else "")
            self.price_entry.delete(0, tk.END)
            self.price_entry.insert(0, row[4] if row[4] else "")
            self.quantity_entry.delete(0, tk.END)
            self.quantity_entry.insert(0, row[5] if row[5] else "")
            self.desc_entry.delete(0, tk.END)
            self.desc_entry.insert(0, row[6] if row[6] else "")
            if row[7] and os.path.exists(row[7]):
                self.photo_path.set(row[7])
                img = Image.open(row[7]).resize((80, 80))
                self.photo_image = ImageTk.PhotoImage(img)
                self.photo_label.config(image=self.photo_image, text="")


# Billing Frame
class BillingFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.pack(fill=tk.BOTH, expand=True)
        self.cart_items = []
        self.invoice_no = self.generate_invoice()
        self.setup_ui()

    def generate_invoice(self):
        return "INV-" + "".join(random.choices(string.digits, k=8))

    def get_products(self):
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT product_id, name, price FROM products")
        products = cursor.fetchall()
        conn.close()
        return products

    def setup_ui(self):
        tk.Label(self, text="Billing / Invoice", font=("Arial", 18, "bold"), bg="#1a1a2e", fg="white").pack(pady=(10, 5))

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left: Customer + Product selection
        left = tk.Frame(main, bg="#16213e", width=400)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=5)
        left.pack_propagate(False)

        # Invoice info
        inv_frame = tk.LabelFrame(left, text="Invoice Info", font=("Arial", 11, "bold"), bg="#16213e", fg="#e94560", bd=2)
        inv_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(inv_frame, text=f"Invoice No: {self.invoice_no}", font=("Arial", 11, "bold"), bg="#16213e", fg="#a8dadc").pack(anchor="w", padx=10, pady=3)
        tk.Label(inv_frame, text=f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", font=("Arial", 10), bg="#16213e", fg="white").pack(anchor="w", padx=10, pady=3)

        # Customer info
        cust_frame = tk.LabelFrame(left, text="Customer Details", font=("Arial", 11, "bold"), bg="#16213e", fg="#e94560", bd=2)
        cust_frame.pack(fill=tk.X, padx=10, pady=5)

        for i, (label, key) in enumerate([("Name", "cust_name"), ("Phone", "cust_phone"), ("Email", "cust_email")]):
            tk.Label(cust_frame, text=label + ":", font=("Arial", 10), bg="#16213e", fg="white").grid(row=i, column=0, padx=8, pady=4, sticky="w")
            entry = tk.Entry(cust_frame, font=("Arial", 10), width=22, bg="#0f3460", fg="white", insertbackground="white")
            entry.grid(row=i, column=1, padx=8, pady=4)
            setattr(self, key + "_entry", entry)

        # Product selection
        prod_frame = tk.LabelFrame(left, text="Add Product", font=("Arial", 11, "bold"), bg="#16213e", fg="#e94560", bd=2)
        prod_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(prod_frame, text="Product:", font=("Arial", 10), bg="#16213e", fg="white").grid(row=0, column=0, padx=8, pady=4, sticky="w")
        self.product_var = tk.StringVar()
        products = self.get_products()
        product_names = [f"{p[0]} - {p[1]}" for p in products]
        self.product_data = {f"{p[0]} - {p[1]}": p for p in products}
        self.product_combo = ttk.Combobox(prod_frame, textvariable=self.product_var, values=product_names, width=22, font=("Arial", 10))
        self.product_combo.grid(row=0, column=1, padx=8, pady=4)
        self.product_combo.bind("<<ComboboxSelected>>", self.on_product_select)

        tk.Label(prod_frame, text="Price:", font=("Arial", 10), bg="#16213e", fg="white").grid(row=1, column=0, padx=8, pady=4, sticky="w")
        self.price_var = tk.StringVar()
        tk.Entry(prod_frame, textvariable=self.price_var, font=("Arial", 10), width=22, bg="#0f3460", fg="white", insertbackground="white", state="readonly").grid(row=1, column=1, padx=8, pady=4)

        tk.Label(prod_frame, text="Quantity:", font=("Arial", 10), bg="#16213e", fg="white").grid(row=2, column=0, padx=8, pady=4, sticky="w")
        self.qty_entry = tk.Entry(prod_frame, font=("Arial", 10), width=22, bg="#0f3460", fg="white", insertbackground="white")
        self.qty_entry.grid(row=2, column=1, padx=8, pady=4)
        self.qty_entry.insert(0, "1")

        tk.Button(prod_frame, text="Add to Cart", command=self.add_to_cart, bg="#2b9348", fg="white", font=("Arial", 10, "bold"), cursor="hand2").grid(row=3, column=0, columnspan=2, pady=8)

        # Right: Cart + Bill
        right = tk.Frame(main, bg="#1a1a2e")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        cart_frame = tk.LabelFrame(right, text="Cart", font=("Arial", 11, "bold"), bg="#1a1a2e", fg="#e94560", bd=2)
        cart_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        cols = ("Product ID", "Name", "Price", "Qty", "Total")
        self.cart_tree = ttk.Treeview(cart_frame, columns=cols, show="headings", height=12)
        for col in cols:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=130, anchor="center")

        vsb = ttk.Scrollbar(cart_frame, orient=tk.VERTICAL, command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.cart_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Total
        total_frame = tk.Frame(right, bg="#1a1a2e")
        total_frame.pack(fill=tk.X, pady=5)

        self.total_label = tk.Label(total_frame, text="Total: $0.00", font=("Arial", 16, "bold"), bg="#1a1a2e", fg="#e94560")
        self.total_label.pack(side=tk.LEFT, padx=10)

        btn_frame = tk.Frame(right, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X, pady=5)

        tk.Button(btn_frame, text="Remove Selected", command=self.remove_from_cart, bg="#e94560", fg="white", font=("Arial", 10, "bold"), cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear Cart", command=self.clear_cart, bg="#533483", fg="white", font=("Arial", 10, "bold"), cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Generate Bill", command=self.generate_bill, bg="#2b9348", fg="white", font=("Arial", 12, "bold"), cursor="hand2").pack(side=tk.RIGHT, padx=5)

        # Bill preview
        bill_frame = tk.LabelFrame(right, text="Bill Preview", font=("Arial", 11, "bold"), bg="#1a1a2e", fg="#e94560", bd=2)
        bill_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.bill_text = tk.Text(bill_frame, font=("Courier", 10), bg="#0f3460", fg="white", height=10, state=tk.DISABLED)
        self.bill_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def on_product_select(self, event):
        selected = self.product_var.get()
        if selected in self.product_data:
            self.price_var.set(str(self.product_data[selected][2]))

    def add_to_cart(self):
        selected = self.product_var.get()
        if not selected or selected not in self.product_data:
            messagebox.showerror("Error", "Please select a product!")
            return
        try:
            qty = int(self.qty_entry.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid quantity!")
            return

        product = self.product_data[selected]
        pid, name, price = product
        total = price * qty
        self.cart_items.append((pid, name, price, qty, total))
        self.cart_tree.insert("", tk.END, values=(pid, name, f"${price:.2f}", qty, f"${total:.2f}"))
        self.update_total()
        self.qty_entry.delete(0, tk.END)
        self.qty_entry.insert(0, "1")

    def remove_from_cart(self):
        selected = self.cart_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select an item to remove!")
            return
        idx = self.cart_tree.index(selected[0])
        self.cart_tree.delete(selected[0])
        self.cart_items.pop(idx)
        self.update_total()

    def clear_cart(self):
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        self.cart_items.clear()
        self.update_total()

    def update_total(self):
        total = sum(item[4] for item in self.cart_items)
        self.total_label.config(text=f"Total: ${total:.2f}")

    def generate_bill(self):
        if not self.cart_items:
            messagebox.showerror("Error", "Cart is empty!")
            return

        cust_name = self.cust_name_entry.get().strip()
        cust_phone = self.cust_phone_entry.get().strip()
        cust_email = self.cust_email_entry.get().strip()

        if not cust_name:
            messagebox.showerror("Error", "Customer name is required!")
            return

        total = sum(item[4] for item in self.cart_items)
        bill_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build bill details string
        details_lines = []
        for item in self.cart_items:
            details_lines.append(f"{item[0]}|{item[1]}|{item[2]}|{item[3]}|{item[4]}")
        bill_details = ";".join(details_lines)

        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bills (invoice_no, customer_name, customer_phone, customer_email, total_amount, bill_date, bill_details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (self.invoice_no, cust_name, cust_phone, cust_email, total, bill_date, bill_details))
            conn.commit()
            conn.close()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Invoice already saved!")
            return

        # Show bill preview
        bill_text = self.build_bill_text(cust_name, cust_phone, cust_email, total, bill_date)
        self.bill_text.config(state=tk.NORMAL)
        self.bill_text.delete("1.0", tk.END)
        self.bill_text.insert(tk.END, bill_text)
        self.bill_text.config(state=tk.DISABLED)

        messagebox.showinfo("Success", f"Bill generated successfully!\nInvoice No: {self.invoice_no}")

        # Reset for new bill
        self.invoice_no = self.generate_invoice()
        self.clear_cart()
        self.cust_name_entry.delete(0, tk.END)
        self.cust_phone_entry.delete(0, tk.END)
        self.cust_email_entry.delete(0, tk.END)

    def build_bill_text(self, name, phone, email, total, date):
        lines = []
        lines.append("=" * 50)
        lines.append("       INVENTORY MANAGEMENT SYSTEM")
        lines.append("              INVOICE")
        lines.append("=" * 50)
        lines.append(f"Invoice No : {self.invoice_no}")
        lines.append(f"Date       : {date}")
        lines.append("-" * 50)
        lines.append(f"Customer   : {name}")
        lines.append(f"Phone      : {phone}")
        lines.append(f"Email      : {email}")
        lines.append("-" * 50)
        lines.append(f"{'Product':<20} {'Price':>8} {'Qty':>5} {'Total':>10}")
        lines.append("-" * 50)
        for item in self.cart_items:
            lines.append(f"{item[1]:<20} {item[2]:>8.2f} {item[3]:>5} {item[4]:>10.2f}")
        lines.append("=" * 50)
        lines.append(f"{'TOTAL':>43} {total:>6.2f}")
        lines.append("=" * 50)
        lines.append("       Thank you for your purchase!")
        lines.append("=" * 50)
        return "\n".join(lines)


# Bills Frame
class BillsFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.pack(fill=tk.BOTH, expand=True)
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        tk.Label(self, text="Bills / Invoices", font=("Arial", 18, "bold"), bg="#1a1a2e", fg="white").pack(pady=(10, 5))

        search_frame = tk.Frame(self, bg="#1a1a2e")
        search_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(search_frame, text="Search:", bg="#1a1a2e", fg="white", font=("Arial", 11)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 11), bg="#0f3460", fg="white", insertbackground="white", width=30).pack(side=tk.LEFT, padx=5)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = ("ID", "Invoice No", "Customer", "Phone", "Email", "Total", "Date")
        self.tree = ttk.Treeview(main, columns=cols, show="headings", height=15)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=130, anchor="center")
        self.tree.column("ID", width=40)

        vsb = ttk.Scrollbar(main, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Bill detail view
        detail_frame = tk.LabelFrame(self, text="Bill Details", font=("Arial", 11, "bold"), bg="#1a1a2e", fg="#e94560", bd=2)
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.detail_text = tk.Text(detail_frame, font=("Courier", 10), bg="#0f3460", fg="white", height=12, state=tk.DISABLED)
        self.detail_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        btn_frame = tk.Frame(self, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(btn_frame, text="Delete Bill", command=self.delete_bill, bg="#e94560", fg="white", font=("Arial", 10, "bold"), cursor="hand2").pack(side=tk.LEFT, padx=5)

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, invoice_no, customer_name, customer_phone, customer_email, total_amount, bill_date FROM bills ORDER BY id DESC")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get().strip()
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, invoice_no, customer_name, customer_phone, customer_email, total_amount, bill_date FROM bills
            WHERE invoice_no LIKE ? OR customer_name LIKE ? OR customer_phone LIKE ?
            ORDER BY id DESC
        """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])["values"]
        bill_id = values[0]
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bills WHERE id=?", (bill_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            self.show_bill_detail(row)

    def show_bill_detail(self, row):
        _, invoice_no, cust_name, cust_phone, cust_email, total, bill_date, bill_details = row

        lines = []
        lines.append("=" * 55)
        lines.append("         INVENTORY MANAGEMENT SYSTEM")
        lines.append("                 INVOICE")
        lines.append("=" * 55)
        lines.append(f"Invoice No : {invoice_no}")
        lines.append(f"Date       : {bill_date}")
        lines.append("-" * 55)
        lines.append(f"Customer   : {cust_name}")
        lines.append(f"Phone      : {cust_phone}")
        lines.append(f"Email      : {cust_email}")
        lines.append("-" * 55)
        lines.append(f"{'Product':<22} {'Price':>8} {'Qty':>5} {'Total':>12}")
        lines.append("-" * 55)

        if bill_details:
            for item_str in bill_details.split(";"):
                parts = item_str.split("|")
                if len(parts) == 5:
                    pid, name, price, qty, item_total = parts
                    try:
                        lines.append(f"{name:<22} {float(price):>8.2f} {int(qty):>5} {float(item_total):>12.2f}")
                    except Exception:
                        lines.append(item_str)

        lines.append("=" * 55)
        lines.append(f"{'TOTAL':>47} {float(total):>6.2f}")
        lines.append("=" * 55)
        lines.append("          Thank you for your purchase!")
        lines.append("=" * 55)

        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert(tk.END, "\n".join(lines))
        self.detail_text.config(state=tk.DISABLED)

    def delete_bill(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a bill to delete!")
            return
        values = self.tree.item(selected[0])["values"]
        bill_id = values[0]
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this bill?"):
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bills WHERE id=?", (bill_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Bill deleted successfully!")
            self.detail_text.config(state=tk.NORMAL)
            self.detail_text.delete("1.0", tk.END)
            self.detail_text.config(state=tk.DISABLED)
            self.load_data()


if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()