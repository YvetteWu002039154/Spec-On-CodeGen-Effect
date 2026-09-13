import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog
import sqlite3
import os
import datetime
from PIL import Image, ImageTk
import random


class DatabaseManager:
    """Handles all database operations."""
    def __init__(self, db_name="ims.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.executescript("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                address TEXT,
                join_date TEXT
            );
            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact_person TEXT,
                phone TEXT,
                email TEXT,
                address TEXT
            );
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER,
                price REAL NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                supplier_id INTEGER,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            );
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT UNIQUE NOT NULL,
                date TEXT NOT NULL,
                total_amount REAL NOT NULL,
                customer_name TEXT
            );
            CREATE TABLE IF NOT EXISTS bill_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER,
                product_id INTEGER,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
        """)
        self.connection.commit()

    def execute(self, query, params=None):
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        self.connection.commit()

    def fetch_all(self, query, params=None):
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        return self.cursor.fetchall()

    def fetch_one(self, query, params=None):
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        return self.cursor.fetchone()

    def close(self):
        self.connection.close()


class EmployeeWindow(tk.Toplevel):
    """Window for managing employees."""
    def __init__(self, master, db: DatabaseManager):
        super().__init__(master)
        self.db = db
        self.title("Employee Management")
        self.geometry("800x500")
        self._build_ui()
        self._refresh_tree()

    def _build_ui(self):
        # Form frame
        form_frame = ttk.LabelFrame(self, text="Employee Details")
        form_frame.pack(pady=5, padx=5, fill="x")

        ttk.Label(form_frame, text="Name").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.name_entry = ttk.Entry(form_frame, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(form_frame, text="Email").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.email_entry = ttk.Entry(form_frame, width=30)
        self.email_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(form_frame, text="Phone").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.phone_entry = ttk.Entry(form_frame, width=30)
        self.phone_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(form_frame, text="Address").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.addr_entry = ttk.Entry(form_frame, width=30)
        self.addr_entry.grid(row=3, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(form_frame, text="Join Date (YYYY-MM-DD)").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.join_entry = ttk.Entry(form_frame, width=30)
        self.join_entry.grid(row=4, column=1, padx=5, pady=2, sticky="w")

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=5)
        ttk.Button(btn_frame, text="Add", command=self._add_employee).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Update Selected", command=self._update_employee).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete Selected", command=self._delete_employee).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear", command=self._clear_form).pack(side="left", padx=5)

        # Treeview
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        columns = ("ID", "Name", "Email", "Phone", "Address", "Join Date")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _refresh_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = self.db.fetch_all("SELECT id, name, email, phone, address, join_date FROM employees")
        for row in rows:
            self.tree.insert("", "end", values=row)

    def _clear_form(self):
        self.name_entry.delete(0, tk.END)
        self.email_entry.delete(0, tk.END)
        self.phone_entry.delete(0, tk.END)
        self.addr_entry.delete(0, tk.END)
        self.join_entry.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def _add_employee(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        email = self.email_entry.get().strip()
        phone = self.phone_entry.get().strip()
        addr = self.addr_entry.get().strip()
        join = self.join_entry.get().strip()
        self.db.execute("INSERT INTO employees (name, email, phone, address, join_date) VALUES (?,?,?,?,?)",
                        (name, email, phone, addr, join))
        self._refresh_tree()
        self._clear_form()

    def _update_employee(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select an employee to update")
            return
        emp_id = self.tree.item(selected[0])['values'][0]
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name is required")
            return
        email = self.email_entry.get().strip()
        phone = self.phone_entry.get().strip()
        addr = self.addr_entry.get().strip()
        join = self.join_entry.get().strip()
        self.db.execute("UPDATE employees SET name=?, email=?, phone=?, address=?, join_date=? WHERE id=?",
                        (name, email, phone, addr, join, emp_id))
        self._refresh_tree()
        self._clear_form()

    def _delete_employee(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select an employee to delete")
            return
        if messagebox.askyesno("Confirm", "Delete selected employee?"):
            emp_id = self.tree.item(selected[0])['values'][0]
            self.db.execute("DELETE FROM employees WHERE id=?", (emp_id,))
            self._refresh_tree()
            self._clear_form()

    def _on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])['values']
        self._clear_form()
        self.name_entry.insert(0, values[1])
        self.email_entry.insert(0, values[2])
        self.phone_entry.insert(0, values[3])
        self.addr_entry.insert(0, values[4])
        self.join_entry.insert(0, values[5])


class SupplierWindow(tk.Toplevel):
    """Window for managing suppliers."""
    def __init__(self, master, db: DatabaseManager):
        super().__init__(master)
        self.db = db
        self.title("Supplier Management")
        self.geometry("800x500")
        self._build_ui()
        self._refresh_tree()

    def _build_ui(self):
        form_frame = ttk.LabelFrame(self, text="Supplier Details")
        form_frame.pack(pady=5, padx=5, fill="x")

        ttk.Label(form_frame, text="Name").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.name_entry = ttk.Entry(form_frame, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(form_frame, text="Contact Person").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.contact_entry = ttk.Entry(form_frame, width=30)
        self.contact_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(form_frame, text="Phone").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.phone_entry = ttk.Entry(form_frame, width=30)
        self.phone_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(form_frame, text="Email").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.email_entry = ttk.Entry(form_frame, width=30)
        self.email_entry.grid(row=3, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(form_frame, text="Address").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.addr_entry = ttk.Entry(form_frame, width=30)
        self.addr_entry.grid(row=4, column=1, padx=5, pady=2, sticky="w")

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=5)
        ttk.Button(btn_frame, text="Add", command=self._add_supplier).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Update", command=self._update_supplier).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete", command=self._delete_supplier).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear", command=self._clear_form).pack(side="left", padx=5)

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        columns = ("ID", "Name", "Contact Person", "Phone", "Email", "Address")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _refresh_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = self.db.fetch_all("SELECT id, name, contact_person, phone, email, address FROM suppliers")
        for row in rows:
            self.tree.insert("", "end", values=row)

    def _clear_form(self):
        self.name_entry.delete(0, tk.END)
        self.contact_entry.delete(0, tk.END)
        self.phone_entry.delete(0, tk.END)
        self.email_entry.delete(0, tk.END)
        self.addr_entry.delete(0, tk.END)
        self.tree.selection_remove(self.tree.selection())

    def _add_supplier(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required")
            return
        self.db.execute("INSERT INTO suppliers (name, contact_person, phone, email, address) VALUES (?,?,?,?,?)",
                        (name, self.contact_entry.get().strip(), self.phone_entry.get().strip(),
                         self.email_entry.get().strip(), self.addr_entry.get().strip()))
        self._refresh_tree()
        self._clear_form()

    def _update_supplier(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a supplier")
            return
        sup_id = self.tree.item(selected[0])['values'][0]
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Name required")
            return
        self.db.execute(
            "UPDATE suppliers SET name=?, contact_person=?, phone=?, email=?, address=? WHERE id=?",
            (name, self.contact_entry.get().strip(), self.phone_entry.get().strip(),
             self.email_entry.get().strip(), self.addr_entry.get().strip(), sup_id)
        )
        self._refresh_tree()
        self._clear_form()

    def _delete_supplier(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a supplier")
            return
        if messagebox.askyesno("Confirm", "Delete supplier?"):
            sup_id = self.tree.item(selected[0])['values'][0]
            self.db.execute("DELETE FROM suppliers WHERE id=?", (sup_id,))
            self._refresh_tree()
            self._clear_form()

    def _on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])['values']
        self._clear_form()
        self.name_entry.insert(0, values[1])
        self.contact_entry.insert(0, values[2])
        self.phone_entry.insert(0, values[3])
        self.email_entry.insert(0, values[4])
        self.addr_entry.insert(0, values[5])


class CategoryWindow(tk.Toplevel):
    """Window for managing product categories."""
    def __init__(self, master, db: DatabaseManager):
        super().__init__(master)
        self.db = db
        self.title("Category Management")
        self.geometry("500x400")
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        form_frame = ttk.Frame(self)
        form_frame.pack(pady=5, padx=5, fill="x")
        ttk.Label(form_frame, text="Category Name").grid(row=0, column=0, padx=5, pady=2)
        self.name_entry = ttk.Entry(form_frame, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(form_frame, text="Add", command=self._add_category).grid(row=0, column=2, padx=5)
        ttk.Button(form_frame, text="Delete Selected", command=self._delete_category).grid(row=0, column=3, padx=5)

        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.listbox = tk.Listbox(list_frame, selectmode="single")
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        rows = self.db.fetch_all("SELECT id, name FROM categories ORDER BY name")
        for row in rows:
            self.listbox.insert(tk.END, row[1])  # display name, store id maybe via mapping

    def _add_category(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Category name required")
            return
        try:
            self.db.execute("INSERT INTO categories (name) VALUES (?)", (name,))
            self.name_entry.delete(0, tk.END)
            self._refresh_list()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Category already exists")

    def _delete_category(self):
        selection = self.listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Select a category")
            return
        name = self.listbox.get(selection[0])
        # check if used in products
        cat_id = self.db.fetch_one("SELECT id FROM categories WHERE name=?", (name,))
        if cat_id:
            products = self.db.fetch_one("SELECT COUNT(*) FROM products WHERE category_id=?", (cat_id[0],))
            if products and products[0] > 0:
                messagebox.showerror("Error", "Cannot delete category with associated products")
                return
            if messagebox.askyesno("Confirm", f"Delete category '{name}'?"):
                self.db.execute("DELETE FROM categories WHERE id=?", (cat_id[0],))
                self._refresh_list()


class ProductWindow(tk.Toplevel):
    """Window for managing products."""
    def __init__(self, master, db: DatabaseManager):
        super().__init__(master)
        self.db = db
        self.title("Product Management")
        self.geometry("900x550")
        self._build_ui()
        self._populate_combos()
        self._refresh_tree()

    def _build_ui(self):
        form_frame = ttk.LabelFrame(self, text="Product Details")
        form_frame.pack(pady=5, padx=5, fill="x")

        ttk.Label(form_frame, text="Name").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.name_entry = ttk.Entry(form_frame, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(form_frame, text="Category").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.cat_combo = ttk.Combobox(form_frame, state="readonly", width=27)
        self.cat_combo.grid(row=1, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(form_frame, text="Price").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.price_entry = ttk.Entry(form_frame, width=30)
        self.price_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(form_frame, text="Stock").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.stock_entry = ttk.Entry(form_frame, width=30)
        self.stock_entry.grid(row=3, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(form_frame, text="Supplier").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        self.sup_combo = ttk.Combobox(form_frame, state="readonly", width=27)
        self.sup_combo.grid(row=4, column=1, padx=5, pady=2, sticky="w")

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=5)
        ttk.Button(btn_frame, text="Add", command=self._add_product).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Update", command=self._update_product).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete", command=self._delete_product).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Clear", command=self._clear_form).pack(side="left", padx=5)

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        columns = ("ID", "Name", "Category", "Price", "Stock", "Supplier")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

    def _populate_combos(self):
        cats = self.db.fetch_all("SELECT id, name FROM categories")
        self.cat_combo['values'] = [row[1] for row in cats]
        self.cat_dict = {row[1]: row[0] for row in cats}

        sups = self.db.fetch_all("SELECT id, name FROM suppliers")
        self.sup_combo['values'] = [row[1] for row in sups]
        self.sup_dict = {row[1]: row[0] for row in sups}

    def _refresh_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        query = """SELECT p.id, p.name, c.name, p.price, p.stock, s.name
                   FROM products p
                   LEFT JOIN categories c ON p.category_id = c.id
                   LEFT JOIN suppliers s ON p.supplier_id = s.id"""
        rows = self.db.fetch_all(query)
        for row in rows:
            self.tree.insert("", "end", values=row)

    def _clear_form(self):
        self.name_entry.delete(0, tk.END)
        self.price_entry.delete(0, tk.END)
        self.stock_entry.delete(0, tk.END)
        self.cat_combo.set("")
        self.sup_combo.set("")
        self.tree.selection_remove(self.tree.selection())

    def _add_product(self):
        name = self.name_entry.get().strip()
        try:
            price = float(self.price_entry.get())
            stock = int(self.stock_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Price and stock must be numbers")
            return
        cat_name = self.cat_combo.get()
        sup_name = self.sup_combo.get()
        cat_id = self.cat_dict.get(cat_name)
        sup_id = self.sup_dict.get(sup_name)
        if not name or price < 0 or stock < 0:
            messagebox.showerror("Error", "Invalid input")
            return
        self.db.execute("INSERT INTO products (name, category_id, price, stock, supplier_id) VALUES (?,?,?,?,?)",
                        (name, cat_id, price, stock, sup_id))
        self._refresh_tree()
        self._clear_form()

    def _update_product(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a product")
            return
        prod_id = self.tree.item(selected[0])['values'][0]
        name = self.name_entry.get().strip()
        try:
            price = float(self.price_entry.get())
            stock = int(self.stock_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Price and stock must be numbers")
            return
        cat_id = self.cat_dict.get(self.cat_combo.get())
        sup_id = self.sup_dict.get(self.sup_combo.get())
        if not name or price < 0 or stock < 0:
            messagebox.showerror("Error", "Invalid input")
            return
        self.db.execute(
            "UPDATE products SET name=?, category_id=?, price=?, stock=?, supplier_id=? WHERE id=?",
            (name, cat_id, price, stock, sup_id, prod_id)
        )
        self._refresh_tree()
        self._clear_form()

    def _delete_product(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a product")
            return
        if messagebox.askyesno("Confirm", "Delete product?"):
            prod_id = self.tree.item(selected[0])['values'][0]
            self.db.execute("DELETE FROM products WHERE id=?", (prod_id,))
            self._refresh_tree()
            self._clear_form()

    def _on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])['values']
        self._clear_form()
        self.name_entry.insert(0, values[1])
        if values[2]:
            self.cat_combo.set(values[2])
        self.price_entry.insert(0, values[3])
        self.stock_entry.insert(0, values[4])
        if values[5]:
            self.sup_combo.set(values[5])


class BillingWindow(tk.Toplevel):
    """Window for creating new bills/invoices."""
    def __init__(self, master, db: DatabaseManager):
        super().__init__(master)
        self.db = db
        self.title("Billing / New Invoice")
        self.geometry("800x600")
        self.cart = []  # list of (product_id, name, price, quantity)
        self._build_ui()
        self._load_products()

    def _build_ui(self):
        # Customer info
        cust_frame = ttk.Frame(self)
        cust_frame.pack(pady=5, padx=5, fill="x")
        ttk.Label(cust_frame, text="Customer Name").pack(side="left", padx=5)
        self.customer_entry = ttk.Entry(cust_frame, width=30)
        self.customer_entry.pack(side="left", padx=5)

        # Product selection
        select_frame = ttk.LabelFrame(self, text="Select Product")
        select_frame.pack(pady=5, padx=5, fill="x")
        ttk.Label(select_frame, text="Product").pack(side="left", padx=5)
        self.prod_combo = ttk.Combobox(select_frame, state="readonly", width=30)
        self.prod_combo.pack(side="left", padx=5)
        self.prod_combo.bind("<<ComboboxSelected>>", self._update_price_display)
        ttk.Label(select_frame, text="Price").pack(side="left", padx=5)
        self.price_label = ttk.Label(select_frame, text="0.00")
        self.price_label.pack(side="left", padx=5)
        ttk.Label(select_frame, text="Quantity").pack(side="left", padx=5)
        self.qty_entry = ttk.Entry(select_frame, width=10)
        self.qty_entry.pack(side="left", padx=5)
        self.qty_entry.insert(0, "1")
        ttk.Button(select_frame, text="Add to Cart", command=self._add_to_cart).pack(side="left", padx=5)

        # Cart display
        cart_frame = ttk.LabelFrame(self, text="Cart")
        cart_frame.pack(fill="both", expand=True, padx=5, pady=5)
        columns = ("Product", "Price", "Qty", "Subtotal")
        self.cart_tree = ttk.Treeview(cart_frame, columns=columns, show="headings", selectmode="browse")
        for col in columns:
            self.cart_tree.heading(col, text=col)
            self.cart_tree.column(col, width=120, anchor="w")
        self.cart_tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(cart_frame, orient="vertical", command=self.cart_tree.yview)
        self.cart_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Totals and actions
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(pady=5, padx=5, fill="x")
        self.total_label = ttk.Label(bottom_frame, text="Total: 0.00", font=("Arial", 12, "bold"))
        self.total_label.pack(side="left", padx=10)
        ttk.Button(bottom_frame, text="Remove Selected", command=self._remove_item).pack(side="left", padx=5)
        ttk.Button(bottom_frame, text="Clear Cart", command=self._clear_cart).pack(side="left", padx=5)
        ttk.Button(bottom_frame, text="Generate Invoice", command=self._generate_invoice).pack(side="left", padx=5)

    def _load_products(self):
        rows = self.db.fetch_all("SELECT id, name, price FROM products WHERE stock > 0")
        self.products = {row[1]: {'id': row[0], 'price': row[2]} for row in rows}
        self.prod_combo['values'] = list(self.products.keys())

    def _update_price_display(self, event=None):
        prod_name = self.prod_combo.get()
        if prod_name in self.products:
            self.price_label.config(text=f"{self.products[prod_name]['price']:.2f}")

    def _add_to_cart(self):
        prod_name = self.prod_combo.get()
        if not prod_name:
            messagebox.showerror("Error", "Select a product")
            return
        try:
            qty = int(self.qty_entry.get())
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Quantity must be a positive integer")
            return
        prod = self.products[prod_name]
        # Check stock (optional but don't allow over stock in one go? We'll just add to cart, stock will be deducted on invoice)
        # For simplicity, allow add.
        self.cart.append((prod['id'], prod_name, prod['price'], qty))
        self._refresh_cart()
        self.qty_entry.delete(0, tk.END)
        self.qty_entry.insert(0, "1")

    def _refresh_cart(self):
        for row in self.cart_tree.get_children():
            self.cart_tree.delete(row)
        total = 0.0
        for item in self.cart:
            subtotal = item[2] * item[3]
            total += subtotal
            self.cart_tree.insert("", "end", values=(item[1], f"{item[2]:.2f}", item[3], f"{subtotal:.2f}"))
        self.total_label.config(text=f"Total: {total:.2f}")

    def _remove_item(self):
        selected = self.cart_tree.selection()
        if not selected:
            return
        idx = self.cart_tree.index(selected[0])
        del self.cart[idx]
        self._refresh_cart()

    def _clear_cart(self):
        self.cart.clear()
        self._refresh_cart()

    def _generate_invoice(self):
        if not self.cart:
            messagebox.showerror("Error", "Cart is empty")
            return
        customer = self.customer_entry.get().strip() or "Walk-in Customer"
        total = sum(item[2] * item[3] for item in self.cart)
        # Generate unique invoice number: INV-YYYYMMDD-XXXX
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")
        inv_prefix = now.strftime("INV-%Y%m%d-")
        # Find max id to append
        last_inv = self.db.fetch_one("SELECT MAX(id) FROM bills")
        next_id = (last_inv[0] + 1) if last_inv[0] else 1
        invoice_no = f"{inv_prefix}{next_id:04d}"

        # Deduct stock and insert bill
        try:
            for item in self.cart:
                prod_id = item[0]
                qty = item[3]
                # Check stock
                stock = self.db.fetch_one("SELECT stock FROM products WHERE id=?", (prod_id,))
                if not stock or stock[0] < qty:
                    raise Exception(f"Not enough stock for product {item[1]}")
            # All good, insert bill
            self.db.execute("INSERT INTO bills (invoice_no, date, total_amount, customer_name) VALUES (?,?,?,?)",
                            (invoice_no, date_str, total, customer))
            bill_id = self.db.fetch_one("SELECT id FROM bills WHERE invoice_no=?", (invoice_no,))[0]

            for item in self.cart:
                prod_id, name, price, qty = item
                self.db.execute("INSERT INTO bill_items (bill_id, product_id, quantity, price) VALUES (?,?,?,?)",
                                (bill_id, prod_id, qty, price))
                # Deduct stock
                self.db.execute("UPDATE products SET stock = stock - ? WHERE id=?", (qty, prod_id))

            messagebox.showinfo("Success", f"Invoice {invoice_no} generated successfully!")
            self._clear_cart()
        except Exception as e:
            messagebox.showerror("Error", str(e))


class InvoiceViewer(tk.Toplevel):
    """View/search invoices by invoice number."""
    def __init__(self, master, db: DatabaseManager):
        super().__init__(master)
        self.db = db
        self.title("View Invoices")
        self.geometry("900x550")
        self._build_ui()
        self._load_all_invoices()

    def _build_ui(self):
        search_frame = ttk.Frame(self)
        search_frame.pack(pady=5, padx=5, fill="x")
        ttk.Label(search_frame, text="Invoice No:").pack(side="left", padx=5)
        self.search_entry = ttk.Entry(search_frame, width=30)
        self.search_entry.pack(side="left", padx=5)
        ttk.Button(search_frame, text="Search", command=self._search_invoice).pack(side="left", padx=5)
        ttk.Button(search_frame, text="Show All", command=self._load_all_invoices).pack(side="left", padx=5)

        # Bill list
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        columns = ("Invoice No", "Date", "Customer", "Total")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Items detail
        detail_frame = ttk.LabelFrame(self, text="Invoice Items")
        detail_frame.pack(fill="both", padx=5, pady=5)
        item_columns = ("Product", "Qty", "Price", "Subtotal")
        self.item_tree = ttk.Treeview(detail_frame, columns=item_columns, show="headings", height=6)
        for col in item_columns:
            self.item_tree.heading(col, text=col)
            self.item_tree.column(col, width=120, anchor="w")
        self.item_tree.pack(side="left", fill="both", expand=True)

    def _load_all_invoices(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = self.db.fetch_all("SELECT invoice_no, date, customer_name, total_amount FROM bills ORDER BY id DESC")
        for row in rows:
            self.tree.insert("", "end", values=row)

    def _search_invoice(self):
        inv = self.search_entry.get().strip()
        if not inv:
            self._load_all_invoices()
            return
        for row in self.tree.get_children():
            self.tree.delete(row)
        rows = self.db.fetch_all("SELECT invoice_no, date, customer_name, total_amount FROM bills WHERE invoice_no LIKE ?",
                                 (f"%{inv}%",))
        for row in rows:
            self.tree.insert("", "end", values=row)

    def _on_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        inv_no = self.tree.item(selected[0])['values'][0]
        # Fetch items
        query = """SELECT p.name, bi.quantity, bi.price, bi.quantity * bi.price
                   FROM bill_items bi
                   JOIN products p ON bi.product_id = p.id
                   JOIN bills b ON bi.bill_id = b.id
                   WHERE b.invoice_no = ?"""
        items = self.db.fetch_all(query, (inv_no,))
        for row in self.item_tree.get_children():
            self.item_tree.delete(row)
        for item in items:
            self.item_tree.insert("", "end", values=(item[0], item[1], f"{item[2]:.2f}", f"{item[3]:.2f}"))


class InventoryApp:
    """Main application class for Inventory Management System."""
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Inventory Management System")
        self.root.geometry("900x600")
        self.db = DatabaseManager()
        self._build_dashboard()
        self._update_clock()

    def _build_dashboard(self):
        # Banner frame with image and title
        banner = ttk.Frame(self.root)
        banner.pack(pady=10)

        # Try to load an image (placeholder if missing)
        try:
            img = Image.open("inventory_logo.png")
            img = img.resize((100, 100), Image.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(img)
            ttk.Label(banner, image=self.logo_img).pack(side="left", padx=10)
        except Exception:
            # No image, just text
            pass

        ttk.Label(banner, text="Inventory Management System", font=("Helvetica", 24, "bold")).pack(side="left")

        # Clock
        self.clock_label = ttk.Label(self.root, text="", font=("Arial", 12))
        self.clock_label.pack(pady=5)

        # Dashboard buttons
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(pady=20)

        buttons = [
            ("Manage Employees", self._open_employees),
            ("Manage Suppliers", self._open_suppliers),
            ("Manage Categories", self._open_categories),
            ("Manage Products", self._open_products),
            ("Billing / New Invoice", self._open_billing),
            ("View Invoices", self._open_invoices)
        ]

        for idx, (text, cmd) in enumerate(buttons):
            btn = ttk.Button(btn_frame, text=text, command=cmd, width=20)
            btn.grid(row=idx//2, column=idx % 2, padx=10, pady=5)

        # Optional: exit button
        ttk.Button(self.root, text="Exit", command=self.root.quit).pack(pady=10)

    def _update_clock(self):
        now = datetime.datetime.now()
        self.clock_label.config(text=now.strftime("%A, %B %d, %Y  %I:%M:%S %p"))
        self.root.after(1000, self._update_clock)

    def _open_employees(self):
        EmployeeWindow(self.root, self.db)

    def _open_suppliers(self):
        SupplierWindow(self.root, self.db)

    def _open_categories(self):
        CategoryWindow(self.root, self.db)

    def _open_products(self):
        ProductWindow(self.root, self.db)

    def _open_billing(self):
        BillingWindow(self.root, self.db)

    def _open_invoices(self):
        InvoiceViewer(self.root, self.db)

    def run(self):
        self.root.mainloop()
        self.db.close()


if __name__ == "__main__":
    app = InventoryApp()
    app.run()