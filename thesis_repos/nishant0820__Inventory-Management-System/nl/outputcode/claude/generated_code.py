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
            doj TEXT,
            department TEXT,
            designation TEXT,
            salary REAL,
            photo TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sup_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            contact TEXT,
            email TEXT,
            address TEXT,
            company TEXT,
            gst TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cat_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prod_id TEXT UNIQUE NOT NULL,
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


# ==================== DASHBOARD ====================
class Dashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1400x800")
        self.configure(bg="#1a1a2e")
        self.resizable(True, True)

        create_database()
        self.build_ui()
        self.update_time()

    def build_ui(self):
        # Header
        header = tk.Frame(self, bg="#16213e", height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="📦 Inventory Management System",
            font=("Arial", 24, "bold"),
            bg="#16213e",
            fg="#e94560"
        ).pack(side=tk.LEFT, padx=20, pady=15)

        self.time_label = tk.Label(
            header,
            text="",
            font=("Arial", 14),
            bg="#16213e",
            fg="#a8dadc"
        )
        self.time_label.pack(side=tk.RIGHT, padx=20)

        self.date_label = tk.Label(
            header,
            text="",
            font=("Arial", 12),
            bg="#16213e",
            fg="#a8dadc"
        )
        self.date_label.pack(side=tk.RIGHT, padx=10)

        # Navigation
        nav = tk.Frame(self, bg="#0f3460", height=50)
        nav.pack(fill=tk.X)
        nav.pack_propagate(False)

        nav_buttons = [
            ("🏠 Dashboard", self.show_dashboard),
            ("👤 Employees", self.open_employees),
            ("🏭 Suppliers", self.open_suppliers),
            ("📦 Products", self.open_products),
            ("🗂️ Categories", self.open_categories),
            ("🧾 Billing", self.open_billing),
            ("📋 Bills", self.open_bills),
        ]

        for text, cmd in nav_buttons:
            btn = tk.Button(
                nav,
                text=text,
                command=cmd,
                bg="#0f3460",
                fg="white",
                font=("Arial", 11, "bold"),
                relief=tk.FLAT,
                padx=15,
                cursor="hand2",
                activebackground="#e94560",
                activeforeground="white"
            )
            btn.pack(side=tk.LEFT, pady=8, padx=2)

        # Main content area
        self.main_frame = tk.Frame(self, bg="#1a1a2e")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.show_dashboard()

    def show_dashboard(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # Stats cards
        stats_frame = tk.Frame(self.main_frame, bg="#1a1a2e")
        stats_frame.pack(fill=tk.X, padx=20, pady=20)

        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM employees")
        emp_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM suppliers")
        sup_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM products")
        prod_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM bills")
        bill_count = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(grand_total) FROM bills")
        total_sales = cursor.fetchone()[0] or 0
        conn.close()

        cards = [
            ("👤 Employees", emp_count, "#e94560"),
            ("🏭 Suppliers", sup_count, "#0f3460"),
            ("📦 Products", prod_count, "#533483"),
            ("🧾 Bills", bill_count, "#05c46b"),
            ("💰 Total Sales", f"₹{total_sales:.2f}", "#f53b57"),
        ]

        for i, (title, value, color) in enumerate(cards):
            card = tk.Frame(stats_frame, bg=color, width=220, height=120)
            card.grid(row=0, column=i, padx=10, pady=5)
            card.pack_propagate(False)

            tk.Label(card, text=title, font=("Arial", 13, "bold"), bg=color, fg="white").pack(pady=(20, 5))
            tk.Label(card, text=str(value), font=("Arial", 20, "bold"), bg=color, fg="white").pack()

        # Recent bills table
        recent_frame = tk.LabelFrame(
            self.main_frame,
            text="Recent Bills",
            font=("Arial", 13, "bold"),
            bg="#1a1a2e",
            fg="white",
            padx=10,
            pady=10
        )
        recent_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        cols = ("Invoice No", "Customer", "Phone", "Date", "Grand Total")
        tree = ttk.Treeview(recent_frame, columns=cols, show="headings", height=10)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=200)

        style = ttk.Style()
        style.configure("Treeview", background="#16213e", foreground="white", fieldbackground="#16213e", rowheight=28)
        style.configure("Treeview.Heading", background="#0f3460", foreground="white", font=("Arial", 11, "bold"))

        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT invoice_no, customer_name, customer_phone, bill_date, grand_total FROM bills ORDER BY id DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            tree.insert("", tk.END, values=row)

        scrollbar = ttk.Scrollbar(recent_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(fill=tk.BOTH, expand=True)

    def update_time(self):
        now = datetime.now()
        self.time_label.config(text=now.strftime("🕐 %H:%M:%S"))
        self.date_label.config(text=now.strftime("📅 %d-%m-%Y"))
        self.after(1000, self.update_time)

    def open_employees(self):
        EmployeeWindow(self)

    def open_suppliers(self):
        SupplierWindow(self)

    def open_products(self):
        ProductWindow(self)

    def open_categories(self):
        CategoryWindow(self)

    def open_billing(self):
        BillingWindow(self)

    def open_bills(self):
        BillsWindow(self)


# ==================== EMPLOYEE MODULE ====================
class EmployeeWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Employee Management")
        self.geometry("1200x700")
        self.configure(bg="#1a1a2e")
        self.photo_path = tk.StringVar()
        self.photo_label = None
        self.selected_id = None
        self.build_ui()
        self.load_employees()

    def build_ui(self):
        title = tk.Label(self, text="Employee Management", font=("Arial", 18, "bold"), bg="#1a1a2e", fg="#e94560")
        title.pack(pady=10)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left form
        form_frame = tk.LabelFrame(main, text="Employee Details", font=("Arial", 12, "bold"),
                                   bg="#16213e", fg="white", padx=10, pady=10)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        fields = [
            ("Employee ID", "emp_id"),
            ("Name", "name"),
            ("Email", "email"),
            ("Phone", "phone"),
            ("Address", "address"),
            ("Date of Birth", "dob"),
            ("Date of Joining", "doj"),
            ("Department", "department"),
            ("Designation", "designation"),
            ("Salary", "salary"),
        ]

        self.vars = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label + ":", bg="#16213e", fg="white", font=("Arial", 10)).grid(
                row=i, column=0, sticky=tk.W, pady=3)
            var = tk.StringVar()
            self.vars[key] = var
            tk.Entry(form_frame, textvariable=var, width=25, bg="#0f3460", fg="white",
                     insertbackground="white").grid(row=i, column=1, pady=3, padx=5)

        # Gender
        tk.Label(form_frame, text="Gender:", bg="#16213e", fg="white", font=("Arial", 10)).grid(
            row=len(fields), column=0, sticky=tk.W, pady=3)
        self.gender_var = tk.StringVar(value="Male")
        gender_combo = ttk.Combobox(form_frame, textvariable=self.gender_var,
                                    values=["Male", "Female", "Other"], width=23, state="readonly")
        gender_combo.grid(row=len(fields), column=1, pady=3, padx=5)

        # Photo
        tk.Label(form_frame, text="Photo:", bg="#16213e", fg="white", font=("Arial", 10)).grid(
            row=len(fields) + 1, column=0, sticky=tk.W, pady=3)
        photo_btn = tk.Button(form_frame, text="Browse Photo", command=self.browse_photo,
                              bg="#e94560", fg="white", font=("Arial", 9))
        photo_btn.grid(row=len(fields) + 1, column=1, pady=3, padx=5, sticky=tk.W)

        self.photo_display = tk.Label(form_frame, bg="#16213e", text="No Photo", fg="gray")
        self.photo_display.grid(row=len(fields) + 2, column=0, columnspan=2, pady=5)

        # Buttons
        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=len(fields) + 3, column=0, columnspan=2, pady=10)

        buttons = [
            ("Add", self.add_employee, "#05c46b"),
            ("Update", self.update_employee, "#f53b57"),
            ("Delete", self.delete_employee, "#e94560"),
            ("Clear", self.clear_form, "#0f3460"),
        ]
        for text, cmd, color in buttons:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=3)

        # Right table
        table_frame = tk.LabelFrame(main, text="Employee List", font=("Arial", 12, "bold"),
                                    bg="#16213e", fg="white", padx=5, pady=5)
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        # Search
        search_frame = tk.Frame(table_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_employees())
        tk.Entry(search_frame, textvariable=self.search_var, bg="#0f3460", fg="white",
                 insertbackground="white", width=30).pack(side=tk.LEFT, padx=5)

        cols = ("ID", "Emp ID", "Name", "Email", "Phone", "Department", "Designation", "Salary")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=20)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        style = ttk.Style()
        style.configure("Treeview", background="#16213e", foreground="white",
                        fieldbackground="#16213e", rowheight=25)
        style.configure("Treeview.Heading", background="#0f3460", foreground="white",
                        font=("Arial", 10, "bold"))

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<ButtonRelease-1>", self.select_employee)

    def browse_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif")])
        if path:
            self.photo_path.set(path)
            img = Image.open(path).resize((80, 80))
            photo = ImageTk.PhotoImage(img)
            self.photo_display.config(image=photo, text="")
            self.photo_display.image = photo

    def generate_emp_id(self):
        return "EMP" + "".join(random.choices(string.digits, k=4))

    def add_employee(self):
        if not self.vars["name"].get():
            messagebox.showerror("Error", "Name is required!")
            return
        emp_id = self.vars["emp_id"].get() or self.generate_emp_id()
        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO employees (emp_id, name, email, phone, address, gender, dob, doj,
                department, designation, salary, photo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                emp_id, self.vars["name"].get(), self.vars["email"].get(),
                self.vars["phone"].get(), self.vars["address"].get(),
                self.gender_var.get(), self.vars["dob"].get(), self.vars["doj"].get(),
                self.vars["department"].get(), self.vars["designation"].get(),
                self.vars["salary"].get(), self.photo_path.get()
            ))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee added successfully!")
            self.clear_form()
            self.load_employees()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Employee ID already exists!")

    def update_employee(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select an employee to update!")
            return
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE employees SET emp_id=?, name=?, email=?, phone=?, address=?, gender=?,
            dob=?, doj=?, department=?, designation=?, salary=?, photo=? WHERE id=?
        """, (
            self.vars["emp_id"].get(), self.vars["name"].get(), self.vars["email"].get(),
            self.vars["phone"].get(), self.vars["address"].get(), self.gender_var.get(),
            self.vars["dob"].get(), self.vars["doj"].get(), self.vars["department"].get(),
            self.vars["designation"].get(), self.vars["salary"].get(),
            self.photo_path.get(), self.selected_id
        ))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Employee updated successfully!")
        self.clear_form()
        self.load_employees()

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
            self.load_employees()

    def clear_form(self):
        for var in self.vars.values():
            var.set("")
        self.gender_var.set("Male")
        self.photo_path.set("")
        self.photo_display.config(image="", text="No Photo")
        self.photo_display.image = None
        self.selected_id = None

    def load_employees(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, emp_id, name, email, phone, department, designation, salary FROM employees")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_employees(self):
        query = self.search_var.get().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, emp_id, name, email, phone, department, designation, salary
            FROM employees WHERE LOWER(name) LIKE ? OR LOWER(emp_id) LIKE ?
        """, (f"%{query}%", f"%{query}%"))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_employee(self, event):
        selected = self.tree.focus()
        if selected:
            values = self.tree.item(selected, "values")
            if values:
                self.selected_id = values[0]
                conn = sqlite3.connect("inventory.db")
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM employees WHERE id=?", (self.selected_id,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    keys = ["emp_id", "name", "email", "phone", "address", "gender",
                            "dob", "doj", "department", "designation", "salary"]
                    for i, key in enumerate(keys):
                        if key == "gender":
                            self.gender_var.set(row[i + 1])
                        else:
                            self.vars[key].set(row[i + 1] if row[i + 1] else "")
                    if row[12]:
                        self.photo_path.set(row[12])
                        try:
                            img = Image.open(row[12]).resize((80, 80))
                            photo = ImageTk.PhotoImage(img)
                            self.photo_display.config(image=photo, text="")
                            self.photo_display.image = photo
                        except Exception:
                            pass


