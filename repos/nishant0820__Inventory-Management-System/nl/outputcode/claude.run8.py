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
            department TEXT,
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
            cat_id TEXT UNIQUE NOT NULL,
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
            photo TEXT
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
            bill_details TEXT
        )
    """)

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# Main Application Window
# ─────────────────────────────────────────────
class InventoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1200x700")
        self.resizable(True, True)
        self.configure(bg="#1a1a2e")
        init_db()
        self.current_frame = None
        self.show_dashboard()

    def clear_frame(self):
        if self.current_frame:
            self.current_frame.destroy()

    def show_dashboard(self):
        self.clear_frame()
        self.current_frame = Dashboard(self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_employee(self):
        self.clear_frame()
        self.current_frame = EmployeeModule(self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_supplier(self):
        self.clear_frame()
        self.current_frame = SupplierModule(self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_category(self):
        self.clear_frame()
        self.current_frame = CategoryModule(self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_product(self):
        self.clear_frame()
        self.current_frame = ProductModule(self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)

    def show_billing(self):
        self.clear_frame()
        self.current_frame = BillingModule(self)
        self.current_frame.pack(fill=tk.BOTH, expand=True)


# ─────────────────────────────────────────────
# Navigation Bar (shared)
# ─────────────────────────────────────────────
class NavBar(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg="#16213e", height=50)
        self.app = app
        self.pack(fill=tk.X, side=tk.TOP)

        buttons = [
            ("🏠 Dashboard", app.show_dashboard),
            ("👤 Employee", app.show_employee),
            ("🚚 Supplier", app.show_supplier),
            ("📦 Category", app.show_category),
            ("🛒 Product", app.show_product),
            ("🧾 Billing", app.show_billing),
        ]

        for text, cmd in buttons:
            btn = tk.Button(
                self, text=text, command=cmd,
                bg="#0f3460", fg="white", font=("Arial", 10, "bold"),
                relief=tk.FLAT, padx=10, pady=8, cursor="hand2",
                activebackground="#e94560", activeforeground="white"
            )
            btn.pack(side=tk.LEFT, padx=2, pady=5)

        # Clock label on the right
        self.clock_label = tk.Label(self, bg="#16213e", fg="#e94560",
                                    font=("Arial", 11, "bold"))
        self.clock_label.pack(side=tk.RIGHT, padx=15)
        self.update_clock()

    def update_clock(self):
        now = datetime.now().strftime("%A, %d %B %Y   %H:%M:%S")
        self.clock_label.config(text=now)
        self.after(1000, self.update_clock)


# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────
class Dashboard(tk.Frame):
    def __init__(self, app):
        super().__init__(app, bg="#1a1a2e")
        self.app = app
        NavBar(self, app)
        self.build_ui()

    def build_ui(self):
        # Title
        title = tk.Label(self, text="📊 Inventory Management System",
                         bg="#1a1a2e", fg="white",
                         font=("Arial", 22, "bold"))
        title.pack(pady=20)

        subtitle = tk.Label(self, text="Welcome to the Dashboard",
                            bg="#1a1a2e", fg="#a0a0b0",
                            font=("Arial", 13))
        subtitle.pack()

        # Stats cards
        card_frame = tk.Frame(self, bg="#1a1a2e")
        card_frame.pack(pady=30, padx=40, fill=tk.X)

        stats = self.get_stats()
        cards = [
            ("👤 Employees", stats["employees"], "#e94560"),
            ("🚚 Suppliers", stats["suppliers"], "#0f3460"),
            ("📦 Categories", stats["categories"], "#533483"),
            ("🛒 Products", stats["products"], "#05c46b"),
            ("🧾 Bills", stats["bills"], "#f0a500"),
        ]

        for i, (label, value, color) in enumerate(cards):
            card = tk.Frame(card_frame, bg=color, width=180, height=120,
                            relief=tk.RAISED, bd=2)
            card.grid(row=0, column=i, padx=15, pady=10)
            card.pack_propagate(False)

            tk.Label(card, text=label, bg=color, fg="white",
                     font=("Arial", 12, "bold")).pack(pady=(20, 5))
            tk.Label(card, text=str(value), bg=color, fg="white",
                     font=("Arial", 24, "bold")).pack()

        # Quick access buttons
        btn_frame = tk.Frame(self, bg="#1a1a2e")
        btn_frame.pack(pady=20)

        quick = [
            ("➕ Add Employee", self.app.show_employee, "#e94560"),
            ("➕ Add Supplier", self.app.show_supplier, "#0f3460"),
            ("➕ Add Product", self.app.show_product, "#533483"),
            ("🧾 New Bill", self.app.show_billing, "#f0a500"),
        ]

        for text, cmd, color in quick:
            tk.Button(btn_frame, text=text, command=cmd,
                      bg=color, fg="white", font=("Arial", 11, "bold"),
                      relief=tk.FLAT, padx=15, pady=10, cursor="hand2",
                      activebackground="#16213e", activeforeground="white"
                      ).pack(side=tk.LEFT, padx=10)

        # Recent activity label
        tk.Label(self, text="System Information",
                 bg="#1a1a2e", fg="#a0a0b0",
                 font=("Arial", 12)).pack(pady=(20, 5))

        info_frame = tk.Frame(self, bg="#16213e", relief=tk.RIDGE, bd=1)
        info_frame.pack(padx=40, fill=tk.X)

        info_text = (
            f"  Database: inventory.db   |   "
            f"Date: {datetime.now().strftime('%d %B %Y')}   |   "
            f"Time: {datetime.now().strftime('%H:%M:%S')}   |   "
            f"OS: {os.name.upper()}"
        )
        tk.Label(info_frame, text=info_text, bg="#16213e", fg="#a0a0b0",
                 font=("Arial", 10)).pack(pady=8)

    def get_stats(self):
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        stats = {}
        for table in ["employees", "suppliers", "categories", "products", "bills"]:
            c.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = c.fetchone()[0]
        conn.close()
        return stats


# ─────────────────────────────────────────────
# Employee Module
# ─────────────────────────────────────────────
class EmployeeModule(tk.Frame):
    def __init__(self, app):
        super().__init__(app, bg="#1a1a2e")
        self.app = app
        self.photo_path = tk.StringVar()
        self.photo_image = None
        NavBar(self, app)
        self.build_ui()
        self.load_employees()

    def build_ui(self):
        tk.Label(self, text="👤 Employee Management",
                 bg="#1a1a2e", fg="white",
                 font=("Arial", 18, "bold")).pack(pady=10)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        # Left: Form
        form_frame = tk.LabelFrame(main, text="Employee Details",
                                   bg="#16213e", fg="white",
                                   font=("Arial", 11, "bold"),
                                   relief=tk.RIDGE, bd=2)
        form_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        fields = [
            ("Employee ID", "emp_id"),
            ("Full Name", "name"),
            ("Email", "email"),
            ("Phone", "phone"),
            ("Address", "address"),
            ("Department", "department"),
            ("Salary", "salary"),
            ("Join Date (YYYY-MM-DD)", "join_date"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label + ":", bg="#16213e", fg="#a0a0b0",
                     font=("Arial", 10)).grid(row=i, column=0, padx=10, pady=5, sticky="w")
            entry = tk.Entry(form_frame, font=("Arial", 10), width=25,
                             bg="#0f3460", fg="white", insertbackground="white")
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.entries[key] = entry

        # Photo
        tk.Label(form_frame, text="Photo:", bg="#16213e", fg="#a0a0b0",
                 font=("Arial", 10)).grid(row=len(fields), column=0, padx=10, pady=5, sticky="w")
        photo_frame = tk.Frame(form_frame, bg="#16213e")
        photo_frame.grid(row=len(fields), column=1, padx=10, pady=5, sticky="w")
        tk.Entry(photo_frame, textvariable=self.photo_path, width=15,
                 bg="#0f3460", fg="white", insertbackground="white").pack(side=tk.LEFT)
        tk.Button(photo_frame, text="Browse", command=self.browse_photo,
                  bg="#e94560", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)

        self.photo_label = tk.Label(form_frame, bg="#16213e", text="No Photo",
                                    fg="#a0a0b0", width=15, height=6, relief=tk.SUNKEN)
        self.photo_label.grid(row=len(fields) + 1, column=0, columnspan=2, pady=5)

        # Buttons
        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=len(fields) + 2, column=0, columnspan=2, pady=10)

        for text, cmd, color in [
            ("Add", self.add_employee, "#05c46b"),
            ("Update", self.update_employee, "#f0a500"),
            ("Delete", self.delete_employee, "#e94560"),
            ("Clear", self.clear_form, "#533483"),
        ]:
            tk.Button(btn_frame, text=text, command=cmd,
                      bg=color, fg="white", font=("Arial", 10, "bold"),
                      width=8, relief=tk.FLAT, cursor="hand2"
                      ).pack(side=tk.LEFT, padx=5)

        # Right: Table
        table_frame = tk.LabelFrame(main, text="Employee Records",
                                    bg="#16213e", fg="white",
                                    font=("Arial", 11, "bold"),
                                    relief=tk.RIDGE, bd=2)
        table_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        main.columnconfigure(1, weight=1)

        # Search
        search_frame = tk.Frame(table_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self.search_employees())
        tk.Entry(search_frame, textvariable=self.search_var,
                 bg="#0f3460", fg="white", insertbackground="white",
                 width=25).pack(side=tk.LEFT, padx=5)

        cols = ("ID", "Emp ID", "Name", "Email", "Phone", "Department", "Salary", "Join Date")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=18)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#0f3460", foreground="white",
                        fieldbackground="#0f3460", rowheight=25)
        style.configure("Treeview.Heading", background="#e94560", foreground="white",
                        font=("Arial", 10, "bold"))

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=90, anchor="center")

        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=5)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<ButtonRelease-1>", self.select_employee)

    def browse_photo(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if path:
            self.photo_path.set(path)
            try:
                img = Image.open(path).resize((100, 80))
                self.photo_image = ImageTk.PhotoImage(img)
                self.photo_label.config(image=self.photo_image, text="")
            except Exception:
                self.photo_label.config(text="Preview N/A")

    def add_employee(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        if not data["emp_id"] or not data["name"]:
            messagebox.showerror("Error", "Employee ID and Name are required!")
            return
        try:
            conn = sqlite3.connect("inventory.db")
            c = conn.cursor()
            c.execute("""INSERT INTO employees (emp_id, name, email, phone, address,
                         department, salary, join_date, photo)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                      (data["emp_id"], data["name"], data["email"], data["phone"],
                       data["address"], data["department"],
                       float(data["salary"]) if data["salary"] else 0.0,
                       data["join_date"], self.photo_path.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee added successfully!")
            self.clear_form()
            self.load_employees()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Employee ID already exists!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_employee(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select an employee to update!")
            return
        row_id = self.tree.item(selected[0])["values"][0]
        data = {k: v.get().strip() for k, v in self.entries.items()}
        try:
            conn = sqlite3.connect("inventory.db")
            c = conn.cursor()
            c.execute("""UPDATE employees SET emp_id=?, name=?, email=?, phone=?,
                         address=?, department=?, salary=?, join_date=?, photo=?
                         WHERE id=?""",
                      (data["emp_id"], data["name"], data["email"], data["phone"],
                       data["address"], data["department"],
                       float(data["salary"]) if data["salary"] else 0.0,
                       data["join_date"], self.photo_path.get(), row_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee updated successfully!")
            self.load_employees()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_employee(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select an employee to delete!")
            return
        if not messagebox.askyesno("Confirm", "Delete selected employee?"):
            return
        row_id = self.tree.item(selected[0])["values"][0]
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("DELETE FROM employees WHERE id=?", (row_id,))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Employee deleted!")
        self.clear_form()
        self.load_employees()

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.photo_path.set("")
        self.photo_label.config(image="", text="No Photo")
        self.photo_image = None

    def load_employees(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("SELECT id, emp_id, name, email, phone, department, salary, join_date FROM employees")
        for row in c.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_employees(self):
        query = self.search_var.get().strip().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("""SELECT id, emp_id, name, email, phone, department, salary, join_date
                     FROM employees WHERE LOWER(name) LIKE ? OR LOWER(emp_id) LIKE ?
                     OR LOWER(department) LIKE ?""",
                  (f"%{query}%", f"%{query}%", f"%{query}%"))
        for row in c.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_employee(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])["values"]
        keys = ["emp_id", "name", "email", "phone", "department", "salary", "join_date"]
        # values: id, emp_id, name, email, phone, department, salary, join_date
        mapping = {
            "emp_id": values[1], "name": values[2], "email": values[3],
            "phone": values[4], "address": "", "department": values[5],
            "salary": values[6], "join_date": values[7]
        }
        # Fetch full record for address
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("SELECT address, photo FROM employees WHERE id=?", (values[0],))
        row = c.fetchone()
        conn.close()
        if row:
            mapping["address"] = row[0] or ""
            self.photo_path.set(row[1] or "")
            if row[1] and os.path.exists(row[1]):
                try:
                    img = Image.open(row[1]).resize((100, 80))
                    self.photo_image = ImageTk.PhotoImage(img)
                    self.photo_label.config(image=self.photo_image, text="")
                except Exception:
                    self.photo_label.config(text="Preview N/A")

        for key, entry in self.entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, str(mapping.get(key, "")))


# ─────────────────────────────────────────────
# Supplier Module
# ─────────────────────────────────────────────
class SupplierModule(tk.Frame):
    def __init__(self, app):
        super().__init__(app, bg="#1a1a2e")
        self.app = app
        NavBar(self, app)
        self.build_ui()
        self.load_suppliers()

    def build_ui(self):
        tk.Label(self, text="🚚 Supplier Management",
                 bg="#1a1a2e", fg="white",
                 font=("Arial", 18, "bold")).pack(pady=10)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        form_frame = tk.LabelFrame(main, text="Supplier Details",
                                   bg="#16213e", fg="white",
                                   font=("Arial", 11, "bold"),
                                   relief=tk.RIDGE, bd=2)
        form_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

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
            tk.Label(form_frame, text=label + ":", bg="#16213e", fg="#a0a0b0",
                     font=("Arial", 10)).grid(row=i, column=0, padx=10, pady=5, sticky="w")
            entry = tk.Entry(form_frame, font=("Arial", 10), width=25,
                             bg="#0f3460", fg="white", insertbackground="white")
            entry.grid(row=i, column=1, padx=10, pady=5)
            self.entries[key] = entry

        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=10)

        for text, cmd, color in [
            ("Add", self.add_supplier, "#05c46b"),
            ("Update", self.update_supplier, "#f0a500"),
            ("Delete", self.delete_supplier, "#e94560"),
            ("Clear", self.clear_form, "#533483"),
        ]:
            tk.Button(btn_frame, text=text, command=cmd,
                      bg=color, fg="white", font=("Arial", 10, "bold"),
                      width=8, relief=tk.FLAT, cursor="hand2"
                      ).pack(side=tk.LEFT, padx=5)

        table_frame = tk.LabelFrame(main, text="Supplier Records",
                                    bg="#16213e", fg="white",
                                    font=("Arial", 11, "bold"),
                                    relief=tk.RIDGE, bd=2)
        table_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        main.columnconfigure(1, weight=1)

        search_frame = tk.Frame(table_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self.search_suppliers())
        tk.Entry(search_frame, textvariable=self.search_var,
                 bg="#0f3460", fg="white", insertbackground="white",
                 width=25).pack(side=tk.LEFT, padx=5)

        cols = ("ID", "Supplier ID", "Name", "Email", "Phone", "Company", "Description")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=18)
        style = ttk.Style()
        style.configure("Treeview", background="#0f3460", foreground="white",
                        fieldbackground="#0f3460", rowheight=25)
        style.configure("Treeview.Heading", background="#0f3460", foreground="white",
                        font=("Arial", 10, "bold"))

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")

        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<ButtonRelease-1>", self.select_supplier)

    def add_supplier(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        if not data["supplier_id"] or not data["name"]:
            messagebox.showerror("Error", "Supplier ID and Name are required!")
            return
        try:
            conn = sqlite3.connect("inventory.db")
            c = conn.cursor()
            c.execute("""INSERT INTO suppliers (supplier_id, name, email, phone, address, company, description)
                         VALUES (?, ?, ?, ?, ?, ?, ?)""",
                      (data["supplier_id"], data["name"], data["email"], data["phone"],
                       data["address"], data["company"], data["description"]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier added successfully!")
            self.clear_form()
            self.load_suppliers()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Supplier ID already exists!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_supplier(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a supplier to update!")
            return
        row_id = self.tree.item(selected[0])["values"][0]
        data = {k: v.get().strip() for k, v in self.entries.items()}
        try:
            conn = sqlite3.connect("inventory.db")
            c = conn.cursor()
            c.execute("""UPDATE suppliers SET supplier_id=?, name=?, email=?, phone=?,
                         address=?, company=?, description=? WHERE id=?""",
                      (data["supplier_id"], data["name"], data["email"], data["phone"],
                       data["address"], data["company"], data["description"], row_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier updated!")
            self.load_suppliers()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_supplier(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a supplier to delete!")
            return
        if not messagebox.askyesno("Confirm", "Delete selected supplier?"):
            return
        row_id = self.tree.item(selected[0])["values"][0]
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("DELETE FROM suppliers WHERE id=?", (row_id,))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Supplier deleted!")
        self.clear_form()
        self.load_suppliers()

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)

    def load_suppliers(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("SELECT id, supplier_id, name, email, phone, company, description FROM suppliers")
        for row in c.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_suppliers(self):
        query = self.search_var.get().strip().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("""SELECT id, supplier_id, name, email, phone, company, description
                     FROM suppliers WHERE LOWER(name) LIKE ? OR LOWER(supplier_id) LIKE ?
                     OR LOWER(company) LIKE ?""",
                  (f"%{query}%", f"%{query}%", f"%{query}%"))
        for row in c.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_supplier(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])["values"]
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("SELECT supplier_id, name, email, phone, address, company, description FROM suppliers WHERE id=?",
                  (values[0],))
        row = c.fetchone()
        conn.close()
        if row:
            keys = ["supplier_id", "name", "email", "phone", "address", "company", "description"]
            for key, val in zip(keys, row):
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, str(val) if val else "")


# ─────────────────────────────────────────────
# Category Module
# ─────────────────────────────────────────────
class CategoryModule(tk.Frame):
    def __init__(self, app):
        super().__init__(app, bg="#1a1a2e")
        self.app = app
        NavBar(self, app)
        self.build_ui()
        self.load_categories()

    def build_ui(self):
        tk.Label(self, text="📦 Category Management",
                 bg="#1a1a2e", fg="white",
                 font=("Arial", 18, "bold")).pack(pady=10)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        form_frame = tk.LabelFrame(main, text="Category Details",
                                   bg="#16213e", fg="white",
                                   font=("Arial", 11, "bold"),
                                   relief=tk.RIDGE, bd=2)
        form_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        fields = [
            ("Category ID", "cat_id"),
            ("Category Name", "name"),
            ("Description", "description"),
        ]

        self.entries = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label + ":", bg="#16213e", fg="#a0a0b0",
                     font=("Arial", 10)).grid(row=i, column=0, padx=10, pady=8, sticky="w")
            entry = tk.Entry(form_frame, font=("Arial", 10), width=25,
                             bg="#0f3460", fg="white", insertbackground="white")
            entry.grid(row=i, column=1, padx=10, pady=8)
            self.entries[key] = entry

        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=15)

        for text, cmd, color in [
            ("Add", self.add_category, "#05c46b"),
            ("Update", self.update_category, "#f0a500"),
            ("Delete", self.delete_category, "#e94560"),
            ("Clear", self.clear_form, "#533483"),
        ]:
            tk.Button(btn_frame, text=text, command=cmd,
                      bg=color, fg="white", font=("Arial", 10, "bold"),
                      width=8, relief=tk.FLAT, cursor="hand2"
                      ).pack(side=tk.LEFT, padx=5)

        table_frame = tk.LabelFrame(main, text="Category Records",
                                    bg="#16213e", fg="white",
                                    font=("Arial", 11, "bold"),
                                    relief=tk.RIDGE, bd=2)
        table_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        main.columnconfigure(1, weight=1)

        search_frame = tk.Frame(table_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self.search_categories())
        tk.Entry(search_frame, textvariable=self.search_var,
                 bg="#0f3460", fg="white", insertbackground="white",
                 width=25).pack(side=tk.LEFT, padx=5)

        cols = ("ID", "Category ID", "Name", "Description")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=20)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor="center")

        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<ButtonRelease-1>", self.select_category)

    def add_category(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        if not data["cat_id"] or not data["name"]:
            messagebox.showerror("Error", "Category ID and Name are required!")
            return
        try:
            conn = sqlite3.connect("inventory.db")
            c = conn.cursor()
            c.execute("INSERT INTO categories (cat_id, name, description) VALUES (?, ?, ?)",
                      (data["cat_id"], data["name"], data["description"]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category added!")
            self.clear_form()
            self.load_categories()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Category ID already exists!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_category(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a category to update!")
            return
        row_id = self.tree.item(selected[0])["values"][0]
        data = {k: v.get().strip() for k, v in self.entries.items()}
        try:
            conn = sqlite3.connect("inventory.db")
            c = conn.cursor()
            c.execute("UPDATE categories SET cat_id=?, name=?, description=? WHERE id=?",
                      (data["cat_id"], data["name"], data["description"], row_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category updated!")
            self.load_categories()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_category(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a category to delete!")
            return
        if not messagebox.askyesno("Confirm", "Delete selected category?"):
            return
        row_id = self.tree.item(selected[0])["values"][0]
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("DELETE FROM categories WHERE id=?", (row_id,))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Category deleted!")
        self.clear_form()
        self.load_categories()

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)

    def load_categories(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("SELECT id, cat_id, name, description FROM categories")
        for row in c.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_categories(self):
        query = self.search_var.get().strip().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("""SELECT id, cat_id, name, description FROM categories
                     WHERE LOWER(name) LIKE ? OR LOWER(cat_id) LIKE ?""",
                  (f"%{query}%", f"%{query}%"))
        for row in c.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_category(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])["values"]
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("SELECT cat_id, name, description FROM categories WHERE id=?", (values[0],))
        row = c.fetchone()
        conn.close()
        if row:
            for key, val in zip(["cat_id", "name", "description"], row):
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, str(val) if val else "")


# ─────────────────────────────────────────────
# Product Module
# ─────────────────────────────────────────────
class ProductModule(tk.Frame):
    def __init__(self, app):
        super().__init__(app, bg="#1a1a2e")
        self.app = app
        self.photo_path = tk.StringVar()
        self.photo_image = None
        NavBar(self, app)
        self.build_ui()
        self.load_products()

    def get_categories(self):
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("SELECT name FROM categories")
        cats = [row[0] for row in c.fetchall()]
        conn.close()
        return cats if cats else ["No Category"]

    def get_suppliers(self):
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("SELECT name FROM suppliers")
        sups = [row[0] for row in c.fetchall()]
        conn.close()
        return sups if sups else ["No Supplier"]

    def build_ui(self):
        tk.Label(self, text="🛒 Product Management",
                 bg="#1a1a2e", fg="white",
                 font=("Arial", 18, "bold")).pack(pady=10)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        form_frame = tk.LabelFrame(main, text="Product Details",
                                   bg="#16213e", fg="white",
                                   font=("Arial", 11, "bold"),
                                   relief=tk.RIDGE, bd=2)
        form_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew")

        self.entries = {}

        # Product ID
        tk.Label(form_frame, text="Product ID:", bg="#16213e", fg="#a0a0b0",
                 font=("Arial", 10)).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.entries["product_id"] = tk.Entry(form_frame, font=("Arial", 10), width=25,
                                              bg="#0f3460", fg="white", insertbackground="white")
        self.entries["product_id"].grid(row=0, column=1, padx=10, pady=5)

        # Name
        tk.Label(form_frame, text="Product Name:", bg="#16213e", fg="#a0a0b0",
                 font=("Arial", 10)).grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entries["name"] = tk.Entry(form_frame, font=("Arial", 10), width=25,
                                        bg="#0f3460", fg="white", insertbackground="white")
        self.entries["name"].grid(row=1, column=1, padx=10, pady=5)

        # Category dropdown
        tk.Label(form_frame, text="Category:", bg="#16213e", fg="#a0a0b0",
                 font=("Arial", 10)).grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(form_frame, textvariable=self.category_var,
                                           values=self.get_categories(), width=23,
                                           state="readonly")
        self.category_combo.grid(row=2, column=1, padx=10, pady=5)

        # Supplier dropdown
        tk.Label(form_frame, text="Supplier:", bg="#16213e", fg="#a0a0b0",
                 font=("Arial", 10)).grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.supplier_var = tk.StringVar()
        self.supplier_combo = ttk.Combobox(form_frame, textvariable=self.supplier_var,
                                           values=self.get_suppliers(), width=23,
                                           state="readonly")
        self.supplier_combo.grid(row=3, column=1, padx=10, pady=5)

        # Price
        tk.Label(form_frame, text="Price:", bg="#16213e", fg="#a0a0b0",
                 font=("Arial", 10)).grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.entries["price"] = tk.Entry(form_frame, font=("Arial", 10), width=25,
                                         bg="#0f3460", fg="white", insertbackground="white")
        self.entries["price"].grid(row=4, column=1, padx=10, pady=5)

        # Quantity
        tk.Label(form_frame, text="Quantity:", bg="#16213e", fg="#a0a0b0",
                 font=("Arial", 10)).grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.entries["quantity"] = tk.Entry(form_frame, font=("Arial", 10), width=25,
                                            bg="#0f3460", fg="white", insertbackground="white")
        self.entries["quantity"].grid(row=5, column=1, padx=10, pady=5)

        # Description
        tk.Label(form_frame, text="Description:", bg="#16213e", fg="#a0a0b0",
                 font=("Arial", 10)).grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.entries["description"] = tk.Entry(form_frame, font=("Arial", 10), width=25,
                                               bg="#0f3460", fg="white", insertbackground="white")
        self.entries["description"].grid(row=6, column=1, padx=10, pady=5)

        # Photo
        tk.Label(form_frame, text="Photo:", bg="#16213e", fg="#a0a0b0",
                 font=("Arial", 10)).grid(row=7, column=0, padx=10, pady=5, sticky="w")
        photo_frame = tk.Frame(form_frame, bg="#16213e")
        photo_frame.grid(row=7, column=1, padx=10, pady=5, sticky="w")
        tk.Entry(photo_frame, textvariable=self.photo_path, width=15,
                 bg="#0f3460", fg="white", insertbackground="white").pack(side=tk.LEFT)
        tk.Button(photo_frame, text="Browse", command=self.browse_photo,
                  bg="#e94560", fg="white", font=("Arial", 9)).pack(side=tk.LEFT, padx=5)

        self.photo_label = tk.Label(form_frame, bg="#16213e", text="No Photo",
                                    fg="#a0a0b0", width=15, height=5, relief=tk.SUNKEN)
        self.photo_label.grid(row=8, column=0, columnspan=2, pady=5)

        btn_frame = tk.Frame(form_frame, bg="#16213e")
        btn_frame.grid(row=9, column=0, columnspan=2, pady=10)

        for text, cmd, color in [
            ("Add", self.add_product, "#05c46b"),
            ("Update", self.update_product, "#f0a500"),
            ("Delete", self.delete_product, "#e94560"),
            ("Clear", self.clear_form, "#533483"),
        ]:
            tk.Button(btn_frame, text=text, command=cmd,
                      bg=color, fg="white", font=("Arial", 10, "bold"),
                      width=8, relief=tk.FLAT, cursor="hand2"
                      ).pack(side=tk.LEFT, padx=5)

        table_frame = tk.LabelFrame(main, text="Product Records",
                                    bg="#16213e", fg="white",
                                    font=("Arial", 11, "bold"),
                                    relief=tk.RIDGE, bd=2)
        table_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        main.columnconfigure(1, weight=1)

        search_frame = tk.Frame(table_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *a: self.search_products())
        tk.Entry(search_frame, textvariable=self.search_var,
                 bg="#0f3460", fg="white", insertbackground="white",
                 width=25).pack(side=tk.LEFT, padx=5)

        cols = ("ID", "Product ID", "Name", "Category", "Supplier", "Price", "Quantity", "Description")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=18)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="center")

        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<ButtonRelease-1>", self.select_product)

    def browse_photo(self):
        path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.gif *.bmp")])
        if path:
            self.photo_path.set(path)
            try:
                img = Image.open(path).resize((100, 70))
                self.photo_image = ImageTk.PhotoImage(img)
                self.photo_label.config(image=self.photo_image, text="")
            except Exception:
                self.photo_label.config(text="Preview N/A")

    def add_product(self):
        data = {k: v.get().strip() for k, v in self.entries.items()}
        data["category"] = self.category_var.get()
        data["supplier"] = self.supplier_var.get()
        if not data["product_id"] or not data["name"]:
            messagebox.showerror("Error", "Product ID and Name are required!")
            return
        try:
            conn = sqlite3.connect("inventory.db")
            c = conn.cursor()
            c.execute("""INSERT INTO products (product_id, name, category, supplier, price, quantity, description, photo)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                      (data["product_id"], data["name"], data["category"], data["supplier"],
                       float(data["price"]) if data["price"] else 0.0,
                       int(data["quantity"]) if data["quantity"] else 0,
                       data["description"], self.photo_path.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product added!")
            self.clear_form()
            self.load_products()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Product ID already exists!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_product(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a product to update!")
            return
        row_id = self.tree.item(selected[0])["values"][0]
        data = {k: v.get().strip() for k, v in self.entries.items()}
        data["category"] = self.category_var.get()
        data["supplier"] = self.supplier_var.get()
        try:
            conn = sqlite3.connect("inventory.db")
            c = conn.cursor()
            c.execute("""UPDATE products SET product_id=?, name=?, category=?, supplier=?,
                         price=?, quantity=?, description=?, photo=? WHERE id=?""",
                      (data["product_id"], data["name"], data["category"], data["supplier"],
                       float(data["price"]) if data["price"] else 0.0,
                       int(data["quantity"]) if data["quantity"] else 0,
                       data["description"], self.photo_path.get(), row_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product updated!")
            self.load_products()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_product(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a product to delete!")
            return
        if not messagebox.askyesno("Confirm", "Delete selected product?"):
            return
        row_id = self.tree.item(selected[0])["values"][0]
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("DELETE FROM products WHERE id=?", (row_id,))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Product deleted!")
        self.clear_form()
        self.load_products()

    def clear_form(self):
        for entry in self.entries.values():
            entry.delete(0, tk.END)
        self.category_var.set("")
        self.supplier_var.set("")
        self.photo_path.set("")
        self.photo_label.config(image="", text="No Photo")
        self.photo_image = None

    def load_products(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("SELECT id, product_id, name, category, supplier, price, quantity, description FROM products")
        for row in c.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def search_products(self):
        query = self.search_var.get().strip().lower()
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("""SELECT id, product_id, name, category, supplier, price, quantity, description
                     FROM products WHERE LOWER(name) LIKE ? OR LOWER(product_id) LIKE ?
                     OR LOWER(category) LIKE ?""",
                  (f"%{query}%", f"%{query}%", f"%{query}%"))
        for row in c.fetchall():
            self.tree.insert("", tk.END, values=row)
        conn.close()

    def select_product(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])["values"]
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("""SELECT product_id, name, category, supplier, price, quantity, description, photo
                     FROM products WHERE id=?""", (values[0],))
        row = c.fetchone()
        conn.close()
        if row:
            keys = ["product_id", "name", "price", "quantity", "description"]
            mapping = {
                "product_id": row[0], "name": row[1], "price": row[4],
                "quantity": row[5], "description": row[6]
            }
            for key, entry in self.entries.items():
                entry.delete(0, tk.END)
                entry.insert(0, str(mapping.get(key, "")) if mapping.get(key) is not None else "")
            self.category_var.set(row[2] or "")
            self.supplier_var.set(row[3] or "")
            self.photo_path.set(row[7] or "")
            if row[7] and os.path.exists(row[7]):
                try:
                    img = Image.open(row[7]).resize((100, 70))
                    self.photo_image = ImageTk.PhotoImage(img)
                    self.photo_label.config(image=self.photo_image, text="")
                except Exception:
                    self.photo_label.config(text="Preview N/A")


# ─────────────────────────────────────────────
# Billing Module
# ─────────────────────────────────────────────
class BillingModule(tk.Frame):
    def __init__(self, app):
        super().__init__(app, bg="#1a1a2e")
        self.app = app
        self.cart_items = []
        NavBar(self, app)
        self.build_ui()
        self.load_bills()
        self.generate_invoice_no()

    def generate_invoice_no(self):
        inv = "INV-" + "".join(random.choices(string.digits, k=8))
        self.invoice_var.set(inv)

    def get_products(self):
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("SELECT name, price FROM products")
        products = {row[0]: row[1] for row in c.fetchall()}
        conn.close()
        return products

    def build_ui(self):
        tk.Label(self, text="🧾 Billing & Invoice",
                 bg="#1a1a2e", fg="white",
                 font=("Arial", 18, "bold")).pack(pady=8)

        main = tk.Frame(self, bg="#1a1a2e")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left: Customer & Product selection
        left_frame = tk.Frame(main, bg="#1a1a2e")
        left_frame.grid(row=0, column=0, padx=5, sticky="nsew")

        # Customer Info
        cust_frame = tk.LabelFrame(left_frame, text="Customer Information",
                                   bg="#16213e", fg="white",
                                   font=("Arial", 10, "bold"),
                                   relief=tk.RIDGE, bd=2)
        cust_frame.pack(fill=tk.X, pady=5)

        self.invoice_var = tk.StringVar()
        cust_fields = [
            ("Invoice No", "invoice_no", self.invoice_var),
            ("Customer Name", "cust_name", None),
            ("Phone", "cust_phone", None),
            ("Email", "cust_email", None),
        ]

        self.cust_entries = {}
        for i, (label, key, var) in enumerate(cust_fields):
            tk.Label(cust_frame, text=label + ":", bg="#16213e", fg="#a0a0b0",
                     font=("Arial", 10)).grid(row=i, column=0, padx=8, pady=4, sticky="w")
            if var:
                entry = tk.Entry(cust_frame, textvariable=var, font=("Arial", 10), width=22,
                                 bg="#0f3460", fg="white", insertbackground="white")
            else:
                entry = tk.Entry(cust_frame, font=("Arial", 10), width=22,
                                 bg="#0f3460", fg="white", insertbackground="white")
            entry.grid(row=i, column=1, padx=8, pady=4)
            self.cust_entries[key] = entry

        tk.Button(cust_frame, text="🔄 New Invoice No", command=self.generate_invoice_no,
                  bg="#533483", fg="white", font=("Arial", 9), relief=tk.FLAT
                  ).grid(row=0, column=2, padx=5)

        # Product selection
        prod_frame = tk.LabelFrame(left_frame, text="Add Product to Cart",
                                   bg="#16213e", fg="white",
                                   font=("Arial", 10, "bold"),
                                   relief=tk.RIDGE, bd=2)
        prod_frame.pack(fill=tk.X, pady=5)

        tk.Label(prod_frame, text="Product:", bg="#16213e", fg="#a0a0b0",
                 font=("Arial", 10)).grid(row=0, column=0, padx=8, pady=5, sticky="w")
        self.product_var = tk.StringVar()
        products = self.get_products()
        self.product_combo = ttk.Combobox(prod_frame, textvariable=self.product_var,
                                          values=list(products.keys()), width=20, state="readonly")
        self.product_combo.grid(row=0, column=1, padx=8, pady=5)
        self.product_combo.bind("<<ComboboxSelected>>", self.on_product_select)

        tk.Label(prod_frame, text="Price:", bg="#16213e", fg="#a0a0b0",
                 font=("Arial", 10)).grid(row=1, column=0, padx=8, pady=5, sticky="w")
        self.price_var = tk.StringVar()
        tk.Entry(prod_frame, textvariable=self.price_var, font=("Arial", 10), width=22,
                 bg="#0f3460", fg="white", insertbackground="white",
                 state="readonly").grid(row=1, column=1, padx=8, pady=5)

        tk.Label(prod_frame, text="Quantity:", bg="#16213e", fg="#a0a0b0",
                 font=("Arial", 10)).grid(row=2, column=0, padx=8, pady=5, sticky="w")
        self.qty_var = tk.StringVar(value="1")
        tk.Entry(prod_frame, textvariable=self.qty_var, font=("Arial", 10), width=22,
                 bg="#0f3460", fg="white", insertbackground="white"
                 ).grid(row=2, column=1, padx=8, pady=5)

        tk.Button(prod_frame, text="➕ Add to Cart", command=self.add_to_cart,
                  bg="#05c46b", fg="white", font=("Arial", 10, "bold"),
                  relief=tk.FLAT, cursor="hand2"
                  ).grid(row=3, column=0, columnspan=2, pady=8)

        # Cart
        cart_frame = tk.LabelFrame(left_frame, text="Shopping Cart",
                                   bg="#16213e", fg="white",
                                   font=("Arial", 10, "bold"),
                                   relief=tk.RIDGE, bd=2)
        cart_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        cart_cols = ("Product", "Price", "Qty", "Total")
        self.cart_tree = ttk.Treeview(cart_frame, columns=cart_cols, show="headings", height=8)
        for col in cart_cols:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=100, anchor="center")
        self.cart_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        cart_btn_frame = tk.Frame(cart_frame, bg="#16213e")
        cart_btn_frame.pack(pady=5)
        tk.Button(cart_btn_frame, text="🗑 Remove Selected", command=self.remove_from_cart,
                  bg="#e94560", fg="white", font=("Arial", 9), relief=tk.FLAT
                  ).pack(side=tk.LEFT, padx=5)
        tk.Button(cart_btn_frame, text="🧹 Clear Cart", command=self.clear_cart,
                  bg="#533483", fg="white", font=("Arial", 9), relief=tk.FLAT
                  ).pack(side=tk.LEFT, padx=5)

        # Total
        total_frame = tk.Frame(left_frame, bg="#16213e", relief=tk.RIDGE, bd=1)
        total_frame.pack(fill=tk.X, pady=5)
        tk.Label(total_frame, text="Total Amount: ", bg="#16213e", fg="white",
                 font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=10, pady=8)
        self.total_var = tk.StringVar(value="$0.00")
        tk.Label(total_frame, textvariable=self.total_var, bg="#16213e", fg="#05c46b",
                 font=("Arial", 14, "bold")).pack(side=tk.LEFT)

        # Generate Bill button
        tk.Button(left_frame, text="🧾 Generate Bill", command=self.generate_bill,
                  bg="#f0a500", fg="white", font=("Arial", 12, "bold"),
                  relief=tk.FLAT, cursor="hand2", pady=8
                  ).pack(fill=tk.X, pady=5)

        # Right: Bill records
        right_frame = tk.LabelFrame(main, text="Bill Records",
                                    bg="#16213e", fg="white",
                                    font=("Arial", 11, "bold"),
                                    relief=tk.RIDGE, bd=2)
        right_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew")
        main.columnconfigure(1, weight=1)

        search_frame = tk.Frame(right_frame, bg="#16213e")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="#16213e", fg="white").pack(side=tk.LEFT)
        self.bill_search_var = tk.StringVar()
        self.bill_search_var.trace("w", lambda *a: self.search_bills())
        tk.Entry(search_frame, textvariable=self.bill_search_var,
                 bg="#0f3460", fg="white", insertbackground="white",
                 width=25).pack(side=tk.LEFT, padx=5)

        bill_cols = ("ID", "Invoice No", "Customer", "Phone", "Email", "Date", "Total")
        self.bill_tree = ttk.Treeview(right_frame, columns=bill_cols, show="headings", height=15)
        for col in bill_cols:
            self.bill_tree.heading(col, text=col)
            self.bill_tree.column(col, width=100, anchor="center")

        scroll_y = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.bill_tree.yview)
        self.bill_tree.configure(yscrollcommand=scroll_y.set)
        self.bill_tree.pack(fill=tk.BOTH, expand=True, padx=5)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.bill_tree.bind("<ButtonRelease-1>", self.view_bill_details)

        # Bill detail view
        detail_frame = tk.LabelFrame(right_frame, text="Bill Details",
                                     bg="#16213e", fg="white",
                                     font=("Arial", 10, "bold"),
                                     relief=tk.RIDGE, bd=2)
        detail_frame.pack(fill=tk.X, padx=5, pady=5)

        self.bill_detail_text = tk.Text(detail_frame, height=8, bg="#0f3460", fg="white",
                                        font=("Courier", 9), state=tk.DISABLED)
        self.bill_detail_text.pack(fill=tk.X, padx=5, pady=5)

        btn_row = tk.Frame(right_frame, bg="#16213e")
        btn_row.pack(pady=5)
        tk.Button(btn_row, text="🖨 Print Bill", command=self.print_bill,
                  bg="#0f3460", fg="white", font=("Arial", 10), relief=tk.FLAT
                  ).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_row, text="🗑 Delete Bill", command=self.delete_bill,
                  bg="#e94560", fg="white", font=("Arial", 10), relief=tk.FLAT
                  ).pack(side=tk.LEFT, padx=5)

    def on_product_select(self, event):
        products = self.get_products()
        name = self.product_var.get()
        price = products.get(name, 0.0)
        self.price_var.set(str(price))

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
        if qty <= 0:
            messagebox.showerror("Error", "Quantity must be positive!")
            return
        total = price * qty
        self.cart_items.append({"product": product, "price": price, "qty": qty, "total": total})
        self.cart_tree.insert("", tk.END, values=(product, f"${price:.2f}", qty, f"${total:.2f}"))
        self.update_total()
        self.product_var.set("")
        self.price_var.set("")
        self.qty_var.set("1")

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

    def clear_cart(self):
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        self.cart_items.clear()
        self.update_total()

    def update_total(self):
        total = sum(item["total"] for item in self.cart_items)
        self.total_var.set(f"${total:.2f}")

    def generate_bill(self):
        invoice_no = self.invoice_var.get().strip()
        cust_name = self.cust_entries["cust_name"].get().strip()
        cust_phone = self.cust_entries["cust_phone"].get().strip()
        cust_email = self.cust_entries["cust_email"].get().strip()

        if not invoice_no:
            messagebox.showerror("Error", "Invoice number is required!")
            return
        if not cust_name:
            messagebox.showerror("Error", "Customer name is required!")
            return
        if not self.cart_items:
            messagebox.showerror("Error", "Cart is empty!")
            return

        total = sum(item["total"] for item in self.cart_items)
        bill_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build bill details string
        details_lines = []
        for item in self.cart_items:
            details_lines.append(f"{item['product']}|{item['price']}|{item['qty']}|{item['total']}")
        bill_details = ";".join(details_lines)

        try:
            conn = sqlite3.connect("inventory.db")
            c = conn.cursor()
            c.execute("""INSERT INTO bills (invoice_no, customer_name, customer_phone,
                         customer_email, bill_date, total_amount, bill_details)
                         VALUES (?, ?, ?, ?, ?, ?, ?)""",
                      (invoice_no, cust_name, cust_phone, cust_email,
                       bill_date, total, bill_details))
            conn.commit()
            conn.close()
            self.show_bill_receipt(invoice_no, cust_name, cust_phone, cust_email,
                                   bill_date, total)
            self.clear_cart()
            for entry in self.cust_entries.values():
                entry.delete(0, tk.END)
            self.generate_invoice_no()
            self.load_bills()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Invoice number already exists!")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def show_bill_receipt(self, invoice_no, cust_name, cust_phone, cust_email, bill_date, total):
        win = tk.Toplevel(self)
        win.title(f"Bill Receipt - {invoice_no}")
        win.geometry("500x600")
        win.configure(bg="#1a1a2e")

        tk.Label(win, text="INVENTORY MANAGEMENT SYSTEM",
                 bg="#1a1a2e", fg="white", font=("Arial", 14, "bold")).pack(pady=10)
        tk.Label(win, text="─" * 55, bg="#1a1a2e", fg="#a0a0b0").pack()

        receipt = tk.Text(win, bg="#0f3460", fg="white", font=("Courier", 10),
                          width=55, height=28)
        receipt.pack(padx=20, pady=10)

        lines = [
            f"  Invoice No : {invoice_no}",
            f"  Date       : {bill_date}",
            f"  Customer   : {cust_name}",
            f"  Phone      : {cust_phone}",
            f"  Email      : {cust_email}",
            "  " + "─" * 50,
            f"  {'Product':<20} {'Price':>8} {'Qty':>5} {'Total':>10}",
            "  " + "─" * 50,
        ]
        for item in self.cart_items:
            lines.append(f"  {item['product']:<20} ${item['price']:>7.2f} {item['qty']:>5} ${item['total']:>9.2f}")
        lines += [
            "  " + "─" * 50,
            f"  {'TOTAL AMOUNT':>35} ${total:>9.2f}",
            "  " + "─" * 50,
            "",
            "       Thank you for your purchase!",
        ]

        receipt.insert(tk.END, "\n".join(lines))
        receipt.config(state=tk.DISABLED)

        tk.Button(win, text="Close", command=win.destroy,
                  bg="#e94560", fg="white", font=("Arial", 11, "bold"),
                  relief=tk.FLAT, padx=20).pack(pady=10)

    def load_bills(self):
        for row in self.bill_tree.get_children():
            self.bill_tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("""SELECT id, invoice_no, customer_name, customer_phone,
                     customer_email, bill_date, total_amount FROM bills ORDER BY id DESC""")
        for row in c.fetchall():
            self.bill_tree.insert("", tk.END, values=(
                row[0], row[1], row[2], row[3], row[4], row[5], f"${row[6]:.2f}"
            ))
        conn.close()

    def search_bills(self):
        query = self.bill_search_var.get().strip().lower()
        for row in self.bill_tree.get_children():
            self.bill_tree.delete(row)
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("""SELECT id, invoice_no, customer_name, customer_phone,
                     customer_email, bill_date, total_amount FROM bills
                     WHERE LOWER(invoice_no) LIKE ? OR LOWER(customer_name) LIKE ?
                     ORDER BY id DESC""",
                  (f"%{query}%", f"%{query}%"))
        for row in c.fetchall():
            self.bill_tree.insert("", tk.END, values=(
                row[0], row[1], row[2], row[3], row[4], row[5], f"${row[6]:.2f}"
            ))
        conn.close()

    def view_bill_details(self, event):
        selected = self.bill_tree.selection()
        if not selected:
            return
        values = self.bill_tree.item(selected[0])["values"]
        bill_id = values[0]
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("SELECT * FROM bills WHERE id=?", (bill_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return

        invoice_no, cust_name, cust_phone, cust_email, bill_date, total, details_str = \
            row[1], row[2], row[3], row[4], row[5], row[6], row[7]

        lines = [
            f"Invoice No : {invoice_no}",
            f"Date       : {bill_date}",
            f"Customer   : {cust_name}",
            f"Phone      : {cust_phone}",
            f"Email      : {cust_email}",
            "─" * 50,
            f"{'Product':<20} {'Price':>8} {'Qty':>5} {'Total':>10}",
            "─" * 50,
        ]
        if details_str:
            for item_str in details_str.split(";"):
                parts = item_str.split("|")
                if len(parts) == 4:
                    lines.append(f"{parts[0]:<20} ${float(parts[1]):>7.2f} {parts[2]:>5} ${float(parts[3]):>9.2f}")
        lines += [
            "─" * 50,
            f"{'TOTAL':>35} ${total:>9.2f}",
        ]

        self.bill_detail_text.config(state=tk.NORMAL)
        self.bill_detail_text.delete("1.0", tk.END)
        self.bill_detail_text.insert(tk.END, "\n".join(lines))
        self.bill_detail_text.config(state=tk.DISABLED)

    def print_bill(self):
        selected = self.bill_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a bill to print!")
            return
        values = self.bill_tree.item(selected[0])["values"]
        bill_id = values[0]
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("SELECT * FROM bills WHERE id=?", (bill_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return

        invoice_no, cust_name, cust_phone, cust_email, bill_date, total, details_str = \
            row[1], row[2], row[3], row[4], row[5], row[6], row[7]

        # Save to text file
        filename = f"bill_{invoice_no}.txt"
        lines = [
            "=" * 55,
            "       INVENTORY MANAGEMENT SYSTEM",
            "=" * 55,
            f"  Invoice No : {invoice_no}",
            f"  Date       : {bill_date}",
            f"  Customer   : {cust_name}",
            f"  Phone      : {cust_phone}",
            f"  Email      : {cust_email}",
            "  " + "-" * 50,
            f"  {'Product':<20} {'Price':>8} {'Qty':>5} {'Total':>10}",
            "  " + "-" * 50,
        ]
        if details_str:
            for item_str in details_str.split(";"):
                parts = item_str.split("|")
                if len(parts) == 4:
                    lines.append(
                        f"  {parts[0]:<20} ${float(parts[1]):>7.2f} {parts[2]:>5} ${float(parts[3]):>9.2f}")
        lines += [
            "  " + "-" * 50,
            f"  {'TOTAL AMOUNT':>35} ${total:>9.2f}",
            "  " + "-" * 50,
            "",
            "       Thank you for your purchase!",
            "=" * 55,
        ]

        with open(filename, "w") as f:
            f.write("\n".join(lines))

        messagebox.showinfo("Print", f"Bill saved as '{filename}' in current directory!")

    def delete_bill(self):
        selected = self.bill_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a bill to delete!")
            return
        if not messagebox.askyesno("Confirm", "Delete selected bill?"):
            return
        bill_id = self.bill_tree.item(selected[0])["values"][0]
        conn = sqlite3.connect("inventory.db")
        c = conn.cursor()
        c.execute("DELETE FROM bills WHERE id=?", (bill_id,))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "Bill deleted!")
        self.bill_detail_text.config(state=tk.NORMAL)
        self.bill_detail_text.delete("1.0", tk.END)
        self.bill_detail_text.config(state=tk.DISABLED)
        self.load_bills()


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()