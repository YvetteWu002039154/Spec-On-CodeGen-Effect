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
        customer_email TEXT,
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
        self.geometry("1400x800")
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
        self.app = app
        self.pack(fill=tk.X, side=tk.TOP)
        self.create_widgets()

    def create_widgets(self):
        title_label = tk.Label(self, text="Inventory Management System",
                               font=("Arial", 18, "bold"), bg="#1a252f", fg="white")
        title_label.pack(side=tk.LEFT, padx=20, pady=10)

        buttons = [
            ("Dashboard", self.app.show_dashboard),
            ("Employee", self.app.show_employee),
            ("Supplier", self.app.show_supplier),
            ("Category", self.app.show_category),
            ("Product", self.app.show_product),
            ("Billing", self.app.show_billing),
        ]

        for text, command in buttons:
            btn = tk.Button(self, text=text, command=command,
                            bg="#2980b9", fg="white", font=("Arial", 10, "bold"),
                            relief=tk.FLAT, padx=10, pady=5, cursor="hand2")
            btn.pack(side=tk.LEFT, padx=5, pady=10)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg="#3498db"))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg="#2980b9"))

        exit_btn = tk.Button(self, text="Exit", command=self.app.quit,
                             bg="#e74c3c", fg="white", font=("Arial", 10, "bold"),
                             relief=tk.FLAT, padx=10, pady=5, cursor="hand2")
        exit_btn.pack(side=tk.RIGHT, padx=20, pady=10)


