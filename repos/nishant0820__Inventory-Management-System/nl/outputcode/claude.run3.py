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
        product_type TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cat_id TEXT UNIQUE NOT NULL,
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
        description TEXT
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
        self.configure(bg="#1a1a2e")
        
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
        self.show_frame(EmployeeFrame)
    
    def show_supplier(self):
        self.show_frame(SupplierFrame)
    
    def show_category(self):
        self.show_frame(CategoryFrame)
    
    def show_product(self):
        self.show_frame(ProductFrame)
    
    def show_billing(self):
        self.show_frame(BillingFrame)
    
    def show_bills(self):
        self.show_frame(BillsFrame)

class NavigationBar(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#16213e", height=60)
        self.app = app
        self.pack(fill=tk.X, side=tk.TOP)
        self.create_nav()
    
    def create_nav(self):
        title_label = tk.Label(self, text="Inventory Management System",
                               font=("Arial", 18, "bold"), bg="#16213e", fg="white")
        title_label.pack(side=tk.LEFT, padx=20, pady=10)
        
        nav_buttons = [
            ("Dashboard", self.app.show_dashboard),
            ("Employee", self.app.show_employee),
            ("Supplier", self.app.show_supplier),
            ("Category", self.app.show_category),
            ("Product", self.app.show_product),
            ("Billing", self.app.show_billing),
            ("Bills", self.app.show_bills),
        ]
        
        for text, command in nav_buttons:
            btn = tk.Button(self, text=text, command=command,
                           bg="#0f3460", fg="white", font=("Arial", 10, "bold"),
                           relief=tk.FLAT, padx=10, pady=5,
                           activebackground="#e94560", activeforeground="white",
                           cursor="hand2")
            btn.pack(side=tk.RIGHT, padx=5, pady=10)

class Dashboard(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.app = parent
        self.create_widgets()
        self.update_time()
    
    def create_widgets(self):
        nav = NavigationBar(self, self.app)
        
        # Header with time
        header_frame = tk.Frame(self, bg="#16213e", pady=10)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.time_label = tk.Label(header_frame, text="", font=("Arial", 14),
                                   bg="#16213e", fg="#e94560")
        self.time_label.pack(side=tk.RIGHT, padx=20)
        
        welcome_label = tk.Label(header_frame, text="Welcome to Inventory Management System",
                                 font=("Arial", 16, "bold"), bg="#16213e", fg="white")
        welcome_label.pack(side=tk.LEFT, padx=20)
        
        # Stats frame
        stats_frame = tk.Frame(self, bg="#1a1a2e")
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.create_stat_card(stats_frame, "Employees", self.get_count("employees"), "#e94560", 0)
        self.create_stat_card(stats_frame, "Suppliers", self.get_count("suppliers"), "#0f3460", 1)
        self.create_stat_card(stats_frame, "Categories", self.get_count("categories"), "#533483", 2)
        self.create_stat_card(stats_frame, "Products", self.get_count("products"), "#05c46b", 3)
        self.create_stat_card(stats_frame, "Bills", self.get_count("bills"), "#ffd32a", 4)
        
        # Quick access buttons
        quick_frame = tk.Frame(self, bg="#1a1a2e")
        quick_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(quick_frame, text="Quick Access", font=("Arial", 14, "bold"),
                 bg="#1a1a2e", fg="white").pack(anchor=tk.W, pady=5)
        
        buttons_frame = tk.Frame(quick_frame, bg="#1a1a2e")
        buttons_frame.pack(fill=tk.BOTH, expand=True)
        
        quick_buttons = [
            ("👤 Manage Employees", self.app.show_employee, "#e94560"),
            ("🏢 Manage Suppliers", self.app.show_supplier, "#0f3460"),
            ("📦 Manage Categories", self.app.show_category, "#533483"),
            ("🛍️ Manage Products", self.app.show_product, "#05c46b"),
            ("🧾 Create Bill", self.app.show_billing, "#ffd32a"),
            ("📋 View Bills", self.app.show_bills, "#ff5e57"),
        ]
        
        for i, (text, command, color) in enumerate(quick_buttons):
            row = i // 3
            col = i % 3
            btn = tk.Button(buttons_frame, text=text, command=command,
                           bg=color, fg="white", font=("Arial", 12, "bold"),
                           relief=tk.FLAT, padx=20, pady=30,
                           activebackground=color, cursor="hand2",
                           width=20)
            btn.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        for i in range(3):
            buttons_frame.columnconfigure(i, weight=1)
        for i in range(2):
            buttons_frame.rowconfigure(i, weight=1)
    
    def create_stat_card(self, parent, title, count, color, col):
        card = tk.Frame(parent, bg=color, padx=20, pady=15, relief=tk.RAISED, bd=2)
        card.grid(row=0, column=col, padx=10, pady=5, sticky="ew")
        parent.columnconfigure(col, weight=1)
        
        tk.Label(card, text=str(count), font=("Arial", 24, "bold"),
                 bg=color, fg="white").pack()
        tk.Label(card, text=title, font=("Arial", 12),
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
    
    def update_time(self):
        now = datetime.now().strftime("%A, %B %d, %Y  %H:%M:%S")
        self.time_label.config(text=now)
        self.after(1000, self.update_time)

class EmployeeFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.app = parent
        self.photo_path = tk.StringVar()
        self.selected_id = None
        self.photo_image = None
        self.create_widgets()
        self.load_data()
    
    def create_widgets(self):
        nav = NavigationBar(self, self.app)
        
        tk.Label(self, text="Employee Management", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="white").pack(pady=10)
        
        main_frame = tk.Frame(self, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left form
        form_frame = tk.Frame(main_frame, bg="#16213e", padx=20, pady=20)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        tk.Label(form_frame, text="Employee Details", font=("Arial", 14, "bold"),
                 bg="#16213e", fg="#e94560").grid(row=0, column=0, columnspan=2, pady=10)
        
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
        for i, (label, key) in enumerate(fields, 1):
            tk.Label(form_frame, text=label, bg="#16213e", fg="white",
                    font=("Arial", 10)).grid(row=i, column=0, sticky=tk.W, pady=5)
            entry = tk.Entry(form_frame, font=("Arial", 10), width=25,
                           bg="#0f3460", fg="white", insertbackground="white")
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.entries[key] = entry
        
        # Photo
        tk.Label(form_frame, text="Photo:", bg="#16213e", fg="white",
                font=("Arial", 10)).grid(row=len(fields)+1, column=0, sticky=tk.W, pady=5)
        
        photo_frame = tk.Frame(form_frame, bg="#16213e")
        photo_frame.grid(row=len(fields)+1, column=1, pady=5)
        
        self.photo_label = tk.Label(photo_frame, text="No Photo", bg="#0f3460",
                                    fg="white", width=15, height=5)
        self.photo_label.pack()
        
        tk.Button(photo_frame, text="Browse Photo", command=self.browse_photo,
                 bg="#533483", fg="white", font=("Arial", 9)).pack(pady=2)
        
        # Buttons
        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=len(fields)+2, column=0, columnspan=2, pady=15)
        
        tk.Button(btn_frame, text="Add", command=self.add_employee,
                 bg="#05c46b", fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", command=self.update_employee,
                 bg="#ffd32a", fg="black", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_employee,
                 bg="#e94560", fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_form,
                 bg="#0f3460", fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        # Right table
        table_frame = tk.Frame(main_frame, bg="#16213e")
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # Search
        search_frame = tk.Frame(table_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.search_data)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                               bg="#0f3460", fg="white", insertbackground="white", width=30)
        search_entry.pack(side=tk.LEFT, padx=10)
        
        # Treeview
        columns = ("ID", "Emp ID", "Name", "Email", "Phone", "Designation", "Salary", "Join Date")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        
        style = ttk.Style()
        style.configure("Treeview", background="#0f3460", foreground="white",
                       fieldbackground="#0f3460", font=("Arial", 9))
        style.configure("Treeview.Heading", background="#e94560", foreground="white",
                       font=("Arial", 9, "bold"))
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<ButtonRelease-1>", self.select_record)
    
    def browse_photo(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif")])
        if path:
            self.photo_path.set(path)
            try:
                img = Image.open(path)
                img = img.resize((100, 80), Image.LANCZOS)
                self.photo_image = ImageTk.PhotoImage(img)
                self.photo_label.config(image=self.photo_image, text="")
            except:
                self.photo_label.config(text="Photo loaded")
    
    def add_employee(self):
        data = {k: v.get() for k, v in self.entries.items()}
        if not data['emp_id'] or not data['name']:
            messagebox.showerror("Error", "Employee ID and Name are required!")
            return
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO employees (emp_id, name, email, phone, address, 
                            designation, salary, join_date, photo) VALUES (?,?,?,?,?,?,?,?,?)''',
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
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def update_employee(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select an employee to update!")
            return
        data = {k: v.get() for k, v in self.entries.items()}
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''UPDATE employees SET emp_id=?, name=?, email=?, phone=?, 
                            address=?, designation=?, salary=?, join_date=?, photo=? 
                            WHERE id=?''',
                          (data['emp_id'], data['name'], data['email'], data['phone'],
                           data['address'], data['designation'], data['salary'],
                           data['join_date'], self.photo_path.get(), self.selected_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee updated successfully!")
            self.clear_form()
            self.load_data()
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def delete_employee(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select an employee to delete!")
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
        self.photo_path.set("")
        self.photo_label.config(image="", text="No Photo")
        self.photo_image = None
        self.selected_id = None
    
    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, emp_id, name, email, phone, designation, salary, join_date FROM employees")
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def search_data(self, *args):
        search_term = self.search_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT id, emp_id, name, email, phone, designation, salary, join_date 
                            FROM employees WHERE LOWER(name) LIKE ? OR LOWER(emp_id) LIKE ?''',
                          (f'%{search_term}%', f'%{search_term}%'))
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            pass
    
    def select_record(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])['values']
            self.selected_id = values[0]
            try:
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
                            img = Image.open(row[9])
                            img = img.resize((100, 80), Image.LANCZOS)
                            self.photo_image = ImageTk.PhotoImage(img)
                            self.photo_label.config(image=self.photo_image, text="")
                        except:
                            self.photo_label.config(text="Photo")
            except Exception as e:
                pass

class SupplierFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.app = parent
        self.selected_id = None
        self.create_widgets()
        self.load_data()
    
    def create_widgets(self):
        nav = NavigationBar(self, self.app)
        
        tk.Label(self, text="Supplier Management", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="white").pack(pady=10)
        
        main_frame = tk.Frame(self, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left form
        form_frame = tk.Frame(main_frame, bg="#16213e", padx=20, pady=20)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        tk.Label(form_frame, text="Supplier Details", font=("Arial", 14, "bold"),
                 bg="#16213e", fg="#0f3460").grid(row=0, column=0, columnspan=2, pady=10)
        
        fields = [
            ("Supplier ID:", "supplier_id"),
            ("Name:", "name"),
            ("Email:", "email"),
            ("Phone:", "phone"),
            ("Address:", "address"),
            ("Company:", "company"),
            ("Product Type:", "product_type"),
        ]
        
        self.entries = {}
        for i, (label, key) in enumerate(fields, 1):
            tk.Label(form_frame, text=label, bg="#16213e", fg="white",
                    font=("Arial", 10)).grid(row=i, column=0, sticky=tk.W, pady=5)
            entry = tk.Entry(form_frame, font=("Arial", 10), width=25,
                           bg="#0f3460", fg="white", insertbackground="white")
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.entries[key] = entry
        
        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=15)
        
        tk.Button(btn_frame, text="Add", command=self.add_supplier,
                 bg="#05c46b", fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", command=self.update_supplier,
                 bg="#ffd32a", fg="black", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_supplier,
                 bg="#e94560", fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_form,
                 bg="#0f3460", fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        # Right table
        table_frame = tk.Frame(main_frame, bg="#16213e")
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        search_frame = tk.Frame(table_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.search_data)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                               bg="#0f3460", fg="white", insertbackground="white", width=30)
        search_entry.pack(side=tk.LEFT, padx=10)
        
        columns = ("ID", "Supplier ID", "Name", "Email", "Phone", "Company", "Product Type")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<ButtonRelease-1>", self.select_record)
    
    def add_supplier(self):
        data = {k: v.get() for k, v in self.entries.items()}
        if not data['supplier_id'] or not data['name']:
            messagebox.showerror("Error", "Supplier ID and Name are required!")
            return
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO suppliers (supplier_id, name, email, phone, address, company, product_type) 
                            VALUES (?,?,?,?,?,?,?)''',
                          (data['supplier_id'], data['name'], data['email'], data['phone'],
                           data['address'], data['company'], data['product_type']))
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
            messagebox.showerror("Error", "Please select a supplier to update!")
            return
        data = {k: v.get() for k, v in self.entries.items()}
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''UPDATE suppliers SET supplier_id=?, name=?, email=?, phone=?, 
                            address=?, company=?, product_type=? WHERE id=?''',
                          (data['supplier_id'], data['name'], data['email'], data['phone'],
                           data['address'], data['company'], data['product_type'], self.selected_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier updated successfully!")
            self.clear_form()
            self.load_data()
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def delete_supplier(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a supplier to delete!")
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
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.selected_id = None
    
    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, supplier_id, name, email, phone, company, product_type FROM suppliers")
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def search_data(self, *args):
        search_term = self.search_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT id, supplier_id, name, email, phone, company, product_type 
                            FROM suppliers WHERE LOWER(name) LIKE ? OR LOWER(supplier_id) LIKE ?''',
                          (f'%{search_term}%', f'%{search_term}%'))
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except:
            pass
    
    def select_record(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])['values']
            self.selected_id = values[0]
            try:
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM suppliers WHERE id=?", (self.selected_id,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    keys = ['supplier_id', 'name', 'email', 'phone', 'address', 'company', 'product_type']
                    for i, key in enumerate(keys):
                        self.entries[key].delete(0, tk.END)
                        self.entries[key].insert(0, row[i+1] if row[i+1] else "")
            except:
                pass

class CategoryFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.app = parent
        self.selected_id = None
        self.create_widgets()
        self.load_data()
    
    def create_widgets(self):
        nav = NavigationBar(self, self.app)
        
        tk.Label(self, text="Category Management", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="white").pack(pady=10)
        
        main_frame = tk.Frame(self, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left form
        form_frame = tk.Frame(main_frame, bg="#16213e", padx=20, pady=20)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        tk.Label(form_frame, text="Category Details", font=("Arial", 14, "bold"),
                 bg="#16213e", fg="#533483").grid(row=0, column=0, columnspan=2, pady=10)
        
        fields = [
            ("Category ID:", "cat_id"),
            ("Name:", "name"),
            ("Description:", "description"),
        ]
        
        self.entries = {}
        for i, (label, key) in enumerate(fields, 1):
            tk.Label(form_frame, text=label, bg="#16213e", fg="white",
                    font=("Arial", 10)).grid(row=i, column=0, sticky=tk.W, pady=5)
            if key == "description":
                entry = tk.Text(form_frame, font=("Arial", 10), width=25, height=4,
                               bg="#0f3460", fg="white", insertbackground="white")
                entry.grid(row=i, column=1, padx=10, pady=5)
            else:
                entry = tk.Entry(form_frame, font=("Arial", 10), width=25,
                               bg="#0f3460", fg="white", insertbackground="white")
                entry.grid(row=i, column=1, padx=10, pady=5)
            self.entries[key] = entry
        
        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=15)
        
        tk.Button(btn_frame, text="Add", command=self.add_category,
                 bg="#05c46b", fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", command=self.update_category,
                 bg="#ffd32a", fg="black", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_category,
                 bg="#e94560", fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_form,
                 bg="#0f3460", fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        # Right table
        table_frame = tk.Frame(main_frame, bg="#16213e")
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        search_frame = tk.Frame(table_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.search_data)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                               bg="#0f3460", fg="white", insertbackground="white", width=30)
        search_entry.pack(side=tk.LEFT, padx=10)
        
        columns = ("ID", "Category ID", "Name", "Description")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<ButtonRelease-1>", self.select_record)
    
    def get_entry_value(self, key):
        entry = self.entries[key]
        if isinstance(entry, tk.Text):
            return entry.get("1.0", tk.END).strip()
        return entry.get()
    
    def add_category(self):
        cat_id = self.get_entry_value('cat_id')
        name = self.get_entry_value('name')
        description = self.get_entry_value('description')
        
        if not cat_id or not name:
            messagebox.showerror("Error", "Category ID and Name are required!")
            return
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("INSERT INTO categories (cat_id, name, description) VALUES (?,?,?)",
                          (cat_id, name, description))
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
            messagebox.showerror("Error", "Please select a category to update!")
            return
        cat_id = self.get_entry_value('cat_id')
        name = self.get_entry_value('name')
        description = self.get_entry_value('description')
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("UPDATE categories SET cat_id=?, name=?, description=? WHERE id=?",
                          (cat_id, name, description, self.selected_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category updated successfully!")
            self.clear_form()
            self.load_data()
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def delete_category(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a category to delete!")
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
        for key, entry in self.entries.items():
            if isinstance(entry, tk.Text):
                entry.delete("1.0", tk.END)
            else:
                entry.delete(0, tk.END)
        self.selected_id = None
    
    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, cat_id, name, description FROM categories")
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def search_data(self, *args):
        search_term = self.search_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT id, cat_id, name, description FROM categories 
                            WHERE LOWER(name) LIKE ? OR LOWER(cat_id) LIKE ?''',
                          (f'%{search_term}%', f'%{search_term}%'))
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except:
            pass
    
    def select_record(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])['values']
            self.selected_id = values[0]
            try:
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM categories WHERE id=?", (self.selected_id,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    self.entries['cat_id'].delete(0, tk.END)
                    self.entries['cat_id'].insert(0, row[1] if row[1] else "")
                    self.entries['name'].delete(0, tk.END)
                    self.entries['name'].insert(0, row[2] if row[2] else "")
                    self.entries['description'].delete("1.0", tk.END)
                    self.entries['description'].insert("1.0", row[3] if row[3] else "")
            except:
                pass

class ProductFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.app = parent
        self.selected_id = None
        self.create_widgets()
        self.load_data()
    
    def create_widgets(self):
        nav = NavigationBar(self, self.app)
        
        tk.Label(self, text="Product Management", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="white").pack(pady=10)
        
        main_frame = tk.Frame(self, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left form
        form_frame = tk.Frame(main_frame, bg="#16213e", padx=20, pady=20)
        form_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        tk.Label(form_frame, text="Product Details", font=("Arial", 14, "bold"),
                 bg="#16213e", fg="#05c46b").grid(row=0, column=0, columnspan=2, pady=10)
        
        # Get categories and suppliers for dropdowns
        categories = self.get_categories()
        suppliers = self.get_suppliers()
        
        tk.Label(form_frame, text="Product ID:", bg="#16213e", fg="white",
                font=("Arial", 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.product_id_entry = tk.Entry(form_frame, font=("Arial", 10), width=25,
                                        bg="#0f3460", fg="white", insertbackground="white")
        self.product_id_entry.grid(row=1, column=1, padx=10, pady=5)
        
        tk.Label(form_frame, text="Name:", bg="#16213e", fg="white",
                font=("Arial", 10)).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.name_entry = tk.Entry(form_frame, font=("Arial", 10), width=25,
                                  bg="#0f3460", fg="white", insertbackground="white")
        self.name_entry.grid(row=2, column=1, padx=10, pady=5)
        
        tk.Label(form_frame, text="Category:", bg="#16213e", fg="white",
                font=("Arial", 10)).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(form_frame, textvariable=self.category_var,
                                          values=categories, width=23)
        self.category_combo.grid(row=3, column=1, padx=10, pady=5)
        
        tk.Label(form_frame, text="Supplier:", bg="#16213e", fg="white",
                font=("Arial", 10)).grid(row=4, column=0, sticky=tk.W, pady=5)
        self.supplier_var = tk.StringVar()
        self.supplier_combo = ttk.Combobox(form_frame, textvariable=self.supplier_var,
                                          values=suppliers, width=23)
        self.supplier_combo.grid(row=4, column=1, padx=10, pady=5)
        
        tk.Label(form_frame, text="Price:", bg="#16213e", fg="white",
                font=("Arial", 10)).grid(row=5, column=0, sticky=tk.W, pady=5)
        self.price_entry = tk.Entry(form_frame, font=("Arial", 10), width=25,
                                   bg="#0f3460", fg="white", insertbackground="white")
        self.price_entry.grid(row=5, column=1, padx=10, pady=5)
        
        tk.Label(form_frame, text="Quantity:", bg="#16213e", fg="white",
                font=("Arial", 10)).grid(row=6, column=0, sticky=tk.W, pady=5)
        self.quantity_entry = tk.Entry(form_frame, font=("Arial", 10), width=25,
                                      bg="#0f3460", fg="white", insertbackground="white")
        self.quantity_entry.grid(row=6, column=1, padx=10, pady=5)
        
        tk.Label(form_frame, text="Description:", bg="#16213e", fg="white",
                font=("Arial", 10)).grid(row=7, column=0, sticky=tk.W, pady=5)
        self.desc_text = tk.Text(form_frame, font=("Arial", 10), width=25, height=4,
                                bg="#0f3460", fg="white", insertbackground="white")
        self.desc_text.grid(row=7, column=1, padx=10, pady=5)
        
        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=8, column=0, columnspan=2, pady=15)
        
        tk.Button(btn_frame, text="Add", command=self.add_product,
                 bg="#05c46b", fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", command=self.update_product,
                 bg="#ffd32a", fg="black", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_product,
                 bg="#e94560", fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_form,
                 bg="#0f3460", fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        # Right table
        table_frame = tk.Frame(main_frame, bg="#16213e")
        table_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        search_frame = tk.Frame(table_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.search_data)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                               bg="#0f3460", fg="white", insertbackground="white", width=30)
        search_entry.pack(side=tk.LEFT, padx=10)
        
        columns = ("ID", "Product ID", "Name", "Category", "Supplier", "Price", "Quantity")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=110)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<ButtonRelease-1>", self.select_record)
    
    def get_categories(self):
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM categories")
            cats = [row[0] for row in cursor.fetchall()]
            conn.close()
            return cats
        except:
            return []
    
    def get_suppliers(self):
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM suppliers")
            sups = [row[0] for row in cursor.fetchall()]
            conn.close()
            return sups
        except:
            return []
    
    def add_product(self):
        product_id = self.product_id_entry.get()
        name = self.name_entry.get()
        category = self.category_var.get()
        supplier = self.supplier_var.get()
        price = self.price_entry.get()
        quantity = self.quantity_entry.get()
        description = self.desc_text.get("1.0", tk.END).strip()
        
        if not product_id or not name:
            messagebox.showerror("Error", "Product ID and Name are required!")
            return
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO products (product_id, name, category, supplier, price, quantity, description) 
                            VALUES (?,?,?,?,?,?,?)''',
                          (product_id, name, category, supplier, price, quantity, description))
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
            messagebox.showerror("Error", "Please select a product to update!")
            return
        product_id = self.product_id_entry.get()
        name = self.name_entry.get()
        category = self.category_var.get()
        supplier = self.supplier_var.get()
        price = self.price_entry.get()
        quantity = self.quantity_entry.get()
        description = self.desc_text.get("1.0", tk.END).strip()
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''UPDATE products SET product_id=?, name=?, category=?, supplier=?, 
                            price=?, quantity=?, description=? WHERE id=?''',
                          (product_id, name, category, supplier, price, quantity, description, self.selected_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product updated successfully!")
            self.clear_form()
            self.load_data()
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def delete_product(self):
        if not self.selected_id:
            messagebox.showerror("Error", "Please select a product to delete!")
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
        self.product_id_entry.delete(0, tk.END)
        self.name_entry.delete(0, tk.END)
        self.category_var.set("")
        self.supplier_var.set("")
        self.price_entry.delete(0, tk.END)
        self.quantity_entry.delete(0, tk.END)
        self.desc_text.delete("1.0", tk.END)
        self.selected_id = None
    
    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, product_id, name, category, supplier, price, quantity FROM products")
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def search_data(self, *args):
        search_term = self.search_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT id, product_id, name, category, supplier, price, quantity 
                            FROM products WHERE LOWER(name) LIKE ? OR LOWER(product_id) LIKE ?''',
                          (f'%{search_term}%', f'%{search_term}%'))
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=row)
        except:
            pass
    
    def select_record(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])['values']
            self.selected_id = values[0]
            try:
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM products WHERE id=?", (self.selected_id,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    self.product_id_entry.delete(0, tk.END)
                    self.product_id_entry.insert(0, row[1] if row[1] else "")
                    self.name_entry.delete(0, tk.END)
                    self.name_entry.insert(0, row[2] if row[2] else "")
                    self.category_var.set(row[3] if row[3] else "")
                    self.supplier_var.set(row[4] if row[4] else "")
                    self.price_entry.delete(0, tk.END)
                    self.price_entry.insert(0, row[5] if row[5] else "")
                    self.quantity_entry.delete(0, tk.END)
                    self.quantity_entry.insert(0, row[6] if row[6] else "")
                    self.desc_text.delete("1.0", tk.END)
                    self.desc_text.insert("1.0", row[7] if row[7] else "")
            except:
                pass

class BillingFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.app = parent
        self.cart_items = []
        self.create_widgets()
    
    def create_widgets(self):
        nav = NavigationBar(self, self.app)
        
        tk.Label(self, text="Billing / Invoice", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="white").pack(pady=10)
        
        main_frame = tk.Frame(self, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left - Customer and Product selection
        left_frame = tk.Frame(main_frame, bg="#16213e", padx=15, pady=15)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Customer info
        tk.Label(left_frame, text="Customer Information", font=("Arial", 12, "bold"),
                 bg="#16213e", fg="#e94560").grid(row=0, column=0, columnspan=2, pady=5)
        
        customer_fields = [
            ("Invoice No:", "invoice_no"),
            ("Customer Name:", "customer_name"),
            ("Phone:", "customer_phone"),
            ("Email:", "customer_email"),
        ]
        
        self.customer_entries = {}
        for i, (label, key) in enumerate(customer_fields, 1):
            tk.Label(left_frame, text=label, bg="#16213e", fg="white",
                    font=("Arial", 10)).grid(row=i, column=0, sticky=tk.W, pady=3)
            entry = tk.Entry(left_frame, font=("Arial", 10), width=22,
                           bg="#0f3460", fg="white", insertbackground="white")
            entry.grid(row=i, column=1, padx=5, pady=3)
            self.customer_entries[key] = entry
        
        # Auto-generate invoice number
        invoice_no = "INV-" + ''.join(random.choices(string.digits, k=6))
        self.customer_entries['invoice_no'].insert(0, invoice_no)
        
        # Product selection
        tk.Label(left_frame, text="Add Product", font=("Arial", 12, "bold"),
                 bg="#16213e", fg="#05c46b").grid(row=6, column=0, columnspan=2, pady=10)
        
        tk.Label(left_frame, text="Product:", bg="#16213e", fg="white",
                font=("Arial", 10)).grid(row=7, column=0, sticky=tk.W, pady=3)
        self.product_var = tk.StringVar()
        products = self.get_products()
        self.product_combo = ttk.Combobox(left_frame, textvariable=self.product_var,
                                         values=products, width=20)
        self.product_combo.grid(row=7, column=1, padx=5, pady=3)
        self.product_combo.bind("<<ComboboxSelected>>", self.on_product_select)
        
        tk.Label(left_frame, text="Price:", bg="#16213e", fg="white",
                font=("Arial", 10)).grid(row=8, column=0, sticky=tk.W, pady=3)
        self.price_var = tk.StringVar()
        self.price_entry = tk.Entry(left_frame, textvariable=self.price_var,
                                   font=("Arial", 10), width=22,
                                   bg="#0f3460", fg="white", insertbackground="white")
        self.price_entry.grid(row=8, column=1, padx=5, pady=3)
        
        tk.Label(left_frame, text="Quantity:", bg="#16213e", fg="white",
                font=("Arial", 10)).grid(row=9, column=0, sticky=tk.W, pady=3)
        self.qty_entry = tk.Entry(left_frame, font=("Arial", 10), width=22,
                                 bg="#0f3460", fg="white", insertbackground="white")
        self.qty_entry.grid(row=9, column=1, padx=5, pady=3)
        self.qty_entry.insert(0, "1")
        
        tk.Button(left_frame, text="Add to Cart", command=self.add_to_cart,
                 bg="#05c46b", fg="white", font=("Arial", 10, "bold"),
                 padx=10, pady=5).grid(row=10, column=0, columnspan=2, pady=10)
        
        # Totals
        tk.Label(left_frame, text="Subtotal:", bg="#16213e", fg="white",
                font=("Arial", 10)).grid(row=11, column=0, sticky=tk.W, pady=3)
        self.subtotal_var = tk.StringVar(value="0.00")
        tk.Label(left_frame, textvariable=self.subtotal_var, bg="#16213e", fg="#ffd32a",
                font=("Arial", 10, "bold")).grid(row=11, column=1, sticky=tk.W, pady=3)
        
        tk.Label(left_frame, text="Tax (10%):", bg="#16213e", fg="white",
                font=("Arial", 10)).grid(row=12, column=0, sticky=tk.W, pady=3)
        self.tax_var = tk.StringVar(value="0.00")
        tk.Label(left_frame, textvariable=self.tax_var, bg="#16213e", fg="#ffd32a",
                font=("Arial", 10, "bold")).grid(row=12, column=1, sticky=tk.W, pady=3)
        
        tk.Label(left_frame, text="Total:", bg="#16213e", fg="white",
                font=("Arial", 12, "bold")).grid(row=13, column=0, sticky=tk.W, pady=3)
        self.total_var = tk.StringVar(value="0.00")
        tk.Label(left_frame, textvariable=self.total_var, bg="#16213e", fg="#e94560",
                font=("Arial", 12, "bold")).grid(row=13, column=1, sticky=tk.W, pady=3)
        
        # Action buttons
        action_frame = tk.Frame(left_frame, bg="#16213e")
        action_frame.grid(row=14, column=0, columnspan=2, pady=10)
        
        tk.Button(action_frame, text="Generate Bill", command=self.generate_bill,
                 bg="#e94560", fg="white", font=("Arial", 10, "bold"),
                 padx=10, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(action_frame, text="Clear All", command=self.clear_all,
                 bg="#0f3460", fg="white", font=("Arial", 10, "bold"),
                 padx=10, pady=5).pack(side=tk.LEFT, padx=5)
        
        # Right - Cart and Bill preview
        right_frame = tk.Frame(main_frame, bg="#16213e")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        tk.Label(right_frame, text="Cart Items", font=("Arial", 12, "bold"),
                 bg="#16213e", fg="white").pack(pady=5)
        
        cart_columns = ("Product", "Price", "Quantity", "Total")
        self.cart_tree = ttk.Treeview(right_frame, columns=cart_columns, show="headings", height=10)
        
        for col in cart_columns:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=150)
        
        self.cart_tree.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(right_frame, text="Remove Selected", command=self.remove_from_cart,
                 bg="#e94560", fg="white", font=("Arial", 9)).pack(pady=5)
        
        # Bill preview
        tk.Label(right_frame, text="Bill Preview", font=("Arial", 12, "bold"),
                 bg="#16213e", fg="white").pack(pady=5)
        
        self.bill_text = tk.Text(right_frame, font=("Courier", 9), bg="#0f3460", fg="white",
                                height=15, width=60)
        self.bill_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    def get_products(self):
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM products")
            products = [row[0] for row in cursor.fetchall()]
            conn.close()
            return products
        except:
            return []
    
    def on_product_select(self, event):
        product_name = self.product_var.get()
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT price FROM products WHERE name=?", (product_name,))
            row = cursor.fetchone()
            conn.close()
            if row:
                self.price_var.set(str(row[0]))
        except:
            pass
    
    def add_to_cart(self):
        product = self.product_var.get()
        price_str = self.price_var.get()
        qty_str = self.qty_entry.get()
        
        if not product or not price_str or not qty_str:
            messagebox.showerror("Error", "Please select a product and enter quantity!")
            return
        
        try:
            price = float(price_str)
            qty = int(qty_str)
            total = price * qty
            
            self.cart_items.append({
                'product': product,
                'price': price,
                'quantity': qty,
                'total': total
            })
            
            self.cart_tree.insert("", tk.END, values=(product, f"{price:.2f}", qty, f"{total:.2f}"))
            self.update_totals()
            self.update_bill_preview()
            
            self.product_var.set("")
            self.price_var.set("")
            self.qty_entry.delete(0, tk.END)
            self.qty_entry.insert(0, "1")
        except ValueError:
            messagebox.showerror("Error", "Invalid price or quantity!")
    
    def remove_from_cart(self):
        selected = self.cart_tree.selection()
        if selected:
            idx = self.cart_tree.index(selected[0])
            self.cart_tree.delete(selected[0])
            if 0 <= idx < len(self.cart_items):
                self.cart_items.pop(idx)
            self.update_totals()
            self.update_bill_preview()
    
    def update_totals(self):
        subtotal = sum(item['total'] for item in self.cart_items)
        tax = subtotal * 0.10
        total = subtotal + tax
        
        self.subtotal_var.set(f"{subtotal:.2f}")
        self.tax_var.set(f"{tax:.2f}")
        self.total_var.set(f"{total:.2f}")
    
    def update_bill_preview(self):
        self.bill_text.delete("1.0", tk.END)
        
        invoice_no = self.customer_entries['invoice_no'].get()
        customer_name = self.customer_entries['customer_name'].get()
        customer_phone = self.customer_entries['customer_phone'].get()
        
        bill = "=" * 50 + "\n"
        bill += "       INVENTORY MANAGEMENT SYSTEM\n"
        bill += "=" * 50 + "\n"
        bill += f"Invoice No: {invoice_no}\n"
        bill += f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        bill += f"Customer: {customer_name}\n"
        bill += f"Phone: {customer_phone}\n"
        bill += "-" * 50 + "\n"
        bill += f"{'Product':<20} {'Price':>8} {'Qty':>5} {'Total':>10}\n"
        bill += "-" * 50 + "\n"
        
        for item in self.cart_items:
            bill += f"{item['product']:<20} {item['price']:>8.2f} {item['quantity']:>5} {item['total']:>10.2f}\n"
        
        subtotal = sum(item['total'] for item in self.cart_items)
        tax = subtotal * 0.10
        total = subtotal + tax
        
        bill += "-" * 50 + "\n"
        bill += f"{'Subtotal:':<35} {subtotal:>10.2f}\n"
        bill += f"{'Tax (10%):':<35} {tax:>10.2f}\n"
        bill += f"{'TOTAL:':<35} {total:>10.2f}\n"
        bill += "=" * 50 + "\n"
        bill += "        Thank you for your purchase!\n"
        bill += "=" * 50 + "\n"
        
        self.bill_text.insert("1.0", bill)
    
    def generate_bill(self):
        if not self.cart_items:
            messagebox.showerror("Error", "Cart is empty!")
            return
        
        invoice_no = self.customer_entries['invoice_no'].get()
        customer_name = self.customer_entries['customer_name'].get()
        customer_phone = self.customer_entries['customer_phone'].get()
        customer_email = self.customer_entries['customer_email'].get()
        
        if not invoice_no or not customer_name:
            messagebox.showerror("Error", "Invoice number and customer name are required!")
            return
        
        subtotal = sum(item['total'] for item in self.cart_items)
        tax = subtotal * 0.10
        total = subtotal + tax
        
        bill_details = str(self.cart_items)
        bill_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO bills (invoice_no, customer_name, customer_phone, 
                            customer_email, bill_date, total_amount, bill_details) 
                            VALUES (?,?,?,?,?,?,?)''',
                          (invoice_no, customer_name, customer_phone, customer_email,
                           bill_date, total, bill_details))
            
            # Update product quantities
            for item in self.cart_items:
                cursor.execute('''UPDATE products SET quantity = quantity - ? 
                                WHERE name = ?''', (item['quantity'], item['product']))
            
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Success", f"Bill generated successfully!\nInvoice No: {invoice_no}\nTotal: ${total:.2f}")
            self.clear_all()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Invoice number already exists!")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def clear_all(self):
        for entry in self.customer_entries.values():
            entry.delete(0, tk.END)
        
        invoice_no = "INV-" + ''.join(random.choices(string.digits, k=6))
        self.customer_entries['invoice_no'].insert(0, invoice_no)
        
        self.cart_items.clear()
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        
        self.product_var.set("")
        self.price_var.set("")
        self.qty_entry.delete(0, tk.END)
        self.qty_entry.insert(0, "1")
        
        self.subtotal_var.set("0.00")
        self.tax_var.set("0.00")
        self.total_var.set("0.00")
        
        self.bill_text.delete("1.0", tk.END)

class BillsFrame(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg="#1a1a2e")
        self.app = parent
        self.create_widgets()
        self.load_data()
    
    def create_widgets(self):
        nav = NavigationBar(self, self.app)
        
        tk.Label(self, text="Bills / Invoices", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="white").pack(pady=10)
        
        main_frame = tk.Frame(self, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left - Bills list
        left_frame = tk.Frame(main_frame, bg="#16213e")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        search_frame = tk.Frame(left_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.search_data)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                               bg="#0f3460", fg="white", insertbackground="white", width=30)
        search_entry.pack(side=tk.LEFT, padx=10)
        
        columns = ("ID", "Invoice No", "Customer", "Phone", "Date", "Total")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=130)
        
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<ButtonRelease-1>", self.select_bill)
        
        # Right - Bill details
        right_frame = tk.Frame(main_frame, bg="#16213e", padx=15, pady=15)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        
        tk.Label(right_frame, text="Bill Details", font=("Arial", 14, "bold"),
                 bg="#16213e", fg="#e94560").pack(pady=5)
        
        self.bill_detail_text = tk.Text(right_frame, font=("Courier", 9), bg="#0f3460",
                                       fg="white", width=50, height=30)
        self.bill_detail_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        btn_frame = tk.Frame(right_frame, bg="#16213e")
        btn_frame.pack(pady=5)
        
        tk.Button(btn_frame, text="Delete Bill", command=self.delete_bill,
                 bg="#e94560", fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Refresh", command=self.load_data,
                 bg="#0f3460", fg="white", font=("Arial", 10, "bold"),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        self.selected_bill_id = None
    
    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute("SELECT id, invoice_no, customer_name, customer_phone, bill_date, total_amount FROM bills")
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=(row[0], row[1], row[2], row[3], row[4], f"${row[5]:.2f}"))
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def search_data(self, *args):
        search_term = self.search_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute('''SELECT id, invoice_no, customer_name, customer_phone, bill_date, total_amount 
                            FROM bills WHERE LOWER(customer_name) LIKE ? OR LOWER(invoice_no) LIKE ?''',
                          (f'%{search_term}%', f'%{search_term}%'))
            rows = cursor.fetchall()
            conn.close()
            for row in rows:
                self.tree.insert("", tk.END, values=(row[0], row[1], row[2], row[3], row[4], f"${row[5]:.2f}"))
        except:
            pass
    
    def select_bill(self, event):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])['values']
            self.selected_bill_id = values[0]
            try:
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM bills WHERE id=?", (self.selected_bill_id,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    self.show_bill_detail(row)
            except:
                pass
    
    def show_bill_detail(self, row):
        self.bill_detail_text.delete("1.0", tk.END)
        
        bill = "=" * 50 + "\n"
        bill += "       INVENTORY MANAGEMENT SYSTEM\n"
        bill += "=" * 50 + "\n"
        bill += f"Invoice No: {row[1]}\n"
        bill += f"Date: {row[5]}\n"
        bill += f"Customer: {row[2]}\n"
        bill += f"Phone: {row[3]}\n"
        bill += f"Email: {row[4]}\n"
        bill += "-" * 50 + "\n"
        
        try:
            import ast
            items = ast.literal_eval(row[7])
            bill += f"{'Product':<20} {'Price':>8} {'Qty':>5} {'Total':>10}\n"
            bill += "-" * 50 + "\n"
            for item in items:
                bill += f"{item['product']:<20} {item['price']:>8.2f} {item['quantity']:>5} {item['total']:>10.2f}\n"
        except:
            bill += "Item details not available\n"
        
        total = row[6]
        subtotal = total / 1.10
        tax = total - subtotal
        
        bill += "-" * 50 + "\n"
        bill += f"{'Subtotal:':<35} {subtotal:>10.2f}\n"
        bill += f"{'Tax (10%):':<35} {tax:>10.2f}\n"
        bill += f"{'TOTAL:':<35} {total:>10.2f}\n"
        bill += "=" * 50 + "\n"
        bill += "        Thank you for your purchase!\n"
        bill += "=" * 50 + "\n"
        
        self.bill_detail_text.insert("1.0", bill)
    
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
                self.bill_detail_text.delete("1.0", tk.END)
                self.load_data()
            except Exception as e:
                messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()