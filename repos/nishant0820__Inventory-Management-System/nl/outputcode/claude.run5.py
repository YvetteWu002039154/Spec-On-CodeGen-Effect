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
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        address TEXT,
        company TEXT,
        contact_person TEXT,
        description TEXT
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
        bill_details TEXT
    )''')

    conn.commit()
    conn.close()


create_database()


# Main Application
class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1400x800")
        self.resizable(True, True)
        self.configure(bg="#1a1a2e")

        self.current_frame = None
        self.show_dashboard()

    def show_frame(self, frame_class):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = frame_class(self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_dashboard(self):
        self.show_frame(Dashboard)

    def show_employee(self):
        self.show_frame(EmployeeManagement)

    def show_supplier(self):
        self.show_frame(SupplierManagement)

    def show_category(self):
        self.show_frame(CategoryManagement)

    def show_product(self):
        self.show_frame(ProductManagement)

    def show_billing(self):
        self.show_frame(BillingManagement)


# Sidebar Navigation
class Sidebar(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#16213e", width=220)
        self.app = app
        self.pack_propagate(False)
        self.create_widgets()

    def create_widgets(self):
        # Logo
        logo_frame = tk.Frame(self, bg="#0f3460", pady=20)
        logo_frame.pack(fill=tk.X)
        tk.Label(logo_frame, text="📦", font=("Arial", 30), bg="#0f3460", fg="white").pack()
        tk.Label(logo_frame, text="Inventory", font=("Arial", 16, "bold"), bg="#0f3460", fg="white").pack()
        tk.Label(logo_frame, text="Management System", font=("Arial", 10), bg="#0f3460", fg="#a0a0b0").pack()

        # Navigation buttons
        nav_items = [
            ("🏠  Dashboard", self.app.show_dashboard),
            ("👤  Employees", self.app.show_employee),
            ("🚚  Suppliers", self.app.show_supplier),
            ("📂  Categories", self.app.show_category),
            ("📦  Products", self.app.show_product),
            ("🧾  Billing", self.app.show_billing),
        ]

        nav_frame = tk.Frame(self, bg="#16213e")
        nav_frame.pack(fill=tk.BOTH, expand=True, pady=20)

        for text, command in nav_items:
            btn = tk.Button(
                nav_frame, text=text, command=command,
                bg="#16213e", fg="white", font=("Arial", 12),
                relief=tk.FLAT, anchor="w", padx=20, pady=12,
                activebackground="#0f3460", activeforeground="white",
                cursor="hand2"
            )
            btn.pack(fill=tk.X)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg="#0f3460"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg="#16213e"))

        # Exit button
        exit_btn = tk.Button(
            self, text="🚪  Exit", command=self.app.quit,
            bg="#e94560", fg="white", font=("Arial", 12),
            relief=tk.FLAT, pady=12, cursor="hand2"
        )
        exit_btn.pack(fill=tk.X, side=tk.BOTTOM)


# Dashboard
class Dashboard(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.parent = parent
        self.create_widgets()
        self.update_time()

    def create_widgets(self):
        # Main layout
        main_frame = tk.Frame(self, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Sidebar
        sidebar = Sidebar(main_frame, self.parent)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)

        # Content area
        content = tk.Frame(main_frame, bg="#1a1a2e")
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Header
        header = tk.Frame(content, bg="#16213e", pady=15)
        header.pack(fill=tk.X)

        tk.Label(header, text="Dashboard", font=("Arial", 22, "bold"),
                 bg="#16213e", fg="white").pack(side=tk.LEFT, padx=20)

        self.time_label = tk.Label(header, text="", font=("Arial", 12),
                                   bg="#16213e", fg="#a0a0b0")
        self.time_label.pack(side=tk.RIGHT, padx=20)

        # Stats cards
        stats_frame = tk.Frame(content, bg="#1a1a2e", pady=20)
        stats_frame.pack(fill=tk.X, padx=20)

        self.create_stat_card(stats_frame, "👤 Employees", self.get_count("employees"), "#e94560", 0)
        self.create_stat_card(stats_frame, "🚚 Suppliers", self.get_count("suppliers"), "#0f3460", 1)
        self.create_stat_card(stats_frame, "📂 Categories", self.get_count("categories"), "#533483", 2)
        self.create_stat_card(stats_frame, "📦 Products", self.get_count("products"), "#05c46b", 3)

        # Recent activity
        activity_frame = tk.Frame(content, bg="#16213e", pady=10)
        activity_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        tk.Label(activity_frame, text="Recent Bills", font=("Arial", 16, "bold"),
                 bg="#16213e", fg="white").pack(anchor="w", padx=15, pady=10)

        # Treeview for recent bills
        tree_frame = tk.Frame(activity_frame, bg="#16213e")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        columns = ("Invoice No", "Customer", "Phone", "Date", "Amount")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#1a1a2e", foreground="white",
                        fieldbackground="#1a1a2e", rowheight=30)
        style.configure("Treeview.Heading", background="#0f3460", foreground="white",
                        font=("Arial", 11, "bold"))

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.load_recent_bills()

    def create_stat_card(self, parent, title, count, color, col):
        card = tk.Frame(parent, bg=color, padx=20, pady=20)
        card.grid(row=0, column=col, padx=10, sticky="ew")
        parent.columnconfigure(col, weight=1)

        tk.Label(card, text=str(count), font=("Arial", 36, "bold"),
                 bg=color, fg="white").pack()
        tk.Label(card, text=title, font=("Arial", 13),
                 bg=color, fg="white").pack()

    def get_count(self, table):
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0

    def load_recent_bills(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT invoice_no, customer_name, customer_phone, bill_date, total_amount FROM bills ORDER BY id DESC LIMIT 10")
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except:
            pass

    def update_time(self):
        now = datetime.now().strftime("%A, %d %B %Y  |  %I:%M:%S %p")
        self.time_label.config(text=now)
        self.after(1000, self.update_time)


# Employee Management
class EmployeeManagement(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.parent = parent
        self.photo_path = tk.StringVar()
        self.photo_image = None
        self.selected_id = None
        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        main_frame = tk.Frame(self, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True)

        sidebar = Sidebar(main_frame, self.parent)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)

        content = tk.Frame(main_frame, bg="#1a1a2e")
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Header
        header = tk.Frame(content, bg="#16213e", pady=15)
        header.pack(fill=tk.X)
        tk.Label(header, text="Employee Management", font=("Arial", 22, "bold"),
                 bg="#16213e", fg="white").pack(side=tk.LEFT, padx=20)

        # Body
        body = tk.Frame(content, bg="#1a1a2e")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - Form
        left = tk.Frame(body, bg="#16213e", padx=15, pady=15)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        tk.Label(left, text="Employee Details", font=("Arial", 14, "bold"),
                 bg="#16213e", fg="white").grid(row=0, column=0, columnspan=2, pady=(0, 15))

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
        for i, (label, key) in enumerate(fields, start=1):
            tk.Label(left, text=label + ":", font=("Arial", 11),
                     bg="#16213e", fg="#a0a0b0").grid(row=i, column=0, sticky="w", pady=4)
            entry = tk.Entry(left, font=("Arial", 11), bg="#1a1a2e", fg="white",
                             insertbackground="white", width=22)
            entry.grid(row=i, column=1, padx=10, pady=4)
            self.entries[key] = entry

        # Gender
        tk.Label(left, text="Gender:", font=("Arial", 11),
                 bg="#16213e", fg="#a0a0b0").grid(row=len(fields)+1, column=0, sticky="w", pady=4)
        self.gender_var = tk.StringVar(value="Male")
        gender_combo = ttk.Combobox(left, textvariable=self.gender_var,
                                    values=["Male", "Female", "Other"], width=20, state="readonly")
        gender_combo.grid(row=len(fields)+1, column=1, padx=10, pady=4)

        # Photo
        tk.Label(left, text="Photo:", font=("Arial", 11),
                 bg="#16213e", fg="#a0a0b0").grid(row=len(fields)+2, column=0, sticky="w", pady=4)
        photo_frame = tk.Frame(left, bg="#16213e")
        photo_frame.grid(row=len(fields)+2, column=1, padx=10, pady=4)
        tk.Button(photo_frame, text="Browse", command=self.browse_photo,
                  bg="#0f3460", fg="white", font=("Arial", 10), relief=tk.FLAT).pack(side=tk.LEFT)
        self.photo_label = tk.Label(photo_frame, text="No file", bg="#16213e", fg="#a0a0b0",
                                    font=("Arial", 9))
        self.photo_label.pack(side=tk.LEFT, padx=5)

        # Photo preview
        self.photo_preview = tk.Label(left, bg="#16213e", text="📷\nNo Photo",
                                      fg="#a0a0b0", font=("Arial", 10))
        self.photo_preview.grid(row=len(fields)+3, column=0, columnspan=2, pady=10)

        # Buttons
        btn_frame = tk.Frame(left, bg="#16213e")
        btn_frame.grid(row=len(fields)+4, column=0, columnspan=2, pady=10)

        buttons = [
            ("Add", self.add_employee, "#05c46b"),
            ("Update", self.update_employee, "#0f3460"),
            ("Delete", self.delete_employee, "#e94560"),
            ("Clear", self.clear_form, "#533483"),
        ]
        for text, cmd, color in buttons:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 11), relief=tk.FLAT, padx=10, pady=5,
                      cursor="hand2").pack(side=tk.LEFT, padx=5)

        # Right panel - Table
        right = tk.Frame(body, bg="#16213e")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Search
        search_frame = tk.Frame(right, bg="#16213e", pady=10)
        search_frame.pack(fill=tk.X, padx=10)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white",
                 font=("Arial", 11)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 11),
                 bg="#1a1a2e", fg="white", insertbackground="white", width=30).pack(side=tk.LEFT, padx=10)

        # Treeview
        tree_frame = tk.Frame(right, bg="#16213e")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("ID", "Emp ID", "Name", "Email", "Phone", "Department", "Designation", "Salary")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")

        style = ttk.Style()
        style.configure("Treeview", background="#1a1a2e", foreground="white",
                        fieldbackground="#1a1a2e", rowheight=28)
        style.configure("Treeview.Heading", background="#0f3460", foreground="white",
                        font=("Arial", 10, "bold"))

        col_widths = [40, 80, 120, 150, 100, 120, 120, 80]
        for col, width in zip(columns, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<ButtonRelease-1>", self.select_record)

    def browse_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif")])
        if path:
            self.photo_path.set(path)
            self.photo_label.config(text=os.path.basename(path))
            try:
                img = Image.open(path).resize((80, 80))
                self.photo_image = ImageTk.PhotoImage(img)
                self.photo_preview.config(image=self.photo_image, text="")
            except:
                pass

    def add_employee(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        data['gender'] = self.gender_var.get()
        data['photo'] = self.photo_path.get()

        if not data['emp_id'] or not data['name']:
            messagebox.showerror("Error", "Employee ID and Name are required!")
            return

        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO employees (emp_id, name, email, phone, address, gender, dob,
                department, designation, salary, join_date, photo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (data['emp_id'], data['name'], data['email'], data['phone'], data['address'],
                 data['gender'], data['dob'], data['department'], data['designation'],
                 data['salary'], data['join_date'], data['photo']))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee added successfully!")
            self.clear_form()
            self.load_data()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Employee ID already exists!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_employee(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a record to update!")
            return

        data = {k: v.get().strip() for k, v in self.entries.items()}
        data['gender'] = self.gender_var.get()
        data['photo'] = self.photo_path.get()

        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''UPDATE employees SET emp_id=?, name=?, email=?, phone=?, address=?,
                gender=?, dob=?, department=?, designation=?, salary=?, join_date=?, photo=?
                WHERE id=?''',
                (data['emp_id'], data['name'], data['email'], data['phone'], data['address'],
                 data['gender'], data['dob'], data['department'], data['designation'],
                 data['salary'], data['join_date'], data['photo'], self.selected_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee updated successfully!")
            self.clear_form()
            self.load_data()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_employee(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a record to delete!")
            return

        if messagebox.askyesno("Confirm", "Are you sure you want to delete this employee?"):
            try:
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute("DELETE FROM employees WHERE id=?", (self.selected_id,))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Employee deleted successfully!")
                self.clear_form()
                self.load_data()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.gender_var.set("Male")
        self.photo_path.set("")
        self.photo_label.config(text="No file")
        self.photo_preview.config(image="", text="📷\nNo Photo")
        self.photo_image = None
        self.selected_id = None

    def select_record(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])['values']
        self.selected_id = values[0]

        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM employees WHERE id=?", (self.selected_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                keys = ['emp_id', 'name', 'email', 'phone', 'address', 'gender', 'dob',
                        'department', 'designation', 'salary', 'join_date', 'photo']
                data = dict(zip(keys, row[1:]))

                for key, entry in self.entries.items():
                    entry.delete(0, tk.END)
                    entry.insert(0, data.get(key, '') or '')

                self.gender_var.set(data.get('gender', 'Male'))
                photo = data.get('photo', '')
                if photo and os.path.exists(photo):
                    self.photo_path.set(photo)
                    self.photo_label.config(text=os.path.basename(photo))
                    try:
                        img = Image.open(photo).resize((80, 80))
                        self.photo_image = ImageTk.PhotoImage(img)
                        self.photo_preview.config(image=self.photo_image, text="")
                    except:
                        pass
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, emp_id, name, email, phone, department, designation, salary FROM employees")
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def search_data(self):
        query = self.search_var.get().strip()
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT id, emp_id, name, email, phone, department, designation, salary
                FROM employees WHERE name LIKE ? OR emp_id LIKE ? OR department LIKE ?''',
                (f'%{query}%', f'%{query}%', f'%{query}%'))
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", str(e))


# Supplier Management
class SupplierManagement(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.parent = parent
        self.selected_id = None
        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        main_frame = tk.Frame(self, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True)

        sidebar = Sidebar(main_frame, self.parent)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)

        content = tk.Frame(main_frame, bg="#1a1a2e")
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        header = tk.Frame(content, bg="#16213e", pady=15)
        header.pack(fill=tk.X)
        tk.Label(header, text="Supplier Management", font=("Arial", 22, "bold"),
                 bg="#16213e", fg="white").pack(side=tk.LEFT, padx=20)

        body = tk.Frame(content, bg="#1a1a2e")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel
        left = tk.Frame(body, bg="#16213e", padx=15, pady=15)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        tk.Label(left, text="Supplier Details", font=("Arial", 14, "bold"),
                 bg="#16213e", fg="white").grid(row=0, column=0, columnspan=2, pady=(0, 15))

        fields = [
            ("Supplier ID", "supplier_id"),
            ("Name", "name"),
            ("Email", "email"),
            ("Phone", "phone"),
            ("Address", "address"),
            ("Company", "company"),
            ("Contact Person", "contact_person"),
            ("Description", "description"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(fields, start=1):
            tk.Label(left, text=label + ":", font=("Arial", 11),
                     bg="#16213e", fg="#a0a0b0").grid(row=i, column=0, sticky="w", pady=4)
            if key == "description":
                entry = tk.Text(left, font=("Arial", 11), bg="#1a1a2e", fg="white",
                                insertbackground="white", width=22, height=3)
            else:
                entry = tk.Entry(left, font=("Arial", 11), bg="#1a1a2e", fg="white",
                                 insertbackground="white", width=22)
            entry.grid(row=i, column=1, padx=10, pady=4)
            self.entries[key] = entry

        btn_frame = tk.Frame(left, bg="#16213e")
        btn_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=10)

        buttons = [
            ("Add", self.add_supplier, "#05c46b"),
            ("Update", self.update_supplier, "#0f3460"),
            ("Delete", self.delete_supplier, "#e94560"),
            ("Clear", self.clear_form, "#533483"),
        ]
        for text, cmd, color in buttons:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 11), relief=tk.FLAT, padx=10, pady=5,
                      cursor="hand2").pack(side=tk.LEFT, padx=5)

        # Right panel
        right = tk.Frame(body, bg="#16213e")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        search_frame = tk.Frame(right, bg="#16213e", pady=10)
        search_frame.pack(fill=tk.X, padx=10)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white",
                 font=("Arial", 11)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 11),
                 bg="#1a1a2e", fg="white", insertbackground="white", width=30).pack(side=tk.LEFT, padx=10)

        tree_frame = tk.Frame(right, bg="#16213e")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("ID", "Supplier ID", "Name", "Email", "Phone", "Company", "Contact Person")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<ButtonRelease-1>", self.select_record)

    def get_text(self, key):
        widget = self.entries[key]
        if isinstance(widget, tk.Text):
            return widget.get("1.0", tk.END).strip()
        return widget.get().strip()

    def set_text(self, key, value):
        widget = self.entries[key]
        if isinstance(widget, tk.Text):
            widget.delete("1.0", tk.END)
            widget.insert("1.0", value or '')
        else:
            widget.delete(0, tk.END)
            widget.insert(0, value or '')

    def add_supplier(self):
        data = {k: self.get_text(k) for k in self.entries}
        if not data['supplier_id'] or not data['name']:
            messagebox.showerror("Error", "Supplier ID and Name are required!")
            return
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO suppliers (supplier_id, name, email, phone, address, company, contact_person, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (data['supplier_id'], data['name'], data['email'], data['phone'],
                 data['address'], data['company'], data['contact_person'], data['description']))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier added successfully!")
            self.clear_form()
            self.load_data()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Supplier ID already exists!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_supplier(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a record to update!")
            return
        data = {k: self.get_text(k) for k in self.entries}
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''UPDATE suppliers SET supplier_id=?, name=?, email=?, phone=?, address=?,
                company=?, contact_person=?, description=? WHERE id=?''',
                (data['supplier_id'], data['name'], data['email'], data['phone'],
                 data['address'], data['company'], data['contact_person'], data['description'],
                 self.selected_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier updated successfully!")
            self.clear_form()
            self.load_data()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_supplier(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a record to delete!")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this supplier?"):
            try:
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute("DELETE FROM suppliers WHERE id=?", (self.selected_id,))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Supplier deleted successfully!")
                self.clear_form()
                self.load_data()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def clear_form(self):
        for key in self.entries:
            self.set_text(key, '')
        self.selected_id = None

    def select_record(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])['values']
        self.selected_id = values[0]
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM suppliers WHERE id=?", (self.selected_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                keys = ['supplier_id', 'name', 'email', 'phone', 'address', 'company', 'contact_person', 'description']
                for key, val in zip(keys, row[1:]):
                    self.set_text(key, val)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, supplier_id, name, email, phone, company, contact_person FROM suppliers")
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def search_data(self):
        query = self.search_var.get().strip()
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT id, supplier_id, name, email, phone, company, contact_person
                FROM suppliers WHERE name LIKE ? OR supplier_id LIKE ? OR company LIKE ?''',
                (f'%{query}%', f'%{query}%', f'%{query}%'))
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", str(e))


# Category Management
class CategoryManagement(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.parent = parent
        self.selected_id = None
        self.create_widgets()
        self.load_data()

    def create_widgets(self):
        main_frame = tk.Frame(self, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True)

        sidebar = Sidebar(main_frame, self.parent)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)

        content = tk.Frame(main_frame, bg="#1a1a2e")
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        header = tk.Frame(content, bg="#16213e", pady=15)
        header.pack(fill=tk.X)
        tk.Label(header, text="Category Management", font=("Arial", 22, "bold"),
                 bg="#16213e", fg="white").pack(side=tk.LEFT, padx=20)

        body = tk.Frame(content, bg="#1a1a2e")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel
        left = tk.Frame(body, bg="#16213e", padx=15, pady=15)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        tk.Label(left, text="Category Details", font=("Arial", 14, "bold"),
                 bg="#16213e", fg="white").grid(row=0, column=0, columnspan=2, pady=(0, 15))

        fields = [
            ("Category ID", "category_id"),
            ("Name", "name"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(fields, start=1):
            tk.Label(left, text=label + ":", font=("Arial", 11),
                     bg="#16213e", fg="#a0a0b0").grid(row=i, column=0, sticky="w", pady=4)
            entry = tk.Entry(left, font=("Arial", 11), bg="#1a1a2e", fg="white",
                             insertbackground="white", width=25)
            entry.grid(row=i, column=1, padx=10, pady=4)
            self.entries[key] = entry

        tk.Label(left, text="Description:", font=("Arial", 11),
                 bg="#16213e", fg="#a0a0b0").grid(row=len(fields)+1, column=0, sticky="nw", pady=4)
        self.desc_text = tk.Text(left, font=("Arial", 11), bg="#1a1a2e", fg="white",
                                 insertbackground="white", width=25, height=5)
        self.desc_text.grid(row=len(fields)+1, column=1, padx=10, pady=4)

        btn_frame = tk.Frame(left, bg="#16213e")
        btn_frame.grid(row=len(fields)+2, column=0, columnspan=2, pady=10)

        buttons = [
            ("Add", self.add_category, "#05c46b"),
            ("Update", self.update_category, "#0f3460"),
            ("Delete", self.delete_category, "#e94560"),
            ("Clear", self.clear_form, "#533483"),
        ]
        for text, cmd, color in buttons:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 11), relief=tk.FLAT, padx=10, pady=5,
                      cursor="hand2").pack(side=tk.LEFT, padx=5)

        # Right panel
        right = tk.Frame(body, bg="#16213e")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        search_frame = tk.Frame(right, bg="#16213e", pady=10)
        search_frame.pack(fill=tk.X, padx=10)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white",
                 font=("Arial", 11)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 11),
                 bg="#1a1a2e", fg="white", insertbackground="white", width=30).pack(side=tk.LEFT, padx=10)

        tree_frame = tk.Frame(right, bg="#16213e")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("ID", "Category ID", "Name", "Description")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")

        col_widths = [50, 120, 200, 300]
        for col, width in zip(columns, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<ButtonRelease-1>", self.select_record)

    def add_category(self):
        cat_id = self.entries['category_id'].get().strip()
        name = self.entries['name'].get().strip()
        desc = self.desc_text.get("1.0", tk.END).strip()

        if not cat_id or not name:
            messagebox.showerror("Error", "Category ID and Name are required!")
            return
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO categories (category_id, name, description) VALUES (?, ?, ?)",
                           (cat_id, name, desc))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category added successfully!")
            self.clear_form()
            self.load_data()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Category ID already exists!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_category(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a record to update!")
            return
        cat_id = self.entries['category_id'].get().strip()
        name = self.entries['name'].get().strip()
        desc = self.desc_text.get("1.0", tk.END).strip()
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("UPDATE categories SET category_id=?, name=?, description=? WHERE id=?",
                           (cat_id, name, desc, self.selected_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category updated successfully!")
            self.clear_form()
            self.load_data()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_category(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a record to delete!")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this category?"):
            try:
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute("DELETE FROM categories WHERE id=?", (self.selected_id,))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Category deleted successfully!")
                self.clear_form()
                self.load_data()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.desc_text.delete("1.0", tk.END)
        self.selected_id = None

    def select_record(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])['values']
        self.selected_id = values[0]
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories WHERE id=?", (self.selected_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                self.entries['category_id'].delete(0, tk.END)
                self.entries['category_id'].insert(0, row[1] or '')
                self.entries['name'].delete(0, tk.END)
                self.entries['name'].insert(0, row[2] or '')
                self.desc_text.delete("1.0", tk.END)
                self.desc_text.insert("1.0", row[3] or '')
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, category_id, name, description FROM categories")
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def search_data(self):
        query = self.search_var.get().strip()
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT id, category_id, name, description FROM categories
                WHERE name LIKE ? OR category_id LIKE ?''',
                (f'%{query}%', f'%{query}%'))
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", str(e))


