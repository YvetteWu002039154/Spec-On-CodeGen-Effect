import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Text, Entry, Label, Toplevel, Listbox, StringVar, PhotoImage
from typing import List, Optional, Union, Any
import sqlite3
import datetime
import os

# ================= DATABASE SETUP =================
DB_NAME = "ims.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        """CREATE TABLE IF NOT EXISTS category (
            cat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS supplier (
            sup_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice TEXT,
            name TEXT,
            contact TEXT,
            description TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS employee (
            emp_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            dob TEXT,
            doj TEXT,
            contact TEXT,
            email TEXT,
            gender TEXT,
            salary REAL,
            password TEXT,
            user_type TEXT,
            address TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS product (
            pid INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            supplier TEXT,
            price REAL,
            qty INTEGER,
            status TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS sales (
            invoice TEXT PRIMARY KEY,
            bill_text TEXT,
            date TEXT,
            total REAL
        )"""
    )
    conn.commit()
    conn.close()


init_db()


# ================= CATEGORY CLASS =================
class categoryClass:
    def __init__(self, root):
        self.root = root
        self.var_cat_id: StringVar = tk.StringVar()
        self.var_name: StringVar = tk.StringVar()

        # Treeview
        self.CategoryTable: ttk.Treeview = ttk.Treeview(
            root, columns=("cat_id", "name"), show="headings", height=8
        )
        self.CategoryTable.heading("cat_id", text="Cat ID")
        self.CategoryTable.heading("name", text="Name")
        self.CategoryTable.column("cat_id", width=100)
        self.CategoryTable.column("name", width=200)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)
        self.CategoryTable.pack(fill=tk.BOTH, expand=True)

        # Dummy images (PhotoImage)
        self.im1: Optional[PhotoImage] = None
        self.im2: Optional[PhotoImage] = None
        self.lbl_im1: Label = tk.Label(root)
        self.lbl_im2: Label = tk.Label(root)

        # Buttons
        btn_frame = tk.Frame(root)
        tk.Button(btn_frame, text="Add", command=self.add).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Delete", command=self.delete).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Clear", command=self.clear).pack(side=tk.LEFT, padx=2)
        btn_frame.pack()

        self.show()

    def add(self):
        name = self.var_name.get()
        if not name.strip():
            messagebox.showerror("Error", "Category name required")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("INSERT INTO category (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        self.clear()
        self.show()

    def delete(self):
        cat_id = self.var_cat_id.get()
        if not cat_id:
            messagebox.showerror("Error", "Select a category to delete")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM category WHERE cat_id=?", (cat_id,))
        conn.commit()
        conn.close()
        self.clear()
        self.show()

    def clear(self):
        self.var_cat_id.set("")
        self.var_name.set("")

    def get_data(self, ev):
        selected = self.CategoryTable.focus()
        if selected:
            values = self.CategoryTable.item(selected, "values")
            if values:
                self.var_cat_id.set(values[0])
                self.var_name.set(values[1])

    def show(self):
        for row in self.CategoryTable.get_children():
            self.CategoryTable.delete(row)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT * FROM category")
        rows = cur.fetchall()
        for row in rows:
            self.CategoryTable.insert("", tk.END, values=row)
        conn.close()


# ================= EMPLOYEE CLASS =================
class employeeClass:
    def __init__(self, root):
        self.root = root
        self.var_emp_id: StringVar = tk.StringVar()
        self.var_name: StringVar = tk.StringVar()
        self.var_dob: StringVar = tk.StringVar()
        self.var_doj: StringVar = tk.StringVar()
        self.var_contact: StringVar = tk.StringVar()
        self.var_email: StringVar = tk.StringVar()
        self.var_gender: StringVar = tk.StringVar()
        self.var_salary: StringVar = tk.StringVar()
        self.var_pass: StringVar = tk.StringVar()
        self.var_utype: StringVar = tk.StringVar()
        self.var_searchby: StringVar = tk.StringVar()
        self.var_searchtxt: StringVar = tk.StringVar()
        self.txt_address: Text = tk.Text(root, height=3, width=30)

        # Treeview
        self.EmployeeTable: ttk.Treeview = ttk.Treeview(
            root, columns=("emp_id", "name", "contact", "email", "salary"), show="headings"
        )
        self.EmployeeTable.heading("emp_id", text="ID")
        self.EmployeeTable.heading("name", text="Name")
        self.EmployeeTable.heading("contact", text="Contact")
        self.EmployeeTable.heading("email", text="Email")
        self.EmployeeTable.heading("salary", text="Salary")
        self.EmployeeTable.column("emp_id", width=60)
        self.EmployeeTable.column("name", width=120)
        self.EmployeeTable.column("contact", width=100)
        self.EmployeeTable.column("email", width=150)
        self.EmployeeTable.column("salary", width=80)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)
        self.EmployeeTable.pack(fill=tk.BOTH, expand=True)

        # Buttons
        btn_frame = tk.Frame(root)
        tk.Button(btn_frame, text="Add", command=self.add).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Update", command=self.update).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Delete", command=self.delete).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Clear", command=self.clear).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Search", command=self.search).pack(side=tk.LEFT, padx=2)
        btn_frame.pack()

        self.show()

    def add(self):
        # Validation
        try:
            salary = float(self.var_salary.get())
            if salary < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid salary")
            return
        if not self.var_name.get().strip():
            messagebox.showerror("Error", "Name required")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO employee (name, dob, doj, contact, email, gender, salary, password, user_type, address)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                self.var_name.get(),
                self.var_dob.get(),
                self.var_doj.get(),
                self.var_contact.get(),
                self.var_email.get(),
                self.var_gender.get(),
                salary,
                self.var_pass.get(),
                self.var_utype.get(),
                self.txt_address.get("1.0", tk.END).strip(),
            ),
        )
        conn.commit()
        conn.close()
        self.clear()
        self.show()

    def update(self):
        if not self.var_emp_id.get():
            messagebox.showerror("Error", "Select an employee to update")
            return
        try:
            salary = float(self.var_salary.get())
            if salary < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid salary")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            """UPDATE employee SET name=?, dob=?, doj=?, contact=?, email=?, gender=?, salary=?, password=?, user_type=?, address=?
               WHERE emp_id=?""",
            (
                self.var_name.get(),
                self.var_dob.get(),
                self.var_doj.get(),
                self.var_contact.get(),
                self.var_email.get(),
                self.var_gender.get(),
                salary,
                self.var_pass.get(),
                self.var_utype.get(),
                self.txt_address.get("1.0", tk.END).strip(),
                self.var_emp_id.get(),
            ),
        )
        conn.commit()
        conn.close()
        self.clear()
        self.show()

    def delete(self):
        emp_id = self.var_emp_id.get()
        if not emp_id:
            messagebox.showerror("Error", "Select an employee to delete")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM employee WHERE emp_id=?", (emp_id,))
        conn.commit()
        conn.close()
        self.clear()
        self.show()

    def clear(self):
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_contact.set("")
        self.var_email.set("")
        self.var_gender.set("")
        self.var_salary.set("")
        self.var_pass.set("")
        self.var_utype.set("")
        self.txt_address.delete("1.0", tk.END)
        self.var_searchby.set("")
        self.var_searchtxt.set("")

    def get_data(self, ev):
        selected = self.EmployeeTable.focus()
        if selected:
            values = self.EmployeeTable.item(selected, "values")
            if values and len(values) >= 5:
                self.var_emp_id.set(values[0])
                # Fetch full data from DB
                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()
                cur.execute("SELECT * FROM employee WHERE emp_id=?", (values[0],))
                row = cur.fetchone()
                conn.close()
                if row:
                    self.var_name.set(row[1])
                    self.var_dob.set(row[2])
                    self.var_doj.set(row[3])
                    self.var_contact.set(row[4])
                    self.var_email.set(row[5])
                    self.var_gender.set(row[6])
                    self.var_salary.set(str(row[7]))
                    self.var_pass.set(row[8])
                    self.var_utype.set(row[9])
                    self.txt_address.delete("1.0", tk.END)
                    self.txt_address.insert(tk.END, row[10])

    def show(self):
        for row in self.EmployeeTable.get_children():
            self.EmployeeTable.delete(row)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT emp_id, name, contact, email, salary FROM employee")
        rows = cur.fetchall()
        for row in rows:
            self.EmployeeTable.insert("", tk.END, values=row)
        conn.close()

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get()
        if not by or not txt:
            messagebox.showerror("Error", "Select search field and enter text")
            return
        column_map = {
            "Name": "name",
            "Email": "email",
            "Contact": "contact",
        }
        db_col = column_map.get(by, "name")
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            f"SELECT emp_id, name, contact, email, salary FROM employee WHERE {db_col} LIKE ?",
            (f"%{txt}%",),
        )
        rows = cur.fetchall()
        conn.close()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for row in rows:
            self.EmployeeTable.insert("", tk.END, values=row)


# ================= SUPPLIER CLASS =================
class supplierClass:
    def __init__(self, root):
        self.root = root
        self.var_sup_invoice: StringVar = tk.StringVar()
        self.var_name: StringVar = tk.StringVar()
        self.var_contact: StringVar = tk.StringVar()
        self.txt_desc: Text = tk.Text(root, height=3, width=30)
        self.var_searchby: StringVar = tk.StringVar()
        self.var_searchtxt: StringVar = tk.StringVar()

        self.SupplierTable: ttk.Treeview = ttk.Treeview(
            root, columns=("sup_id", "invoice", "name", "contact"), show="headings"
        )
        self.SupplierTable.heading("sup_id", text="Sup ID")
        self.SupplierTable.heading("invoice", text="Invoice")
        self.SupplierTable.heading("name", text="Name")
        self.SupplierTable.heading("contact", text="Contact")
        self.SupplierTable.column("sup_id", width=60)
        self.SupplierTable.column("invoice", width=100)
        self.SupplierTable.column("name", width=120)
        self.SupplierTable.column("contact", width=100)
        self.SupplierTable.bind("<ButtonRelease-1>", self.get_data)
        self.SupplierTable.pack(fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(root)
        tk.Button(btn_frame, text="Add", command=self.add).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Update", command=self.update).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Delete", command=self.delete).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Clear", command=self.clear).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Search", command=self.search).pack(side=tk.LEFT, padx=2)
        btn_frame.pack()

        self.show()

    def add(self):
        if not self.var_name.get().strip():
            messagebox.showerror("Error", "Supplier name required")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO supplier (invoice, name, contact, description) VALUES (?,?,?,?)",
            (
                self.var_sup_invoice.get(),
                self.var_name.get(),
                self.var_contact.get(),
                self.txt_desc.get("1.0", tk.END).strip(),
            ),
        )
        conn.commit()
        conn.close()
        self.clear()
        self.show()

    def update(self):
        sup_id = self.var_sup_invoice.get()  # Using invoice as identifier? Better use hidden ID.
        # For update, we need to know which row is selected. We'll fetch the sup_id from selected row.
        selected = self.SupplierTable.focus()
        if not selected:
            messagebox.showerror("Error", "Select a supplier to update")
            return
        values = self.SupplierTable.item(selected, "values")
        if values:
            sup_id = values[0]
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute(
                "UPDATE supplier SET invoice=?, name=?, contact=?, description=? WHERE sup_id=?",
                (
                    self.var_sup_invoice.get(),
                    self.var_name.get(),
                    self.var_contact.get(),
                    self.txt_desc.get("1.0", tk.END).strip(),
                    sup_id,
                ),
            )
            conn.commit()
            conn.close()
            self.clear()
            self.show()

    def delete(self):
        selected = self.SupplierTable.focus()
        if not selected:
            messagebox.showerror("Error", "Select a supplier to delete")
            return
        values = self.SupplierTable.item(selected, "values")
        if values:
            sup_id = values[0]
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("DELETE FROM supplier WHERE sup_id=?", (sup_id,))
            conn.commit()
            conn.close()
            self.clear()
            self.show()

    def clear(self):
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete("1.0", tk.END)
        self.var_searchby.set("")
        self.var_searchtxt.set("")

    def get_data(self, ev):
        selected = self.SupplierTable.focus()
        if selected:
            values = self.SupplierTable.item(selected, "values")
            if values and len(values) >= 4:
                self.var_sup_invoice.set(values[1])
                self.var_name.set(values[2])
                self.var_contact.set(values[3])
                # fetch description
                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()
                cur.execute("SELECT description FROM supplier WHERE sup_id=?", (values[0],))
                desc = cur.fetchone()
                conn.close()
                self.txt_desc.delete("1.0", tk.END)
                if desc:
                    self.txt_desc.insert(tk.END, desc[0])

    def show(self):
        for row in self.SupplierTable.get_children():
            self.SupplierTable.delete(row)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT sup_id, invoice, name, contact FROM supplier")
        rows = cur.fetchall()
        for row in rows:
            self.SupplierTable.insert("", tk.END, values=row)
        conn.close()

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get()
        if not by or not txt:
            messagebox.showerror("Error", "Select search field and enter text")
            return
        column_map = {"Name": "name", "Invoice": "invoice", "Contact": "contact"}
        db_col = column_map.get(by, "name")
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            f"SELECT sup_id, invoice, name, contact FROM supplier WHERE {db_col} LIKE ?",
            (f"%{txt}%",),
        )
        rows = cur.fetchall()
        conn.close()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert("", tk.END, values=row)


# ================= PRODUCT CLASS =================
class productClass:
    def __init__(self, root):
        self.root = root
        self.var_pid: StringVar = tk.StringVar()
        self.var_name: StringVar = tk.StringVar()
        self.var_cat: StringVar = tk.StringVar()
        self.var_sup: StringVar = tk.StringVar()
        self.var_price: StringVar = tk.StringVar()
        self.var_qty: StringVar = tk.StringVar()
        self.var_status: StringVar = tk.StringVar()
        self.var_searchby: StringVar = tk.StringVar()
        self.var_searchtxt: StringVar = tk.StringVar()
        self.cat_list: List[str] = []
        self.sup_list: List[str] = []

        self.ProductTable: ttk.Treeview = ttk.Treeview(
            root,
            columns=("pid", "name", "category", "supplier", "price", "qty", "status"),
            show="headings",
        )
        self.ProductTable.heading("pid", text="PID")
        self.ProductTable.heading("name", text="Name")
        self.ProductTable.heading("category", text="Category")
        self.ProductTable.heading("supplier", text="Supplier")
        self.ProductTable.heading("price", text="Price")
        self.ProductTable.heading("qty", text="Qty")
        self.ProductTable.heading("status", text="Status")
        for col in ("pid", "name", "category", "supplier", "price", "qty", "status"):
            self.ProductTable.column(col, width=80)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)
        self.ProductTable.pack(fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(root)
        tk.Button(btn_frame, text="Add", command=self.add).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Update", command=self.update).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Delete", command=self.delete).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Clear", command=self.clear).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Search", command=self.search).pack(side=tk.LEFT, padx=2)
        btn_frame.pack()

        self.fetch_cat_sup()
        self.show()

    def fetch_cat_sup(self):
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT name FROM category")
        self.cat_list = [row[0] for row in cur.fetchall()]
        cur.execute("SELECT name FROM supplier")
        self.sup_list = [row[0] for row in cur.fetchall()]
        conn.close()

    def add(self):
        try:
            price = float(self.var_price.get())
            qty = int(self.var_qty.get())
            if price < 0 or qty < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid price or quantity (must be non-negative)")
            return
        if not self.var_name.get().strip():
            messagebox.showerror("Error", "Product name required")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO product (name, category, supplier, price, qty, status) VALUES (?,?,?,?,?,?)",
            (
                self.var_name.get(),
                self.var_cat.get(),
                self.var_sup.get(),
                price,
                qty,
                self.var_status.get(),
            ),
        )
        conn.commit()
        conn.close()
        self.clear()
        self.show()

    def update(self):
        pid = self.var_pid.get()
        if not pid:
            messagebox.showerror("Error", "Select a product to update")
            return
        try:
            price = float(self.var_price.get())
            qty = int(self.var_qty.get())
            if price < 0 or qty < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid price or quantity")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            "UPDATE product SET name=?, category=?, supplier=?, price=?, qty=?, status=? WHERE pid=?",
            (
                self.var_name.get(),
                self.var_cat.get(),
                self.var_sup.get(),
                price,
                qty,
                self.var_status.get(),
                pid,
            ),
        )
        conn.commit()
        conn.close()
        self.clear()
        self.show()

    def delete(self):
        pid = self.var_pid.get()
        if not pid:
            messagebox.showerror("Error", "Select a product to delete")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("DELETE FROM product WHERE pid=?", (pid,))
        conn.commit()
        conn.close()
        self.clear()
        self.show()

    def clear(self):
        self.var_pid.set("")
        self.var_name.set("")
        self.var_cat.set("")
        self.var_sup.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("")
        self.var_searchby.set("")
        self.var_searchtxt.set("")

    def get_data(self, ev):
        selected = self.ProductTable.focus()
        if selected:
            values = self.ProductTable.item(selected, "values")
            if values and len(values) >= 7:
                self.var_pid.set(values[0])
                self.var_name.set(values[1])
                self.var_cat.set(values[2])
                self.var_sup.set(values[3])
                self.var_price.set(values[4])
                self.var_qty.set(values[5])
                self.var_status.set(values[6])

    def show(self):
        for row in self.ProductTable.get_children():
            self.ProductTable.delete(row)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT pid, name, category, supplier, price, qty, status FROM product")
        rows = cur.fetchall()
        for row in rows:
            self.ProductTable.insert("", tk.END, values=row)
        conn.close()

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get()
        if not by or not txt:
            messagebox.showerror("Error", "Select search field and enter text")
            return
        column_map = {
            "Name": "name",
            "Category": "category",
            "Supplier": "supplier",
            "Status": "status",
        }
        db_col = column_map.get(by, "name")
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            f"SELECT pid, name, category, supplier, price, qty, status FROM product WHERE {db_col} LIKE ?",
            (f"%{txt}%",),
        )
        rows = cur.fetchall()
        conn.close()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for row in rows:
            self.ProductTable.insert("", tk.END, values=row)


# ================= SALES CLASS =================
class salesClass:
    def __init__(self, root):
        self.root = root
        self.var_invoice: StringVar = tk.StringVar()
        self.Sales_List: Listbox = tk.Listbox(root, height=15)
        self.bill_area: Text = tk.Text(root, height=10, width=40)
        self.bill_photo: Optional[PhotoImage] = None
        self.blll_list: List[Any] = []  # list of invoice records

        self.Sales_List.bind("<ButtonRelease-1>", self.get_data)
        self.Sales_List.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.bill_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        btn_frame = tk.Frame(root)
        tk.Button(btn_frame, text="Search", command=self.search).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Clear", command=self.clear).pack(side=tk.LEFT, padx=2)
        btn_frame.pack(side=tk.BOTTOM)

        self.show()

    def clear(self):
        self.var_invoice.set("")
        self.bill_area.delete("1.0", tk.END)

    def get_data(self, ev):
        selection = self.Sales_List.curselection()
        if selection:
            index = selection[0]
            if index < len(self.blll_list):
                inv = self.blll_list[index][0]
                self.var_invoice.set(inv)
                # Show bill details
                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()
                cur.execute("SELECT bill_text, date, total FROM sales WHERE invoice=?", (inv,))
                row = cur.fetchone()
                conn.close()
                self.bill_area.delete("1.0", tk.END)
                if row:
                    bill_text = f"Invoice: {inv}\nDate: {row[1]}\nTotal: {row[2]}\n\n{row[0]}"
                    self.bill_area.insert(tk.END, bill_text)

    def show(self):
        self.Sales_List.delete(0, tk.END)
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT invoice, date, total FROM sales ORDER BY date DESC")
        self.blll_list = cur.fetchall()
        conn.close()
        for row in self.blll_list:
            self.Sales_List.insert(tk.END, f"{row[0]} ({row[1]})")

    def search(self):
        inv = self.var_invoice.get()
        if not inv:
            self.show()
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT invoice, date, total FROM sales WHERE invoice LIKE ?", (f"%{inv}%",))
        rows = cur.fetchall()
        conn.close()
        self.blll_list = rows
        self.Sales_List.delete(0, tk.END)
        for row in rows:
            self.Sales_List.insert(tk.END, f"{row[0]} ({row[1]})")


# ================= BILLING CLASS =================
class billClass:
    def __init__(self, root):
        self.root = root
        self.var_pid: StringVar = tk.StringVar()
        self.var_pname: StringVar = tk.StringVar()
        self.var_price: StringVar = tk.StringVar()
        self.var_qty: StringVar = tk.StringVar()
        self.var_stock: StringVar = tk.StringVar()
        self.var_cname: StringVar = tk.StringVar()
        self.var_contact: StringVar = tk.StringVar()
        self.var_search: StringVar = tk.StringVar()
        self.var_cal_input: StringVar = tk.StringVar()
        self.txt_cal_input: Entry = tk.Entry(root, textvariable=self.var_cal_input)
        self.txt_bill_area: Text = tk.Text(root, height=15, width=60)
        self.chk_print: int = 0
        self.invoice: Optional[str] = None
        self.bill_amnt: int = 0
        self.net_pay: float = 0.0
        self.discount: float = 0.0
        self.siscount: int = 0  # typo, maybe meant discount?
        self.cart_list: List[tuple] = []  # (pid, name, price, qty, total)
        self.product_Table: ttk.Treeview = ttk.Treeview(
            root, columns=("pid", "name", "price", "qty"), show="headings"
        )
        self.product_Table.heading("pid", text="PID")
        self.product_Table.heading("name", text="Name")
        self.product_Table.heading("price", text="Price")
        self.product_Table.heading("qty", text="Qty")
        self.product_Table.column("pid", width=60)
        self.product_Table.column("name", width=120)
        self.product_Table.column("price", width=80)
        self.product_Table.column("qty", width=60)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)
        self.product_Table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.CartTable: ttk.Treeview = ttk.Treeview(
            root, columns=("pid", "name", "price", "qty", "total"), show="headings"
        )
        self.CartTable.heading("pid", text="PID")
        self.CartTable.heading("name", text="Name")
        self.CartTable.heading("price", text="Price")
        self.CartTable.heading("qty", text="Qty")
        self.CartTable.heading("total", text="Total")
        self.CartTable.column("pid", width=60)
        self.CartTable.column("name", width=120)
        self.CartTable.column("price", width=80)
        self.CartTable.column("qty", width=60)
        self.CartTable.column("total", width=80)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)
        self.CartTable.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Labels
        self.lbl_clock: Label = tk.Label(root, text="")
        self.lbl_clock.pack()
        self.lbl_amnt: Label = tk.Label(root, text="Bill Amount: 0")
        self.lbl_amnt.pack()
        self.lbl_discount: Label = tk.Label(root, text="Discount: 0%")
        self.lbl_discount.pack()
        self.lbl_net_pay: Label = tk.Label(root, text="Net Pay: 0")
        self.lbl_net_pay.pack()
        self.lbl_inStock: Label = tk.Label(root, text="")
        self.lbl_inStock.pack()

        self.cartTitle: Label = tk.Label(root, text="Cart", font=("Arial", 12, "bold"))
        self.cartTitle.pack()
        self.icon_title: Optional[PhotoImage] = None

        # Buttons
        btn_frame = tk.Frame(root)
        tk.Button(btn_frame, text="Add to Cart", command=self.add_update_cart).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Clear Cart", command=self.clear_cart).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Generate Bill", command=self.generate_bill).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Print Bill", command=self.print_bill).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Clear Calculator", command=self.clear_cal).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Search", command=self.search).pack(side=tk.LEFT, padx=2)
        btn_frame.pack()

        # Calculator entry
        calc_frame = tk.Frame(root)
        tk.Label(calc_frame, text="Calc:").pack(side=tk.LEFT)
        self.txt_cal_input.pack(side=tk.LEFT)
        for num in range(10):
            tk.Button(calc_frame, text=str(num), command=lambda n=num: self.get_input(n)).pack(side=tk.LEFT, padx=1)
        tk.Button(calc_frame, text="+", command=lambda: self.get_input("+")).pack(side=tk.LEFT)
        tk.Button(calc_frame, text="-", command=lambda: self.get_input("-")).pack(side=tk.LEFT)
        tk.Button(calc_frame, text="=", command=self.perform_cal).pack(side=tk.LEFT)
        calc_frame.pack()

        self.show()
        self.update_date_time()

    def add_update_cart(self):
        pid = self.var_pid.get()
        if not pid:
            messagebox.showerror("Error", "Select a product first")
            return
        try:
            qty = int(self.var_qty.get())
            price = float(self.var_price.get())
            stock = int(self.var_stock.get())
            if qty <= 0 or qty > stock:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity or stock insufficient")
            return
        # Check if already in cart
        for i, item in enumerate(self.cart_list):
            if item[0] == pid:
                # Update qty
                new_qty = item[3] + qty
                if new_qty > stock:
                    messagebox.showerror("Error", "Stock limit exceeded")
                    return
                self.cart_list[i] = (pid, item[1], price, new_qty, round(new_qty * price, 2))
                self.show_cart()
                self.bill_update()
                return
        self.cart_list.append((pid, self.var_pname.get(), price, qty, round(qty * price, 2)))
        self.show_cart()
        self.bill_update()

    def bill_update(self):
        total = sum(item[4] for item in self.cart_list)
        self.bill_amnt = total
        self.lbl_amnt.config(text=f"Bill Amount: {total}")
        self.calculate_net()

    def calculate_net(self):
        # Apply discount if any (e.g., from calculator or entry)
        disc_percent = self.discount
        net = self.bill_amnt - (self.bill_amnt * disc_percent / 100)
        self.net_pay = round(net, 2)
        self.lbl_net_pay.config(text=f"Net Pay: {self.net_pay}")

    def clear_all(self):
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")
        self.var_cname.set("")
        self.var_contact.set("")
        self.var_search.set("")

    def clear_cart(self):
        self.cart_list = []
        self.show_cart()
        self.bill_update()
        self.clear_all()

    def clear_cal(self):
        self.var_cal_input.set("")

    def get_data(self, ev):
        selected = self.product_Table.focus()
        if selected:
            values = self.product_Table.item(selected, "values")
            if values and len(values) >= 4:
                pid = values[0]
                self.var_pid.set(pid)
                self.var_pname.set(values[1])
                self.var_price.set(values[2])
                # Fetch stock from DB
                conn = sqlite3.connect(DB_NAME)
                cur = conn.cursor()
                cur.execute("SELECT qty FROM product WHERE pid=?", (pid,))
                row = cur.fetchone()
                conn.close()
                stock = row[0] if row else 0
                self.var_stock.set(str(stock))
                self.lbl_inStock.config(text=f"In Stock: {stock}")

    def get_data_cart(self, ev):
        pass  # Not needed for cart interaction

    def get_input(self, num):
        current = self.var_cal_input.get()
        self.var_cal_input.set(current + str(num))

    def perform_cal(self):
        expr = self.var_cal_input.get()
        try:
            result = eval(expr)  # safe in controlled environment
            self.var_cal_input.set(str(result))
        except Exception:
            messagebox.showerror("Error", "Invalid Expression")
            self.var_cal_input.set("")

    def search(self):
        txt = self.var_search.get()
        if not txt:
            messagebox.showerror("Error", "Enter search text")
            return
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            "SELECT pid, name, price, qty FROM product WHERE name LIKE ? OR pid LIKE ?",
            (f"%{txt}%", f"%{txt}%"),
        )
        rows = cur.fetchall()
        conn.close()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", tk.END, values=(row[0], row[1], row[2], row[3]))

    def show(self):
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute("SELECT pid, name, price, qty FROM product WHERE status='Active'")
        rows = cur.fetchall()
        conn.close()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", tk.END, values=row)

    def show_cart(self):
        self.CartTable.delete(*self.CartTable.get_children())
        for item in self.cart_list:
            self.CartTable.insert("", tk.END, values=item)

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty")
            return
        # Generate invoice number
        inv = f"INV-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        # Build bill text
        bill_lines = [f"Invoice: {inv}"]
        bill_lines.append(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if self.var_cname.get():
            bill_lines.append(f"Customer: {self.var_cname.get()}")
        if self.var_contact.get():
            bill_lines.append(f"Contact: {self.var_contact.get()}")
        bill_lines.append("\n--- Bill Details ---")
        for item in self.cart_list:
            bill_lines.append(f"{item[1]} x {item[3]} @ {item[2]} = {item[4]}")
        bill_lines.append(f"\nTotal: {self.bill_amnt}")
        bill_lines.append(f"Discount: {self.discount}%")
        net = self.net_pay
        bill_lines.append(f"Net Pay: {net}")
        bill_text = "\n".join(bill_lines)
        self.txt_bill_area.delete("1.0", tk.END)
        self.txt_bill_area.insert(tk.END, bill_text)
        self.invoice = inv
        # Save to sales table
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sales (invoice, bill_text, date, total) VALUES (?,?,?,?)",
            (inv, bill_text, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), net),
        )
        conn.commit()
        conn.close()
        # Update stock
        for item in self.cart_list:
            pid = item[0]
            qty_sold = item[3]
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            cur.execute("UPDATE product SET qty = qty - ? WHERE pid=?", (qty_sold, pid))
            conn.commit()
            conn.close()
        self.chk_print = 1
        messagebox.showinfo("Success", f"Bill Generated: {inv}")

    def print_bill(self):
        if self.chk_print == 0:
            messagebox.showerror("Error", "Generate bill first")
            return
        # For simplicity, just show message or save to file
        bill_text = self.txt_bill_area.get("1.0", tk.END).strip()
        try:
            with open(f"{self.invoice}.txt", "w") as f:
                f.write(bill_text)
            messagebox.showinfo("Printed", f"Bill saved as {self.invoice}.txt")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def bill_top(self): pass
    def bill_middle(self): pass
    def bill_bottom(self): pass

    def update_date_time(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.config(text=now)
        self.root.after(1000, self.update_date_time)


# ================= MAIN IMS DASHBOARD =================
class IMS:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("800x600")

        # Icons
        self.MenuLogo: Optional[PhotoImage] = None
        self.icon_side: PhotoImage = tk.PhotoImage()  # dummy
        self.icon_title: PhotoImage = tk.PhotoImage()

        # Labels for sections
        self.lbl_category: Label = tk.Label(root, text="Categories", font=("Arial", 12, "bold"))
        self.lbl_employee: Label = tk.Label(root, text="Employees", font=("Arial", 12, "bold"))
        self.lbl_product: Label = tk.Label(root, text="Products", font=("Arial", 12, "bold"))
        self.lbl_sales: Label = tk.Label(root, text="Sales", font=("Arial", 12, "bold"))
        self.lbl_supplier: Label = tk.Label(root, text="Suppliers", font=("Arial", 12, "bold"))
        self.lbl_clock: Label = tk.Label(root, text="", font=("Arial", 10))

        self.new_win: Optional[Toplevel] = None
        self.new_obj: Optional[Union[categoryClass, employeeClass, productClass, salesClass, supplierClass, billClass]] = None

        # Navigation buttons
        btn_frame = tk.Frame(root)
        tk.Button(btn_frame, text="Category", command=self.category).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Employee", command=self.employee).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Product", command=self.product).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Sales", command=self.sales).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Supplier", command=self.supplier).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Billing", command=self.billing).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Exit", command=root.quit).pack(side=tk.RIGHT, padx=5)
        btn_frame.pack(side=tk.TOP, fill=tk.X)

        self.lbl_clock.pack(side=tk.BOTTOM)
        self.update_content()

    def update_content(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.config(text=now)
        self.root.after(1000, self.update_content)

    def open_window(self, title: str, cls):
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_win = Toplevel(self.root)
        self.new_win.title(title)
        self.new_win.geometry("800x600")
        self.new_obj = cls(self.new_win)

    def category(self):
        self.open_window("Category Management", categoryClass)

    def employee(self):
        self.open_window("Employee Management", employeeClass)

    def product(self):
        self.open_window("Product Management", productClass)

    def sales(self):
        self.open_window("Sales History", salesClass)

    def supplier(self):
        self.open_window("Supplier Management", supplierClass)

    def billing(self):
        self.open_window("Billing", billClass)


# ================= MAIN =================
if __name__ == "__main__":
    root = tk.Tk()
    app = IMS(root)
    root.mainloop()