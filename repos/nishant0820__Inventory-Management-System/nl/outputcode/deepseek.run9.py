import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import Toplevel
from PIL import Image, ImageTk
import sqlite3
import datetime
import os

class InventoryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("900x600")
        self.db_name = "inventory.db"
        self.create_database()
        self.setup_dashboard()

    # ---------- Database Setup ----------
    def create_database(self):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            designation TEXT,
            salary REAL
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT,
            company TEXT,
            email TEXT,
            address TEXT
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            category_id INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS bills (
            invoice_no TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            total REAL NOT NULL,
            employee_id INTEGER,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL
        )""")
        cur.execute("""CREATE TABLE IF NOT EXISTS bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY (invoice_no) REFERENCES bills(invoice_no) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )""")
        conn.commit()
        conn.close()

    # ---------- Dashboard ----------
    def setup_dashboard(self):
        # Header
        header = tk.Frame(self.root, bg="#2c3e50", height=80)
        header.pack(fill=tk.X)
        tk.Label(header, text="Inventory Management System", font=("Helvetica", 24, "bold"),
                 fg="white", bg="#2c3e50").pack(pady=10)

        # Clock
        self.clock_label = tk.Label(header, font=("Helvetica", 14), fg="white", bg="#2c3e50")
        self.clock_label.pack(side=tk.RIGHT, padx=20)
        self.update_clock()

        # Logo image (if available)
        try:
            img = Image.open("logo.png").resize((100, 60), Image.Resampling.LANCZOS)
            self.logo = ImageTk.PhotoImage(img)
            tk.Label(header, image=self.logo, bg="#2c3e50").pack(side=tk.LEFT, padx=20)
        except:
            pass  # No logo

        # Main content area
        content = tk.Frame(self.root, bg="#ecf0f1")
        content.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Button grid
        btn_frame = tk.Frame(content, bg="#ecf0f1")
        btn_frame.pack(pady=20)

        buttons = [
            ("Manage Employees", self.open_employee_window),
            ("Manage Suppliers", self.open_supplier_window),
            ("Manage Categories", self.open_category_window),
            ("Manage Products", self.open_product_window),
            ("New Bill", self.open_billing_window),
            ("View Bills", self.view_bills_window)
        ]
        for i, (text, cmd) in enumerate(buttons):
            btn = tk.Button(btn_frame, text=text, font=("Arial", 12, "bold"),
                           bg="#3498db", fg="white", width=20, height=2, command=cmd)
            btn.grid(row=i//2, column=i%2, padx=10, pady=10)

    def update_clock(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.config(text=now)
        self.root.after(1000, self.update_clock)

    # ---------- Employee Management ----------
    def open_employee_window(self):
        self.new_window = Toplevel(self.root)
        self.new_window.title("Employee Management")
        self.new_window.geometry("800x500")
        self.populate_employee_tree()

    def populate_employee_tree(self):
        for widget in self.new_window.winfo_children():
            widget.destroy()

        # Treeview
        columns = ("ID", "Name", "Phone", "Email", "Designation", "Salary")
        tree = ttk.Treeview(self.new_window, columns=columns, show="headings", height=15)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(self.new_window, orient="vertical", command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)

        # Entry form
        form_frame = tk.Frame(self.new_window, bg="#dfe6e9")
        form_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        labels = ["Name:", "Phone:", "Email:", "Designation:", "Salary:"]
        self.emp_entries = {}
        for i, label in enumerate(labels):
            tk.Label(form_frame, text=label, bg="#dfe6e9").grid(row=0, column=i*2, padx=5)
            entry = tk.Entry(form_frame, width=15)
            entry.grid(row=0, column=i*2+1, padx=5)
            self.emp_entries[label[:-1].lower()] = entry

        # Buttons
        btn_frame = tk.Frame(self.new_window)
        btn_frame.pack(side=tk.BOTTOM, pady=5)
        tk.Button(btn_frame, text="Add", command=self.add_employee, bg="#2ecc71", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", command=self.update_employee, bg="#f39c12", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_employee, bg="#e74c3c", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_employee_form, width=10).pack(side=tk.LEFT, padx=5)

        # Load data
        self.load_employee_data(tree)

    def load_employee_data(self, tree):
        for row in tree.get_children():
            tree.delete(row)
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("SELECT * FROM employees")
        rows = cur.fetchall()
        for row in rows:
            tree.insert("", tk.END, values=row)
        conn.close()

    def add_employee(self):
        data = {k: v.get() for k, v in self.emp_entries.items()}
        if not data["name"]:
            messagebox.showerror("Error", "Name is required")
            return
        try:
            salary = float(data["salary"]) if data["salary"] else 0.0
        except ValueError:
            messagebox.showerror("Error", "Salary must be a number")
            return
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("INSERT INTO employees (name, phone, email, designation, salary) VALUES (?,?,?,?,?)",
                    (data["name"], data["phone"], data["email"], data["designation"], salary))
        conn.commit()
        conn.close()
        self.clear_employee_form()
        self.populate_employee_tree()
        messagebox.showinfo("Success", "Employee added")

    def update_employee(self):
        selected = self.get_selected_employee_id()
        if not selected:
            messagebox.showerror("Error", "Select an employee to update")
            return
        data = {k: v.get() for k, v in self.emp_entries.items()}
        if not data["name"]:
            messagebox.showerror("Error", "Name is required")
            return
        try:
            salary = float(data["salary"]) if data["salary"] else 0.0
        except ValueError:
            messagebox.showerror("Error", "Salary must be a number")
            return
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("UPDATE employees SET name=?, phone=?, email=?, designation=?, salary=? WHERE id=?",
                    (data["name"], data["phone"], data["email"], data["designation"], salary, selected))
        conn.commit()
        conn.close()
        self.populate_employee_tree()
        messagebox.showinfo("Success", "Employee updated")

    def delete_employee(self):
        selected = self.get_selected_employee_id()
        if not selected:
            messagebox.showerror("Error", "Select an employee to delete")
            return
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("DELETE FROM employees WHERE id=?", (selected,))
        conn.commit()
        conn.close()
        self.populate_employee_tree()
        messagebox.showinfo("Success", "Employee deleted")

    def clear_employee_form(self):
        for entry in self.emp_entries.values():
            entry.delete(0, tk.END)

    def get_selected_employee_id(self):
        # Treeview is the first child of new_window in populate method (after destroying)
        # We need a reference to tree, better to store it as instance variable.
        try:
            tree = self.new_window.winfo_children()[0]  # first is tree
            selected = tree.selection()
            if selected:
                return tree.item(selected[0])["values"][0]
            return None
        except:
            return None

    # ---------- Supplier Management ----------
    def open_supplier_window(self):
        self.supp_window = Toplevel(self.root)
        self.supp_window.title("Supplier Management")
        self.supp_window.geometry("800x500")
        self.populate_supplier_tree()

    def populate_supplier_tree(self):
        for widget in self.supp_window.winfo_children():
            widget.destroy()
        columns = ("ID", "Name", "Contact", "Company", "Email", "Address")
        tree = ttk.Treeview(self.supp_window, columns=columns, show="headings", height=15)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(self.supp_window, orient="vertical", command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)

        form_frame = tk.Frame(self.supp_window, bg="#dfe6e9")
        form_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        labels = ["Name:", "Contact:", "Company:", "Email:", "Address:"]
        self.supp_entries = {}
        for i, label in enumerate(labels):
            tk.Label(form_frame, text=label, bg="#dfe6e9").grid(row=0, column=i*2, padx=5)
            entry = tk.Entry(form_frame, width=15)
            entry.grid(row=0, column=i*2+1, padx=5)
            self.supp_entries[label[:-1].lower()] = entry

        btn_frame = tk.Frame(self.supp_window)
        btn_frame.pack(side=tk.BOTTOM, pady=5)
        tk.Button(btn_frame, text="Add", command=self.add_supplier, bg="#2ecc71", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", command=self.update_supplier, bg="#f39c12", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_supplier, bg="#e74c3c", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_supplier_form, width=10).pack(side=tk.LEFT, padx=5)

        self.load_supplier_data(tree)

    def load_supplier_data(self, tree):
        for row in tree.get_children():
            tree.delete(row)
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("SELECT * FROM suppliers")
        rows = cur.fetchall()
        for row in rows:
            tree.insert("", tk.END, values=row)
        conn.close()

    def add_supplier(self):
        data = {k: v.get() for k, v in self.supp_entries.items()}
        if not data["name"]:
            messagebox.showerror("Error", "Name is required")
            return
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("INSERT INTO suppliers (name, contact, company, email, address) VALUES (?,?,?,?,?)",
                    (data["name"], data["contact"], data["company"], data["email"], data["address"]))
        conn.commit()
        conn.close()
        self.clear_supplier_form()
        self.populate_supplier_tree()
        messagebox.showinfo("Success", "Supplier added")

    def update_supplier(self):
        selected = self.get_selected_supplier_id()
        if not selected:
            messagebox.showerror("Error", "Select a supplier to update")
            return
        data = {k: v.get() for k, v in self.supp_entries.items()}
        if not data["name"]:
            messagebox.showerror("Error", "Name is required")
            return
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("UPDATE suppliers SET name=?, contact=?, company=?, email=?, address=? WHERE id=?",
                    (data["name"], data["contact"], data["company"], data["email"], data["address"], selected))
        conn.commit()
        conn.close()
        self.populate_supplier_tree()
        messagebox.showinfo("Success", "Supplier updated")

    def delete_supplier(self):
        selected = self.get_selected_supplier_id()
        if not selected:
            messagebox.showerror("Error", "Select a supplier to delete")
            return
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("DELETE FROM suppliers WHERE id=?", (selected,))
        conn.commit()
        conn.close()
        self.populate_supplier_tree()
        messagebox.showinfo("Success", "Supplier deleted")

    def clear_supplier_form(self):
        for entry in self.supp_entries.values():
            entry.delete(0, tk.END)

    def get_selected_supplier_id(self):
        try:
            tree = self.supp_window.winfo_children()[0]
            selected = tree.selection()
            if selected:
                return tree.item(selected[0])["values"][0]
            return None
        except:
            return None

    # ---------- Category Management ----------
    def open_category_window(self):
        self.cat_window = Toplevel(self.root)
        self.cat_window.title("Category Management")
        self.cat_window.geometry("400x300")
        self.populate_category_tree()

    def populate_category_tree(self):
        for widget in self.cat_window.winfo_children():
            widget.destroy()
        columns = ("ID", "Name")
        tree = ttk.Treeview(self.cat_window, columns=columns, show="headings", height=10)
        tree.heading("ID", text="ID")
        tree.heading("Name", text="Name")
        tree.column("ID", width=50)
        tree.column("Name", width=200)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        form_frame = tk.Frame(self.cat_window, bg="#dfe6e9")
        form_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        tk.Label(form_frame, text="Name:", bg="#dfe6e9").pack(side=tk.LEFT, padx=5)
        self.cat_name_entry = tk.Entry(form_frame, width=20)
        self.cat_name_entry.pack(side=tk.LEFT, padx=5)

        btn_frame = tk.Frame(self.cat_window)
        btn_frame.pack(side=tk.BOTTOM, pady=5)
        tk.Button(btn_frame, text="Add", command=self.add_category, bg="#2ecc71", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_category, bg="#e74c3c", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=lambda: self.cat_name_entry.delete(0, tk.END), width=10).pack(side=tk.LEFT, padx=5)

        self.load_category_data(tree)

    def load_category_data(self, tree):
        for row in tree.get_children():
            tree.delete(row)
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("SELECT * FROM categories")
        rows = cur.fetchall()
        for row in rows:
            tree.insert("", tk.END, values=row)
        conn.close()

    def add_category(self):
        name = self.cat_name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Category name required")
            return
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            conn.commit()
            self.cat_name_entry.delete(0, tk.END)
            self.populate_category_tree()
            messagebox.showinfo("Success", "Category added")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Category already exists")
        finally:
            conn.close()

    def delete_category(self):
        try:
            tree = self.cat_window.winfo_children()[0]
            selected = tree.selection()
            if not selected:
                messagebox.showerror("Error", "Select a category to delete")
                return
            cat_id = tree.item(selected[0])["values"][0]
            conn = sqlite3.connect(self.db_name)
            cur = conn.cursor()
            cur.execute("DELETE FROM categories WHERE id=?", (cat_id,))
            conn.commit()
            conn.close()
            self.populate_category_tree()
            messagebox.showinfo("Success", "Category deleted")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------- Product Management ----------
    def open_product_window(self):
        self.prod_window = Toplevel(self.root)
        self.prod_window.title("Product Management")
        self.prod_window.geometry("900x500")
        self.populate_product_tree()

    def populate_product_tree(self):
        for widget in self.prod_window.winfo_children():
            widget.destroy()
        columns = ("ID", "Name", "Price", "Quantity", "Category")
        tree = ttk.Treeview(self.prod_window, columns=columns, show="headings", height=15)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(self.prod_window, orient="vertical", command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)

        form_frame = tk.Frame(self.prod_window, bg="#dfe6e9")
        form_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        tk.Label(form_frame, text="Name:", bg="#dfe6e9").grid(row=0, column=0, padx=5)
        tk.Label(form_frame, text="Price:", bg="#dfe6e9").grid(row=0, column=2, padx=5)
        tk.Label(form_frame, text="Quantity:", bg="#dfe6e9").grid(row=0, column=4, padx=5)
        tk.Label(form_frame, text="Category:", bg="#dfe6e9").grid(row=0, column=6, padx=5)

        self.prod_name_entry = tk.Entry(form_frame, width=15)
        self.prod_name_entry.grid(row=0, column=1, padx=5)
        self.prod_price_entry = tk.Entry(form_frame, width=15)
        self.prod_price_entry.grid(row=0, column=3, padx=5)
        self.prod_qty_entry = tk.Entry(form_frame, width=15)
        self.prod_qty_entry.grid(row=0, column=5, padx=5)
        self.prod_cat_combo = ttk.Combobox(form_frame, width=15)
        self.prod_cat_combo.grid(row=0, column=7, padx=5)
        self.load_categories_into_combo(self.prod_cat_combo)

        btn_frame = tk.Frame(self.prod_window)
        btn_frame.pack(side=tk.BOTTOM, pady=5)
        tk.Button(btn_frame, text="Add", command=self.add_product, bg="#2ecc71", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", command=self.update_product, bg="#f39c12", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete_product, bg="#e74c3c", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_product_form, width=10).pack(side=tk.LEFT, padx=5)

        self.load_product_data(tree)

    def load_categories_into_combo(self, combo):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM categories")
        categories = cur.fetchall()
        conn.close()
        combo['values'] = [f"{cat[0]} - {cat[1]}" for cat in categories]
        if categories:
            combo.current(0)

    def load_product_data(self, tree):
        for row in tree.get_children():
            tree.delete(row)
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("""SELECT p.id, p.name, p.price, p.quantity, c.name 
                       FROM products p LEFT JOIN categories c ON p.category_id = c.id""")
        rows = cur.fetchall()
        for row in rows:
            tree.insert("", tk.END, values=row)
        conn.close()

    def add_product(self):
        name = self.prod_name_entry.get().strip()
        price_str = self.prod_price_entry.get().strip()
        qty_str = self.prod_qty_entry.get().strip()
        cat_val = self.prod_cat_combo.get()
        if not name or not price_str or not qty_str:
            messagebox.showerror("Error", "Name, price, and quantity required")
            return
        try:
            price = float(price_str)
            qty = int(qty_str)
        except ValueError:
            messagebox.showerror("Error", "Price and quantity must be numbers")
            return
        cat_id = None
        if cat_val:
            cat_id = int(cat_val.split(" - ")[0])
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("INSERT INTO products (name, price, quantity, category_id) VALUES (?,?,?,?)",
                    (name, price, qty, cat_id))
        conn.commit()
        conn.close()
        self.clear_product_form()
        self.populate_product_tree()
        messagebox.showinfo("Success", "Product added")

    def update_product(self):
        selected = self.get_selected_product_id()
        if not selected:
            messagebox.showerror("Error", "Select a product to update")
            return
        name = self.prod_name_entry.get().strip()
        price_str = self.prod_price_entry.get().strip()
        qty_str = self.prod_qty_entry.get().strip()
        cat_val = self.prod_cat_combo.get()
        if not name or not price_str or not qty_str:
            messagebox.showerror("Error", "Name, price, and quantity required")
            return
        try:
            price = float(price_str)
            qty = int(qty_str)
        except ValueError:
            messagebox.showerror("Error", "Price and quantity must be numbers")
            return
        cat_id = None
        if cat_val:
            cat_id = int(cat_val.split(" - ")[0])
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("UPDATE products SET name=?, price=?, quantity=?, category_id=? WHERE id=?",
                    (name, price, qty, cat_id, selected))
        conn.commit()
        conn.close()
        self.populate_product_tree()
        messagebox.showinfo("Success", "Product updated")

    def delete_product(self):
        selected = self.get_selected_product_id()
        if not selected:
            messagebox.showerror("Error", "Select a product to delete")
            return
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id=?", (selected,))
        conn.commit()
        conn.close()
        self.populate_product_tree()
        messagebox.showinfo("Success", "Product deleted")

    def clear_product_form(self):
        self.prod_name_entry.delete(0, tk.END)
        self.prod_price_entry.delete(0, tk.END)
        self.prod_qty_entry.delete(0, tk.END)
        self.prod_cat_combo.set('')

    def get_selected_product_id(self):
        try:
            tree = self.prod_window.winfo_children()[0]
            selected = tree.selection()
            if selected:
                return tree.item(selected[0])["values"][0]
            return None
        except:
            return None

    # ---------- Billing ----------
    def open_billing_window(self):
        self.bill_window = Toplevel(self.root)
        self.bill_window.title("New Bill")
        self.bill_window.geometry("800x600")

        # Top frame for employee selection and date
        top_frame = tk.Frame(self.bill_window)
        top_frame.pack(fill=tk.X, pady=5)
        tk.Label(top_frame, text="Employee:").pack(side=tk.LEFT, padx=5)
        self.emp_combo = ttk.Combobox(top_frame, width=20)
        self.emp_combo.pack(side=tk.LEFT, padx=5)
        self.load_employees_into_combo()
        tk.Label(top_frame, text=f"Date: {datetime.date.today()}").pack(side=tk.RIGHT, padx=10)

        # Cart (Treeview)
        cart_frame = tk.Frame(self.bill_window)
        cart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        columns = ("Product ID", "Product Name", "Price", "Quantity", "Total")
        self.cart_tree = ttk.Treeview(cart_frame, columns=columns, show="headings", height=10)
        for col in columns:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=100)
        self.cart_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cart_scroll = ttk.Scrollbar(cart_frame, orient="vertical", command=self.cart_tree.yview)
        cart_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.cart_tree.configure(yscrollcommand=cart_scroll.set)

        # Add product frame
        add_frame = tk.Frame(self.bill_window, bg="#dfe6e9")
        add_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(add_frame, text="Product:", bg="#dfe6e9").grid(row=0, column=0, padx=5)
        self.bill_prod_combo = ttk.Combobox(add_frame, width=25)
        self.bill_prod_combo.grid(row=0, column=1, padx=5)
        self.load_products_into_combo()
        tk.Label(add_frame, text="Qty:", bg="#dfe6e9").grid(row=0, column=2, padx=5)
        self.bill_qty_entry = tk.Entry(add_frame, width=10)
        self.bill_qty_entry.grid(row=0, column=3, padx=5)
        tk.Button(add_frame, text="Add to Cart", command=self.add_to_cart, bg="#3498db", fg="white").grid(row=0, column=4, padx=5)

        # Total and generate bill
        bottom_frame = tk.Frame(self.bill_window)
        bottom_frame.pack(fill=tk.X, padx=10, pady=5)
        self.total_label = tk.Label(bottom_frame, text="Total: ₹0.00", font=("Arial", 14, "bold"))
        self.total_label.pack(side=tk.LEFT, padx=10)
        tk.Button(bottom_frame, text="Generate Bill", command=self.generate_bill, bg="#27ae60", fg="white",
                 width=15, height=2).pack(side=tk.RIGHT, padx=10)
        tk.Button(bottom_frame, text="Clear Cart", command=self.clear_cart, bg="#e74c3c", fg="white",
                 width=15, height=2).pack(side=tk.RIGHT)

    def load_employees_into_combo(self):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM employees")
        employees = cur.fetchall()
        conn.close()
        self.emp_combo['values'] = [f"{emp[0]} - {emp[1]}" for emp in employees]
        if employees:
            self.emp_combo.current(0)

    def load_products_into_combo(self):
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("SELECT id, name, price, quantity FROM products WHERE quantity > 0")
        products = cur.fetchall()
        conn.close()
        self.prod_list = products  # store for later use
        self.bill_prod_combo['values'] = [f"{p[0]} - {p[1]} (₹{p[2]}, Stock:{p[3]})" for p in products]
        if products:
            self.bill_prod_combo.current(0)

    def add_to_cart(self):
        sel = self.bill_prod_combo.get()
        qty_str = self.bill_qty_entry.get().strip()
        if not sel or not qty_str:
            messagebox.showerror("Error", "Select product and enter quantity")
            return
        try:
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Quantity must be a positive integer")
            return
        # Parse product ID from selection
        prod_id = int(sel.split(" - ")[0])
        # Find product details
        for p in self.prod_list:
            if p[0] == prod_id:
                price = p[2]
                stock = p[3]
                name = p[1]
                break
        else:
            messagebox.showerror("Error", "Product not found")
            return
        if qty > stock:
            messagebox.showerror("Error", f"Insufficient stock. Available: {stock}")
            return
        # Check if product already in cart
        for child in self.cart_tree.get_children():
            values = self.cart_tree.item(child)['values']
            if int(values[0]) == prod_id:
                # update existing row
                old_qty = int(values[3])
                new_qty = old_qty + qty
                if new_qty > stock:
                    messagebox.showerror("Error", f"Total quantity {new_qty} exceeds stock {stock}")
                    return
                new_total = price * new_qty
                self.cart_tree.item(child, values=(prod_id, name, price, new_qty, new_total))
                self.update_cart_total()
                return
        # Add new row
        total = price * qty
        self.cart_tree.insert("", tk.END, values=(prod_id, name, price, qty, total))
        self.update_cart_total()

    def update_cart_total(self):
        total = sum(float(self.cart_tree.item(child)['values'][4]) for child in self.cart_tree.get_children())
        self.total_label.config(text=f"Total: ₹{total:.2f}")

    def clear_cart(self):
        for child in self.cart_tree.get_children():
            self.cart_tree.delete(child)
        self.update_cart_total()

    def generate_bill(self):
        if not self.cart_tree.get_children():
            messagebox.showerror("Error", "Cart is empty")
            return
        employee_sel = self.emp_combo.get()
        employee_id = None
        if employee_sel:
            employee_id = int(employee_sel.split(" - ")[0])
        # Generate invoice number: INV-YYYYMMDD-XXXX random enough? Use datetime + sequence?
        now = datetime.datetime.now()
        inv_date = now.strftime("%Y-%m-%d %H:%M:%S")
        # Simple unique invoice: timestamp-based
        inv_no = "INV-" + now.strftime("%Y%m%d%H%M%S")
        # but to ensure uniqueness, use timestamp + random? For simplicity, use full datetime seconds, unlikely to clash.
        total = sum(float(self.cart_tree.item(child)['values'][4]) for child in self.cart_tree.get_children())

        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        try:
            # Insert bill
            cur.execute("INSERT INTO bills (invoice_no, date, total, employee_id) VALUES (?,?,?,?)",
                        (inv_no, inv_date, total, employee_id))
            # Insert items and update stock
            for child in self.cart_tree.get_children():
                row = self.cart_tree.item(child)['values']
                prod_id = row[0]
                qty = row[3]
                price = row[2]
                cur.execute("INSERT INTO bill_items (invoice_no, product_id, quantity, price) VALUES (?,?,?,?)",
                            (inv_no, prod_id, qty, price))
                cur.execute("UPDATE products SET quantity = quantity - ? WHERE id = ?", (qty, prod_id))
            conn.commit()
            messagebox.showinfo("Success", f"Bill generated successfully.\nInvoice No: {inv_no}")
            self.clear_cart()
            self.bill_window.destroy()  # close after generation
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Failed to generate bill: {e}")
        finally:
            conn.close()

    # ---------- View Bills ----------
    def view_bills_window(self):
        self.view_bills_window_obj = Toplevel(self.root)
        self.view_bills_window_obj.title("Bills History")
        self.view_bills_window_obj.geometry("800x500")
        columns = ("Invoice No", "Date", "Total", "Employee")
        tree = ttk.Treeview(self.view_bills_window_obj, columns=columns, show="headings", height=15)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(self.view_bills_window_obj, orient="vertical", command=tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.configure(yscrollcommand=scrollbar.set)

        # Load bills
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("""SELECT b.invoice_no, b.date, b.total, e.name 
                       FROM bills b LEFT JOIN employees e ON b.employee_id = e.id 
                       ORDER BY b.date DESC""")
        rows = cur.fetchall()
        for row in rows:
            tree.insert("", tk.END, values=row)
        conn.close()

        # Double-click to view details
        tree.bind("<Double-1>", lambda event: self.view_bill_details(tree))

    def view_bill_details(self, tree):
        selected = tree.selection()
        if not selected:
            return
        inv_no = tree.item(selected[0])['values'][0]
        detail_window = Toplevel(self.root)
        detail_window.title(f"Bill Details - {inv_no}")
        detail_window.geometry("600x300")

        # Get bill header info
        conn = sqlite3.connect(self.db_name)
        cur = conn.cursor()
        cur.execute("SELECT date, total FROM bills WHERE invoice_no=?", (inv_no,))
        bill = cur.fetchone()
        tk.Label(detail_window, text=f"Invoice: {inv_no}   Date: {bill[0]}   Total: ₹{bill[1]}", font=("Arial", 12)).pack(pady=5)

        # Items tree
        cols = ("Product", "Qty", "Price", "Subtotal")
        items_tree = ttk.Treeview(detail_window, columns=cols, show="headings", height=10)
        for col in cols:
            items_tree.heading(col, text=col)
            items_tree.column(col, width=100)
        items_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cur.execute("""SELECT p.name, bi.quantity, bi.price, (bi.quantity * bi.price) 
                       FROM bill_items bi JOIN products p ON bi.product_id = p.id 
                       WHERE bi.invoice_no=?""", (inv_no,))
        for row in cur.fetchall():
            items_tree.insert("", tk.END, values=row)
        conn.close()

if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryApp(root)
    root.mainloop()