# Product Management
class ProductManagement(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.parent = parent
        self.selected_id = None
        self.create_widgets()
        self.load_data()

    def get_categories(self):
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM categories")
            rows = cursor.fetchall()
            conn.close()
            return [r[0] for r in rows]
        except:
            return []

    def get_suppliers(self):
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM suppliers")
            rows = cursor.fetchall()
            conn.close()
            return [r[0] for r in rows]
        except:
            return []

    def create_widgets(self):
        main_frame = tk.Frame(self, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True)

        sidebar = Sidebar(main_frame, self.parent)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)

        content = tk.Frame(main_frame, bg="#1a1a2e")
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        header = tk.Frame(content, bg="#16213e", pady=15)
        header.pack(fill=tk.X)
        tk.Label(header, text="Product Management", font=("Arial", 22, "bold"),
                 bg="#16213e", fg="white").pack(side=tk.LEFT, padx=20)

        body = tk.Frame(content, bg="#1a1a2e")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel
        left = tk.Frame(body, bg="#16213e", padx=15, pady=15)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        tk.Label(left, text="Product Details", font=("Arial", 14, "bold"),
                 bg="#16213e", fg="white").grid(row=0, column=0, columnspan=2, pady=(0, 15))

        # Simple entries
        simple_fields = [
            ("Product ID", "product_id"),
            ("Name", "name"),
            ("Price", "price"),
            ("Quantity", "quantity"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(simple_fields, start=1):
            tk.Label(left, text=label + ":", font=("Arial", 11),
                     bg="#16213e", fg="#a0a0b0").grid(row=i, column=0, sticky="w", pady=4)
            entry = tk.Entry(left, font=("Arial", 11), bg="#1a1a2e", fg="white",
                             insertbackground="white", width=22)
            entry.grid(row=i, column=1, padx=10, pady=4)
            self.entries[key] = entry

        # Category combo
        row_idx = len(simple_fields) + 1
        tk.Label(left, text="Category:", font=("Arial", 11),
                 bg="#16213e", fg="#a0a0b0").grid(row=row_idx, column=0, sticky="w", pady=4)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(left, textvariable=self.category_var,
                                           values=self.get_categories(), width=20, state="readonly")
        self.category_combo.grid(row=row_idx, column=1, padx=10, pady=4)

        # Supplier combo
        row_idx += 1
        tk.Label(left, text="Supplier:", font=("Arial", 11),
                 bg="#16213e", fg="#a0a0b0").grid(row=row_idx, column=0, sticky="w", pady=4)
        self.supplier_var = tk.StringVar()
        self.supplier_combo = ttk.Combobox(left, textvariable=self.supplier_var,
                                           values=self.get_suppliers(), width=20, state="readonly")
        self.supplier_combo.grid(row=row_idx, column=1, padx=10, pady=4)

        # Status combo
        row_idx += 1
        tk.Label(left, text="Status:", font=("Arial", 11),
                 bg="#16213e", fg="#a0a0b0").grid(row=row_idx, column=0, sticky="w", pady=4)
        self.status_var = tk.StringVar(value="Active")
        status_combo = ttk.Combobox(left, textvariable=self.status_var,
                                    values=["Active", "Inactive", "Out of Stock"], width=20, state="readonly")
        status_combo.grid(row=row_idx, column=1, padx=10, pady=4)

        # Description
        row_idx += 1
        tk.Label(left, text="Description:", font=("Arial", 11),
                 bg="#16213e", fg="#a0a0b0").grid(row=row_idx, column=0, sticky="nw", pady=4)
        self.desc_text = tk.Text(left, font=("Arial", 11), bg="#1a1a2e", fg="white",
                                 insertbackground="white", width=22, height=4)
        self.desc_text.grid(row=row_idx, column=1, padx=10, pady=4)

        row_idx += 1
        btn_frame = tk.Frame(left, bg="#16213e")
        btn_frame.grid(row=row_idx, column=0, columnspan=2, pady=10)

        buttons = [
            ("Add", self.add_product, "#05c46b"),
            ("Update", self.update_product, "#0f3460"),
            ("Delete", self.delete_product, "#e94560"),
            ("Clear", self.clear_form, "#533483"),
        ]
        for text, cmd, color in buttons:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 11), relief=tk.FLAT, padx=10, pady=5,
                      cursor="hand2").pack(side=tk.LEFT, padx=5)

        # Right panel
        right = tk.Frame(body, bg="#16213e")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        search_frame = tk.Frame(right, bg="#16213e", pady=10)
        search_frame.pack(fill=tk.X, padx=10)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white",
                 font=("Arial", 11)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 11),
                 bg="#1a1a2e", fg="white", insertbackground="white", width=30).pack(side=tk.LEFT, padx=10)

        tree_frame = tk.Frame(right, bg="#16213e")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("ID", "Product ID", "Name", "Category", "Supplier", "Price", "Quantity", "Status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")

        col_widths = [40, 90, 150, 120, 120, 80, 80, 90]
        for col, width in zip(columns, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<ButtonRelease-1>", self.select_record)

    def add_product(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        data['category'] = self.category_var.get()
        data['supplier'] = self.supplier_var.get()
        data['status'] = self.status_var.get()
        data['description'] = self.desc_text.get("1.0", tk.END).strip()

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
            self.clear_form()
            self.load_data()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Product ID already exists!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_product(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a record to update!")
            return
        data = {k: v.get().strip() for k, v in self.entries.items()}
        data['category'] = self.category_var.get()
        data['supplier'] = self.supplier_var.get()
        data['status'] = self.status_var.get()
        data['description'] = self.desc_text.get("1.0", tk.END).strip()
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''UPDATE products SET product_id=?, name=?, category=?, supplier=?,
                price=?, quantity=?, description=?, status=? WHERE id=?''',
                (data['product_id'], data['name'], data['category'], data['supplier'],
                 data['price'], data['quantity'], data['description'], data['status'],
                 self.selected_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product updated successfully!")
            self.clear_form()
            self.load_data()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_product(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a record to delete!")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this product?"):
            try:
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute("DELETE FROM products WHERE id=?", (self.selected_id,))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Product deleted successfully!")
                self.clear_form()
                self.load_data()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.category_var.set('')
        self.supplier_var.set('')
        self.status_var.set('Active')
        self.desc_text.delete("1.0", tk.END)
        self.selected_id = None

    def select_record(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])['values']
        self.selected_id = values[0]
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE id=?", (self.selected_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                keys_order = ['product_id', 'name', 'category', 'supplier', 'price', 'quantity', 'description', 'status']
                data = dict(zip(keys_order, row[1:]))

                for key in ['product_id', 'name', 'price', 'quantity']:
                    self.entries[key].delete(0, tk.END)
                    self.entries[key].insert(0, data.get(key, '') or '')

                self.category_var.set(data.get('category', '') or '')
                self.supplier_var.set(data.get('supplier', '') or '')
                self.status_var.set(data.get('status', 'Active') or 'Active')
                self.desc_text.delete("1.0", tk.END)
                self.desc_text.insert("1.0", data.get('description', '') or '')
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, product_id, name, category, supplier, price, quantity, status FROM products")
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def search_data(self):
        query = self.search_var.get().strip()
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT id, product_id, name, category, supplier, price, quantity, status
                FROM products WHERE name LIKE ? OR product_id LIKE ? OR category LIKE ?''',
                (f'%{query}%', f'%{query}%', f'%{query}%'))
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", str(e))


# Billing Management
class BillingManagement(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.parent = parent
        self.cart_items = []
        self.selected_bill_id = None
        self.create_widgets()
        self.load_bills()
        self.generate_invoice_no()

    def generate_invoice_no(self):
        inv = "INV-" + ''.join(random.choices(string.digits, k=8))
        self.invoice_var.set(inv)

    def get_products(self):
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name, price FROM products WHERE status='Active'")
            rows = cursor.fetchall()
            conn.close()
            return rows
        except:
            return []

    def create_widgets(self):
        main_frame = tk.Frame(self, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True)

        sidebar = Sidebar(main_frame, self.parent)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)

        content = tk.Frame(main_frame, bg="#1a1a2e")
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        header = tk.Frame(content, bg="#16213e", pady=15)
        header.pack(fill=tk.X)
        tk.Label(header, text="Billing Management", font=("Arial", 22, "bold"),
                 bg="#16213e", fg="white").pack(side=tk.LEFT, padx=20)

        body = tk.Frame(content, bg="#1a1a2e")
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - Billing form
        left = tk.Frame(body, bg="#16213e", padx=15, pady=15)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        tk.Label(left, text="New Bill", font=("Arial", 14, "bold"),
                 bg="#16213e", fg="white").grid(row=0, column=0, columnspan=2, pady=(0, 10))

        # Invoice No
        tk.Label(left, text="Invoice No:", font=("Arial", 11),
                 bg="#16213e", fg="#a0a0b0").grid(row=1, column=0, sticky="w", pady=4)
        self.invoice_var = tk.StringVar()
        inv_frame = tk.Frame(left, bg="#16213e")
        inv_frame.grid(row=1, column=1, padx=10, pady=4)
        tk.Entry(inv_frame, textvariable=self.invoice_var, font=("Arial", 11),
                 bg="#1a1a2e", fg="white", insertbackground="white", width=16).pack(side=tk.LEFT)
        tk.Button(inv_frame, text="🔄", command=self.generate_invoice_no,
                  bg="#0f3460", fg="white", font=("Arial", 10), relief=tk.FLAT).pack(side=tk.LEFT, padx=2)

        # Customer fields
        cust_fields = [
            ("Customer Name", "cust_name"),
            ("Customer Phone", "cust_phone"),
            ("Customer Email", "cust_email"),
        ]
        self.cust_entries = {}
        for i, (label, key) in enumerate(cust_fields, start=2):
            tk.Label(left, text=label + ":", font=("Arial", 11),
                     bg="#16213e", fg="#a0a0b0").grid(row=i, column=0, sticky="w", pady=4)
            entry = tk.Entry(left, font=("Arial", 11), bg="#1a1a2e", fg="white",
                             insertbackground="white", width=22)
            entry.grid(row=i, column=1, padx=10, pady=4)
            self.cust_entries[key] = entry

        # Product selection
        tk.Label(left, text="─" * 30, bg="#16213e", fg="#a0a0b0").grid(
            row=5, column=0, columnspan=2, pady=5)
        tk.Label(left, text="Add Product", font=("Arial", 12, "bold"),
                 bg="#16213e", fg="white").grid(row=6, column=0, columnspan=2, pady=5)

        tk.Label(left, text="Product:", font=("Arial", 11),
                 bg="#16213e", fg="#a0a0b0").grid(row=7, column=0, sticky="w", pady=4)
        products = self.get_products()
        product_names = [p[0] for p in products]
        self.product_prices = {p[0]: p[1] for p in products}
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(left, textvariable=self.product_var,
                                          values=product_names, width=20, state="readonly")
        self.product_combo.grid(row=7, column=1, padx=10, pady=4)
        self.product_combo.bind("<<ComboboxSelected>>", self.on_product_select)

        tk.Label(left, text="Price:", font=("Arial", 11),
                 bg="#16213e", fg="#a0a0b0").grid(row=8, column=0, sticky="w", pady=4)
        self.price_var = tk.StringVar()
        tk.Entry(left, textvariable=self.price_var, font=("Arial", 11),
                 bg="#1a1a2e", fg="white", insertbackground="white", width=22,
                 state="readonly").grid(row=8, column=1, padx=10, pady=4)

        tk.Label(left, text="Quantity:", font=("Arial", 11),
                 bg="#16213e", fg="#a0a0b0").grid(row=9, column=0, sticky="w", pady=4)
        self.qty_var = tk.StringVar(value="1")
        tk.Entry(left, textvariable=self.qty_var, font=("Arial", 11),
                 bg="#1a1a2e", fg="white", insertbackground="white", width=22).grid(row=9, column=1, padx=10, pady=4)

        tk.Button(left, text="➕ Add to Cart", command=self.add_to_cart,
                  bg="#05c46b", fg="white", font=("Arial", 11), relief=tk.FLAT,
                  padx=10, pady=5, cursor="hand2").grid(row=10, column=0, columnspan=2, pady=8)

        # Cart
        tk.Label(left, text="─" * 30, bg="#16213e", fg="#a0a0b0").grid(
            row=11, column=0, columnspan=2, pady=5)
        tk.Label(left, text="Cart", font=("Arial", 12, "bold"),
                 bg="#16213e", fg="white").grid(row=12, column=0, columnspan=2, pady=5)

        cart_frame = tk.Frame(left, bg="#16213e")
        cart_frame.grid(row=13, column=0, columnspan=2, pady=5)

        cart_cols = ("Product", "Qty", "Price", "Total")
        self.cart_tree = ttk.Treeview(cart_frame, columns=cart_cols, show="headings", height=6)
        for col in cart_cols:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=90, anchor="center")
        self.cart_tree.pack(side=tk.LEFT)

        cart_vsb = ttk.Scrollbar(cart_frame, orient=tk.VERTICAL, command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=cart_vsb.set)
        cart_vsb.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Button(left, text="🗑 Remove Selected", command=self.remove_from_cart,
                  bg="#e94560", fg="white", font=("Arial", 10), relief=tk.FLAT,
                  padx=8, pady=4, cursor="hand2").grid(row=14, column=0, columnspan=2, pady=5)

        # Total
        total_frame = tk.Frame(left, bg="#16213e")
        total_frame.grid(row=15, column=0, columnspan=2, pady=5)
        tk.Label(total_frame, text="Total Amount: ₹", font=("Arial", 13, "bold"),
                 bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.total_var = tk.StringVar(value="0.00")
        tk.Label(total_frame, textvariable=self.total_var, font=("Arial", 13, "bold"),
                 bg="#16213e", fg="#05c46b").pack(side=tk.LEFT)

        # Action buttons
        action_frame = tk.Frame(left, bg="#16213e")
        action_frame.grid(row=16, column=0, columnspan=2, pady=10)

        tk.Button(action_frame, text="💾 Save Bill", command=self.save_bill,
                  bg="#0f3460", fg="white", font=("Arial", 11), relief=tk.FLAT,
                  padx=10, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(action_frame, text="🖨 Print Bill", command=self.print_bill,
                  bg="#533483", fg="white", font=("Arial", 11), relief=tk.FLAT,
                  padx=10, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=5)
        tk.Button(action_frame, text="🔄 New Bill", command=self.new_bill,
                  bg="#e94560", fg="white", font=("Arial", 11), relief=tk.FLAT,
                  padx=10, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=5)

        # Right panel - Bills history
        right = tk.Frame(body, bg="#16213e")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        tk.Label(right, text="Bills History", font=("Arial", 14, "bold"),
                 bg="#16213e", fg="white").pack(anchor="w", padx=15, pady=10)

        search_frame = tk.Frame(right, bg="#16213e", pady=5)
        search_frame.pack(fill=tk.X, padx=10)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white",
                 font=("Arial", 11)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_bills())
        tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 11),
                 bg="#1a1a2e", fg="white", insertbackground="white", width=25).pack(side=tk.LEFT, padx=10)

        tree_frame = tk.Frame(right, bg="#16213e")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("ID", "Invoice No", "Customer", "Phone", "Date", "Amount")
        self.bills_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")

        col_widths = [40, 120, 150, 110, 130, 100]
        for col, width in zip(columns, col_widths):
            self.bills_tree.heading(col, text=col)
            self.bills_tree.column(col, width=width, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.bills_tree.yview)
        self.bills_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.bills_tree.pack(fill=tk.BOTH, expand=True)
        self.bills_tree.bind("<ButtonRelease-1>", self.view_bill)

        # Bill detail view
        detail_frame = tk.Frame(right, bg="#16213e", pady=10)
        detail_frame.pack(fill=tk.X, padx=10)

        tk.Label(detail_frame, text="Bill Details:", font=("Arial", 12, "bold"),
                 bg="#16213e", fg="white").pack(anchor="w")

        self.bill_detail_text = tk.Text(detail_frame, font=("Courier", 10), bg="#1a1a2e",
                                        fg="white", height=10, state=tk.DISABLED)
        self.bill_detail_text.pack(fill=tk.X, pady=5)

        # Delete bill button
        tk.Button(right, text="🗑 Delete Bill", command=self.delete_bill,
                  bg="#e94560", fg="white", font=("Arial", 11), relief=tk.FLAT,
                  padx=10, pady=5, cursor="hand2").pack(pady=5)

    def on_product_select(self, event):
        product = self.product_var.get()
        price = self.product_prices.get(product, 0)
        self.price_var.set(str(price))

    def add_to_cart(self):
        product = self.product_var.get()
        if not product:
            messagebox.showerror("Error", "Please select a product!")
            return
        try:
            qty = int(self.qty_var.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid quantity!")
            return

        price = float(self.product_prices.get(product, 0))
        total = price * qty

        self.cart_items.append({
            'product': product,
            'qty': qty,
            'price': price,
            'total': total
        })

        self.cart_tree.insert("", tk.END, values=(product, qty, f"{price:.2f}", f"{total:.2f}"))
        self.update_total()
        self.product_var.set('')
        self.price_var.set('')
        self.qty_var.set('1')

    def remove_from_cart(self):
        selected = self.cart_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select an item to remove!")
            return
        idx = self.cart_tree.index(selected[0])
        self.cart_tree.delete(selected[0])
        if 0 <= idx < len(self.cart_items):
            self.cart_items.pop(idx)
        self.update_total()

    def update_total(self):
        total = sum(item['total'] for item in self.cart_items)
        self.total_var.set(f"{total:.2f}")

    def save_bill(self):
        invoice_no = self.invoice_var.get().strip()
        cust_name = self.cust_entries['cust_name'].get().strip()
        cust_phone = self.cust_entries['cust_phone'].get().strip()
        cust_email = self.cust_entries['cust_email'].get().strip()

        if not invoice_no:
            messagebox.showerror("Error", "Invoice number is required!")
            return
        if not cust_name:
            messagebox.showerror("Error", "Customer name is required!")
            return
        if not self.cart_items:
            messagebox.showerror("Error", "Cart is empty! Please add products.")
            return

        total = float(self.total_var.get())
        bill_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build bill details string
        details_lines = []
        for item in self.cart_items:
            details_lines.append(f"{item['product']}|{item['qty']}|{item['price']}|{item['total']}")
        bill_details = ";".join(details_lines)

        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO bills (invoice_no, customer_name, customer_phone, customer_email,
                bill_date, total_amount, bill_details) VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (invoice_no, cust_name, cust_phone, cust_email, bill_date, total, bill_details))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Bill saved successfully!\nInvoice No: {invoice_no}")
            self.new_bill()
            self.load_bills()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Invoice number already exists!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def print_bill(self):
        invoice_no = self.invoice_var.get().strip()
        cust_name = self.cust_entries['cust_name'].get().strip()
        cust_phone = self.cust_entries['cust_phone'].get().strip()
        cust_email = self.cust_entries['cust_email'].get().strip()

        if not self.cart_items:
            messagebox.showerror("Error", "Cart is empty!")
            return

        bill_window = tk.Toplevel(self)
        bill_window.title(f"Bill - {invoice_no}")
        bill_window.geometry("500x600")
        bill_window.configure(bg="white")

        text = tk.Text(bill_window, font=("Courier", 11), bg="white", fg="black")
        text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        bill_content = f"""
{'='*50}
        INVENTORY MANAGEMENT SYSTEM
              BILL / INVOICE
{'='*50}
Invoice No : {invoice_no}
Date       : {now}
{'─'*50}
Customer   : {cust_name}
Phone      : {cust_phone}
Email      : {cust_email}
{'─'*50}
{'Product':<20} {'Qty':>5} {'Price':>8} {'Total':>10}
{'─'*50}
"""
        for item in self.cart_items:
            bill_content += f"{item['product']:<20} {item['qty']:>5} {item['price']:>8.2f} {item['total']:>10.2f}\n"

        bill_content += f"""{'─'*50}
{'TOTAL AMOUNT':>35} : ₹{float(self.total_var.get()):>8.2f}
{'='*50}
        Thank you for your purchase!
{'='*50}
"""
        text.insert(tk.END, bill_content)
        text.config(state=tk.DISABLED)

        tk.Button(bill_window, text="Close", command=bill_window.destroy,
                  bg="#e94560", fg="white", font=("Arial", 11), relief=tk.FLAT,
                  padx=20, pady=5).pack(pady=10)

    def new_bill(self):
        self.invoice_var.set('')
        for entry in self.cust_entries.values():
            entry.delete(0, tk.END)
        self.cart_items.clear()
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        self.total_var.set("0.00")
        self.product_var.set('')
        self.price_var.set('')
        self.qty_var.set('1')
        self.generate_invoice_no()

    def load_bills(self):
        for item in self.bills_tree.get_children():
            self.bills_tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, invoice_no, customer_name, customer_phone, bill_date, total_amount FROM bills ORDER BY id DESC")
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.bills_tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def view_bill(self, event):
        selected = self.bills_tree.selection()
        if not selected:
            return
        values = self.bills_tree.item(selected[0])['values']
        self.selected_bill_id = values[0]

        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bills WHERE id=?", (self.selected_bill_id,))
            row = cursor.fetchone()
            conn.close()

            if row:
                inv_no, cust_name, cust_phone, cust_email, bill_date, total, details = row[1:]

                detail_text = f"Invoice No: {inv_no}\n"
                detail_text += f"Customer: {cust_name} | Phone: {cust_phone}\n"
                detail_text += f"Email: {cust_email}\n"
                detail_text += f"Date: {bill_date}\n"
                detail_text += f"{'─'*50}\n"
                detail_text += f"{'Product':<20} {'Qty':>5} {'Price':>8} {'Total':>10}\n"
                detail_text += f"{'─'*50}\n"

                if details:
                    for item_str in details.split(';'):
                        parts = item_str.split('|')
                        if len(parts) == 4:
                            detail_text += f"{parts[0]:<20} {parts[1]:>5} {float(parts[2]):>8.2f} {float(parts[3]):>10.2f}\n"

                detail_text += f"{'─'*50}\n"
                detail_text += f"{'TOTAL':>35} : ₹{float(total):>8.2f}\n"

                self.bill_detail_text.config(state=tk.NORMAL)
                self.bill_detail_text.delete("1.0", tk.END)
                self.bill_detail_text.insert("1.0", detail_text)
                self.bill_detail_text.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_bill(self):
        if not self.selected_bill_id:
            messagebox.showerror("Error", "Please select a bill to delete!")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this bill?"):
            try:
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute("DELETE FROM bills WHERE id=?", (self.selected_bill_id,))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Bill deleted successfully!")
                self.selected_bill_id = None
                self.bill_detail_text.config(state=tk.NORMAL)
                self.bill_detail_text.delete("1.0", tk.END)
                self.bill_detail_text.config(state=tk.DISABLED)
                self.load_bills()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def search_bills(self):
        query = self.search_var.get().strip()
        for item in self.bills_tree.get_children():
            self.bills_tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT id, invoice_no, customer_name, customer_phone, bill_date, total_amount
                FROM bills WHERE invoice_no LIKE ? OR customer_name LIKE ? OR customer_phone LIKE ?
                ORDER BY id DESC''',
                (f'%{query}%', f'%{query}%', f'%{query}%'))
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.bills_tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()