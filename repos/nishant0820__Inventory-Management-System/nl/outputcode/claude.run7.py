import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import os
from datetime import datetime
from PIL import Image, ImageTk
import random
import string


# Database setup
def init_db():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        address TEXT,
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
        photo TEXT
    )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT UNIQUE NOT NULL,
        customer_name TEXT,
        customer_phone TEXT,
        bill_date TEXT,
        total_amount REAL,
        bill_details TEXT
    )''')

    conn.commit()
    conn.close()


class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1200x700")
        self.resizable(True, True)
        self.configure(bg="#2c3e50")

        init_db()
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


class Navbar(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#1a252f", height=60)
        self.pack(fill=tk.X, side=tk.TOP)
        self.app = app

        tk.Label(self, text="📦 Inventory Management System",
                 bg="#1a252f", fg="white",
                 font=("Arial", 16, "bold")).pack(side=tk.LEFT, padx=20, pady=10)

        buttons = [
            ("🏠 Dashboard", app.show_dashboard),
            ("👤 Employee", app.show_employee),
            ("🚚 Supplier", app.show_supplier),
            ("📂 Category", app.show_category),
            ("📦 Product", app.show_product),
            ("🧾 Billing", app.show_billing),
        ]

        for text, cmd in buttons:
            btn = tk.Button(self, text=text, command=cmd,
                            bg="#2980b9", fg="white",
                            font=("Arial", 10, "bold"),
                            relief=tk.FLAT, padx=10, pady=5,
                            cursor="hand2",
                            activebackground="#3498db",
                            activeforeground="white")
            btn.pack(side=tk.LEFT, padx=5, pady=10)


class Dashboard(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#2c3e50")
        self.app = parent
        self.build_ui()
        self.update_time()

    def build_ui(self):
        Navbar(self, self.app)

        # Time label
        self.time_label = tk.Label(self, text="", bg="#2c3e50", fg="#ecf0f1",
                                   font=("Arial", 12))
        self.time_label.pack(anchor=tk.NE, padx=20, pady=5)

        # Title
        tk.Label(self, text="Welcome to Inventory Management System",
                 bg="#2c3e50", fg="#ecf0f1",
                 font=("Arial", 20, "bold")).pack(pady=20)

        # Stats frame
        stats_frame = tk.Frame(self, bg="#2c3e50")
        stats_frame.pack(fill=tk.X, padx=40, pady=10)

        self.create_stat_card(stats_frame, "👤 Employees", self.get_count("employees"), "#3498db", 0)
        self.create_stat_card(stats_frame, "🚚 Suppliers", self.get_count("suppliers"), "#2ecc71", 1)
        self.create_stat_card(stats_frame, "📂 Categories", self.get_count("categories"), "#e74c3c", 2)
        self.create_stat_card(stats_frame, "📦 Products", self.get_count("products"), "#f39c12", 3)
        self.create_stat_card(stats_frame, "🧾 Bills", self.get_count("bills"), "#9b59b6", 4)

        # Quick access buttons
        tk.Label(self, text="Quick Access", bg="#2c3e50", fg="#ecf0f1",
                 font=("Arial", 14, "bold")).pack(pady=20)

        btn_frame = tk.Frame(self, bg="#2c3e50")
        btn_frame.pack(pady=10)

        quick_buttons = [
            ("👤 Manage Employees", self.app.show_employee, "#3498db"),
            ("🚚 Manage Suppliers", self.app.show_supplier, "#2ecc71"),
            ("📂 Manage Categories", self.app.show_category, "#e74c3c"),
            ("📦 Manage Products", self.app.show_product, "#f39c12"),
            ("🧾 Billing", self.app.show_billing, "#9b59b6"),
        ]

        for text, cmd, color in quick_buttons:
            btn = tk.Button(btn_frame, text=text, command=cmd,
                            bg=color, fg="white",
                            font=("Arial", 11, "bold"),
                            width=20, height=2,
                            relief=tk.FLAT, cursor="hand2",
                            activebackground=color)
            btn.pack(side=tk.LEFT, padx=10)

    def create_stat_card(self, parent, title, count, color, col):
        card = tk.Frame(parent, bg=color, relief=tk.RAISED, bd=2)
        card.grid(row=0, column=col, padx=10, pady=10, ipadx=20, ipady=15, sticky="nsew")
        parent.columnconfigure(col, weight=1)

        tk.Label(card, text=title, bg=color, fg="white",
                 font=("Arial", 12, "bold")).pack()
        tk.Label(card, text=str(count), bg=color, fg="white",
                 font=("Arial", 24, "bold")).pack()

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

    def update_time(self):
        now = datetime.now().strftime("%A, %d %B %Y  |  %H:%M:%S")
        self.time_label.config(text=now)
        self.after(1000, self.update_time)


class EmployeeManagement(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#2c3e50")
        self.app = parent
        self.photo_path = tk.StringVar()
        self.photo_image = None
        self.selected_id = None
        self.build_ui()
        self.load_data()

    def build_ui(self):
        Navbar(self, self.app)

        tk.Label(self, text="Employee Management", bg="#2c3e50", fg="white",
                 font=("Arial", 16, "bold")).pack(pady=10)

        main_frame = tk.Frame(self, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        # Left form
        form_frame = tk.LabelFrame(main_frame, text="Employee Details",
                                   bg="#34495e", fg="white",
                                   font=("Arial", 11, "bold"))
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

        fields = [
            ("Employee ID", "emp_id"),
            ("Name", "name"),
            ("Email", "email"),
            ("Phone", "phone"),
            ("Address", "address"),
            ("Designation", "designation"),
            ("Salary", "salary"),
            ("Join Date (YYYY-MM-DD)", "join_date"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label + ":", bg="#34495e", fg="white",
                     font=("Arial", 10)).grid(row=i, column=0, padx=10, pady=5, sticky=tk.W)
            entry = tk.Entry(form_frame, font=("Arial", 10), width=25)
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.entries[key] = entry

        # Photo
        tk.Label(form_frame, text="Photo:", bg="#34495e", fg="white",
                 font=("Arial", 10)).grid(row=len(fields), column=0, padx=10, pady=5, sticky=tk.W)
        tk.Button(form_frame, text="Browse Photo", command=self.browse_photo,
                  bg="#3498db", fg="white", font=("Arial", 9)).grid(row=len(fields), column=1, padx=10, pady=5)

        self.photo_label = tk.Label(form_frame, bg="#34495e", text="No Photo",
                                    fg="white", width=15, height=8)
        self.photo_label.grid(row=len(fields)+1, column=0, columnspan=2, pady=5)

        # Buttons
        btn_frame = tk.Frame(form_frame, bg="#34495e")
        btn_frame.grid(row=len(fields)+2, column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="Add", command=self.add_employee,
                  bg="#2ecc71", fg="white", font=("Arial", 10, "bold"),
                  width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", command=self.update_employee,
                  bg="#f39c12", fg="white", font=("Arial", 10, "bold"),
                  width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_employee,
                  bg="#e74c3c", fg="white", font=("Arial", 10, "bold"),
                  width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_form,
                  bg="#95a5a6", fg="white", font=("Arial", 10, "bold"),
                  width=8).pack(side=tk.LEFT, padx=5)

        # Right table
        table_frame = tk.LabelFrame(main_frame, text="Employee List",
                                    bg="#34495e", fg="white",
                                    font=("Arial", 11, "bold"))
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Search
        search_frame = tk.Frame(table_frame, bg="#34495e")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="#34495e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Emp ID", "Name", "Email", "Phone", "Designation", "Salary", "Join Date")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def browse_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif")])
        if path:
            self.photo_path.set(path)
            img = Image.open(path).resize((100, 80))
            self.photo_image = ImageTk.PhotoImage(img)
            self.photo_label.config(image=self.photo_image, text="")

    def get_data(self):
        return {key: entry.get() for key, entry in self.entries.items()}

    def validate(self, data):
        if not data['emp_id'] or not data['name']:
            messagebox.showerror("Error", "Employee ID and Name are required!")
            return False
        return True

    def add_employee(self):
        data = self.get_data()
        if not self.validate(data):
            return
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO employees (emp_id, name, email, phone, address, designation, salary, join_date, photo)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (data['emp_id'], data['name'], data['email'], data['phone'],
                            data['address'], data['designation'], data['salary'],
                            data['join_date'], self.photo_path.get()))
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
        data = self.get_data()
        if not self.validate(data):
            return
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE employees SET emp_id=?, name=?, email=?, phone=?, address=?,
                          designation=?, salary=?, join_date=?, photo=? WHERE id=?''',
                       (data['emp_id'], data['name'], data['email'], data['phone'],
                        data['address'], data['designation'], data['salary'],
                        data['join_date'], self.photo_path.get(), self.selected_id))
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
            conn = sqlite3.connect('inventory.db')
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
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, emp_id, name, email, phone, designation, salary, join_date FROM employees")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT id, emp_id, name, email, phone, designation, salary, join_date
                          FROM employees WHERE name LIKE ? OR emp_id LIKE ? OR designation LIKE ?''',
                       (f'%{query}%', f'%{query}%', f'%{query}%'))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])['values']
            self.selected_id = values[0]
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM employees WHERE id=?", (self.selected_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                keys = ['emp_id', 'name', 'email', 'phone', 'address', 'designation', 'salary', 'join_date']
                for i, key in enumerate(keys):
                    self.entries[key].delete(0, tk.END)
                    self.entries[key].insert(0, row[i+1] if row[i+1] else "")
                if row[9]:
                    self.photo_path.set(row[9])
                    try:
                        img = Image.open(row[9]).resize((100, 80))
                        self.photo_image = ImageTk.PhotoImage(img)
                        self.photo_label.config(image=self.photo_image, text="")
                    except:
                        self.photo_label.config(text="Photo not found")


class SupplierManagement(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#2c3e50")
        self.app = parent
        self.selected_id = None
        self.build_ui()
        self.load_data()

    def build_ui(self):
        Navbar(self, self.app)

        tk.Label(self, text="Supplier Management", bg="#2c3e50", fg="white",
                 font=("Arial", 16, "bold")).pack(pady=10)

        main_frame = tk.Frame(self, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        form_frame = tk.LabelFrame(main_frame, text="Supplier Details",
                                   bg="#34495e", fg="white",
                                   font=("Arial", 11, "bold"))
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

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
            tk.Label(form_frame, text=label + ":", bg="#34495e", fg="white",
                     font=("Arial", 10)).grid(row=i, column=0, padx=10, pady=5, sticky=tk.W)
            if key == "description":
                entry = tk.Text(form_frame, font=("Arial", 10), width=25, height=4)
            else:
                entry = tk.Entry(form_frame, font=("Arial", 10), width=25)
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.entries[key] = entry

        btn_frame = tk.Frame(form_frame, bg="#34495e")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="Add", command=self.add_supplier,
                  bg="#2ecc71", fg="white", font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", command=self.update_supplier,
                  bg="#f39c12", fg="white", font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_supplier,
                  bg="#e74c3c", fg="white", font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_form,
                  bg="#95a5a6", fg="white", font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)

        table_frame = tk.LabelFrame(main_frame, text="Supplier List",
                                    bg="#34495e", fg="white",
                                    font=("Arial", 11, "bold"))
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        search_frame = tk.Frame(table_frame, bg="#34495e")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="#34495e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Supplier ID", "Name", "Email", "Phone", "Company")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def get_text(self, key):
        widget = self.entries[key]
        if isinstance(widget, tk.Text):
            return widget.get("1.0", tk.END).strip()
        return widget.get()

    def get_data(self):
        return {key: self.get_text(key) for key in self.entries}

    def validate(self, data):
        if not data['supplier_id'] or not data['name']:
            messagebox.showerror("Error", "Supplier ID and Name are required!")
            return False
        return True

    def add_supplier(self):
        data = self.get_data()
        if not self.validate(data):
            return
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO suppliers (supplier_id, name, email, phone, address, company, description)
                              VALUES (?, ?, ?, ?, ?, ?, ?)''',
                           (data['supplier_id'], data['name'], data['email'], data['phone'],
                            data['address'], data['company'], data['description']))
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
        data = self.get_data()
        if not self.validate(data):
            return
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE suppliers SET supplier_id=?, name=?, email=?, phone=?,
                          address=?, company=?, description=? WHERE id=?''',
                       (data['supplier_id'], data['name'], data['email'], data['phone'],
                        data['address'], data['company'], data['description'], self.selected_id))
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
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM suppliers WHERE id=?", (self.selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier deleted successfully!")
            self.clear_form()
            self.load_data()

    def clear_form(self):
        for key, widget in self.entries.items():
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
            else:
                widget.delete(0, tk.END)
        self.selected_id = None

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, supplier_id, name, email, phone, company FROM suppliers")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT id, supplier_id, name, email, phone, company
                          FROM suppliers WHERE name LIKE ? OR supplier_id LIKE ? OR company LIKE ?''',
                       (f'%{query}%', f'%{query}%', f'%{query}%'))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])['values']
            self.selected_id = values[0]
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM suppliers WHERE id=?", (self.selected_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                keys = ['supplier_id', 'name', 'email', 'phone', 'address', 'company', 'description']
                for i, key in enumerate(keys):
                    widget = self.entries[key]
                    if isinstance(widget, tk.Text):
                        widget.delete("1.0", tk.END)
                        widget.insert("1.0", row[i+1] if row[i+1] else "")
                    else:
                        widget.delete(0, tk.END)
                        widget.insert(0, row[i+1] if row[i+1] else "")