# ==================== SUPPLIER MODULE ====================
class SupplierWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Supplier Management")
        self.geometry("1100x650")
        self.configure(bg="#1a1a2e")
        self.selected_id = None
        self.build_ui()
        self.load_suppliers()

    def build_ui(self):
        tk.Label(self, text="Supplier Management", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(pady=10)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        form_frame = tk.LabelFrame(main, text="Supplier Details", font=("Arial", 12, "bold"),
                                   bg="#16213e", fg="white", padx=10, pady=10)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        fields = [
            ("Supplier ID", "sup_id"),
            ("Name", "name"),
            ("Contact", "contact"),
            ("Email", "email"),
            ("Address", "address"),
            ("Company", "company"),
            ("GST No", "gst"),
        ]

        self.vars = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label + ":", bg="#16213e", fg="white",
                     font=("Arial", 10)).grid(row=i, column=0, sticky=tk.W, pady=5)
            var = tk.StringVar()
            self.vars[key] = var
            tk.Entry(form_frame, textvariable=var, width=25, bg="#0f3460", fg="white",
                     insertbackground="white").grid(row=i, column=1, pady=5, padx=5)

        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)

        buttons = [
            ("Add", self.add_supplier, "#05c46b"),
            ("Update", self.update_supplier, "#f53b57"),
            ("Delete", self.delete_supplier, "#e94560"),
            ("Clear", self.clear_form, "#0f3460"),
        ]
        for text, cmd, color in buttons:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=3)

        table_frame = tk.LabelFrame(main, text="Supplier List", font=("Arial", 12, "bold"),
                                    bg="#16213e", fg="white", padx=5, pady=5)
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        search_frame = tk.Frame(table_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_suppliers())
        tk.Entry(search_frame, textvariable=self.search_var, bg="#0f3460", fg="white",
                 insertbackground="white", width=30).pack(side=tk.LEFT, padx=5)

        cols = ("ID", "Sup ID", "Name", "Contact", "Email", "Company", "GST")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=20)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<ButtonRelease-1>", self.select_supplier)

    def add_supplier(self):
        if not self.vars["name"].get():
            messagebox.showerror("Error", "Name is required!")
            return
        sup_id = self.vars["sup_id"].get() or "SUP" + "".join(random.choices(string.digits, k=4))
        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO suppliers (sup_id, name, contact, email, address, company, gst)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (sup_id, self.vars["name"].get(), self.vars["contact"].get(),
                  self.vars["email"].get(), self.vars["address"].get(),
                  self.vars["company"].get(), self.vars["gst"].get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier added successfully!")
            self.clear_form()
            self.load_suppliers()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Supplier ID already exists!")

    def update_supplier(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a supplier to update!")
            return
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE suppliers SET sup_id=?, name=?, contact=?, email=?, address=?, company=?, gst=?
            WHERE id=?
        """, (self.vars["sup_id"].get(), self.vars["name"].get(), self.vars["contact"].get(),
              self.vars["email"].get(), self.vars["address"].get(),
              self.vars["company"].get(), self.vars["gst"].get(), self.selected_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Supplier updated successfully!")
        self.clear_form()
        self.load_suppliers()

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
            self.load_suppliers()

    def clear_form(self):
        for var in self.vars.values():
            var.set("")
        self.selected_id = None

    def load_suppliers(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, sup_id, name, contact, email, company, gst FROM suppliers")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_suppliers(self):
        query = self.search_var.get().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, sup_id, name, contact, email, company, gst
            FROM suppliers WHERE LOWER(name) LIKE ? OR LOWER(sup_id) LIKE ?
        """, (f"%{query}%", f"%{query}%"))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_supplier(self, event):
        selected = self.tree.focus()
        if selected:
            values = self.tree.item(selected, "values")
            if values:
                self.selected_id = values[0]
                conn = sqlite3.connect("inventory.db")
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM suppliers WHERE id=?", (self.selected_id,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    keys = ["sup_id", "name", "contact", "email", "address", "company", "gst"]
                    for i, key in enumerate(keys):
                        self.vars[key].set(row[i + 1] if row[i + 1] else "")


# ==================== CATEGORY MODULE ====================
class CategoryWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Category Management")
        self.geometry("900x600")
        self.configure(bg="#1a1a2e")
        self.selected_id = None
        self.build_ui()
        self.load_categories()

    def build_ui(self):
        tk.Label(self, text="Category Management", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(pady=10)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        form_frame = tk.LabelFrame(main, text="Category Details", font=("Arial", 12, "bold"),
                                   bg="#16213e", fg="white", padx=10, pady=10)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        fields = [
            ("Category ID", "cat_id"),
            ("Name", "name"),
            ("Description", "description"),
        ]

        self.vars = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label + ":", bg="#16213e", fg="white",
                     font=("Arial", 10)).grid(row=i, column=0, sticky=tk.W, pady=8)
            var = tk.StringVar()
            self.vars[key] = var
            tk.Entry(form_frame, textvariable=var, width=25, bg="#0f3460", fg="white",
                     insertbackground="white").grid(row=i, column=1, pady=8, padx=5)

        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)

        buttons = [
            ("Add", self.add_category, "#05c46b"),
            ("Update", self.update_category, "#f53b57"),
            ("Delete", self.delete_category, "#e94560"),
            ("Clear", self.clear_form, "#0f3460"),
        ]
        for text, cmd, color in buttons:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=3)

        table_frame = tk.LabelFrame(main, text="Category List", font=("Arial", 12, "bold"),
                                    bg="#16213e", fg="white", padx=5, pady=5)
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        cols = ("ID", "Cat ID", "Name", "Description")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=20)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<ButtonRelease-1>", self.select_category)

    def add_category(self):
        if not self.vars["name"].get():
            messagebox.showerror("Error", "Name is required!")
            return
        cat_id = self.vars["cat_id"].get() or "CAT" + "".join(random.choices(string.digits, k=4))
        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO categories (cat_id, name, description) VALUES (?, ?, ?)",
                           (cat_id, self.vars["name"].get(), self.vars["description"].get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category added successfully!")
            self.clear_form()
            self.load_categories()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Category ID already exists!")

    def update_category(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a category to update!")
            return
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE categories SET cat_id=?, name=?, description=? WHERE id=?",
                       (self.vars["cat_id"].get(), self.vars["name"].get(),
                        self.vars["description"].get(), self.selected_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Category updated successfully!")
        self.clear_form()
        self.load_categories()

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
            self.load_categories()

    def clear_form(self):
        for var in self.vars.values():
            var.set("")
        self.selected_id = None

    def load_categories(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, cat_id, name, description FROM categories")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_category(self, event):
        selected = self.tree.focus()
        if selected:
            values = self.tree.item(selected, "values")
            if values:
                self.selected_id = values[0]
                conn = sqlite3.connect("inventory.db")
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM categories WHERE id=?", (self.selected_id,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    keys = ["cat_id", "name", "description"]
                    for i, key in enumerate(keys):
                        self.vars[key].set(row[i + 1] if row[i + 1] else "")


# ==================== PRODUCT MODULE ====================
class ProductWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Product Management")
        self.geometry("1200x700")
        self.configure(bg="#1a1a2e")
        self.selected_id = None
        self.build_ui()
        self.load_products()

    def get_categories(self):
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories")
        cats = [row[0] for row in cursor.fetchall()]
        conn.close()
        return cats

    def get_suppliers(self):
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM suppliers")
        sups = [row[0] for row in cursor.fetchall()]
        conn.close()
        return sups

    def build_ui(self):
        tk.Label(self, text="Product Management", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(pady=10)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        form_frame = tk.LabelFrame(main, text="Product Details", font=("Arial", 12, "bold"),
                                   bg="#16213e", fg="white", padx=10, pady=10)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        text_fields = [
            ("Product ID", "prod_id"),
            ("Name", "name"),
            ("Price", "price"),
            ("Quantity", "quantity"),
            ("Description", "description"),
        ]

        self.vars = {}
        row_idx = 0
        for label, key in text_fields:
            tk.Label(form_frame, text=label + ":", bg="#16213e", fg="white",
                     font=("Arial", 10)).grid(row=row_idx, column=0, sticky=tk.W, pady=5)
            var = tk.StringVar()
            self.vars[key] = var
            tk.Entry(form_frame, textvariable=var, width=25, bg="#0f3460", fg="white",
                     insertbackground="white").grid(row=row_idx, column=1, pady=5, padx=5)
            row_idx += 1

        tk.Label(form_frame, text="Category:", bg="#16213e", fg="white",
                 font=("Arial", 10)).grid(row=row_idx, column=0, sticky=tk.W, pady=5)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(form_frame, textvariable=self.category_var,
                                           values=self.get_categories(), width=23, state="readonly")
        self.category_combo.grid(row=row_idx, column=1, pady=5, padx=5)
        row_idx += 1

        tk.Label(form_frame, text="Supplier:", bg="#16213e", fg="white",
                 font=("Arial", 10)).grid(row=row_idx, column=0, sticky=tk.W, pady=5)
        self.supplier_var = tk.StringVar()
        self.supplier_combo = ttk.Combobox(form_frame, textvariable=self.supplier_var,
                                           values=self.get_suppliers(), width=23, state="readonly")
        self.supplier_combo.grid(row=row_idx, column=1, pady=5, padx=5)
        row_idx += 1

        tk.Label(form_frame, text="Status:", bg="#16213e", fg="white",
                 font=("Arial", 10)).grid(row=row_idx, column=0, sticky=tk.W, pady=5)
        self.status_var = tk.StringVar(value="Active")
        ttk.Combobox(form_frame, textvariable=self.status_var,
                     values=["Active", "Inactive"], width=23, state="readonly").grid(
            row=row_idx, column=1, pady=5, padx=5)
        row_idx += 1

        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=row_idx, column=0, columnspan=2, pady=10)

        buttons = [
            ("Add", self.add_product, "#05c46b"),
            ("Update", self.update_product, "#f53b57"),
            ("Delete", self.delete_product, "#e94560"),
            ("Clear", self.clear_form, "#0f3460"),
        ]
        for text, cmd, color in buttons:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=3)

        table_frame = tk.LabelFrame(main, text="Product List", font=("Arial", 12, "bold"),
                                    bg="#16213e", fg="white", padx=5, pady=5)
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        search_frame = tk.Frame(table_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_products())
        tk.Entry(search_frame, textvariable=self.search_var, bg="#0f3460", fg="white",
                 insertbackground="white", width=30).pack(side=tk.LEFT, padx=5)

        cols = ("ID", "Prod ID", "Name", "Category", "Supplier", "Price", "Quantity", "Status")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=20)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<ButtonRelease-1>", self.select_product)

    def add_product(self):
        if not self.vars["name"].get():
            messagebox.showerror("Error", "Name is required!")
            return
        prod_id = self.vars["prod_id"].get() or "PROD" + "".join(random.choices(string.digits, k=4))
        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO products (prod_id, name, category, supplier, price, quantity, description, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (prod_id, self.vars["name"].get(), self.category_var.get(),
                  self.supplier_var.get(), self.vars["price"].get(),
                  self.vars["quantity"].get(), self.vars["description"].get(),
                  self.status_var.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product added successfully!")
            self.clear_form()
            self.load_products()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Product ID already exists!")

    def update_product(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a product to update!")
            return
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE products SET prod_id=?, name=?, category=?, supplier=?, price=?,
            quantity=?, description=?, status=? WHERE id=?
        """, (self.vars["prod_id"].get(), self.vars["name"].get(), self.category_var.get(),
              self.supplier_var.get(), self.vars["price"].get(), self.vars["quantity"].get(),
              self.vars["description"].get(), self.status_var.get(), self.selected_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Product updated successfully!")
        self.clear_form()
        self.load_products()

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
            self.load_products()

    def clear_form(self):
        for var in self.vars.values():
            var.set("")
        self.category_var.set("")
        self.supplier_var.set("")
        self.status_var.set("Active")
        self.selected_id = None

    def load_products(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, prod_id, name, category, supplier, price, quantity, status FROM products")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_products(self):
        query = self.search_var.get().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, prod_id, name, category, supplier, price, quantity, status
            FROM products WHERE LOWER(name) LIKE ? OR LOWER(prod_id) LIKE ?
        """, (f"%{query}%", f"%{query}%"))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_product(self, event):
        selected = self.tree.focus()
        if selected:
            values = self.tree.item(selected, "values")
            if values:
                self.selected_id = values[0]
                conn = sqlite3.connect("inventory.db")
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM products WHERE id=?", (self.selected_id,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    self.vars["prod_id"].set(row[1])
                    self.vars["name"].set(row[2])
                    self.category_var.set(row[3] or "")
                    self.supplier_var.set(row[4] or "")
                    self.vars["price"].set(row[5] or "")
                    self.vars["quantity"].set(row[6] or "")
                    self.vars["description"].set(row[7] or "")
                    self.status_var.set(row[8] or "Active")


# ==================== BILLING MODULE ====================
class BillingWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Billing")
        self.geometry("1300x750")
        self.configure(bg="#1a1a2e")
        self.cart_items = []
        self.build_ui()

    def get_products(self):
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name, price FROM products WHERE status='Active'")
        products = cursor.fetchall()
        conn.close()
        return products

    def build_ui(self):
        tk.Label(self, text="Billing / Invoice", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(pady=10)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left panel - Customer & Product
        left = tk.Frame(main, bg="#1a1a2e")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Customer info
        cust_frame = tk.LabelFrame(left, text="Customer Details", font=("Arial", 12, "bold"),
                                   bg="#16213e", fg="white", padx=10, pady=10)
        cust_frame.pack(fill=tk.X, pady=5)

        cust_fields = [("Customer Name", "cust_name"), ("Phone", "cust_phone"), ("Email", "cust_email")]
        self.cust_vars = {}
        for i, (label, key) in enumerate(cust_fields):
            tk.Label(cust_frame, text=label + ":", bg="#16213e", fg="white",
                     font=("Arial", 10)).grid(row=i, column=0, sticky=tk.W, pady=5)
            var = tk.StringVar()
            self.cust_vars[key] = var
            tk.Entry(cust_frame, textvariable=var, width=25, bg="#0f3460", fg="white",
                     insertbackground="white").grid(row=i, column=1, pady=5, padx=5)

        # Invoice info
        inv_frame = tk.LabelFrame(left, text="Invoice Details", font=("Arial", 12, "bold"),
                                  bg="#16213e", fg="white", padx=10, pady=10)
        inv_frame.pack(fill=tk.X, pady=5)

        self.invoice_var = tk.StringVar(value=self.generate_invoice())
        tk.Label(inv_frame, text="Invoice No:", bg="#16213e", fg="white").grid(row=0, column=0, sticky=tk.W)
        tk.Entry(inv_frame, textvariable=self.invoice_var, width=25, bg="#0f3460", fg="white",
                 insertbackground="white").grid(row=0, column=1, padx=5, pady=3)

        self.date_var = tk.StringVar(value=datetime.now().strftime("%d-%m-%Y %H:%M"))
        tk.Label(inv_frame, text="Date:", bg="#16213e", fg="white").grid(row=1, column=0, sticky=tk.W)
        tk.Entry(inv_frame, textvariable=self.date_var, width=25, bg="#0f3460", fg="white",
                 insertbackground="white", state="readonly").grid(row=1, column=1, padx=5, pady=3)

        # Product selection
        prod_frame = tk.LabelFrame(left, text="Add Product", font=("Arial", 12, "bold"),
                                   bg="#16213e", fg="white", padx=10, pady=10)
        prod_frame.pack(fill=tk.X, pady=5)

        products = self.get_products()
        product_names = [p[0] for p in products]
        self.product_prices = {p[0]: p[1] for p in products}

        tk.Label(prod_frame, text="Product:", bg="#16213e", fg="white").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.prod_var = tk.StringVar()
        self.prod_combo = ttk.Combobox(prod_frame, textvariable=self.prod_var,
                                       values=product_names, width=22, state="readonly")
        self.prod_combo.grid(row=0, column=1, pady=5, padx=5)
        self.prod_combo.bind("<<ComboboxSelected>>", self.on_product_select)

        tk.Label(prod_frame, text="Price:", bg="#16213e", fg="white").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.price_var = tk.StringVar()
        tk.Entry(prod_frame, textvariable=self.price_var, width=25, bg="#0f3460", fg="white",
                 insertbackground="white").grid(row=1, column=1, pady=5, padx=5)

        tk.Label(prod_frame, text="Quantity:", bg="#16213e", fg="white").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.qty_var = tk.StringVar(value="1")
        tk.Entry(prod_frame, textvariable=self.qty_var, width=25, bg="#0f3460", fg="white",
                 insertbackground="white").grid(row=2, column=1, pady=5, padx=5)

        tk.Button(prod_frame, text="Add to Cart", command=self.add_to_cart,
                  bg="#05c46b", fg="white", font=("Arial", 11, "bold"), width=20).grid(
            row=3, column=0, columnspan=2, pady=10)

        # Tax
        tax_frame = tk.LabelFrame(left, text="Tax & Discount", font=("Arial", 12, "bold"),
                                  bg="#16213e", fg="white", padx=10, pady=10)
        tax_frame.pack(fill=tk.X, pady=5)

        tk.Label(tax_frame, text="Tax (%):", bg="#16213e", fg="white").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.tax_var = tk.StringVar(value="18")
        tk.Entry(tax_frame, textvariable=self.tax_var, width=25, bg="#0f3460", fg="white",
                 insertbackground="white").grid(row=0, column=1, pady=5, padx=5)

        # Right panel - Cart & Bill
        right = tk.Frame(main, bg="#1a1a2e")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        cart_frame = tk.LabelFrame(right, text="Cart", font=("Arial", 12, "bold"),
                                   bg="#16213e", fg="white", padx=5, pady=5)
        cart_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        cols = ("Product", "Price", "Quantity", "Total")
        self.cart_tree = ttk.Treeview(cart_frame, columns=cols, show="headings", height=12)
        for col in cols:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=150)

        cart_scroll = ttk.Scrollbar(cart_frame, orient=tk.VERTICAL, command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=cart_scroll.set)
        cart_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.cart_tree.pack(fill=tk.BOTH, expand=True)

        # Remove from cart
        tk.Button(cart_frame, text="Remove Selected", command=self.remove_from_cart,
                  bg="#e94560", fg="white", font=("Arial", 10, "bold")).pack(pady=5)

        # Bill summary
        summary_frame = tk.LabelFrame(right, text="Bill Summary", font=("Arial", 12, "bold"),
                                      bg="#16213e", fg="white", padx=10, pady=10)
        summary_frame.pack(fill=tk.X, pady=5)

        self.subtotal_var = tk.StringVar(value="₹0.00")
        self.tax_amount_var = tk.StringVar(value="₹0.00")
        self.grand_total_var = tk.StringVar(value="₹0.00")

        summary_items = [
            ("Subtotal:", self.subtotal_var),
            ("Tax Amount:", self.tax_amount_var),
            ("Grand Total:", self.grand_total_var),
        ]

        for i, (label, var) in enumerate(summary_items):
            tk.Label(summary_frame, text=label, bg="#16213e", fg="white",
                     font=("Arial", 12, "bold")).grid(row=i, column=0, sticky=tk.W, pady=5, padx=10)
            tk.Label(summary_frame, textvariable=var, bg="#16213e", fg="#05c46b",
                     font=("Arial", 12, "bold")).grid(row=i, column=1, sticky=tk.W, pady=5, padx=10)

        # Action buttons
        btn_frame = tk.Frame(right, bg="#1a1a2e")
        btn_frame.pack(fill=tk.X, pady=10)

        tk.Button(btn_frame, text="💾 Save Bill", command=self.save_bill,
                  bg="#05c46b", fg="white", font=("Arial", 12, "bold"), width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🖨️ Print Bill", command=self.print_bill,
                  bg="#0f3460", fg="white", font=("Arial", 12, "bold"), width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🗑️ Clear All", command=self.clear_all,
                  bg="#e94560", fg="white", font=("Arial", 12, "bold"), width=15).pack(side=tk.LEFT, padx=5)

    def generate_invoice(self):
        return "INV" + datetime.now().strftime("%Y%m%d%H%M%S")

    def on_product_select(self, event):
        product = self.prod_var.get()
        if product in self.product_prices:
            self.price_var.set(str(self.product_prices[product]))

    def add_to_cart(self):
        product = self.prod_var.get()
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
        self.cart_items.append((product, price, qty, total))
        self.cart_tree.insert("", tk.END, values=(product, f"₹{price:.2f}", qty, f"₹{total:.2f}"))
        self.update_summary()
        self.prod_var.set("")
        self.price_var.set("")
        self.qty_var.set("1")

    def remove_from_cart(self):
        selected = self.cart_tree.focus()
        if selected:
            idx = self.cart_tree.index(selected)
            self.cart_tree.delete(selected)
            if 0 <= idx < len(self.cart_items):
                self.cart_items.pop(idx)
            self.update_summary()

    def update_summary(self):
        subtotal = sum(item[3] for item in self.cart_items)
        try:
            tax_pct = float(self.tax_var.get())
        except ValueError:
            tax_pct = 0
        tax_amount = subtotal * tax_pct / 100
        grand_total = subtotal + tax_amount
        self.subtotal_var.set(f"₹{subtotal:.2f}")
        self.tax_amount_var.set(f"₹{tax_amount:.2f}")
        self.grand_total_var.set(f"₹{grand_total:.2f}")

    def save_bill(self):
        if not self.cart_items:
            messagebox.showerror("Error", "Cart is empty!")
            return
        if not self.cust_vars["cust_name"].get():
            messagebox.showerror("Error", "Customer name is required!")
            return

        subtotal = sum(item[3] for item in self.cart_items)
        try:
            tax_pct = float(self.tax_var.get())
        except ValueError:
            tax_pct = 0
        tax_amount = subtotal * tax_pct / 100
        grand_total = subtotal + tax_amount

        bill_data = str(self.cart_items)

        try:
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bills (invoice_no, customer_name, customer_phone, customer_email,
                bill_date, total, tax, grand_total, bill_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.invoice_var.get(),
                self.cust_vars["cust_name"].get(),
                self.cust_vars["cust_phone"].get(),
                self.cust_vars["cust_email"].get(),
                self.date_var.get(),
                subtotal,
                tax_amount,
                grand_total,
                bill_data
            ))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Bill saved! Invoice: {self.invoice_var.get()}")
            self.clear_all()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Invoice number already exists!")

    def print_bill(self):
        if not self.cart_items:
            messagebox.showerror("Error", "Cart is empty!")
            return

        subtotal = sum(item[3] for item in self.cart_items)
        try:
            tax_pct = float(self.tax_var.get())
        except ValueError:
            tax_pct = 0
        tax_amount = subtotal * tax_pct / 100
        grand_total = subtotal + tax_amount

        bill_win = tk.Toplevel(self)
        bill_win.title("Bill Preview")
        bill_win.geometry("500x600")
        bill_win.configure(bg="white")

        text = tk.Text(bill_win, bg="white", fg="black", font=("Courier", 11))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        bill_text = f"""
{'='*50}
        INVENTORY MANAGEMENT SYSTEM
              INVOICE / BILL
{'='*50}
Invoice No : {self.invoice_var.get()}
Date       : {self.date_var.get()}
Customer   : {self.cust_vars['cust_name'].get()}
Phone      : {self.cust_vars['cust_phone'].get()}
Email      : {self.cust_vars['cust_email'].get()}
{'='*50}
{'Product':<20} {'Price':>8} {'Qty':>5} {'Total':>10}
{'-'*50}
"""
        for item in self.cart_items:
            bill_text += f"{item[0]:<20} {item[1]:>8.2f} {item[2]:>5} {item[3]:>10.2f}\n"

        bill_text += f"""
{'-'*50}
{'Subtotal:':<35} {subtotal:>10.2f}
{'Tax (' + self.tax_var.get() + '%):':<35} {tax_amount:>10.2f}
{'Grand Total:':<35} {grand_total:>10.2f}
{'='*50}
        Thank you for your purchase!
{'='*50}
"""
        text.insert(tk.END, bill_text)
        text.config(state=tk.DISABLED)

        tk.Button(bill_win, text="Close", command=bill_win.destroy,
                  bg="#e94560", fg="white", font=("Arial", 11, "bold")).pack(pady=5)

    def clear_all(self):
        for var in self.cust_vars.values():
            var.set("")
        self.invoice_var.set(self.generate_invoice())
        self.date_var.set(datetime.now().strftime("%d-%m-%Y %H:%M"))
        self.prod_var.set("")
        self.price_var.set("")
        self.qty_var.set("1")
        self.tax_var.set("18")
        self.cart_items.clear()
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        self.update_summary()


# ==================== BILLS MODULE ====================
class BillsWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Bills / Invoices")
        self.geometry("1100x650")
        self.configure(bg="#1a1a2e")
        self.build_ui()
        self.load_bills()

    def build_ui(self):
        tk.Label(self, text="Bills & Invoices", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="#e94560").pack(pady=10)

        # Search
        search_frame = tk.Frame(self, bg="#1a1a2e")
        search_frame.pack(fill=tk.X, padx=20, pady=5)
        tk.Label(search_frame, text="Search Invoice:", bg="#1a1a2e", fg="white",
                 font=("Arial", 11)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_bills())
        tk.Entry(search_frame, textvariable=self.search_var, bg="#0f3460", fg="white",
                 insertbackground="white", width=30, font=("Arial", 11)).pack(side=tk.LEFT, padx=10)

        tk.Button(search_frame, text="View Bill", command=self.view_bill,
                  bg="#0f3460", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Delete Bill", command=self.delete_bill,
                  bg="#e94560", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

        # Table
        table_frame = tk.Frame(self, bg="#1a1a2e")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        cols = ("ID", "Invoice No", "Customer", "Phone", "Email", "Date", "Subtotal", "Tax", "Grand Total")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=20)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)

        style = ttk.Style()
        style.configure("Treeview", background="#16213e", foreground="white",
                        fieldbackground="#16213e", rowheight=28)
        style.configure("Treeview.Heading", background="#0f3460", foreground="white",
                        font=("Arial", 10, "bold"))

        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)

    def load_bills(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, invoice_no, customer_name, customer_phone, customer_email,
            bill_date, total, tax, grand_total FROM bills ORDER BY id DESC
        """)
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_bills(self):
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
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def view_bill(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showerror("Error", "Please select a bill to view!")
            return
        values = self.tree.item(selected, "values")
        bill_id = values[0]

        conn = sqlite3.connect("inventory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bills WHERE id=?", (bill_id,))
        bill = cursor.fetchone()
        conn.close()

        if bill:
            view_win = tk.Toplevel(self)
            view_win.title(f"Bill - {bill[1]}")
            view_win.geometry("500x600")
            view_win.configure(bg="white")

            text = tk.Text(view_win, bg="white", fg="black", font=("Courier", 11))
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            try:
                import ast
                items = ast.literal_eval(bill[9])
            except Exception:
                items = []

            bill_text = f"""
{'='*50}
        INVENTORY MANAGEMENT SYSTEM
              INVOICE / BILL
{'='*50}
Invoice No : {bill[1]}
Date       : {bill[5]}
Customer   : {bill[2]}
Phone      : {bill[3]}
Email      : {bill[4]}
{'='*50}
{'Product':<20} {'Price':>8} {'Qty':>5} {'Total':>10}
{'-'*50}
"""
            for item in items:
                bill_text += f"{str(item[0]):<20} {float(item[1]):>8.2f} {int(item[2]):>5} {float(item[3]):>10.2f}\n"

            bill_text += f"""
{'-'*50}
{'Subtotal:':<35} {float(bill[6]):>10.2f}
{'Tax:':<35} {float(bill[7]):>10.2f}
{'Grand Total:':<35} {float(bill[8]):>10.2f}
{'='*50}
        Thank you for your purchase!
{'='*50}
"""
            text.insert(tk.END, bill_text)
            text.config(state=tk.DISABLED)
            tk.Button(view_win, text="Close", command=view_win.destroy,
                      bg="#e94560", fg="white", font=("Arial", 11, "bold")).pack(pady=5)

    def delete_bill(self):
        selected = self.tree.focus()
        if not selected:
            messagebox.showerror("Error", "Please select a bill to delete!")
            return
        values = self.tree.item(selected, "values")
        if messagebox.askyesno("Confirm", f"Delete invoice {values[1]}?"):
            conn = sqlite3.connect("inventory.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bills WHERE id=?", (values[0],))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Bill deleted successfully!")
            self.load_bills()


# ==================== MAIN ====================
if __name__ == "__main__":
    app = Dashboard()
    app.mainloop()