class Dashboard(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#2c3e50")
        self.app = parent
        self.create_widgets()
        self.update_time()

    def create_widgets(self):
        Navbar(self, self.app)

        main_frame = tk.Frame(self, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Time and Date
        self.time_label = tk.Label(main_frame, text="", font=("Arial", 14, "bold"),
                                   bg="#2c3e50", fg="#f39c12")
        self.time_label.pack(anchor=tk.NE, padx=10, pady=5)

        self.date_label = tk.Label(main_frame, text="", font=("Arial", 12),
                                   bg="#2c3e50", fg="#bdc3c7")
        self.date_label.pack(anchor=tk.NE, padx=10)

        # Welcome
        welcome_label = tk.Label(main_frame, text="Welcome to Inventory Management System",
                                 font=("Arial", 24, "bold"), bg="#2c3e50", fg="white")
        welcome_label.pack(pady=20)

        subtitle = tk.Label(main_frame, text="Manage your inventory efficiently",
                            font=("Arial", 14), bg="#2c3e50", fg="#bdc3c7")
        subtitle.pack(pady=5)

        # Stats Cards
        cards_frame = tk.Frame(main_frame, bg="#2c3e50")
        cards_frame.pack(fill=tk.X, pady=30)

        stats = self.get_stats()
        card_data = [
            ("Employees", stats['employees'], "#3498db", self.app.show_employee),
            ("Suppliers", stats['suppliers'], "#2ecc71", self.app.show_supplier),
            ("Categories", stats['categories'], "#e67e22", self.app.show_category),
            ("Products", stats['products'], "#9b59b6", self.app.show_product),
            ("Bills", stats['bills'], "#e74c3c", self.app.show_billing),
        ]

        for i, (title, count, color, command) in enumerate(card_data):
            card = tk.Frame(cards_frame, bg=color, relief=tk.RAISED, bd=2, cursor="hand2")
            card.grid(row=0, column=i, padx=15, pady=10, ipadx=20, ipady=15, sticky="nsew")
            cards_frame.columnconfigure(i, weight=1)

            tk.Label(card, text=title, font=("Arial", 14, "bold"),
                     bg=color, fg="white").pack(pady=5)
            tk.Label(card, text=str(count), font=("Arial", 28, "bold"),
                     bg=color, fg="white").pack(pady=5)
            tk.Label(card, text="Total Records", font=("Arial", 10),
                     bg=color, fg="white").pack(pady=2)

            card.bind("<Button-1>", lambda e, cmd=command: cmd())
            for widget in card.winfo_children():
                widget.bind("<Button-1>", lambda e, cmd=command: cmd())

        # Quick Actions
        actions_frame = tk.LabelFrame(main_frame, text="Quick Actions",
                                      font=("Arial", 12, "bold"), bg="#2c3e50", fg="white",
                                      relief=tk.GROOVE, bd=2)
        actions_frame.pack(fill=tk.X, pady=20, padx=10)

        actions = [
            ("Add Employee", self.app.show_employee, "#3498db"),
            ("Add Supplier", self.app.show_supplier, "#2ecc71"),
            ("Add Category", self.app.show_category, "#e67e22"),
            ("Add Product", self.app.show_product, "#9b59b6"),
            ("Create Bill", self.app.show_billing, "#e74c3c"),
        ]

        for text, command, color in actions:
            btn = tk.Button(actions_frame, text=text, command=command,
                            bg=color, fg="white", font=("Arial", 11, "bold"),
                            relief=tk.FLAT, padx=15, pady=8, cursor="hand2")
            btn.pack(side=tk.LEFT, padx=10, pady=10)

    def get_stats(self):
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        stats = {}
        for table in ['employees', 'suppliers', 'categories', 'products', 'bills']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = cursor.fetchone()[0]
        conn.close()
        return stats

    def update_time(self):
        now = datetime.now()
        self.time_label.config(text=now.strftime("Time: %H:%M:%S"))
        self.date_label.config(text=now.strftime("Date: %A, %B %d, %Y"))
        self.after(1000, self.update_time)


class EmployeeManagement(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#2c3e50")
        self.app = parent
        self.photo_path = tk.StringVar()
        self.photo_image = None
        self.selected_id = None
        self.create_widgets()
        self.load_employees()

    def create_widgets(self):
        Navbar(self, self.app)

        title = tk.Label(self, text="Employee Management",
                         font=("Arial", 20, "bold"), bg="#2c3e50", fg="white")
        title.pack(pady=10)

        main_frame = tk.Frame(self, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        # Left - Form
        form_frame = tk.LabelFrame(main_frame, text="Employee Details",
                                   font=("Arial", 12, "bold"), bg="#34495e", fg="white",
                                   relief=tk.GROOVE, bd=2)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5, ipadx=10, ipady=10)

        fields = [
            ("Employee ID:", "emp_id"),
            ("Name:", "name"),
            ("Email:", "email"),
            ("Phone:", "phone"),
            ("Address:", "address"),
            ("Designation:", "designation"),
            ("Salary:", "salary"),
            ("Join Date:", "join_date"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label, font=("Arial", 10, "bold"),
                     bg="#34495e", fg="white").grid(row=i, column=0, padx=10, pady=5, sticky=tk.W)
            entry = tk.Entry(form_frame, font=("Arial", 10), width=25, relief=tk.FLAT,
                             bg="#ecf0f1", fg="#2c3e50")
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.entries[key] = entry

        # Photo
        tk.Label(form_frame, text="Photo:", font=("Arial", 10, "bold"),
                 bg="#34495e", fg="white").grid(row=len(fields), column=0, padx=10, pady=5, sticky=tk.W)

        photo_frame = tk.Frame(form_frame, bg="#34495e")
        photo_frame.grid(row=len(fields), column=1, padx=10, pady=5)

        self.photo_label = tk.Label(photo_frame, text="No Photo", bg="#bdc3c7",
                                    width=15, height=5, relief=tk.SUNKEN)
        self.photo_label.pack()

        tk.Button(photo_frame, text="Browse Photo", command=self.browse_photo,
                  bg="#2980b9", fg="white", font=("Arial", 9), relief=tk.FLAT).pack(pady=3)

        # Buttons
        btn_frame = tk.Frame(form_frame, bg="#34495e")
        btn_frame.grid(row=len(fields) + 1, column=0, columnspan=2, pady=10)

        buttons = [
            ("Add", self.add_employee, "#2ecc71"),
            ("Update", self.update_employee, "#f39c12"),
            ("Delete", self.delete_employee, "#e74c3c"),
            ("Clear", self.clear_form, "#95a5a6"),
        ]

        for text, command, color in buttons:
            tk.Button(btn_frame, text=text, command=command,
                      bg=color, fg="white", font=("Arial", 10, "bold"),
                      relief=tk.FLAT, padx=10, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=5)

        # Right - Table
        table_frame = tk.LabelFrame(main_frame, text="Employee Records",
                                    font=("Arial", 12, "bold"), bg="#34495e", fg="white",
                                    relief=tk.GROOVE, bd=2)
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Search
        search_frame = tk.Frame(table_frame, bg="#34495e")
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(search_frame, text="Search:", font=("Arial", 10, "bold"),
                 bg="#34495e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.search_employees)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                                font=("Arial", 10), width=30, relief=tk.FLAT, bg="#ecf0f1")
        search_entry.pack(side=tk.LEFT, padx=10)

        columns = ("ID", "Emp ID", "Name", "Email", "Phone", "Designation", "Salary", "Join Date")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)

        style = ttk.Style()
        style.configure("Treeview", background="#ecf0f1", foreground="#2c3e50",
                        rowheight=25, fieldbackground="#ecf0f1")
        style.configure("Treeview.Heading", background="#2980b9", foreground="white",
                        font=("Arial", 10, "bold"))

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor=tk.CENTER)

        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<ButtonRelease-1>", self.select_employee)

    def browse_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if path:
            self.photo_path.set(path)
            img = Image.open(path)
            img = img.resize((100, 80), Image.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(img)
            self.photo_label.config(image=self.photo_image, text="")

    def add_employee(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        if not data['emp_id'] or not data['name']:
            messagebox.showerror("Error", "Employee ID and Name are required!")
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
            self.load_employees()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Employee ID already exists!")

    def update_employee(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select an employee to update!")
            return
        data = {k: v.get().strip() for k, v in self.entries.items()}
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
        self.load_employees()

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
            self.load_employees()

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.photo_path.set("")
        self.photo_label.config(image="", text="No Photo")
        self.photo_image = None
        self.selected_id = None

    def load_employees(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, emp_id, name, email, phone, designation, salary, join_date FROM employees")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def search_employees(self, *args):
        search = self.search_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT id, emp_id, name, email, phone, designation, salary, join_date
                          FROM employees WHERE LOWER(name) LIKE ? OR LOWER(emp_id) LIKE ?''',
                       (f'%{search}%', f'%{search}%'))
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def select_employee(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
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
                    self.entries[key].insert(0, row[i + 1] if row[i + 1] else "")
                if row[9]:
                    self.photo_path.set(row[9])
                    try:
                        img = Image.open(row[9])
                        img = img.resize((100, 80), Image.LANCZOS)
                        self.photo_image = ImageTk.PhotoImage(img)
                        self.photo_label.config(image=self.photo_image, text="")
                    except Exception:
                        self.photo_label.config(text="Photo N/A")


class SupplierManagement(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#2c3e50")
        self.app = parent
        self.selected_id = None
        self.create_widgets()
        self.load_suppliers()

    def create_widgets(self):
        Navbar(self, self.app)

        title = tk.Label(self, text="Supplier Management",
                         font=("Arial", 20, "bold"), bg="#2c3e50", fg="white")
        title.pack(pady=10)

        main_frame = tk.Frame(self, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        form_frame = tk.LabelFrame(main_frame, text="Supplier Details",
                                   font=("Arial", 12, "bold"), bg="#34495e", fg="white",
                                   relief=tk.GROOVE, bd=2)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5, ipadx=10, ipady=10)

        fields = [
            ("Supplier ID:", "supplier_id"),
            ("Name:", "name"),
            ("Email:", "email"),
            ("Phone:", "phone"),
            ("Address:", "address"),
            ("Company:", "company"),
            ("Description:", "description"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label, font=("Arial", 10, "bold"),
                     bg="#34495e", fg="white").grid(row=i, column=0, padx=10, pady=5, sticky=tk.W)
            if key == "description":
                entry = tk.Text(form_frame, font=("Arial", 10), width=25, height=4,
                                relief=tk.FLAT, bg="#ecf0f1", fg="#2c3e50")
            else:
                entry = tk.Entry(form_frame, font=("Arial", 10), width=25, relief=tk.FLAT,
                                 bg="#ecf0f1", fg="#2c3e50")
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.entries[key] = entry

        btn_frame = tk.Frame(form_frame, bg="#34495e")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)

        buttons = [
            ("Add", self.add_supplier, "#2ecc71"),
            ("Update", self.update_supplier, "#f39c12"),
            ("Delete", self.delete_supplier, "#e74c3c"),
            ("Clear", self.clear_form, "#95a5a6"),
        ]

        for text, command, color in buttons:
            tk.Button(btn_frame, text=text, command=command,
                      bg=color, fg="white", font=("Arial", 10, "bold"),
                      relief=tk.FLAT, padx=10, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=5)

        table_frame = tk.LabelFrame(main_frame, text="Supplier Records",
                                    font=("Arial", 12, "bold"), bg="#34495e", fg="white",
                                    relief=tk.GROOVE, bd=2)
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        search_frame = tk.Frame(table_frame, bg="#34495e")
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(search_frame, text="Search:", font=("Arial", 10, "bold"),
                 bg="#34495e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.search_suppliers)
        tk.Entry(search_frame, textvariable=self.search_var,
                 font=("Arial", 10), width=30, relief=tk.FLAT, bg="#ecf0f1").pack(side=tk.LEFT, padx=10)

        columns = ("ID", "Supplier ID", "Name", "Email", "Phone", "Company")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor=tk.CENTER)

        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<ButtonRelease-1>", self.select_supplier)

    def get_text(self, widget):
        if isinstance(widget, tk.Text):
            return widget.get("1.0", tk.END).strip()
        return widget.get().strip()

    def add_supplier(self):
        data = {k: self.get_text(v) for k, v in self.entries.items()}
        if not data['supplier_id'] or not data['name']:
            messagebox.showerror("Error", "Supplier ID and Name are required!")
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
            self.load_suppliers()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Supplier ID already exists!")

    def update_supplier(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a supplier to update!")
            return
        data = {k: self.get_text(v) for k, v in self.entries.items()}
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
        self.load_suppliers()

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
            self.load_suppliers()

    def clear_form(self):
        for key, widget in self.entries.items():
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
            else:
                widget.delete(0, tk.END)
        self.selected_id = None

    def load_suppliers(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, supplier_id, name, email, phone, company FROM suppliers")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def search_suppliers(self, *args):
        search = self.search_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT id, supplier_id, name, email, phone, company FROM suppliers
                          WHERE LOWER(name) LIKE ? OR LOWER(supplier_id) LIKE ?''',
                       (f'%{search}%', f'%{search}%'))
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def select_supplier(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
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
                        widget.insert("1.0", row[i + 1] if row[i + 1] else "")
                    else:
                        widget.delete(0, tk.END)
                        widget.insert(0, row[i + 1] if row[i + 1] else "")


class CategoryManagement(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#2c3e50")
        self.app = parent
        self.selected_id = None
        self.create_widgets()
        self.load_categories()

    def create_widgets(self):
        Navbar(self, self.app)

        title = tk.Label(self, text="Category Management",
                         font=("Arial", 20, "bold"), bg="#2c3e50", fg="white")
        title.pack(pady=10)

        main_frame = tk.Frame(self, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        form_frame = tk.LabelFrame(main_frame, text="Category Details",
                                   font=("Arial", 12, "bold"), bg="#34495e", fg="white",
                                   relief=tk.GROOVE, bd=2)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5, ipadx=10, ipady=10)

        fields = [
            ("Category ID:", "category_id"),
            ("Name:", "name"),
            ("Description:", "description"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label, font=("Arial", 10, "bold"),
                     bg="#34495e", fg="white").grid(row=i, column=0, padx=10, pady=10, sticky=tk.W)
            if key == "description":
                entry = tk.Text(form_frame, font=("Arial", 10), width=25, height=5,
                                relief=tk.FLAT, bg="#ecf0f1", fg="#2c3e50")
            else:
                entry = tk.Entry(form_frame, font=("Arial", 10), width=25, relief=tk.FLAT,
                                 bg="#ecf0f1", fg="#2c3e50")
            entry.grid(row=i, column=1, padx=10, pady=10)
            self.entries[key] = entry

        btn_frame = tk.Frame(form_frame, bg="#34495e")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=15)

        buttons = [
            ("Add", self.add_category, "#2ecc71"),
            ("Update", self.update_category, "#f39c12"),
            ("Delete", self.delete_category, "#e74c3c"),
            ("Clear", self.clear_form, "#95a5a6"),
        ]

        for text, command, color in buttons:
            tk.Button(btn_frame, text=text, command=command,
                      bg=color, fg="white", font=("Arial", 10, "bold"),
                      relief=tk.FLAT, padx=10, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=5)

        table_frame = tk.LabelFrame(main_frame, text="Category Records",
                                    font=("Arial", 12, "bold"), bg="#34495e", fg="white",
                                    relief=tk.GROOVE, bd=2)
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        search_frame = tk.Frame(table_frame, bg="#34495e")
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(search_frame, text="Search:", font=("Arial", 10, "bold"),
                 bg="#34495e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.search_categories)
        tk.Entry(search_frame, textvariable=self.search_var,
                 font=("Arial", 10), width=30, relief=tk.FLAT, bg="#ecf0f1").pack(side=tk.LEFT, padx=10)

        columns = ("ID", "Category ID", "Name", "Description")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor=tk.CENTER)

        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_y.set)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<ButtonRelease-1>", self.select_category)

    def get_text(self, widget):
        if isinstance(widget, tk.Text):
            return widget.get("1.0", tk.END).strip()
        return widget.get().strip()

    def add_category(self):
        data = {k: self.get_text(v) for k, v in self.entries.items()}
        if not data['category_id'] or not data['name']:
            messagebox.showerror("Error", "Category ID and Name are required!")
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
            self.load_categories()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Category ID already exists!")

    def update_category(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a category to update!")
            return
        data = {k: self.get_text(v) for k, v in self.entries.items()}
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE categories SET category_id=?, name=?, description=? WHERE id=?''',
                       (data['category_id'], data['name'], data['description'], self.selected_id))
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
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM categories WHERE id=?", (self.selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category deleted successfully!")
            self.clear_form()
            self.load_categories()

    def clear_form(self):
        for key, widget in self.entries.items():
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
            else:
                widget.delete(0, tk.END)
        self.selected_id = None

    def load_categories(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, category_id, name, description FROM categories")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def search_categories(self, *args):
        search = self.search_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT id, category_id, name, description FROM categories
                          WHERE LOWER(name) LIKE ? OR LOWER(category_id) LIKE ?''',
                       (f'%{search}%', f'%{search}%'))
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def select_category(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
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
                        widget.insert("1.0", row[i + 1] if row[i + 1] else "")
                    else:
                        widget.delete(0, tk.END)
                        widget.insert(0, row[i + 1] if row[i + 1] else "")


class ProductManagement(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#2c3e50")
        self.app = parent
        self.photo_path = tk.StringVar()
        self.photo_image = None
        self.selected_id = None
        self.create_widgets()
        self.load_products()

    def create_widgets(self):
        Navbar(self, self.app)

        title = tk.Label(self, text="Product Management",
                         font=("Arial", 20, "bold"), bg="#2c3e50", fg="white")
        title.pack(pady=10)

        main_frame = tk.Frame(self, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        form_frame = tk.LabelFrame(main_frame, text="Product Details",
                                   font=("Arial", 12, "bold"), bg="#34495e", fg="white",
                                   relief=tk.GROOVE, bd=2)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5, ipadx=10, ipady=10)

        fields = [
            ("Product ID:", "product_id"),
            ("Name:", "name"),
            ("Price:", "price"),
            ("Quantity:", "quantity"),
            ("Description:", "description"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label, font=("Arial", 10, "bold"),
                     bg="#34495e", fg="white").grid(row=i, column=0, padx=10, pady=5, sticky=tk.W)
            if key == "description":
                entry = tk.Text(form_frame, font=("Arial", 10), width=25, height=3,
                                relief=tk.FLAT, bg="#ecf0f1", fg="#2c3e50")
            else:
                entry = tk.Entry(form_frame, font=("Arial", 10), width=25, relief=tk.FLAT,
                                 bg="#ecf0f1", fg="#2c3e50")
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.entries[key] = entry

        # Category dropdown
        tk.Label(form_frame, text="Category:", font=("Arial", 10, "bold"),
                 bg="#34495e", fg="white").grid(row=len(fields), column=0, padx=10, pady=5, sticky=tk.W)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(form_frame, textvariable=self.category_var,
                                           font=("Arial", 10), width=23, state="readonly")
        self.category_combo.grid(row=len(fields), column=1, padx=10, pady=5)
        self.load_categories_combo()

        # Supplier dropdown
        tk.Label(form_frame, text="Supplier:", font=("Arial", 10, "bold"),
                 bg="#34495e", fg="white").grid(row=len(fields) + 1, column=0, padx=10, pady=5, sticky=tk.W)
        self.supplier_var = tk.StringVar()
        self.supplier_combo = ttk.Combobox(form_frame, textvariable=self.supplier_var,
                                           font=("Arial", 10), width=23, state="readonly")
        self.supplier_combo.grid(row=len(fields) + 1, column=1, padx=10, pady=5)
        self.load_suppliers_combo()

        # Photo
        tk.Label(form_frame, text="Photo:", font=("Arial", 10, "bold"),
                 bg="#34495e", fg="white").grid(row=len(fields) + 2, column=0, padx=10, pady=5, sticky=tk.W)

        photo_frame = tk.Frame(form_frame, bg="#34495e")
        photo_frame.grid(row=len(fields) + 2, column=1, padx=10, pady=5)

        self.photo_label = tk.Label(photo_frame, text="No Photo", bg="#bdc3c7",
                                    width=15, height=5, relief=tk.SUNKEN)
        self.photo_label.pack()

        tk.Button(photo_frame, text="Browse Photo", command=self.browse_photo,
                  bg="#2980b9", fg="white", font=("Arial", 9), relief=tk.FLAT).pack(pady=3)

        btn_frame = tk.Frame(form_frame, bg="#34495e")
        btn_frame.grid(row=len(fields) + 3, column=0, columnspan=2, pady=10)

        buttons = [
            ("Add", self.add_product, "#2ecc71"),
            ("Update", self.update_product, "#f39c12"),
            ("Delete", self.delete_product, "#e74c3c"),
            ("Clear", self.clear_form, "#95a5a6"),
        ]

        for text, command, color in buttons:
            tk.Button(btn_frame, text=text, command=command,
                      bg=color, fg="white", font=("Arial", 10, "bold"),
                      relief=tk.FLAT, padx=10, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=5)

        table_frame = tk.LabelFrame(main_frame, text="Product Records",
                                    font=("Arial", 12, "bold"), bg="#34495e", fg="white",
                                    relief=tk.GROOVE, bd=2)
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=5)

        search_frame = tk.Frame(table_frame, bg="#34495e")
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(search_frame, text="Search:", font=("Arial", 10, "bold"),
                 bg="#34495e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.search_products)
        tk.Entry(search_frame, textvariable=self.search_var,
                 font=("Arial", 10), width=30, relief=tk.FLAT, bg="#ecf0f1").pack(side=tk.LEFT, padx=10)

        columns = ("ID", "Product ID", "Name", "Category", "Supplier", "Price", "Quantity")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110, anchor=tk.CENTER)

        scrollbar_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<ButtonRelease-1>", self.select_product)

    def load_categories_combo(self):
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM categories")
        cats = [row[0] for row in cursor.fetchall()]
        conn.close()
        self.category_combo['values'] = cats

    def load_suppliers_combo(self):
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM suppliers")
        sups = [row[0] for row in cursor.fetchall()]
        conn.close()
        self.supplier_combo['values'] = sups

    def browse_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if path:
            self.photo_path.set(path)
            img = Image.open(path)
            img = img.resize((100, 80), Image.LANCZOS)
            self.photo_image = ImageTk.PhotoImage(img)
            self.photo_label.config(image=self.photo_image, text="")

    def get_text(self, widget):
        if isinstance(widget, tk.Text):
            return widget.get("1.0", tk.END).strip()
        return widget.get().strip()

    def add_product(self):
        data = {k: self.get_text(v) for k, v in self.entries.items()}
        if not data['product_id'] or not data['name']:
            messagebox.showerror("Error", "Product ID and Name are required!")
            return
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO products (product_id, name, category, supplier, price, quantity, description, photo)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                           (data['product_id'], data['name'], self.category_var.get(),
                            self.supplier_var.get(), data['price'], data['quantity'],
                            data['description'], self.photo_path.get()))
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
        data = {k: self.get_text(v) for k, v in self.entries.items()}
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''UPDATE products SET product_id=?, name=?, category=?, supplier=?,
                          price=?, quantity=?, description=?, photo=? WHERE id=?''',
                       (data['product_id'], data['name'], self.category_var.get(),
                        self.supplier_var.get(), data['price'], data['quantity'],
                        data['description'], self.photo_path.get(), self.selected_id))
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
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id=?", (self.selected_id,))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product deleted successfully!")
            self.clear_form()
            self.load_products()

    def clear_form(self):
        for key, widget in self.entries.items():
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
            else:
                widget.delete(0, tk.END)
        self.category_var.set("")
        self.supplier_var.set("")
        self.photo_path.set("")
        self.photo_label.config(image="", text="No Photo")
        self.photo_image = None
        self.selected_id = None

    def load_products(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, product_id, name, category, supplier, price, quantity FROM products")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def search_products(self, *args):
        search = self.search_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT id, product_id, name, category, supplier, price, quantity FROM products
                          WHERE LOWER(name) LIKE ? OR LOWER(product_id) LIKE ?''',
                       (f'%{search}%', f'%{search}%'))
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.tree.insert("", tk.END, values=row)

    def select_product(self, event):
        selected = self.tree.selection()
        if selected:
            item = self.tree.item(selected[0])
            values = item['values']
            self.selected_id = values[0]
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE id=?", (self.selected_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                keys = ['product_id', 'name', 'price', 'quantity', 'description']
                field_indices = [1, 2, 5, 6, 7]
                for key, idx in zip(keys, field_indices):
                    widget = self.entries[key]
                    if isinstance(widget, tk.Text):
                        widget.delete("1.0", tk.END)
                        widget.insert("1.0", row[idx] if row[idx] else "")
                    else:
                        widget.delete(0, tk.END)
                        widget.insert(0, row[idx] if row[idx] else "")
                self.category_var.set(row[3] if row[3] else "")
                self.supplier_var.set(row[4] if row[4] else "")
                if row[8]:
                    self.photo_path.set(row[8])
                    try:
                        img = Image.open(row[8])
                        img = img.resize((100, 80), Image.LANCZOS)
                        self.photo_image = ImageTk.PhotoImage(img)
                        self.photo_label.config(image=self.photo_image, text="")
                    except Exception:
                        self.photo_label.config(text="Photo N/A")


class BillingManagement(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#2c3e50")
        self.app = parent
        self.cart_items = []
        self.selected_bill_id = None
        self.create_widgets()
        self.load_bills()
        self.generate_invoice_no()

    def create_widgets(self):
        Navbar(self, self.app)

        title = tk.Label(self, text="Billing Management",
                         font=("Arial", 20, "bold"), bg="#2c3e50", fg="white")
        title.pack(pady=5)

        main_frame = tk.Frame(self, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left - Billing Form
        left_frame = tk.Frame(main_frame, bg="#2c3e50")
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Customer Info
        cust_frame = tk.LabelFrame(left_frame, text="Customer Information",
                                   font=("Arial", 11, "bold"), bg="#34495e", fg="white",
                                   relief=tk.GROOVE, bd=2)
        cust_frame.pack(fill=tk.X, pady=5, ipadx=5, ipady=5)

        cust_fields = [
            ("Invoice No:", "invoice_no"),
            ("Customer Name:", "customer_name"),
            ("Phone:", "customer_phone"),
            ("Email:", "customer_email"),
            ("Date:", "bill_date"),
        ]

        self.cust_entries = {}
        for i, (label, key) in enumerate(cust_fields):
            tk.Label(cust_frame, text=label, font=("Arial", 9, "bold"),
                     bg="#34495e", fg="white").grid(row=i, column=0, padx=5, pady=3, sticky=tk.W)
            entry = tk.Entry(cust_frame, font=("Arial", 9), width=22, relief=tk.FLAT,
                             bg="#ecf0f1", fg="#2c3e50")
            entry.grid(row=i, column=1, padx=5, pady=3)
            self.cust_entries[key] = entry

        # Product Selection
        prod_frame = tk.LabelFrame(left_frame, text="Add Product to Cart",
                                   font=("Arial", 11, "bold"), bg="#34495e", fg="white",
                                   relief=tk.GROOVE, bd=2)
        prod_frame.pack(fill=tk.X, pady=5, ipadx=5, ipady=5)

        tk.Label(prod_frame, text="Product:", font=("Arial", 9, "bold"),
                 bg="#34495e", fg="white").grid(row=0, column=0, padx=5, pady=3, sticky=tk.W)
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(prod_frame, textvariable=self.product_var,
                                          font=("Arial", 9), width=20, state="readonly")
        self.product_combo.grid(row=0, column=1, padx=5, pady=3)
        self.product_combo.bind("<<ComboboxSelected>>", self.on_product_select)
        self.load_products_combo()

        tk.Label(prod_frame, text="Price:", font=("Arial", 9, "bold"),
                 bg="#34495e", fg="white").grid(row=1, column=0, padx=5, pady=3, sticky=tk.W)
        self.price_var = tk.StringVar()
        self.price_entry = tk.Entry(prod_frame, textvariable=self.price_var,
                                    font=("Arial", 9), width=22, relief=tk.FLAT,
                                    bg="#ecf0f1", fg="#2c3e50", state="readonly")
        self.price_entry.grid(row=1, column=1, padx=5, pady=3)

        tk.Label(prod_frame, text="Quantity:", font=("Arial", 9, "bold"),
                 bg="#34495e", fg="white").grid(row=2, column=0, padx=5, pady=3, sticky=tk.W)
        self.qty_var = tk.StringVar(value="1")
        self.qty_entry = tk.Entry(prod_frame, textvariable=self.qty_var,
                                  font=("Arial", 9), width=22, relief=tk.FLAT,
                                  bg="#ecf0f1", fg="#2c3e50")
        self.qty_entry.grid(row=2, column=1, padx=5, pady=3)

        tk.Button(prod_frame, text="Add to Cart", command=self.add_to_cart,
                  bg="#2ecc71", fg="white", font=("Arial", 10, "bold"),
                  relief=tk.FLAT, padx=10, pady=5, cursor="hand2").grid(row=3, column=0, columnspan=2, pady=5)

        # Cart
        cart_frame = tk.LabelFrame(left_frame, text="Cart",
                                   font=("Arial", 11, "bold"), bg="#34495e", fg="white",
                                   relief=tk.GROOVE, bd=2)
        cart_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        cart_columns = ("Product", "Price", "Qty", "Total")
        self.cart_tree = ttk.Treeview(cart_frame, columns=cart_columns, show="headings", height=8)
        for col in cart_columns:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=90, anchor=tk.CENTER)
        self.cart_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        cart_btn_frame = tk.Frame(cart_frame, bg="#34495e")
        cart_btn_frame.pack(fill=tk.X, padx=5, pady=3)

        tk.Button(cart_btn_frame, text="Remove Selected", command=self.remove_from_cart,
                  bg="#e74c3c", fg="white", font=("Arial", 9, "bold"),
                  relief=tk.FLAT, padx=5, pady=3).pack(side=tk.LEFT, padx=3)

        tk.Button(cart_btn_frame, text="Clear Cart", command=self.clear_cart,
                  bg="#95a5a6", fg="white", font=("Arial", 9, "bold"),
                  relief=tk.FLAT, padx=5, pady=3).pack(side=tk.LEFT, padx=3)

        # Total
        total_frame = tk.Frame(left_frame, bg="#34495e", relief=tk.GROOVE, bd=2)
        total_frame.pack(fill=tk.X, pady=5, ipadx=5, ipady=5)

        self.total_var = tk.StringVar(value="Total: $0.00")
        tk.Label(total_frame, textvariable=self.total_var, font=("Arial", 14, "bold"),
                 bg="#34495e", fg="#f39c12").pack(pady=5)

        bill_btn_frame = tk.Frame(left_frame, bg="#2c3e50")
        bill_btn_frame.pack(fill=tk.X, pady=5)

        tk.Button(bill_btn_frame, text="Generate Bill", command=self.generate_bill,
                  bg="#2ecc71", fg="white", font=("Arial", 11, "bold"),
                  relief=tk.FLAT, padx=15, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=5)

        tk.Button(bill_btn_frame, text="Print Bill", command=self.print_bill,
                  bg="#3498db", fg="white", font=("Arial", 11, "bold"),
                  relief=tk.FLAT, padx=15, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=5)

        tk.Button(bill_btn_frame, text="New Bill", command=self.new_bill,
                  bg="#9b59b6", fg="white", font=("Arial", 11, "bold"),
                  relief=tk.FLAT, padx=15, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=5)

        # Right - Bill Records
        right_frame = tk.Frame(main_frame, bg="#2c3e50")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        bills_frame = tk.LabelFrame(right_frame, text="Bill Records",
                                    font=("Arial", 12, "bold"), bg="#34495e", fg="white",
                                    relief=tk.GROOVE, bd=2)
        bills_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        search_frame = tk.Frame(bills_frame, bg="#34495e")
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(search_frame, text="Search:", font=("Arial", 10, "bold"),
                 bg="#34495e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.search_bills)
        tk.Entry(search_frame, textvariable=self.search_var,
                 font=("Arial", 10), width=25, relief=tk.FLAT, bg="#ecf0f1").pack(side=tk.LEFT, padx=10)

        bill_columns = ("ID", "Invoice No", "Customer", "Phone", "Date", "Total")
        self.bills_tree = ttk.Treeview(bills_frame, columns=bill_columns, show="headings", height=12)
        for col in bill_columns:
            self.bills_tree.heading(col, text=col)
            self.bills_tree.column(col, width=110, anchor=tk.CENTER)

        scrollbar_y = ttk.Scrollbar(bills_frame, orient=tk.VERTICAL, command=self.bills_tree.yview)
        self.bills_tree.configure(yscrollcommand=scrollbar_y.set)
        self.bills_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.bills_tree.bind("<ButtonRelease-1>", self.select_bill)

        # Bill Details
        detail_frame = tk.LabelFrame(right_frame, text="Bill Details",
                                     font=("Arial", 12, "bold"), bg="#34495e", fg="white",
                                     relief=tk.GROOVE, bd=2)
        detail_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.bill_detail_text = tk.Text(detail_frame, font=("Courier", 10), bg="#1a252f",
                                        fg="#2ecc71", height=12, relief=tk.FLAT)
        self.bill_detail_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        del_btn_frame = tk.Frame(right_frame, bg="#2c3e50")
        del_btn_frame.pack(fill=tk.X, pady=3)

        tk.Button(del_btn_frame, text="Delete Bill", command=self.delete_bill,
                  bg="#e74c3c", fg="white", font=("Arial", 10, "bold"),
                  relief=tk.FLAT, padx=10, pady=5, cursor="hand2").pack(side=tk.LEFT, padx=5)

    def generate_invoice_no(self):
        invoice_no = "INV-" + ''.join(random.choices(string.digits, k=6))
        self.cust_entries['invoice_no'].delete(0, tk.END)
        self.cust_entries['invoice_no'].insert(0, invoice_no)
        self.cust_entries['bill_date'].delete(0, tk.END)
        self.cust_entries['bill_date'].insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def load_products_combo(self):
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT name, price FROM products")
        self.products_data = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        self.product_combo['values'] = list(self.products_data.keys())

    def on_product_select(self, event):
        product = self.product_var.get()
        if product in self.products_data:
            self.price_var.set(str(self.products_data[product]))

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

        price = float(self.products_data.get(product, 0))
        total = price * qty

        self.cart_items.append({
            'product': product,
            'price': price,
            'qty': qty,
            'total': total
        })

        self.cart_tree.insert("", tk.END, values=(product, f"${price:.2f}", qty, f"${total:.2f}"))
        self.update_total()
        self.product_var.set("")
        self.price_var.set("")
        self.qty_var.set("1")

    def remove_from_cart(self):
        selected = self.cart_tree.selection()
        if selected:
            idx = self.cart_tree.index(selected[0])
            self.cart_tree.delete(selected[0])
            if 0 <= idx < len(self.cart_items):
                self.cart_items.pop(idx)
            self.update_total()

    def clear_cart(self):
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        self.cart_items = []
        self.update_total()

    def update_total(self):
        total = sum(item['total'] for item in self.cart_items)
        self.total_var.set(f"Total: ${total:.2f}")

    def generate_bill(self):
        if not self.cart_items:
            messagebox.showerror("Error", "Cart is empty!")
            return

        invoice_no = self.cust_entries['invoice_no'].get().strip()
        customer_name = self.cust_entries['customer_name'].get().strip()
        customer_phone = self.cust_entries['customer_phone'].get().strip()
        customer_email = self.cust_entries['customer_email'].get().strip()
        bill_date = self.cust_entries['bill_date'].get().strip()

        if not invoice_no or not customer_name:
            messagebox.showerror("Error", "Invoice No and Customer Name are required!")
            return

        total = sum(item['total'] for item in self.cart_items)

        bill_details = "INVOICE: " + invoice_no + "\n"
        bill_details += "=" * 50 + "\n"
        bill_details += f"Customer: {customer_name}\n"
        bill_details += f"Phone: {customer_phone}\n"
        bill_details += f"Email: {customer_email}\n"
        bill_details += f"Date: {bill_date}\n"
        bill_details += "=" * 50 + "\n"
        bill_details += f"{'Product':<20} {'Price':>8} {'Qty':>5} {'Total':>10}\n"
        bill_details += "-" * 50 + "\n"
        for item in self.cart_items:
            bill_details += f"{item['product']:<20} ${item['price']:>7.2f} {item['qty']:>5} ${item['total']:>9.2f}\n"
        bill_details += "=" * 50 + "\n"
        bill_details += f"{'TOTAL AMOUNT':>40} ${total:>9.2f}\n"
        bill_details += "=" * 50 + "\n"
        bill_details += "Thank you for your purchase!\n"

        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO bills (invoice_no, customer_name, customer_phone, customer_email, bill_date, total_amount, bill_details)
                              VALUES (?, ?, ?, ?, ?, ?, ?)''',
                           (invoice_no, customer_name, customer_phone, customer_email,
                            bill_date, total, bill_details))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Bill generated successfully!\nInvoice No: {invoice_no}")
            self.bill_detail_text.delete("1.0", tk.END)
            self.bill_detail_text.insert("1.0", bill_details)
            self.load_bills()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Invoice No already exists!")

    def print_bill(self):
        selected = self.bills_tree.selection()
        if not selected and not self.bill_detail_text.get("1.0", tk.END).strip():
            messagebox.showerror("Error", "No bill to print!")
            return

        bill_text = self.bill_detail_text.get("1.0", tk.END)
        if not bill_text.strip():
            messagebox.showerror("Error", "No bill content to print!")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Save Bill"
        )
        if save_path:
            with open(save_path, 'w') as f:
                f.write(bill_text)
            messagebox.showinfo("Success", f"Bill saved to {save_path}")

    def new_bill(self):
        self.clear_cart()
        for entry in self.cust_entries.values():
            entry.delete(0, tk.END)
        self.generate_invoice_no()
        self.bill_detail_text.delete("1.0", tk.END)
        self.selected_bill_id = None

    def load_bills(self):
        for item in self.bills_tree.get_children():
            self.bills_tree.delete(item)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, invoice_no, customer_name, customer_phone, bill_date, total_amount FROM bills ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.bills_tree.insert("", tk.END, values=(row[0], row[1], row[2], row[3], row[4], f"${row[5]:.2f}"))

    def search_bills(self, *args):
        search = self.search_var.get().lower()
        for item in self.bills_tree.get_children():
            self.bills_tree.delete(item)
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT id, invoice_no, customer_name, customer_phone, bill_date, total_amount FROM bills
                          WHERE LOWER(invoice_no) LIKE ? OR LOWER(customer_name) LIKE ?
                          ORDER BY id DESC''',
                       (f'%{search}%', f'%{search}%'))
        rows = cursor.fetchall()
        conn.close()
        for row in rows:
            self.bills_tree.insert("", tk.END, values=(row[0], row[1], row[2], row[3], row[4], f"${row[5]:.2f}"))

    def select_bill(self, event):
        selected = self.bills_tree.selection()
        if selected:
            item = self.bills_tree.item(selected[0])
            values = item['values']
            self.selected_bill_id = values[0]
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bills WHERE id=?", (self.selected_bill_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                self.bill_detail_text.delete("1.0", tk.END)
                self.bill_detail_text.insert("1.0", row[7] if row[7] else "")

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
            self.bill_detail_text.delete("1.0", tk.END)
            self.selected_bill_id = None
            self.load_bills()


if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()