class CategoryManagement(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#2c3e50")
        self.app = parent
        self.selected_id = None
        self.build_ui()
        self.load_data()

    def build_ui(self):
        Navbar(self, self.app)

        tk.Label(self, text="Category Management", bg="#2c3e50", fg="white",
                 font=("Arial", 16, "bold")).pack(pady=10)

        main_frame = tk.Frame(self, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        form_frame = tk.LabelFrame(main_frame, text="Category Details",
                                   bg="#34495e", fg="white",
                                   font=("Arial", 11, "bold"))
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

        fields = [
            ("Category ID", "category_id"),
            ("Name", "name"),
            ("Description", "description"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label + ":", bg="#34495e", fg="white",
                     font=("Arial", 10)).grid(row=i, column=0, padx=10, pady=5, sticky=tk.W)
            if key == "description":
                entry = tk.Text(form_frame, font=("Arial", 10), width=25, height=5)
            else:
                entry = tk.Entry(form_frame, font=("Arial", 10), width=25)
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.entries[key] = entry

        btn_frame = tk.Frame(form_frame, bg="#34495e")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="Add", command=self.add_category,
                  bg="#2ecc71", fg="white", font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", command=self.update_category,
                  bg="#f39c12", fg="white", font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_category,
                  bg="#e74c3c", fg="white", font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_form,
                  bg="#95a5a6", fg="white", font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)

        table_frame = tk.LabelFrame(main_frame, text="Category List",
                                    bg="#34495e", fg="white",
                                    font=("Arial", 11, "bold"))
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        search_frame = tk.Frame(table_frame, bg="#34495e")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="#34495e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Category ID", "Name", "Description")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def get_text(self, key):
        widget = self.entries[key]
        if isinstance(widget, tk.Text):
            return widget.get("1.0", tk.END).strip()
        return widget.get()

    def get_data(self):
        return {key: self.get_text(key) for key in self.entries}

    def validate(self, data):
        if not data['category_id'] or not data['name']:
            messagebox.showerror("Error", "Category ID and Name are required!")
            return False
        return True

    def add_category(self):
        data = self.get_data()
        if not self.validate(data):
            return
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO categories (category_id, name, description)
                              VALUES (?, ?, ?)''',
                           (data['category_id'], data['name'], data['description']))
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
        data = self.get_data()
        if not self.validate(data):
            return
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE categories SET category_id=?, name=?, description=? WHERE id=?''',
                       (data['category_id'], data['name'], data['description'], self.selected_id))
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
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM categories WHERE id=?", (self.selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category deleted successfully!")
            self.clear_form()
            self.load_data()

    def clear_form(self):
        for key, widget in self.entries.items():
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
            else:
                widget.delete(0, tk.END)
        self.selected_id = None

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, category_id, name, description FROM categories")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT id, category_id, name, description
                          FROM categories WHERE name LIKE ? OR category_id LIKE ?''',
                       (f'%{query}%', f'%{query}%'))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])['values']
            self.selected_id = values[0]
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories WHERE id=?", (self.selected_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                keys = ['category_id', 'name', 'description']
                for i, key in enumerate(keys):
                    widget = self.entries[key]
                    if isinstance(widget, tk.Text):
                        widget.delete("1.0", tk.END)
                        widget.insert("1.0", row[i+1] if row[i+1] else "")
                    else:
                        widget.delete(0, tk.END)
                        widget.insert(0, row[i+1] if row[i+1] else "")


class ProductManagement(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#2c3e50")
        self.app = parent
        self.photo_path = tk.StringVar()
        self.photo_image = None
        self.selected_id = None
        self.build_ui()
        self.load_data()

    def build_ui(self):
        Navbar(self, self.app)

        tk.Label(self, text="Product Management", bg="#2c3e50", fg="white",
                 font=("Arial", 16, "bold")).pack(pady=10)

        main_frame = tk.Frame(self, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        form_frame = tk.LabelFrame(main_frame, text="Product Details",
                                   bg="#34495e", fg="white",
                                   font=("Arial", 11, "bold"))
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

        # Get categories and suppliers for dropdowns
        categories = self.get_categories()
        suppliers = self.get_suppliers()

        fields_config = [
            ("Product ID", "product_id", "entry"),
            ("Name", "name", "entry"),
            ("Category", "category", "combo", categories),
            ("Supplier", "supplier", "combo", suppliers),
            ("Price", "price", "entry"),
            ("Quantity", "quantity", "entry"),
            ("Description", "description", "text"),
        ]

        self.entries = {}
        row_idx = 0
        for config in fields_config:
            label = config[0]
            key = config[1]
            wtype = config[2]

            tk.Label(form_frame, text=label + ":", bg="#34495e", fg="white",
                     font=("Arial", 10)).grid(row=row_idx, column=0, padx=10, pady=5, sticky=tk.W)

            if wtype == "entry":
                widget = tk.Entry(form_frame, font=("Arial", 10), width=25)
            elif wtype == "combo":
                options = config[3]
                widget = ttk.Combobox(form_frame, values=options, width=23, font=("Arial", 10))
            elif wtype == "text":
                widget = tk.Text(form_frame, font=("Arial", 10), width=25, height=4)

            widget.grid(row=row_idx, column=1, padx=10, pady=5)
            self.entries[key] = widget
            row_idx += 1

        tk.Label(form_frame, text="Photo:", bg="#34495e", fg="white",
                 font=("Arial", 10)).grid(row=row_idx, column=0, padx=10, pady=5, sticky=tk.W)
        tk.Button(form_frame, text="Browse Photo", command=self.browse_photo,
                  bg="#3498db", fg="white", font=("Arial", 9)).grid(row=row_idx, column=1, padx=10, pady=5)
        row_idx += 1

        self.photo_label = tk.Label(form_frame, bg="#34495e", text="No Photo",
                                    fg="white", width=15, height=6)
        self.photo_label.grid(row=row_idx, column=0, columnspan=2, pady=5)
        row_idx += 1

        btn_frame = tk.Frame(form_frame, bg="#34495e")
        btn_frame.grid(row=row_idx, column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="Add", command=self.add_product,
                  bg="#2ecc71", fg="white", font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", command=self.update_product,
                  bg="#f39c12", fg="white", font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_product,
                  bg="#e74c3c", fg="white", font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_form,
                  bg="#95a5a6", fg="white", font=("Arial", 10, "bold"), width=8).pack(side=tk.LEFT, padx=5)

        table_frame = tk.LabelFrame(main_frame, text="Product List",
                                    bg="#34495e", fg="white",
                                    font=("Arial", 11, "bold"))
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        search_frame = tk.Frame(table_frame, bg="#34495e")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="#34495e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.search_data())
        tk.Entry(search_frame, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)

        columns = ("ID", "Product ID", "Name", "Category", "Supplier", "Price", "Quantity")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def get_categories(self):
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories")
        cats = [row[0] for row in cursor.fetchall()]
        conn.close()
        return cats

    def get_suppliers(self):
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM suppliers")
        sups = [row[0] for row in cursor.fetchall()]
        conn.close()
        return sups

    def browse_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif")])
        if path:
            self.photo_path.set(path)
            img = Image.open(path).resize((100, 70))
            self.photo_image = ImageTk.PhotoImage(img)
            self.photo_label.config(image=self.photo_image, text="")

    def get_widget_value(self, key):
        widget = self.entries[key]
        if isinstance(widget, tk.Text):
            return widget.get("1.0", tk.END).strip()
        return widget.get()

    def get_data(self):
        return {key: self.get_widget_value(key) for key in self.entries}

    def validate(self, data):
        if not data['product_id'] or not data['name']:
            messagebox.showerror("Error", "Product ID and Name are required!")
            return False
        return True

    def add_product(self):
        data = self.get_data()
        if not self.validate(data):
            return
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO products (product_id, name, category, supplier, price, quantity, description, photo)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                           (data['product_id'], data['name'], data['category'], data['supplier'],
                            data['price'], data['quantity'], data['description'], self.photo_path.get()))
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
        data = self.get_data()
        if not self.validate(data):
            return
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE products SET product_id=?, name=?, category=?, supplier=?,
                          price=?, quantity=?, description=?, photo=? WHERE id=?''',
                       (data['product_id'], data['name'], data['category'], data['supplier'],
                        data['price'], data['quantity'], data['description'],
                        self.photo_path.get(), self.selected_id))
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
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id=?", (self.selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product deleted successfully!")
            self.clear_form()
            self.load_data()

    def clear_form(self):
        for key, widget in self.entries.items():
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
            elif isinstance(widget, ttk.Combobox):
                widget.set("")
            else:
                widget.delete(0, tk.END)
        self.photo_path.set("")
        self.photo_label.config(image="", text="No Photo")
        self.photo_image = None
        self.selected_id = None

    def load_data(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, product_id, name, category, supplier, price, quantity FROM products")
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_data(self):
        query = self.search_var.get()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT id, product_id, name, category, supplier, price, quantity
                          FROM products WHERE name LIKE ? OR product_id LIKE ? OR category LIKE ?''',
                       (f'%{query}%', f'%{query}%', f'%{query}%'))
        for row in cursor.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])['values']
            self.selected_id = values[0]
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE id=?", (self.selected_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                keys = ['product_id', 'name', 'category', 'supplier', 'price', 'quantity', 'description']
                for i, key in enumerate(keys):
                    widget = self.entries[key]
                    val = row[i+1] if row[i+1] else ""
                    if isinstance(widget, tk.Text):
                        widget.delete("1.0", tk.END)
                        widget.insert("1.0", val)
                    elif isinstance(widget, ttk.Combobox):
                        widget.set(val)
                    else:
                        widget.delete(0, tk.END)
                        widget.insert(0, val)
                if row[8]:
                    self.photo_path.set(row[8])
                    try:
                        img = Image.open(row[8]).resize((100, 70))
                        self.photo_image = ImageTk.PhotoImage(img)
                        self.photo_label.config(image=self.photo_image, text="")
                    except:
                        self.photo_label.config(text="Photo not found")


class BillingManagement(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#2c3e50")
        self.app = parent
        self.cart_items = []
        self.selected_bill_id = None
        self.build_ui()
        self.load_bills()
        self.generate_invoice_no()

    def build_ui(self):
        Navbar(self, self.app)

        tk.Label(self, text="Billing Management", bg="#2c3e50", fg="white",
                 font=("Arial", 16, "bold")).pack(pady=5)

        main_frame = tk.Frame(self, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left: Billing form
        left_frame = tk.Frame(main_frame, bg="#2c3e50")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # Customer info
        cust_frame = tk.LabelFrame(left_frame, text="Customer Information",
                                   bg="#34495e", fg="white", font=("Arial", 11, "bold"))
        cust_frame.pack(fill=tk.X, pady=5)

        tk.Label(cust_frame, text="Invoice No:", bg="#34495e", fg="white").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        self.invoice_var = tk.StringVar()
        tk.Entry(cust_frame, textvariable=self.invoice_var, font=("Arial", 10), width=20,
                 state="readonly").grid(row=0, column=1, padx=10, pady=5)

        tk.Label(cust_frame, text="Customer Name:", bg="#34495e", fg="white").grid(row=0, column=2, padx=10, pady=5, sticky=tk.W)
        self.cust_name = tk.Entry(cust_frame, font=("Arial", 10), width=20)
        self.cust_name.grid(row=0, column=3, padx=10, pady=5)

        tk.Label(cust_frame, text="Customer Phone:", bg="#34495e", fg="white").grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
        self.cust_phone = tk.Entry(cust_frame, font=("Arial", 10), width=20)
        self.cust_phone.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(cust_frame, text="Date:", bg="#34495e", fg="white").grid(row=1, column=2, padx=10, pady=5, sticky=tk.W)
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        tk.Entry(cust_frame, textvariable=self.date_var, font=("Arial", 10), width=20).grid(row=1, column=3, padx=10, pady=5)

        # Product selection
        prod_frame = tk.LabelFrame(left_frame, text="Add Product to Cart",
                                   bg="#34495e", fg="white", font=("Arial", 11, "bold"))
        prod_frame.pack(fill=tk.X, pady=5)

        tk.Label(prod_frame, text="Product:", bg="#34495e", fg="white").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        self.product_combo = ttk.Combobox(prod_frame, values=self.get_products(), width=25, font=("Arial", 10))
        self.product_combo.grid(row=0, column=1, padx=10, pady=5)
        self.product_combo.bind("<<ComboboxSelected>>", self.on_product_select)

        tk.Label(prod_frame, text="Price:", bg="#34495e", fg="white").grid(row=0, column=2, padx=10, pady=5, sticky=tk.W)
        self.price_var = tk.StringVar()
        tk.Entry(prod_frame, textvariable=self.price_var, font=("Arial", 10), width=15).grid(row=0, column=3, padx=10, pady=5)

        tk.Label(prod_frame, text="Quantity:", bg="#34495e", fg="white").grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
        self.qty_var = tk.StringVar(value="1")
        tk.Entry(prod_frame, textvariable=self.qty_var, font=("Arial", 10), width=15).grid(row=1, column=1, padx=10, pady=5)

        tk.Button(prod_frame, text="Add to Cart", command=self.add_to_cart,
                  bg="#2ecc71", fg="white", font=("Arial", 10, "bold")).grid(row=1, column=2, padx=10, pady=5)
        tk.Button(prod_frame, text="Remove Selected", command=self.remove_from_cart,
                  bg="#e74c3c", fg="white", font=("Arial", 10, "bold")).grid(row=1, column=3, padx=10, pady=5)

        # Cart
        cart_frame = tk.LabelFrame(left_frame, text="Cart",
                                   bg="#34495e", fg="white", font=("Arial", 11, "bold"))
        cart_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        cart_cols = ("Product", "Price", "Quantity", "Total")
        self.cart_tree = ttk.Treeview(cart_frame, columns=cart_cols, show="headings", height=8)
        for col in cart_cols:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=120)
        self.cart_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Total and actions
        total_frame = tk.Frame(left_frame, bg="#34495e")
        total_frame.pack(fill=tk.X, pady=5)

        tk.Label(total_frame, text="Total Amount: ₹", bg="#34495e", fg="white",
                 font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=10)
        self.total_var = tk.StringVar(value="0.00")
        tk.Label(total_frame, textvariable=self.total_var, bg="#34495e", fg="#2ecc71",
                 font=("Arial", 14, "bold")).pack(side=tk.LEFT)

        btn_frame = tk.Frame(left_frame, bg="#2c3e50")
        btn_frame.pack(fill=tk.X, pady=5)

        tk.Button(btn_frame, text="💾 Save Bill", command=self.save_bill,
                  bg="#2ecc71", fg="white", font=("Arial", 11, "bold"),
                  width=15).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="🖨️ Print Bill", command=self.print_bill,
                  bg="#3498db", fg="white", font=("Arial", 11, "bold"),
                  width=15).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="🗑️ Clear", command=self.clear_billing,
                  bg="#e74c3c", fg="white", font=("Arial", 11, "bold"),
                  width=15).pack(side=tk.LEFT, padx=10)

        # Right: Bill history
        right_frame = tk.LabelFrame(main_frame, text="Bill History",
                                    bg="#34495e", fg="white", font=("Arial", 11, "bold"))
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)

        search_frame = tk.Frame(right_frame, bg="#34495e")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="#34495e", fg="white").pack(side=tk.LEFT)
        self.bill_search_var = tk.StringVar()
        self.bill_search_var.trace("w", lambda *args: self.search_bills())
        tk.Entry(search_frame, textvariable=self.bill_search_var, width=20).pack(side=tk.LEFT, padx=5)

        bill_cols = ("ID", "Invoice No", "Customer", "Phone", "Date", "Total")
        self.bill_tree = ttk.Treeview(right_frame, columns=bill_cols, show="headings", height=15)
        for col in bill_cols:
            self.bill_tree.heading(col, text=col)
            self.bill_tree.column(col, width=90)
        self.bill_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.bill_tree.bind("<<TreeviewSelect>>", self.on_bill_select)

        scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.bill_tree.yview)
        self.bill_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        tk.Button(right_frame, text="🗑️ Delete Bill", command=self.delete_bill,
                  bg="#e74c3c", fg="white", font=("Arial", 10, "bold")).pack(pady=5)

    def get_products(self):
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM products")
        prods = [row[0] for row in cursor.fetchall()]
        conn.close()
        return prods

    def on_product_select(self, event):
        product_name = self.product_combo.get()
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT price FROM products WHERE name=?", (product_name,))
        row = cursor.fetchone()
        conn.close()
        if row:
            self.price_var.set(str(row[0]))

    def add_to_cart(self):
        product = self.product_combo.get()
        price_str = self.price_var.get()
        qty_str = self.qty_var.get()

        if not product:
            messagebox.showerror("Error", "Please select a product!")
            return
        try:
            price = float(price_str)
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid price or quantity!")
            return

        total = price * qty
        self.cart_items.append({"product": product, "price": price, "qty": qty, "total": total})
        self.cart_tree.insert("", tk.END, values=(product, f"₹{price:.2f}", qty, f"₹{total:.2f}"))
        self.update_total()
        self.product_combo.set("")
        self.price_var.set("")
        self.qty_var.set("1")

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
        total = sum(item['total'] for item in self.cart_items)
        self.total_var.set(f"{total:.2f}")

    def generate_invoice_no(self):
        inv = "INV-" + ''.join(random.choices(string.digits, k=8))
        self.invoice_var.set(inv)

    def save_bill(self):
        if not self.cart_items:
            messagebox.showerror("Error", "Cart is empty!")
            return
        invoice_no = self.invoice_var.get()
        customer_name = self.cust_name.get()
        customer_phone = self.cust_phone.get()
        bill_date = self.date_var.get()
        total = float(self.total_var.get())

        import json
        bill_details = json.dumps(self.cart_items)

        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO bills (invoice_no, customer_name, customer_phone, bill_date, total_amount, bill_details)
                              VALUES (?, ?, ?, ?, ?, ?)''',
                           (invoice_no, customer_name, customer_phone, bill_date, total, bill_details))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Bill saved successfully!\nInvoice No: {invoice_no}")
            self.clear_billing()
            self.load_bills()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Invoice number already exists!")

    def print_bill(self):
        if not self.cart_items:
            messagebox.showerror("Error", "Cart is empty!")
            return

        bill_window = tk.Toplevel(self)
        bill_window.title("Bill Preview")
        bill_window.geometry("500x600")
        bill_window.configure(bg="white")

        text = tk.Text(bill_window, font=("Courier", 11), bg="white", fg="black")
        text.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        bill_content = f"""
{'='*50}
        INVENTORY MANAGEMENT SYSTEM
              BILL / INVOICE
{'='*50}
Invoice No : {self.invoice_var.get()}
Date       : {self.date_var.get()}
Customer   : {self.cust_name.get()}
Phone      : {self.cust_phone.get()}
{'='*50}
{'Product':<20} {'Price':>8} {'Qty':>5} {'Total':>10}
{'-'*50}
"""
        for item in self.cart_items:
            bill_content += f"{item['product']:<20} {item['price']:>8.2f} {item['qty']:>5} {item['total']:>10.2f}\n"

        bill_content += f"""
{'-'*50}
{'TOTAL AMOUNT':>35} : ₹{float(self.total_var.get()):>8.2f}
{'='*50}
        Thank you for your purchase!
{'='*50}
"""
        text.insert(tk.END, bill_content)
        text.config(state=tk.DISABLED)

        tk.Button(bill_window, text="Close", command=bill_window.destroy,
                  bg="#e74c3c", fg="white", font=("Arial", 10, "bold")).pack(pady=10)

    def clear_billing(self):
        self.cart_items = []
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        self.total_var.set("0.00")
        self.cust_name.delete(0, tk.END)
        self.cust_phone.delete(0, tk.END)
        self.product_combo.set("")
        self.price_var.set("")
        self.qty_var.set("1")
        self.generate_invoice_no()
        self.selected_bill_id = None

    def load_bills(self):
        for row in self.bill_tree.get_children():
            self.bill_tree.delete(row)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, invoice_no, customer_name, customer_phone, bill_date, total_amount FROM bills ORDER BY id DESC")
        for row in cursor.fetchall():
            self.bill_tree.insert("", tk.END, values=(row[0], row[1], row[2], row[3], row[4], f"₹{row[5]:.2f}"))
        conn.close()

    def search_bills(self):
        query = self.bill_search_var.get()
        for row in self.bill_tree.get_children():
            self.bill_tree.delete(row)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT id, invoice_no, customer_name, customer_phone, bill_date, total_amount
                          FROM bills WHERE invoice_no LIKE ? OR customer_name LIKE ? ORDER BY id DESC''',
                       (f'%{query}%', f'%{query}%'))
        for row in cursor.fetchall():
            self.bill_tree.insert("", tk.END, values=(row[0], row[1], row[2], row[3], row[4], f"₹{row[5]:.2f}"))
        conn.close()

    def on_bill_select(self, event):
        selected = self.bill_tree.selection()
        if selected:
            values = self.bill_tree.item(selected[0])['values']
            self.selected_bill_id = values[0]
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bills WHERE id=?", (self.selected_bill_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                import json
                self.invoice_var.set(row[1])
                self.cust_name.delete(0, tk.END)
                self.cust_name.insert(0, row[2] if row[2] else "")
                self.cust_phone.delete(0, tk.END)
                self.cust_phone.insert(0, row[3] if row[3] else "")
                self.date_var.set(row[4] if row[4] else "")

                # Load cart items
                self.cart_items = []
                for row_item in self.cart_tree.get_children():
                    self.cart_tree.delete(row_item)

                try:
                    items = json.loads(row[6]) if row[6] else []
                    for item in items:
                        self.cart_items.append(item)
                        self.cart_tree.insert("", tk.END, values=(
                            item['product'],
                            f"₹{item['price']:.2f}",
                            item['qty'],
                            f"₹{item['total']:.2f}"
                        ))
                except:
                    pass
                self.update_total()

    def delete_bill(self):
        if not self.selected_bill_id:
            messagebox.showerror("Error", "Please select a bill to delete!")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this bill?"):
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bills WHERE id=?", (self.selected_bill_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Bill deleted successfully!")
            self.clear_billing()
            self.load_bills()


if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()