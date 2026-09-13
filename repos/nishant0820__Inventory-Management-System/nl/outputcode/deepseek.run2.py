import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Toplevel
from tkinter import PhotoImage
from PIL import Image, ImageTk
import sqlite3
import os
from datetime import datetime
import threading
import time


class DatabaseManager:
    def __init__(self, db_name='inventory.db'):
        self.conn = sqlite3.connect(db_name)
        self.cur = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        self.cur.executescript('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                address TEXT,
                designation TEXT,
                salary REAL
            );

            CREATE TABLE IF NOT EXISTS suppliers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT,
                email TEXT,
                address TEXT
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                supplier_id INTEGER,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
            );

            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_no TEXT NOT NULL UNIQUE,
                date_time TEXT NOT NULL,
                customer_name TEXT,
                total REAL NOT NULL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS bill_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
        ''')
        self.conn.commit()

    def execute_query(self, query, params=(), fetch=False):
        try:
            self.cur.execute(query, params)
            self.conn.commit()
            if fetch:
                return self.cur.fetchall()
            return True
        except Exception as e:
            raise e

    def fetch_all(self, table):
        return self.execute_query(f"SELECT * FROM {table}", fetch=True)

    def insert_employee(self, data):
        return self.execute_query('''INSERT INTO employees (name, email, phone, address, designation, salary)
                                    VALUES (?,?,?,?,?,?)''', data)

    def update_employee(self, eid, data):
        return self.execute_query('''UPDATE employees SET name=?, email=?, phone=?, address=?, designation=?, salary=?
                                    WHERE id=?''', (*data, eid))

    def delete_employee(self, eid):
        return self.execute_query('DELETE FROM employees WHERE id=?', (eid,))

    def insert_supplier(self, data):
        return self.execute_query('''INSERT INTO suppliers (name, contact, email, address) VALUES (?,?,?,?)''', data)

    def update_supplier(self, sid, data):
        return self.execute_query('''UPDATE suppliers SET name=?, contact=?, email=?, address=? WHERE id=?''', (*data, sid))

    def delete_supplier(self, sid):
        return self.execute_query('DELETE FROM suppliers WHERE id=?', (sid,))

    def insert_category(self, name):
        return self.execute_query('INSERT INTO categories (name) VALUES (?)', (name,))

    def update_category(self, cid, name):
        return self.execute_query('UPDATE categories SET name=? WHERE id=?', (name, cid))

    def delete_category(self, cid):
        return self.execute_query('DELETE FROM categories WHERE id=?', (cid,))

    def insert_product(self, data):
        return self.execute_query('''INSERT INTO products (name, category_id, price, quantity, supplier_id)
                                    VALUES (?,?,?,?,?)''', data)

    def update_product(self, pid, data):
        return self.execute_query('''UPDATE products SET name=?, category_id=?, price=?, quantity=?, supplier_id=?
                                    WHERE id=?''', (*data, pid))

    def delete_product(self, pid):
        return self.execute_query('DELETE FROM products WHERE id=?', (pid,))

    def get_next_invoice_no(self):
        today = datetime.now().strftime("%Y%m%d")
        self.cur.execute("SELECT MAX(invoice_no) FROM bills WHERE invoice_no LIKE ?", (f"INV-{today}%",))
        row = self.cur.fetchone()
        if row[0]:
            last_num = int(row[0].split('-')[-1])
            next_num = last_num + 1
        else:
            next_num = 1
        return f"INV-{today}-{next_num:04d}"

    def insert_bill(self, invoice_no, customer_name, total):
        date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return self.execute_query('''INSERT INTO bills (invoice_no, date_time, customer_name, total)
                                    VALUES (?,?,?,?)''', (invoice_no, date_time, customer_name, total))

    def insert_bill_item(self, bill_id, product_id, quantity, price):
        self.execute_query('''INSERT INTO bill_items (bill_id, product_id, quantity, price) VALUES (?,?,?,?)''',
                           (bill_id, product_id, quantity, price))
        # Update product quantity
        self.execute_query('UPDATE products SET quantity = quantity - ? WHERE id=?', (quantity, product_id))

    def get_all_bills(self):
        return self.fetch_all('bills')

    def get_bill_items(self, bill_id):
        self.cur.execute('''SELECT p.name, bi.quantity, bi.price FROM bill_items bi
                            JOIN products p ON bi.product_id = p.id
                            WHERE bi.bill_id=?''', (bill_id,))
        return self.cur.fetchall()

    def close(self):
        self.conn.close()


class Dashboard(tk.Tk):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.title("Inventory Management System")
        self.geometry("800x500")
        self.configure(bg='lightgray')

        # Load and display image
        try:
            img = Image.open("logo.png")
            img = img.resize((200, 100), Image.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(img)
            logo_label = tk.Label(self, image=self.logo_img, bg='lightgray')
            logo_label.pack(pady=10)
        except Exception:
            logo_label = tk.Label(self, text="INVENTORY SYSTEM", font=("Arial", 24, "bold"), bg='lightgray')
            logo_label.pack(pady=10)

        # Clock display
        self.clock_label = tk.Label(self, font=("Arial", 14), bg='lightgray')
        self.clock_label.pack(pady=5)
        self.update_clock()

        # Buttons for features
        button_frame = tk.Frame(self, bg='lightgray')
        button_frame.pack(pady=20)

        buttons_info = [
            ("Manage Employees", self.open_employee_window),
            ("Manage Suppliers", self.open_supplier_window),
            ("Manage Categories", self.open_category_window),
            ("Manage Products", self.open_product_window),
            ("Billing", self.open_billing_window),
            ("View Bills", self.open_bills_list_window)
        ]

        for text, cmd in buttons_info:
            btn = tk.Button(button_frame, text=text, width=20, height=2, command=cmd)
            btn.pack(side=tk.LEFT, padx=10)

    def update_clock(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.config(text=f"Current Time: {now}")
        self.after(1000, self.update_clock)

    def open_employee_window(self):
        EmployeeWindow(self, self.db)

    def open_supplier_window(self):
        SupplierWindow(self, self.db)

    def open_category_window(self):
        CategoryWindow(self, self.db)

    def open_product_window(self):
        ProductWindow(self, self.db)

    def open_billing_window(self):
        BillingWindow(self, self.db)

    def open_bills_list_window(self):
        BillsListWindow(self, self.db)


class BaseCRUDWindow(Toplevel):
    def __init__(self, parent, db, title, entity_name, columns, add_cmd, update_cmd, delete_cmd):
        super().__init__(parent)
        self.db = db
        self.title(title)
        self.geometry("700x500")
        self.columns = columns  # list of column names for treeview
        self.add_cmd = add_cmd
        self.update_cmd = update_cmd
        self.delete_cmd = delete_cmd

        self.create_widgets()
        self.refresh_treeview()

    def create_widgets(self):
        # Input frame
        self.inputs = {}
        input_frame = tk.LabelFrame(self, text="Details", padx=5, pady=5)
        input_frame.pack(fill="x", padx=10, pady=5)

        # Dynamically create entry fields based on columns (skip first 'ID' column)
        row = 0
        for i, col in enumerate(self.columns[1:]):  # skip ID column
            tk.Label(input_frame, text=col+":", width=15, anchor='w').grid(row=row, column=0, sticky='w')
            entry = tk.Entry(input_frame, width=30)
            entry.grid(row=row, column=1, pady=2)
            self.inputs[col] = entry
            row += 1

        # Buttons
        btn_frame = tk.Frame(input_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=5)
        tk.Button(btn_frame, text="Add", command=self.add_record).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update Selected", command=self.update_record).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete Selected", command=self.delete_record).pack(side=tk.LEFT, padx=5)

        # Treeview for listing
        tree_frame = tk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.tree = ttk.Treeview(tree_frame, columns=self.columns, show="headings", selectmode="browse")
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor='center')
        self.tree.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    def get_input_values(self):
        return tuple(entry.get() for entry in self.inputs.values())

    def clear_inputs(self):
        for entry in self.inputs.values():
            entry.delete(0, tk.END)

    def add_record(self):
        try:
            values = self.get_input_values()
            self.add_cmd(values)
            self.refresh_treeview()
            self.clear_inputs()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_record(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a record to update")
            return
        item = self.tree.item(selected)
        rec_id = item['values'][0]
        try:
            values = self.get_input_values()
            self.update_cmd(rec_id, values)
            self.refresh_treeview()
            self.clear_inputs()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_record(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a record to delete")
            return
        if messagebox.askyesno("Confirm", "Delete selected record?"):
            item = self.tree.item(selected)
            rec_id = item['values'][0]
            try:
                self.delete_cmd(rec_id)
                self.refresh_treeview()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected)
        values = item['values']
        # Populate input fields (skip ID)
        entries = list(self.inputs.values())
        for i, val in enumerate(values[1:]):
            if i < len(entries):
                entries[i].delete(0, tk.END)
                entries[i].insert(0, str(val))

    def refresh_treeview(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        try:
            data = self.fetch_data()
            for record in data:
                self.tree.insert("", "end", values=record)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch data: {e}")

    def fetch_data(self):
        # Override in subclasses to return all records
        raise NotImplementedError


class EmployeeWindow(BaseCRUDWindow):
    def __init__(self, parent, db):
        columns = ["ID", "Name", "Email", "Phone", "Address", "Designation", "Salary"]
        super().__init__(parent, db, "Employee Management", "Employee", columns,
                         self.add_emp, self.update_emp, self.delete_emp)
        # Override input fields ordering: we need to match columns order
        # Redefine layout to match columns: ID skipped, then Name, Email, Phone, Address, Designation, Salary
        # Our default creation assumes order of self.inputs dict (which is insertion order in Python 3.7+)
        # columns[1:] = ['Name','Email','Phone','Address','Designation','Salary'] -> correct
        # However, generic BaseCRUD uses columns order as presented. That's fine because we create inputs in that order.

    def fetch_data(self):
        return self.db.fetch_all('employees')

    def add_emp(self, values):
        self.db.insert_employee(values)

    def update_emp(self, eid, values):
        self.db.update_employee(eid, values)

    def delete_emp(self, eid):
        self.db.delete_employee(eid)


class SupplierWindow(BaseCRUDWindow):
    def __init__(self, parent, db):
        columns = ["ID", "Name", "Contact", "Email", "Address"]
        super().__init__(parent, db, "Supplier Management", "Supplier", columns,
                         self.add_sup, self.update_sup, self.delete_sup)

    def fetch_data(self):
        return self.db.fetch_all('suppliers')

    def add_sup(self, values):
        self.db.insert_supplier(values)

    def update_sup(self, sid, values):
        self.db.update_supplier(sid, values)

    def delete_sup(self, sid):
        self.db.delete_supplier(sid)


class CategoryWindow(BaseCRUDWindow):
    def __init__(self, parent, db):
        columns = ["ID", "Name"]
        super().__init__(parent, db, "Category Management", "Category", columns,
                         self.add_cat, self.update_cat, self.delete_cat)

    def fetch_data(self):
        return self.db.fetch_all('categories')

    def add_cat(self, values):
        # Only one value: name
        name = values[0]  # values is a tuple (name,)
        if not name:
            raise ValueError("Category name cannot be empty")
        self.db.insert_category(name)

    def update_cat(self, cid, values):
        name = values[0]
        self.db.update_category(cid, name)

    def delete_cat(self, cid):
        self.db.delete_category(cid)


class ProductWindow(BaseCRUDWindow):
    def __init__(self, parent, db):
        columns = ["ID", "Name", "Category ID", "Price", "Quantity", "Supplier ID"]
        super().__init__(parent, db, "Product Management", "Product", columns,
                         self.add_prod, self.update_prod, self.delete_prod)

    def fetch_data(self):
        return self.db.fetch_all('products')

    def add_prod(self, values):
        # values: (name, category_id, price, quantity, supplier_id)
        name, cat_id, price, qty, sup_id = values
        if not name:
            raise ValueError("Product name required")
        try:
            price = float(price)
            qty = int(qty)
            cat_id = int(cat_id)
            sup_id = int(sup_id) if sup_id else None
        except ValueError:
            raise ValueError("Invalid numeric values")
        self.db.insert_product((name, cat_id, price, qty, sup_id))

    def update_prod(self, pid, values):
        name, cat_id, price, qty, sup_id = values
        try:
            price = float(price)
            qty = int(qty)
            cat_id = int(cat_id)
            sup_id = int(sup_id) if sup_id else None
        except ValueError:
            raise ValueError("Invalid numeric values")
        self.db.update_product(pid, (name, cat_id, price, qty, sup_id))

    def delete_prod(self, pid):
        self.db.delete_product(pid)


class BillingWindow(Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.title("Billing")
        self.geometry("800x600")
        self.bill_items = []  # list of (product_id, product_name, qty, price, subtotal)
        self.total_var = tk.DoubleVar(value=0.0)
        self.customer_var = tk.StringVar()
        self.invoice_no = self.db.get_next_invoice_no()

        self.create_widgets()

    def create_widgets(self):
        # Top section: Invoice info
        info_frame = tk.Frame(self)
        info_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(info_frame, text="Invoice No:").grid(row=0, column=0, sticky='w')
        tk.Label(info_frame, text=self.invoice_no, font=("Arial", 12, "bold")).grid(row=0, column=1, sticky='w')
        tk.Label(info_frame, text="Customer:").grid(row=1, column=0, sticky='w')
        tk.Entry(info_frame, textvariable=self.customer_var).grid(row=1, column=1, sticky='we')

        # Product selection frame
        select_frame = tk.LabelFrame(self, text="Add Product", padx=5, pady=5)
        select_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(select_frame, text="Product:").grid(row=0, column=0)
        self.product_combo = ttk.Combobox(select_frame, state="readonly")
        self.product_combo.grid(row=0, column=1, padx=5)
        self.load_products()

        tk.Label(select_frame, text="Quantity:").grid(row=0, column=2)
        self.qty_entry = tk.Entry(select_frame, width=10)
        self.qty_entry.grid(row=0, column=3, padx=5)

        tk.Button(select_frame, text="Add to Bill", command=self.add_item).grid(row=0, column=4, padx=5)

        # Bill items treeview
        tree_frame = tk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        columns = ("Product ID", "Product Name", "Qty", "Price", "Subtotal")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor='center')
        self.tree.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill="y")

        # Bottom frame: total and buttons
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(bottom_frame, text="Total:", font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=10)
        tk.Label(bottom_frame, textvariable=self.total_var, font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        tk.Button(bottom_frame, text="Generate Invoice", command=self.generate_invoice, bg="green", fg="white").pack(side=tk.RIGHT, padx=10)
        tk.Button(bottom_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=10)

    def load_products(self):
        products = self.db.fetch_all('products')
        self.product_map = {f"{p[1]} (ID:{p[0]})": p for p in products}  # name (ID) -> row
        self.product_combo['values'] = list(self.product_map.keys())
        if self.product_map:
            self.product_combo.current(0)

    def add_item(self):
        prod_key = self.product_combo.get()
        if not prod_key:
            messagebox.showwarning("Select Product", "Please select a product")
            return
        qty_str = self.qty_entry.get()
        try:
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Quantity", "Quantity must be a positive integer")
            return

        product = self.product_map[prod_key]
        if product[4] < qty:  # index 4 is quantity
            messagebox.showerror("Insufficient Stock", f"Only {product[4]} units available")
            return
        price = product[3]  # index 3 is price
        subtotal = price * qty
        item = (product[0], product[1], qty, price, subtotal)
        self.bill_items.append(item)
        self.qty_entry.delete(0, tk.END)
        self.update_treeview()
        self.calculate_total()

    def update_treeview(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for item in self.bill_items:
            self.tree.insert("", "end", values=(item[0], item[1], item[2], f"{item[3]:.2f}", f"{item[4]:.2f}"))

    def calculate_total(self):
        total = sum(item[4] for item in self.bill_items)
        self.total_var.set(f"{total:.2f}")

    def generate_invoice(self):
        if not self.bill_items:
            messagebox.showwarning("Empty Bill", "Add at least one product")
            return
        customer = self.customer_var.get().strip() or "Walk-in Customer"
        total = sum(item[4] for item in self.bill_items)
        try:
            self.db.insert_bill(self.invoice_no, customer, total)
            bill_id = self.db.cur.lastrowid
            for item in self.bill_items:
                # item: (product_id, product_name, qty, price, subtotal)
                self.db.insert_bill_item(bill_id, item[0], item[2], item[3])
            messagebox.showinfo("Success", f"Invoice {self.invoice_no} generated successfully")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Could not save invoice: {e}")


class BillsListWindow(Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        self.title("Bills List")
        self.geometry("600x400")
        self.create_widgets()
        self.refresh_list()

    def create_widgets(self):
        tree_frame = tk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        columns = ("ID", "Invoice No", "Date", "Customer", "Total")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor='center')
        self.tree.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        tk.Button(self, text="View Details", command=self.view_details).pack(pady=5)

    def refresh_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        bills = self.db.get_all_bills()
        for bill in bills:
            self.tree.insert("", "end", values=bill)

    def view_details(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a bill")
            return
        bill = self.tree.item(selected)['values']
        bill_id = bill[0]
        invoice_no = bill[1]
        items = self.db.get_bill_items(bill_id)
        if not items:
            messagebox.showinfo("No Items", "This bill has no items (data issue)")
            return
        detail_str = f"Invoice: {invoice_no}\nCustomer: {bill[3]}\nDate: {bill[2]}\n\nItems:\n"
        for item in items:
            detail_str += f"{item[0]} - Qty: {item[1]} x ${item[2]:.2f} = ${item[1]*item[2]:.2f}\n"
        detail_str += f"\nTotal: ${bill[4]:.2f}"
        messagebox.showinfo("Bill Details", detail_str)


def main():
    db = DatabaseManager()
    app = Dashboard(db)
    app.protocol("WM_DELETE_WINDOW", lambda: (db.close(), app.destroy()))
    app.mainloop()


if __name__ == "__main__":
    main()