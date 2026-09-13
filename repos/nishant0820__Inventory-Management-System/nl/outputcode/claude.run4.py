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
            contact TEXT,
            email TEXT,
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
            total_amount REAL,
            bill_data TEXT
        )
    """)

    conn.commit()
    conn.close()


# Utility Functions
def generate_id(prefix, length=6):
    return prefix + ''.join(random.choices(string.digits, k=length))


def get_current_time():
    return datetime.now().strftime("%H:%M:%S")


def get_current_date():
    return datetime.now().strftime("%Y-%m-%d")


# Color Scheme
BG_COLOR = "#1a1a2e"
SIDEBAR_COLOR = "#16213e"
CARD_COLOR = "#0f3460"
ACCENT_COLOR = "#e94560"
TEXT_COLOR = "#ffffff"
ENTRY_BG = "#1a1a2e"
BUTTON_COLOR = "#e94560"
BUTTON_HOVER = "#c73652"
HEADER_COLOR = "#0f3460"
TABLE_BG = "#16213e"
TABLE_FG = "#ffffff"
TABLE_SELECT = "#e94560"


class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1400x800")
        self.configure(bg=BG_COLOR)
        self.resizable(True, True)
        create_database()
        self.current_frame = None
        self.setup_main_layout()
        self.show_dashboard()

    def setup_main_layout(self):
        # Header
        self.header_frame = tk.Frame(self, bg=HEADER_COLOR, height=70)
        self.header_frame.pack(fill=tk.X, side=tk.TOP)
        self.header_frame.pack_propagate(False)

        tk.Label(
            self.header_frame,
            text="📦 Inventory Management System",
            font=("Arial", 22, "bold"),
            bg=HEADER_COLOR,
            fg=TEXT_COLOR
        ).pack(side=tk.LEFT, padx=20, pady=15)

        self.time_label = tk.Label(
            self.header_frame,
            text="",
            font=("Arial", 14),
            bg=HEADER_COLOR,
            fg=ACCENT_COLOR
        )
        self.time_label.pack(side=tk.RIGHT, padx=20)
        self.update_time()

        self.date_label = tk.Label(
            self.header_frame,
            text=f"📅 {get_current_date()}",
            font=("Arial", 12),
            bg=HEADER_COLOR,
            fg=TEXT_COLOR
        )
        self.date_label.pack(side=tk.RIGHT, padx=10)

        # Main container
        self.main_container = tk.Frame(self, bg=BG_COLOR)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Sidebar
        self.sidebar = tk.Frame(self.main_container, bg=SIDEBAR_COLOR, width=220)
        self.sidebar.pack(fill=tk.Y, side=tk.LEFT)
        self.sidebar.pack_propagate(False)
        self.setup_sidebar()

        # Content area
        self.content_area = tk.Frame(self.main_container, bg=BG_COLOR)
        self.content_area.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

    def update_time(self):
        self.time_label.config(text=f"🕐 {get_current_time()}")
        self.after(1000, self.update_time)

    def setup_sidebar(self):
        tk.Label(
            self.sidebar,
            text="MENU",
            font=("Arial", 12, "bold"),
            bg=SIDEBAR_COLOR,
            fg=ACCENT_COLOR
        ).pack(pady=(20, 10))

        menu_items = [
            ("🏠 Dashboard", self.show_dashboard),
            ("👤 Employees", self.show_employees),
            ("🏭 Suppliers", self.show_suppliers),
            ("📂 Categories", self.show_categories),
            ("📦 Products", self.show_products),
            ("🧾 Billing", self.show_billing),
            ("📋 Bills", self.show_bills),
            ("❌ Exit", self.quit),
        ]

        for text, command in menu_items:
            btn = tk.Button(
                self.sidebar,
                text=text,
                font=("Arial", 12),
                bg=SIDEBAR_COLOR,
                fg=TEXT_COLOR,
                activebackground=ACCENT_COLOR,
                activeforeground=TEXT_COLOR,
                relief=tk.FLAT,
                cursor="hand2",
                command=command,
                anchor="w",
                padx=20
            )
            btn.pack(fill=tk.X, pady=2)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=CARD_COLOR))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=SIDEBAR_COLOR))

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

    def show_categories(self):
        self.clear_content()
        CategoryFrame(self.content_area)

    def show_products(self):
        self.clear_content()
        ProductFrame(self.content_area)

    def show_billing(self):
        self.clear_content()
        BillingFrame(self.content_area)

    def show_bills(self):
        self.clear_content()
        BillsFrame(self.content_area)


class DashboardFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.pack(fill=tk.BOTH, expand=True)
        self.setup_ui()

    def setup_ui(self):
        tk.Label(
            self,
            text="Dashboard",
            font=("Arial", 24, "bold"),
            bg=BG_COLOR,
            fg=TEXT_COLOR
        ).pack(pady=20)

        stats_frame = tk.Frame(self, bg=BG_COLOR)
        stats_frame.pack(fill=tk.X, padx=20)

        stats = self.get_stats()
        cards = [
            ("👤 Employees", stats["employees"], "#e94560"),
            ("🏭 Suppliers", stats["suppliers"], "#0f3460"),
            ("📂 Categories", stats["categories"], "#533483"),
            ("📦 Products", stats["products"], "#05c46b"),
            ("🧾 Bills", stats["bills"], "#ffd32a"),
        ]

        for i, (title, value, color) in enumerate(cards):
            card = tk.Frame(stats_frame, bg=color, relief=tk.RAISED, bd=2)
            card.grid(row=0, column=i, padx=10, pady=10, ipadx=20, ipady=20, sticky="nsew")
            stats_frame.columnconfigure(i, weight=1)

            tk.Label(card, text=title, font=("Arial", 13, "bold"), bg=color, fg="white").pack(pady=(10, 5))
            tk.Label(card, text=str(value), font=("Arial", 28, "bold"), bg=color, fg="white").pack(pady=(0, 10))

        # Recent activity
        activity_frame = tk.Frame(self, bg=CARD_COLOR, relief=tk.RAISED, bd=2)
        activity_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tk.Label(
            activity_frame,
            text="📊 System Overview",
            font=("Arial", 16, "bold"),
            bg=CARD_COLOR,
            fg=TEXT_COLOR
        ).pack(pady=10)

        info_text = tk.Text(activity_frame, bg=ENTRY_BG, fg=TEXT_COLOR, font=("Arial", 11), height=12)
        info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        info_text.insert(tk.END, f"Welcome to Inventory Management System\n")
        info_text.insert(tk.END, f"{'='*50}\n")
        info_text.insert(tk.END, f"Date: {get_current_date()}\n")
        info_text.insert(tk.END, f"Time: {get_current_time()}\n\n")
        info_text.insert(tk.END, f"Total Employees: {stats['employees']}\n")
        info_text.insert(tk.END, f"Total Suppliers: {stats['suppliers']}\n")
        info_text.insert(tk.END, f"Total Categories: {stats['categories']}\n")
        info_text.insert(tk.END, f"Total Products: {stats['products']}\n")
        info_text.insert(tk.END, f"Total Bills Generated: {stats['bills']}\n")
        info_text.config(state=tk.DISABLED)

    def get_stats(self):
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        stats = {}
        for table in ["employees", "suppliers", "categories", "products", "bills"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        conn.close()
        return stats


class EmployeeFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.pack(fill=tk.BOTH, expand=True)
        self.photo_path = tk.StringVar()
        self.selected_id = None
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        tk.Label(self, text="Employee Management", font=("Arial", 20, "bold"), bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=10)

        main_frame = tk.Frame(self, bg=BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        # Left form
        form_frame = tk.Frame(main_frame, bg=CARD_COLOR, relief=tk.RAISED, bd=2)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=5)

        tk.Label(form_frame, text="Employee Details", font=("Arial", 14, "bold"), bg=CARD_COLOR, fg=ACCENT_COLOR).grid(
            row=0, column=0, columnspan=2, pady=10)

        fields = [
            ("Employee ID", "emp_id"),
            ("Name", "name"),
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
        for i, (label, key) in enumerate(fields, start=1):
            tk.Label(form_frame, text=label + ":", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).grid(
                row=i, column=0, sticky="w", padx=10, pady=3)
            entry = tk.Entry(form_frame, font=("Arial", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, width=22)
            entry.grid(row=i, column=1, padx=10, pady=3)
            self.entries[key] = entry

        # Gender
        tk.Label(form_frame, text="Gender:", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).grid(
            row=len(fields)+1, column=0, sticky="w", padx=10, pady=3)
        self.gender_var = tk.StringVar(value="Male")
        gender_combo = ttk.Combobox(form_frame, textvariable=self.gender_var, values=["Male", "Female", "Other"],
                                    width=20, state="readonly")
        gender_combo.grid(row=len(fields)+1, column=1, padx=10, pady=3)

        # Photo
        tk.Label(form_frame, text="Photo:", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).grid(
            row=len(fields)+2, column=0, sticky="w", padx=10, pady=3)
        photo_btn = tk.Button(form_frame, text="Browse Photo", font=("Arial", 9), bg=BUTTON_COLOR, fg=TEXT_COLOR,
                              command=self.browse_photo, cursor="hand2")
        photo_btn.grid(row=len(fields)+2, column=1, padx=10, pady=3)

        self.photo_label = tk.Label(form_frame, text="No photo selected", font=("Arial", 8), bg=CARD_COLOR, fg=TEXT_COLOR)
        self.photo_label.grid(row=len(fields)+3, column=0, columnspan=2, pady=2)

        # Buttons
        btn_frame = tk.Frame(form_frame, bg=CARD_COLOR)
        btn_frame.grid(row=len(fields)+4, column=0, columnspan=2, pady=10)

        buttons = [
            ("Add", self.add_employee, "#05c46b"),
            ("Update", self.update_employee, "#ffd32a"),
            ("Delete", self.delete_employee, "#e94560"),
            ("Clear", self.clear_form, "#808080"),
        ]
        for text, cmd, color in buttons:
            tk.Button(btn_frame, text=text, font=("Arial", 10, "bold"), bg=color, fg=TEXT_COLOR,
                      command=cmd, cursor="hand2", width=8).pack(side=tk.LEFT, padx=3)

        # Right table
        table_frame = tk.Frame(main_frame, bg=CARD_COLOR, relief=tk.RAISED, bd=2)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)

        # Search
        search_frame = tk.Frame(table_frame, bg=CARD_COLOR)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="Search:", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 10), bg=ENTRY_BG, fg=TEXT_COLOR,
                 insertbackground=TEXT_COLOR, width=25).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Emp ID", "Name", "Email", "Phone", "Department", "Designation", "Salary")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background=TABLE_BG, foreground=TABLE_FG, rowheight=25,
                        fieldbackground=TABLE_BG, font=("Arial", 9))
        style.configure("Treeview.Heading", background=CARD_COLOR, foreground=ACCENT_COLOR,
                        font=("Arial", 10, "bold"))
        style.map("Treeview", background=[("selected", TABLE_SELECT)])

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<ButtonRelease-1>", self.select_row)

    def browse_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif")])
        if path:
            self.photo_path.set(path)
            self.photo_label.config(text=os.path.basename(path))

    def add_employee(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        if not data["emp_id"] or not data["name"]:
            messagebox.showerror("Error", "Employee ID and Name are required!")
            return
        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO employees (emp_id, name, email, phone, address, gender, dob, department, designation, salary, join_date, photo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data["emp_id"], data["name"], data["email"], data["phone"], data["address"],
                  self.gender_var.get(), data["dob"], data["department"], data["designation"],
                  data["salary"], data["join_date"], self.photo_path.get()))
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
            UPDATE employees SET emp_id=?, name=?, email=?, phone=?, address=?, gender=?, dob=?,
            department=?, designation=?, salary=?, join_date=?, photo=? WHERE id=?
        """, (data["emp_id"], data["name"], data["email"], data["phone"], data["address"],
              self.gender_var.get(), data["dob"], data["department"], data["designation"],
              data["salary"], data["join_date"], self.photo_path.get(), self.selected_id))
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
        self.gender_var.set("Male")
        self.photo_path.set("")
        self.photo_label.config(text="No photo selected")
        self.selected_id = None

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, emp_id, name, email, phone, department, designation, salary FROM employees")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get().strip()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, emp_id, name, email, phone, department, designation, salary FROM employees
            WHERE name LIKE ? OR emp_id LIKE ? OR department LIKE ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_row(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])["values"]
        self.selected_id = values[0]
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE id=?", (self.selected_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            keys = ["emp_id", "name", "email", "phone", "address", "dob", "department", "designation", "salary", "join_date"]
            row_data = list(row)
            for i, key in enumerate(keys):
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, row_data[i+1] if row_data[i+1] else "")
            self.gender_var.set(row[6] if row[6] else "Male")
            if row[12]:
                self.photo_path.set(row[12])
                self.photo_label.config(text=os.path.basename(row[12]))


class SupplierFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.pack(fill=tk.BOTH, expand=True)
        self.selected_id = None
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        tk.Label(self, text="Supplier Management", font=("Arial", 20, "bold"), bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=10)

        main_frame = tk.Frame(self, bg=BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        form_frame = tk.Frame(main_frame, bg=CARD_COLOR, relief=tk.RAISED, bd=2)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=5)

        tk.Label(form_frame, text="Supplier Details", font=("Arial", 14, "bold"), bg=CARD_COLOR, fg=ACCENT_COLOR).grid(
            row=0, column=0, columnspan=2, pady=10)

        fields = [
            ("Supplier ID", "supplier_id"),
            ("Name", "name"),
            ("Contact", "contact"),
            ("Email", "email"),
            ("Address", "address"),
            ("Company", "company"),
            ("Description", "description"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(fields, start=1):
            tk.Label(form_frame, text=label + ":", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).grid(
                row=i, column=0, sticky="w", padx=10, pady=5)
            entry = tk.Entry(form_frame, font=("Arial", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, width=22)
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.entries[key] = entry

        btn_frame = tk.Frame(form_frame, bg=CARD_COLOR)
        btn_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=10)

        buttons = [
            ("Add", self.add_supplier, "#05c46b"),
            ("Update", self.update_supplier, "#ffd32a"),
            ("Delete", self.delete_supplier, "#e94560"),
            ("Clear", self.clear_form, "#808080"),
        ]
        for text, cmd, color in buttons:
            tk.Button(btn_frame, text=text, font=("Arial", 10, "bold"), bg=color, fg=TEXT_COLOR,
                      command=cmd, cursor="hand2", width=8).pack(side=tk.LEFT, padx=3)

        gen_btn = tk.Button(form_frame, text="Generate ID", font=("Arial", 9), bg=CARD_COLOR, fg=ACCENT_COLOR,
                            command=self.generate_supplier_id, cursor="hand2")
        gen_btn.grid(row=len(fields)+2, column=0, columnspan=2, pady=5)

        table_frame = tk.Frame(main_frame, bg=CARD_COLOR, relief=tk.RAISED, bd=2)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)

        search_frame = tk.Frame(table_frame, bg=CARD_COLOR)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="Search:", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 10), bg=ENTRY_BG, fg=TEXT_COLOR,
                 insertbackground=TEXT_COLOR, width=25).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Supplier ID", "Name", "Contact", "Email", "Company")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<ButtonRelease-1>", self.select_row)

    def generate_supplier_id(self):
        self.entries["supplier_id"].delete(0, tk.END)
        self.entries["supplier_id"].insert(0, generate_id("SUP"))

    def add_supplier(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        if not data["supplier_id"] or not data["name"]:
            messagebox.showerror("Error", "Supplier ID and Name are required!")
            return
        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO suppliers (supplier_id, name, contact, email, address, company, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data["supplier_id"], data["name"], data["contact"], data["email"],
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
            UPDATE suppliers SET supplier_id=?, name=?, contact=?, email=?, address=?, company=?, description=?
            WHERE id=?
        """, (data["supplier_id"], data["name"], data["contact"], data["email"],
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
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, supplier_id, name, contact, email, company FROM suppliers")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get().strip()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, supplier_id, name, contact, email, company FROM suppliers
            WHERE name LIKE ? OR supplier_id LIKE ? OR company LIKE ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_row(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])["values"]
        self.selected_id = values[0]
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM suppliers WHERE id=?", (self.selected_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            keys = ["supplier_id", "name", "contact", "email", "address", "company", "description"]
            for i, key in enumerate(keys):
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, row[i+1] if row[i+1] else "")


class CategoryFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.pack(fill=tk.BOTH, expand=True)
        self.selected_id = None
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        tk.Label(self, text="Category Management", font=("Arial", 20, "bold"), bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=10)

        main_frame = tk.Frame(self, bg=BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        form_frame = tk.Frame(main_frame, bg=CARD_COLOR, relief=tk.RAISED, bd=2)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=5)

        tk.Label(form_frame, text="Category Details", font=("Arial", 14, "bold"), bg=CARD_COLOR, fg=ACCENT_COLOR).grid(
            row=0, column=0, columnspan=2, pady=10)

        fields = [
            ("Category ID", "category_id"),
            ("Name", "name"),
            ("Description", "description"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(fields, start=1):
            tk.Label(form_frame, text=label + ":", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).grid(
                row=i, column=0, sticky="w", padx=10, pady=8)
            entry = tk.Entry(form_frame, font=("Arial", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, width=22)
            entry.grid(row=i, column=1, padx=10, pady=8)
            self.entries[key] = entry

        gen_btn = tk.Button(form_frame, text="Generate ID", font=("Arial", 9), bg=CARD_COLOR, fg=ACCENT_COLOR,
                            command=self.generate_category_id, cursor="hand2")
        gen_btn.grid(row=len(fields)+1, column=0, columnspan=2, pady=5)

        btn_frame = tk.Frame(form_frame, bg=CARD_COLOR)
        btn_frame.grid(row=len(fields)+2, column=0, columnspan=2, pady=10)

        buttons = [
            ("Add", self.add_category, "#05c46b"),
            ("Update", self.update_category, "#ffd32a"),
            ("Delete", self.delete_category, "#e94560"),
            ("Clear", self.clear_form, "#808080"),
        ]
        for text, cmd, color in buttons:
            tk.Button(btn_frame, text=text, font=("Arial", 10, "bold"), bg=color, fg=TEXT_COLOR,
                      command=cmd, cursor="hand2", width=8).pack(side=tk.LEFT, padx=3)

        table_frame = tk.Frame(main_frame, bg=CARD_COLOR, relief=tk.RAISED, bd=2)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)

        search_frame = tk.Frame(table_frame, bg=CARD_COLOR)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="Search:", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 10), bg=ENTRY_BG, fg=TEXT_COLOR,
                 insertbackground=TEXT_COLOR, width=25).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Category ID", "Name", "Description")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<ButtonRelease-1>", self.select_row)

    def generate_category_id(self):
        self.entries["category_id"].delete(0, tk.END)
        self.entries["category_id"].insert(0, generate_id("CAT"))

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
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, category_id, name, description FROM categories")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get().strip()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, category_id, name, description FROM categories
            WHERE name LIKE ? OR category_id LIKE ?
        """, (f"%{query}%", f"%{query}%"))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_row(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])["values"]
        self.selected_id = values[0]
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE id=?", (self.selected_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            keys = ["category_id", "name", "description"]
            for i, key in enumerate(keys):
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, row[i+1] if row[i+1] else "")


class ProductFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.pack(fill=tk.BOTH, expand=True)
        self.selected_id = None
        self.setup_ui()
        self.load_data()

    def get_categories(self):
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories")
        cats = [row[0] for row in cursor.fetchall()]
        conn.close()
        return cats if cats else ["No Categories"]

    def get_suppliers(self):
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM suppliers")
        sups = [row[0] for row in cursor.fetchall()]
        conn.close()
        return sups if sups else ["No Suppliers"]

    def setup_ui(self):
        tk.Label(self, text="Product Management", font=("Arial", 20, "bold"), bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=10)

        main_frame = tk.Frame(self, bg=BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        form_frame = tk.Frame(main_frame, bg=CARD_COLOR, relief=tk.RAISED, bd=2)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=5)

        tk.Label(form_frame, text="Product Details", font=("Arial", 14, "bold"), bg=CARD_COLOR, fg=ACCENT_COLOR).grid(
            row=0, column=0, columnspan=2, pady=10)

        self.entries = {}
        text_fields = [
            ("Product ID", "product_id"),
            ("Name", "name"),
            ("Price", "price"),
            ("Quantity", "quantity"),
            ("Description", "description"),
        ]

        for i, (label, key) in enumerate(text_fields, start=1):
            tk.Label(form_frame, text=label + ":", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).grid(
                row=i, column=0, sticky="w", padx=10, pady=5)
            entry = tk.Entry(form_frame, font=("Arial", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, width=22)
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.entries[key] = entry

        # Category dropdown
        tk.Label(form_frame, text="Category:", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).grid(
            row=len(text_fields)+1, column=0, sticky="w", padx=10, pady=5)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(form_frame, textvariable=self.category_var,
                                           values=self.get_categories(), width=20, state="readonly")
        self.category_combo.grid(row=len(text_fields)+1, column=1, padx=10, pady=5)

        # Supplier dropdown
        tk.Label(form_frame, text="Supplier:", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).grid(
            row=len(text_fields)+2, column=0, sticky="w", padx=10, pady=5)
        self.supplier_var = tk.StringVar()
        self.supplier_combo = ttk.Combobox(form_frame, textvariable=self.supplier_var,
                                           values=self.get_suppliers(), width=20, state="readonly")
        self.supplier_combo.grid(row=len(text_fields)+2, column=1, padx=10, pady=5)

        # Status dropdown
        tk.Label(form_frame, text="Status:", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).grid(
            row=len(text_fields)+3, column=0, sticky="w", padx=10, pady=5)
        self.status_var = tk.StringVar(value="Available")
        status_combo = ttk.Combobox(form_frame, textvariable=self.status_var,
                                    values=["Available", "Out of Stock", "Discontinued"], width=20, state="readonly")
        status_combo.grid(row=len(text_fields)+3, column=1, padx=10, pady=5)

        gen_btn = tk.Button(form_frame, text="Generate ID", font=("Arial", 9), bg=CARD_COLOR, fg=ACCENT_COLOR,
                            command=self.generate_product_id, cursor="hand2")
        gen_btn.grid(row=len(text_fields)+4, column=0, columnspan=2, pady=5)

        btn_frame = tk.Frame(form_frame, bg=CARD_COLOR)
        btn_frame.grid(row=len(text_fields)+5, column=0, columnspan=2, pady=10)

        buttons = [
            ("Add", self.add_product, "#05c46b"),
            ("Update", self.update_product, "#ffd32a"),
            ("Delete", self.delete_product, "#e94560"),
            ("Clear", self.clear_form, "#808080"),
        ]
        for text, cmd, color in buttons:
            tk.Button(btn_frame, text=text, font=("Arial", 10, "bold"), bg=color, fg=TEXT_COLOR,
                      command=cmd, cursor="hand2", width=8).pack(side=tk.LEFT, padx=3)

        table_frame = tk.Frame(main_frame, bg=CARD_COLOR, relief=tk.RAISED, bd=2)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)

        search_frame = tk.Frame(table_frame, bg=CARD_COLOR)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="Search:", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 10), bg=ENTRY_BG, fg=TEXT_COLOR,
                 insertbackground=TEXT_COLOR, width=25).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Product ID", "Name", "Category", "Supplier", "Price", "Quantity", "Status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<ButtonRelease-1>", self.select_row)

    def generate_product_id(self):
        self.entries["product_id"].delete(0, tk.END)
        self.entries["product_id"].insert(0, generate_id("PRD"))

    def add_product(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        if not data["product_id"] or not data["name"]:
            messagebox.showerror("Error", "Product ID and Name are required!")
            return
        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (product_id, name, category, supplier, price, quantity, description, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (data["product_id"], data["name"], self.category_var.get(), self.supplier_var.get(),
                  data["price"], data["quantity"], data["description"], self.status_var.get()))
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
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE products SET product_id=?, name=?, category=?, supplier=?, price=?, quantity=?, description=?, status=?
            WHERE id=?
        """, (data["product_id"], data["name"], self.category_var.get(), self.supplier_var.get(),
              data["price"], data["quantity"], data["description"], self.status_var.get(), self.selected_id))
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
        self.category_var.set("")
        self.supplier_var.set("")
        self.status_var.set("Available")
        self.selected_id = None

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, product_id, name, category, supplier, price, quantity, status FROM products")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get().strip()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, product_id, name, category, supplier, price, quantity, status FROM products
            WHERE name LIKE ? OR product_id LIKE ? OR category LIKE ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%"))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_row(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])["values"]
        self.selected_id = values[0]
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id=?", (self.selected_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            keys = ["product_id", "name", "price", "quantity", "description"]
            field_indices = [1, 2, 5, 6, 7]
            for key, idx in zip(keys, field_indices):
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, row[idx] if row[idx] else "")
            self.category_var.set(row[3] if row[3] else "")
            self.supplier_var.set(row[4] if row[4] else "")
            self.status_var.set(row[8] if row[8] else "Available")


class BillingFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.pack(fill=tk.BOTH, expand=True)
        self.cart_items = []
        self.setup_ui()

    def get_products(self):
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name, price FROM products WHERE status='Available'")
        products = cursor.fetchall()
        conn.close()
        return products

    def setup_ui(self):
        tk.Label(self, text="Billing / Invoice", font=("Arial", 20, "bold"), bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=10)

        main_frame = tk.Frame(self, bg=BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        # Left panel - Customer & Product
        left_frame = tk.Frame(main_frame, bg=CARD_COLOR, relief=tk.RAISED, bd=2)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=5)

        # Customer info
        tk.Label(left_frame, text="Customer Information", font=("Arial", 13, "bold"), bg=CARD_COLOR, fg=ACCENT_COLOR).grid(
            row=0, column=0, columnspan=2, pady=10)

        customer_fields = [
            ("Invoice No", "invoice_no"),
            ("Customer Name", "customer_name"),
            ("Phone", "customer_phone"),
            ("Email", "customer_email"),
        ]

        self.customer_entries = {}
        for i, (label, key) in enumerate(customer_fields, start=1):
            tk.Label(left_frame, text=label + ":", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).grid(
                row=i, column=0, sticky="w", padx=10, pady=5)
            entry = tk.Entry(left_frame, font=("Arial", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, width=22)
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.customer_entries[key] = entry

        tk.Button(left_frame, text="Generate Invoice No", font=("Arial", 9), bg=CARD_COLOR, fg=ACCENT_COLOR,
                  command=self.generate_invoice, cursor="hand2").grid(row=len(customer_fields)+1, column=0, columnspan=2, pady=5)

        # Product selection
        tk.Label(left_frame, text="Add Product", font=("Arial", 13, "bold"), bg=CARD_COLOR, fg=ACCENT_COLOR).grid(
            row=len(customer_fields)+2, column=0, columnspan=2, pady=(15, 5))

        tk.Label(left_frame, text="Product:", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).grid(
            row=len(customer_fields)+3, column=0, sticky="w", padx=10, pady=5)
        self.product_var = tk.StringVar()
        products = self.get_products()
        product_names = [p[0] for p in products]
        self.product_prices = {p[0]: p[1] for p in products}
        self.product_combo = ttk.Combobox(left_frame, textvariable=self.product_var, values=product_names, width=20)
        self.product_combo.grid(row=len(customer_fields)+3, column=1, padx=10, pady=5)
        self.product_combo.bind("<<ComboboxSelected>>", self.on_product_select)

        tk.Label(left_frame, text="Price:", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).grid(
            row=len(customer_fields)+4, column=0, sticky="w", padx=10, pady=5)
        self.price_entry = tk.Entry(left_frame, font=("Arial", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, width=22)
        self.price_entry.grid(row=len(customer_fields)+4, column=1, padx=10, pady=5)

        tk.Label(left_frame, text="Quantity:", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).grid(
            row=len(customer_fields)+5, column=0, sticky="w", padx=10, pady=5)
        self.qty_entry = tk.Entry(left_frame, font=("Arial", 10), bg=ENTRY_BG, fg=TEXT_COLOR, insertbackground=TEXT_COLOR, width=22)
        self.qty_entry.grid(row=len(customer_fields)+5, column=1, padx=10, pady=5)
        self.qty_entry.insert(0, "1")

        tk.Button(left_frame, text="Add to Cart", font=("Arial", 10, "bold"), bg="#05c46b", fg=TEXT_COLOR,
                  command=self.add_to_cart, cursor="hand2", width=20).grid(row=len(customer_fields)+6, column=0, columnspan=2, pady=10)

        # Right panel - Cart & Bill
        right_frame = tk.Frame(main_frame, bg=CARD_COLOR, relief=tk.RAISED, bd=2)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)

        tk.Label(right_frame, text="Shopping Cart", font=("Arial", 13, "bold"), bg=CARD_COLOR, fg=ACCENT_COLOR).pack(pady=10)

        cart_columns = ("Product", "Price", "Quantity", "Total")
        self.cart_tree = ttk.Treeview(right_frame, columns=cart_columns, show="headings", height=10)
        for col in cart_columns:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=150, anchor="center")
        self.cart_tree.pack(fill=tk.X, padx=10, pady=5)

        # Bill area
        bill_frame = tk.Frame(right_frame, bg=CARD_COLOR)
        bill_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.bill_text = tk.Text(bill_frame, bg=ENTRY_BG, fg=TEXT_COLOR, font=("Courier", 10), height=15)
        self.bill_text.pack(fill=tk.BOTH, expand=True)

        # Total and buttons
        total_frame = tk.Frame(right_frame, bg=CARD_COLOR)
        total_frame.pack(fill=tk.X, padx=10, pady=5)

        self.total_label = tk.Label(total_frame, text="Total: $0.00", font=("Arial", 14, "bold"),
                                    bg=CARD_COLOR, fg=ACCENT_COLOR)
        self.total_label.pack(side=tk.LEFT, padx=10)

        btn_frame2 = tk.Frame(total_frame, bg=CARD_COLOR)
        btn_frame2.pack(side=tk.RIGHT)

        tk.Button(btn_frame2, text="Generate Bill", font=("Arial", 10, "bold"), bg="#05c46b", fg=TEXT_COLOR,
                  command=self.generate_bill, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame2, text="Save Bill", font=("Arial", 10, "bold"), bg=BUTTON_COLOR, fg=TEXT_COLOR,
                  command=self.save_bill, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame2, text="Clear", font=("Arial", 10, "bold"), bg="#808080", fg=TEXT_COLOR,
                  command=self.clear_billing, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame2, text="Remove Item", font=("Arial", 10, "bold"), bg="#ffd32a", fg="#000",
                  command=self.remove_from_cart, cursor="hand2").pack(side=tk.LEFT, padx=5)

    def generate_invoice(self):
        self.customer_entries["invoice_no"].delete(0, tk.END)
        self.customer_entries["invoice_no"].insert(0, generate_id("INV"))

    def on_product_select(self, event):
        product = self.product_var.get()
        if product in self.product_prices:
            self.price_entry.delete(0, tk.END)
            self.price_entry.insert(0, str(self.product_prices[product]))

    def add_to_cart(self):
        product = self.product_var.get()
        if not product:
            messagebox.showerror("Error", "Please select a product!")
            return
        try:
            price = float(self.price_entry.get())
            qty = int(self.qty_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid price or quantity!")
            return

        total = price * qty
        self.cart_items.append({"product": product, "price": price, "qty": qty, "total": total})
        self.cart_tree.insert("", tk.END, values=(product, f"${price:.2f}", qty, f"${total:.2f}"))
        self.update_total()
        self.product_var.set("")
        self.price_entry.delete(0, tk.END)
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

    def update_total(self):
        total = sum(item["total"] for item in self.cart_items)
        self.total_label.config(text=f"Total: ${total:.2f}")

    def generate_bill(self):
        if not self.cart_items:
            messagebox.showerror("Error", "Cart is empty!")
            return

        invoice = self.customer_entries["invoice_no"].get() or generate_id("INV")
        name = self.customer_entries["customer_name"].get() or "Walk-in Customer"
        phone = self.customer_entries["customer_phone"].get()
        email = self.customer_entries["customer_email"].get()
        date = get_current_date()
        time = get_current_time()

        bill = f"""
{'='*50}
       INVENTORY MANAGEMENT SYSTEM
           INVOICE / BILL
{'='*50}
Invoice No : {invoice}
Date       : {date}
Time       : {time}
{'='*50}
Customer   : {name}
Phone      : {phone}
Email      : {email}
{'='*50}
{'Product':<20} {'Price':>8} {'Qty':>5} {'Total':>10}
{'-'*50}
"""
        total = 0
        for item in self.cart_items:
            bill += f"{item['product']:<20} ${item['price']:>7.2f} {item['qty']:>5} ${item['total']:>9.2f}\n"
            total += item["total"]

        bill += f"""{'-'*50}
{'TOTAL':>35} ${total:>9.2f}
{'='*50}
        Thank you for your purchase!
{'='*50}
"""
        self.bill_text.config(state=tk.NORMAL)
        self.bill_text.delete(1.0, tk.END)
        self.bill_text.insert(tk.END, bill)
        self.bill_text.config(state=tk.DISABLED)
        self.current_bill_data = bill
        self.current_total = total

    def save_bill(self):
        if not hasattr(self, 'current_bill_data'):
            messagebox.showerror("Error", "Please generate a bill first!")
            return

        invoice = self.customer_entries["invoice_no"].get()
        if not invoice:
            messagebox.showerror("Error", "Invoice number is required!")
            return

        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bills (invoice_no, customer_name, customer_phone, customer_email, bill_date, total_amount, bill_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (invoice,
                  self.customer_entries["customer_name"].get(),
                  self.customer_entries["customer_phone"].get(),
                  self.customer_entries["customer_email"].get(),
                  get_current_date(),
                  self.current_total,
                  self.current_bill_data))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Bill saved successfully!")
            self.clear_billing()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Invoice number already exists!")

    def clear_billing(self):
        for entry in self.customer_entries.values():
            entry.delete(0, tk.END)
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        self.cart_items = []
        self.bill_text.config(state=tk.NORMAL)
        self.bill_text.delete(1.0, tk.END)
        self.bill_text.config(state=tk.DISABLED)
        self.total_label.config(text="Total: $0.00")
        if hasattr(self, 'current_bill_data'):
            del self.current_bill_data


class BillsFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_COLOR)
        self.pack(fill=tk.BOTH, expand=True)
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        tk.Label(self, text="Bills / Invoices", font=("Arial", 20, "bold"), bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=10)

        main_frame = tk.Frame(self, bg=BG_COLOR)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        # Left - bills list
        list_frame = tk.Frame(main_frame, bg=CARD_COLOR, relief=tk.RAISED, bd=2)
        list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10), pady=5)

        tk.Label(list_frame, text="All Bills", font=("Arial", 13, "bold"), bg=CARD_COLOR, fg=ACCENT_COLOR).pack(pady=10)

        search_frame = tk.Frame(list_frame, bg=CARD_COLOR)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="Search:", font=("Arial", 10), bg=CARD_COLOR, fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 10), bg=ENTRY_BG, fg=TEXT_COLOR,
                 insertbackground=TEXT_COLOR, width=20).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Invoice No", "Customer", "Date", "Total")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=25)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor="center")

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<ButtonRelease-1>", self.select_bill)

        btn_frame = tk.Frame(list_frame, bg=CARD_COLOR)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Delete Bill", font=("Arial", 10, "bold"), bg=ACCENT_COLOR, fg=TEXT_COLOR,
                  command=self.delete_bill, cursor="hand2").pack(side=tk.LEFT, padx=5)

        # Right - bill detail
        detail_frame = tk.Frame(main_frame, bg=CARD_COLOR, relief=tk.RAISED, bd=2)
        detail_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=5)

        tk.Label(detail_frame, text="Bill Details", font=("Arial", 13, "bold"), bg=CARD_COLOR, fg=ACCENT_COLOR).pack(pady=10)

        self.bill_detail = tk.Text(detail_frame, bg=ENTRY_BG, fg=TEXT_COLOR, font=("Courier", 10))
        self.bill_detail.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, invoice_no, customer_name, bill_date, total_amount FROM bills ORDER BY id DESC")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=(row[0], row[1], row[2], row[3], f"${row[4]:.2f}"))
        conn.close()

    def search_data(self):
        query = self.search_var.get().strip()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, invoice_no, customer_name, bill_date, total_amount FROM bills
            WHERE invoice_no LIKE ? OR customer_name LIKE ?
            ORDER BY id DESC
        """, (f"%{query}%", f"%{query}%"))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=(row[0], row[1], row[2], row[3], f"${row[4]:.2f}"))
        conn.close()

    def select_bill(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])["values"]
        bill_id = values[0]
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT bill_data FROM bills WHERE id=?", (bill_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            self.bill_detail.config(state=tk.NORMAL)
            self.bill_detail.delete(1.0, tk.END)
            self.bill_detail.insert(tk.END, row[0])
            self.bill_detail.config(state=tk.DISABLED)

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
            self.bill_detail.config(state=tk.NORMAL)
            self.bill_detail.delete(1.0, tk.END)
            self.bill_detail.config(state=tk.DISABLED)
            self.load_data()


if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()