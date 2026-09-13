import tkinter as tk
from tkinter import ttk, messagebox, Text, Listbox, Entry, Label, Toplevel, PhotoImage
import sqlite3
from datetime import datetime
import os

DB_NAME = 'ims.db'

class Database:
    _instance = None
    _conn = None

    @classmethod
    def get_connection(cls):
        if cls._conn is None:
            cls._conn = sqlite3.connect(DB_NAME)
            cls._conn.execute("PRAGMA foreign_keys = ON")
        return cls._conn

    @classmethod
    def close(cls):
        if cls._conn:
            cls._conn.close()
            cls._conn = None

def init_db():
    conn = Database.get_connection()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS category (
            cat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS supplier (
            sup_invoice TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            contact TEXT,
            desc TEXT
        );
        CREATE TABLE IF NOT EXISTS employee (
            emp_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            dob TEXT,
            doj TEXT,
            gender TEXT,
            contact TEXT,
            email TEXT,
            pass TEXT,
            utype TEXT,
            address TEXT,
            salary REAL
        );
        CREATE TABLE IF NOT EXISTS product (
            pid TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            qty INTEGER DEFAULT 0,
            status TEXT,
            cat TEXT,
            sup TEXT,
            FOREIGN KEY (cat) REFERENCES category(name),
            FOREIGN KEY (sup) REFERENCES supplier(sup_invoice)
        );
        CREATE TABLE IF NOT EXISTS sales (
            invoice TEXT PRIMARY KEY,
            bill_data TEXT NOT NULL,
            date TEXT NOT NULL
        );
    ''')
    conn.commit()

class categoryClass:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Manage Categories")
        self.root.geometry("800x500")
        self.var_cat_id = tk.StringVar()
        self.var_name = tk.StringVar()

        # PhotoImage placeholders
        self.im1 = tk.PhotoImage()  # empty
        self.im2 = tk.PhotoImage()

        # UI
        title = tk.Label(self.root, text="Manage Categories", font=("times new roman", 20, "bold"), bg="#0f4d7a", fg="white")
        title.pack(side=tk.TOP, fill=tk.X)

        # Form Frame
        form_frame = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        form_frame.place(x=20, y=60, width=400, height=300)

        tk.Label(form_frame, text="Category ID", font=("times new roman", 12), bg="white").grid(row=0, column=0, pady=10, padx=10, sticky="w")
        tk.Entry(form_frame, textvariable=self.var_cat_id, state='readonly', font=("times new roman", 12)).grid(row=0, column=1, pady=10, padx=10, sticky="w")
        tk.Label(form_frame, text="Category Name", font=("times new roman", 12), bg="white").grid(row=1, column=0, pady=10, padx=10, sticky="w")
        tk.Entry(form_frame, textvariable=self.var_name, font=("times new roman", 12)).grid(row=1, column=1, pady=10, padx=10, sticky="w")

        btn_frame = tk.Frame(form_frame, bg="white")
        btn_frame.grid(row=2, columnspan=2, pady=20)

        tk.Button(btn_frame, text="Add", width=10, command=self.add).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", width=10, command=self.delete).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", width=10, command=self.clear).pack(side=tk.LEFT, padx=5)

        # Image labels (decorative)
        self.lbl_im1 = tk.Label(self.root, image=self.im1, bg="white")
        self.lbl_im1.place(x=450, y=80)
        self.lbl_im2 = tk.Label(self.root, image=self.im2, bg="white")
        self.lbl_im2.place(x=550, y=80)

        # Treeview
        table_frame = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        table_frame.place(x=20, y=380, width=760, height=100)
        scroll_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        self.CategoryTable = ttk.Treeview(table_frame, columns=("cat_id", "name"), yscrollcommand=scroll_y.set)
        scroll_y.config(command=self.CategoryTable.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.CategoryTable.heading("cat_id", text="Category ID")
        self.CategoryTable.heading("name", text="Name")
        self.CategoryTable['show'] = 'headings'
        self.CategoryTable.column("cat_id", width=100)
        self.CategoryTable.column("name", width=150)
        self.CategoryTable.pack(fill=tk.BOTH, expand=1)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def add(self):
        name = self.var_name.get().strip()
        if not name:
            messagebox.showerror("Error", "Category name required", parent=self.root)
            return
        try:
            conn = Database.get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO category (name) VALUES (?)", (name,))
            conn.commit()
            messagebox.showinfo("Success", "Category added", parent=self.root)
            self.clear()
            self.show()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Category already exists", parent=self.root)

    def delete(self):
        cat_id = self.var_cat_id.get()
        if not cat_id:
            messagebox.showerror("Error", "Select a category first", parent=self.root)
            return
        if messagebox.askyesno("Confirm", "Delete selected category?", parent=self.root):
            conn = Database.get_connection()
            conn.execute("DELETE FROM category WHERE cat_id=?", (cat_id,))
            conn.commit()
            self.clear()
            self.show()

    def clear(self):
        self.var_cat_id.set("")
        self.var_name.set("")

    def get_data(self, ev):
        selected = self.CategoryTable.focus()
        if selected:
            row = self.CategoryTable.item(selected)['values']
            self.var_cat_id.set(row[0])
            self.var_name.set(row[1])

    def show(self):
        self.CategoryTable.delete(*self.CategoryTable.get_children())
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM category")
        for row in cur.fetchall():
            self.CategoryTable.insert('', tk.END, values=row)

class employeeClass:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Manage Employees")
        self.root.geometry("1100x600")
        self.var_emp_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_dob = tk.StringVar()
        self.var_doj = tk.StringVar()
        self.var_gender = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_pass = tk.StringVar()
        self.var_utype = tk.StringVar()
        self.var_salary = tk.StringVar()
        self.txt_address = None
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()

        title = tk.Label(self.root, text="Employee Management", font=("times new roman", 20, "bold"), bg="#0f4d7a", fg="white")
        title.pack(side=tk.TOP, fill=tk.X)

        # Form
        form_frame = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        form_frame.place(x=10, y=50, width=500, height=500)

        fields = [
            ("Employee ID", self.var_emp_id, True),
            ("Name", self.var_name, False),
            ("DOB (YYYY-MM-DD)", self.var_dob, False),
            ("DOJ (YYYY-MM-DD)", self.var_doj, False),
            ("Gender", self.var_gender, False),
            ("Contact", self.var_contact, False),
            ("Email", self.var_email, False),
            ("Password", self.var_pass, False),
            ("User Type", self.var_utype, False),
            ("Salary", self.var_salary, False),
        ]
        for i, (label, var, readonly) in enumerate(fields):
            tk.Label(form_frame, text=label, font=("times new roman", 12), bg="white").grid(row=i, column=0, sticky="w", padx=10, pady=5)
            ent = tk.Entry(form_frame, textvariable=var, font=("times new roman", 12))
            if readonly:
                ent.configure(state='readonly')
            ent.grid(row=i, column=1, sticky="w", padx=10, pady=5)

        tk.Label(form_frame, text="Address", font=("times new roman", 12), bg="white").grid(row=10, column=0, sticky="nw", padx=10, pady=5)
        self.txt_address = tk.Text(form_frame, width=30, height=4, font=("times new roman", 12))
        self.txt_address.grid(row=10, column=1, sticky="w", padx=10, pady=5)

        btn_frame = tk.Frame(form_frame, bg="white")
        btn_frame.grid(row=11, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Add", width=10, command=self.add).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", width=10, command=self.update).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", width=10, command=self.delete).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", width=10, command=self.clear).pack(side=tk.LEFT, padx=5)

        # Search
        search_frame = tk.LabelFrame(self.root, text="Search", font=("times new roman", 12), bg="white")
        search_frame.place(x=530, y=50, width=550, height=70)
        tk.Label(search_frame, text="Search By", font=("times new roman", 11), bg="white").grid(row=0, column=0, padx=5)
        cmb = ttk.Combobox(search_frame, textvariable=self.var_searchby, values=("emp_id", "name", "contact", "email"), state='readonly', font=("times new roman", 11), width=12)
        cmb.grid(row=0, column=1, padx=5)
        tk.Label(search_frame, text="Search Text", font=("times new roman", 11), bg="white").grid(row=0, column=2, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, font=("times new roman", 11)).grid(row=0, column=3, padx=5)
        tk.Button(search_frame, text="Search", width=8, command=self.search).grid(row=0, column=4, padx=5)

        # Table
        table_frame = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        table_frame.place(x=530, y=130, width=550, height=420)
        scroll_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        self.EmployeeTable = ttk.Treeview(table_frame,
                                          columns=("emp_id", "name", "dob", "doj", "gender", "contact", "email", "pass", "utype", "salary", "address"),
                                          yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.config(command=self.EmployeeTable.yview)
        scroll_x.config(command=self.EmployeeTable.xview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        cols = ["Employee ID", "Name", "DOB", "DOJ", "Gender", "Contact", "Email", "Password", "User Type", "Salary", "Address"]
        for col, text in zip(self.EmployeeTable['columns'], cols):
            self.EmployeeTable.heading(col, text=text)
            self.EmployeeTable.column(col, width=100)
        self.EmployeeTable['show'] = 'headings'
        self.EmployeeTable.pack(fill=tk.BOTH, expand=1)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def add(self):
        if not self.var_emp_id.get():
            messagebox.showerror("Error", "Employee ID required", parent=self.root)
            return
        try:
            conn = Database.get_connection()
            conn.execute('''INSERT INTO employee VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                         (self.var_emp_id.get(), self.var_name.get(), self.var_dob.get(), self.var_doj.get(),
                          self.var_gender.get(), self.var_contact.get(), self.var_email.get(),
                          self.var_pass.get(), self.var_utype.get(), float(self.var_salary.get() or 0),
                          self.txt_address.get("1.0", tk.END).strip()))
            conn.commit()
            messagebox.showinfo("Success", "Employee added", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)

    def update(self):
        if not self.var_emp_id.get():
            messagebox.showerror("Error", "Select an employee to update", parent=self.root)
            return
        try:
            conn = Database.get_connection()
            conn.execute('''UPDATE employee SET name=?, dob=?, doj=?, gender=?, contact=?, email=?, pass=?, utype=?, salary=?, address=? WHERE emp_id=?''',
                         (self.var_name.get(), self.var_dob.get(), self.var_doj.get(), self.var_gender.get(),
                          self.var_contact.get(), self.var_email.get(), self.var_pass.get(), self.var_utype.get(),
                          float(self.var_salary.get() or 0), self.txt_address.get("1.0", tk.END).strip(),
                          self.var_emp_id.get()))
            conn.commit()
            messagebox.showinfo("Success", "Employee updated", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)

    def delete(self):
        if not self.var_emp_id.get():
            messagebox.showerror("Error", "Select an employee to delete", parent=self.root)
            return
        if messagebox.askyesno("Confirm", "Delete this employee?", parent=self.root):
            conn = Database.get_connection()
            conn.execute("DELETE FROM employee WHERE emp_id=?", (self.var_emp_id.get(),))
            conn.commit()
            self.clear()
            self.show()

    def clear(self):
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_gender.set("")
        self.var_contact.set("")
        self.var_email.set("")
        self.var_pass.set("")
        self.var_utype.set("")
        self.var_salary.set("")
        self.txt_address.delete("1.0", tk.END)
        self.var_searchtxt.set("")

    def get_data(self, ev):
        selected = self.EmployeeTable.focus()
        if selected:
            vals = self.EmployeeTable.item(selected)['values']
            self.var_emp_id.set(vals[0])
            self.var_name.set(vals[1])
            self.var_dob.set(vals[2])
            self.var_doj.set(vals[3])
            self.var_gender.set(vals[4])
            self.var_contact.set(vals[5])
            self.var_email.set(vals[6])
            self.var_pass.set(vals[7])
            self.var_utype.set(vals[8])
            self.var_salary.set(vals[9])
            self.txt_address.delete("1.0", tk.END)
            self.txt_address.insert(tk.END, vals[10] if len(vals) > 10 else "")

    def show(self, rows=None):
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        if rows is None:
            conn = Database.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM employee")
            rows = cur.fetchall()
        for row in rows:
            self.EmployeeTable.insert('', tk.END, values=row)

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get().strip()
        if not by or not txt:
            self.show()
            return
        conn = Database.get_connection()
        cur = conn.cursor()
        # vulnerable to SQL injection? For demo, we sanitize by using allowed columns
        allowed = {"emp_id", "name", "contact", "email"}
        if by in allowed:
            cur.execute(f"SELECT * FROM employee WHERE {by} LIKE ?", ('%'+txt+'%',))
            rows = cur.fetchall()
            self.show(rows)
        else:
            messagebox.showerror("Error", "Invalid search column", parent=self.root)

class supplierClass:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Manage Suppliers")
        self.root.geometry("900x550")
        self.var_sup_invoice = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.txt_desc = None
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()

        title = tk.Label(self.root, text="Supplier Management", font=("times new roman", 20, "bold"), bg="#0f4d7a", fg="white")
        title.pack(side=tk.TOP, fill=tk.X)

        form_frame = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        form_frame.place(x=10, y=50, width=400, height=350)

        fields = [
            ("Invoice No", self.var_sup_invoice, False),
            ("Name", self.var_name, False),
            ("Contact", self.var_contact, False),
        ]
        for i, (label, var, readonly) in enumerate(fields):
            tk.Label(form_frame, text=label, font=("times new roman", 12), bg="white").grid(row=i, column=0, sticky="w", padx=10, pady=10)
            ent = tk.Entry(form_frame, textvariable=var, font=("times new roman", 12))
            if readonly:
                ent.configure(state='readonly')
            ent.grid(row=i, column=1, sticky="w", padx=10, pady=10)

        tk.Label(form_frame, text="Description", font=("times new roman", 12), bg="white").grid(row=3, column=0, sticky="nw", padx=10, pady=10)
        self.txt_desc = tk.Text(form_frame, width=25, height=4, font=("times new roman", 12))
        self.txt_desc.grid(row=3, column=1, sticky="w", padx=10, pady=10)

        btn_frame = tk.Frame(form_frame, bg="white")
        btn_frame.grid(row=4, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Add", width=10, command=self.add).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", width=10, command=self.update).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", width=10, command=self.delete).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", width=10, command=self.clear).pack(side=tk.LEFT, padx=5)

        # Search
        search_frame = tk.LabelFrame(self.root, text="Search", font=("times new roman", 12), bg="white")
        search_frame.place(x=430, y=50, width=450, height=70)
        tk.Label(search_frame, text="Search By", font=("times new roman", 11), bg="white").grid(row=0, column=0, padx=5)
        cmb = ttk.Combobox(search_frame, textvariable=self.var_searchby, values=("sup_invoice", "name", "contact"), state='readonly', font=("times new roman", 11), width=12)
        cmb.grid(row=0, column=1, padx=5)
        tk.Label(search_frame, text="Search Text", font=("times new roman", 11), bg="white").grid(row=0, column=2, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, font=("times new roman", 11)).grid(row=0, column=3, padx=5)
        tk.Button(search_frame, text="Search", width=8, command=self.search).grid(row=0, column=4, padx=5)

        # Table
        table_frame = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        table_frame.place(x=430, y=130, width=450, height=370)
        scroll_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        self.SupplierTable = ttk.Treeview(table_frame, columns=("invoice", "name", "contact", "desc"), yscrollcommand=scroll_y.set)
        scroll_y.config(command=self.SupplierTable.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.SupplierTable.heading("invoice", text="Invoice No")
        self.SupplierTable.heading("name", text="Name")
        self.SupplierTable.heading("contact", text="Contact")
        self.SupplierTable.heading("desc", text="Description")
        self.SupplierTable['show'] = 'headings'
        self.SupplierTable.column("invoice", width=80)
        self.SupplierTable.column("name", width=100)
        self.SupplierTable.column("contact", width=100)
        self.SupplierTable.column("desc", width=150)
        self.SupplierTable.pack(fill=tk.BOTH, expand=1)
        self.SupplierTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def add(self):
        if not self.var_sup_invoice.get():
            messagebox.showerror("Error", "Invoice number required", parent=self.root)
            return
        try:
            conn = Database.get_connection()
            conn.execute("INSERT INTO supplier VALUES (?,?,?,?)",
                         (self.var_sup_invoice.get(), self.var_name.get(), self.var_contact.get(),
                          self.txt_desc.get("1.0", tk.END).strip()))
            conn.commit()
            messagebox.showinfo("Success", "Supplier added", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)

    def update(self):
        if not self.var_sup_invoice.get():
            messagebox.showerror("Error", "Select a supplier", parent=self.root)
            return
        try:
            conn = Database.get_connection()
            conn.execute("UPDATE supplier SET name=?, contact=?, desc=? WHERE sup_invoice=?",
                         (self.var_name.get(), self.var_contact.get(),
                          self.txt_desc.get("1.0", tk.END).strip(), self.var_sup_invoice.get()))
            conn.commit()
            messagebox.showinfo("Success", "Supplier updated", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)

    def delete(self):
        if not self.var_sup_invoice.get():
            messagebox.showerror("Error", "Select a supplier", parent=self.root)
            return
        if messagebox.askyesno("Confirm", "Delete this supplier?", parent=self.root):
            conn = Database.get_connection()
            conn.execute("DELETE FROM supplier WHERE sup_invoice=?", (self.var_sup_invoice.get(),))
            conn.commit()
            self.clear()
            self.show()

    def clear(self):
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete("1.0", tk.END)
        self.var_searchtxt.set("")

    def get_data(self, ev):
        selected = self.SupplierTable.focus()
        if selected:
            vals = self.SupplierTable.item(selected)['values']
            self.var_sup_invoice.set(vals[0])
            self.var_name.set(vals[1])
            self.var_contact.set(vals[2])
            self.txt_desc.delete("1.0", tk.END)
            self.txt_desc.insert(tk.END, vals[3] if len(vals) > 3 else "")

    def show(self, rows=None):
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        if rows is None:
            conn = Database.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM supplier")
            rows = cur.fetchall()
        for row in rows:
            self.SupplierTable.insert('', tk.END, values=row)

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get().strip()
        if not by or not txt:
            self.show()
            return
        allowed = {"sup_invoice", "name", "contact"}
        if by in allowed:
            conn = Database.get_connection()
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM supplier WHERE {by} LIKE ?", ('%'+txt+'%',))
            rows = cur.fetchall()
            self.show(rows)
        else:
            messagebox.showerror("Error", "Invalid search column", parent=self.root)

class productClass:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Manage Products")
        self.root.geometry("1100x600")
        self.var_pid = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_status = tk.StringVar()
        self.var_cat = tk.StringVar()
        self.var_sup = tk.StringVar()
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()
        self.cat_list = []
        self.sup_list = []

        title = tk.Label(self.root, text="Product Management", font=("times new roman", 20, "bold"), bg="#0f4d7a", fg="white")
        title.pack(side=tk.TOP, fill=tk.X)

        # Fetch dropdown data
        self.fetch_cat_sup()

        form_frame = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        form_frame.place(x=10, y=50, width=500, height=400)

        fields = [
            ("Product ID", self.var_pid),
            ("Name", self.var_name),
            ("Price", self.var_price),
            ("Quantity", self.var_qty),
            ("Status", self.var_status),
        ]
        for i, (label, var) in enumerate(fields):
            tk.Label(form_frame, text=label, font=("times new roman", 12), bg="white").grid(row=i, column=0, sticky="w", padx=10, pady=10)
            tk.Entry(form_frame, textvariable=var, font=("times new roman", 12)).grid(row=i, column=1, sticky="w", padx=10, pady=10)

        tk.Label(form_frame, text="Category", font=("times new roman", 12), bg="white").grid(row=5, column=0, sticky="w", padx=10, pady=10)
        cat_cmb = ttk.Combobox(form_frame, textvariable=self.var_cat, values=self.cat_list, state='readonly', font=("times new roman", 12))
        cat_cmb.grid(row=5, column=1, sticky="w", padx=10, pady=10)

        tk.Label(form_frame, text="Supplier", font=("times new roman", 12), bg="white").grid(row=6, column=0, sticky="w", padx=10, pady=10)
        sup_cmb = ttk.Combobox(form_frame, textvariable=self.var_sup, values=self.sup_list, state='readonly', font=("times new roman", 12))
        sup_cmb.grid(row=6, column=1, sticky="w", padx=10, pady=10)

        btn_frame = tk.Frame(form_frame, bg="white")
        btn_frame.grid(row=7, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Add", width=10, command=self.add).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", width=10, command=self.update).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", width=10, command=self.delete).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", width=10, command=self.clear).pack(side=tk.LEFT, padx=5)

        # Search
        search_frame = tk.LabelFrame(self.root, text="Search", font=("times new roman", 12), bg="white")
        search_frame.place(x=530, y=50, width=550, height=70)
        tk.Label(search_frame, text="Search By", font=("times new roman", 11), bg="white").grid(row=0, column=0, padx=5)
        cmb = ttk.Combobox(search_frame, textvariable=self.var_searchby, values=("pid", "name", "cat", "sup"), state='readonly', font=("times new roman", 11), width=12)
        cmb.grid(row=0, column=1, padx=5)
        tk.Label(search_frame, text="Search Text", font=("times new roman", 11), bg="white").grid(row=0, column=2, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, font=("times new roman", 11)).grid(row=0, column=3, padx=5)
        tk.Button(search_frame, text="Search", width=8, command=self.search).grid(row=0, column=4, padx=5)

        # Table
        table_frame = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        table_frame.place(x=530, y=130, width=550, height=420)
        scroll_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        self.ProductTable = ttk.Treeview(table_frame,
                                         columns=("pid", "name", "price", "qty", "status", "cat", "sup"),
                                         yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.config(command=self.ProductTable.yview)
        scroll_x.config(command=self.ProductTable.xview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        cols = ["Product ID", "Name", "Price", "Qty", "Status", "Category", "Supplier"]
        for col, text in zip(self.ProductTable['columns'], cols):
            self.ProductTable.heading(col, text=text)
            self.ProductTable.column(col, width=100)
        self.ProductTable['show'] = 'headings'
        self.ProductTable.pack(fill=tk.BOTH, expand=1)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def fetch_cat_sup(self):
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM category")
        self.cat_list = [row[0] for row in cur.fetchall()]
        cur.execute("SELECT sup_invoice FROM supplier")
        self.sup_list = [row[0] for row in cur.fetchall()]

    def add(self):
        if not self.var_pid.get():
            messagebox.showerror("Error", "Product ID required", parent=self.root)
            return
        try:
            conn = Database.get_connection()
            conn.execute("INSERT INTO product VALUES (?,?,?,?,?,?,?)",
                         (self.var_pid.get(), self.var_name.get(), float(self.var_price.get() or 0),
                          int(self.var_qty.get() or 0), self.var_status.get(),
                          self.var_cat.get(), self.var_sup.get()))
            conn.commit()
            messagebox.showinfo("Success", "Product added", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)

    def update(self):
        if not self.var_pid.get():
            messagebox.showerror("Error", "Select a product", parent=self.root)
            return
        try:
            conn = Database.get_connection()
            conn.execute("UPDATE product SET name=?, price=?, qty=?, status=?, cat=?, sup=? WHERE pid=?",
                         (self.var_name.get(), float(self.var_price.get() or 0),
                          int(self.var_qty.get() or 0), self.var_status.get(),
                          self.var_cat.get(), self.var_sup.get(), self.var_pid.get()))
            conn.commit()
            messagebox.showinfo("Success", "Product updated", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)

    def delete(self):
        if not self.var_pid.get():
            messagebox.showerror("Error", "Select a product", parent=self.root)
            return
        if messagebox.askyesno("Confirm", "Delete this product?", parent=self.root):
            conn = Database.get_connection()
            conn.execute("DELETE FROM product WHERE pid=?", (self.var_pid.get(),))
            conn.commit()
            self.clear()
            self.show()

    def clear(self):
        self.var_pid.set("")
        self.var_name.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("")
        self.var_cat.set("")
        self.var_sup.set("")
        self.var_searchtxt.set("")

    def get_data(self, ev):
        selected = self.ProductTable.focus()
        if selected:
            vals = self.ProductTable.item(selected)['values']
            self.var_pid.set(vals[0])
            self.var_name.set(vals[1])
            self.var_price.set(vals[2])
            self.var_qty.set(vals[3])
            self.var_status.set(vals[4])
            self.var_cat.set(vals[5])
            self.var_sup.set(vals[6] if len(vals) > 6 else "")

    def show(self, rows=None):
        self.ProductTable.delete(*self.ProductTable.get_children())
        if rows is None:
            conn = Database.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM product")
            rows = cur.fetchall()
        for row in rows:
            self.ProductTable.insert('', tk.END, values=row)

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get().strip()
        if not by or not txt:
            self.show()
            return
        allowed = {"pid", "name", "cat", "sup"}
        if by in allowed:
            conn = Database.get_connection()
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM product WHERE {by} LIKE ?", ('%'+txt+'%',))
            rows = cur.fetchall()
            self.show(rows)
        else:
            messagebox.showerror("Error", "Invalid search column", parent=self.root)

class salesClass:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Sales History")
        self.root.geometry("1000x600")
        self.var_invoice = tk.StringVar()
        self.bill_photo = tk.PhotoImage()
        self.blll_list = []  # list of invoice numbers

        title = tk.Label(self.root, text="Sales History", font=("times new roman", 20, "bold"), bg="#0f4d7a", fg="white")
        title.pack(side=tk.TOP, fill=tk.X)

        # Search bar
        search_frame = tk.Frame(self.root, bg="white")
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="Invoice No", font=("times new roman", 12), bg="white").pack(side=tk.LEFT, padx=5)
        ent = tk.Entry(search_frame, textvariable=self.var_invoice, font=("times new roman", 12))
        ent.pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", command=self.search, font=("times new roman", 12)).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All", command=self.show, font=("times new roman", 12)).pack(side=tk.LEFT, padx=5)

        # Listbox for invoices
        list_frame = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        list_frame.place(x=10, y=50, width=300, height=500)
        scroll_y = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.Sales_List = tk.Listbox(list_frame, yscrollcommand=scroll_y.set, font=("times new roman", 12))
        scroll_y.config(command=self.Sales_List.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.Sales_List.pack(fill=tk.BOTH, expand=1)
        self.Sales_List.bind("<<ListboxSelect>>", self.get_data)

        # Bill display area
        bill_frame = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        bill_frame.place(x=320, y=50, width=660, height=500)
        bill_label = tk.Label(bill_frame, text="Bill Details", font=("times new roman", 14, "bold"), bg="white")
        bill_label.pack(side=tk.TOP, anchor="w", padx=10, pady=5)
        self.bill_area = tk.Text(bill_frame, font=("courier", 10), bg="white")
        self.bill_area.pack(fill=tk.BOTH, expand=1, padx=5, pady=5)

        self.show()

    def clear(self):
        self.var_invoice.set("")
        self.bill_area.delete("1.0", tk.END)

    def get_data(self, ev=None):
        selection = self.Sales_List.curselection()
        if selection:
            invoice = self.Sales_List.get(selection[0])
            self.var_invoice.set(invoice)
            conn = Database.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT bill_data FROM sales WHERE invoice=?", (invoice,))
            row = cur.fetchone()
            if row:
                self.bill_area.delete("1.0", tk.END)
                self.bill_area.insert(tk.END, row[0])
            else:
                self.bill_area.delete("1.0", tk.END)

    def search(self):
        inv = self.var_invoice.get().strip()
        if not inv:
            self.show()
            return
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT invoice FROM sales WHERE invoice LIKE ?", ('%'+inv+'%',))
        rows = cur.fetchall()
        self.Sales_List.delete(0, tk.END)
        for row in rows:
            self.Sales_List.insert(tk.END, row[0])
        self.bill_area.delete("1.0", tk.END)

    def show(self):
        self.Sales_List.delete(0, tk.END)
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT invoice FROM sales ORDER BY date DESC")
        self.blll_list = [row[0] for row in cur.fetchall()]
        for inv in self.blll_list:
            self.Sales_List.insert(tk.END, inv)

class billClass:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Billing System")
        self.root.geometry("1200x700")
        self.invoice = tk.StringVar()
        self.var_cname = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_pid = tk.StringVar()
        self.var_pname = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_stock = tk.StringVar()
        self.var_search = tk.StringVar()
        self.cart_list = []
        self.bill_amnt = 0
        self.net_pay = 0.0
        self.discount = 0.0
        self.siscount = 0  # as per diagram
        self.chk_print = 0
        self.var_cal_input = tk.StringVar()
        self.txt_cal_input = None

        # Images
        self.icon_title = tk.PhotoImage()

        # Bill area
        self.txt_bill_area = None

        # Setup UI
        self.bill_top()
        self.bill_middle()
        self.bill_bottom()
        self.update_date_time()

    def show(self):
        self.root.deiconify()
        self.root.lift()

    def update_date_time(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if hasattr(self, 'lbl_clock'):
            self.lbl_clock.config(text=now)
        self.root.after(1000, self.update_date_time)

    def bill_top(self):
        top = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        top.pack(side=tk.TOP, fill=tk.X)

        tk.Label(top, text="Billing System", font=("times new roman", 24, "bold"), bg="white", fg="#0f4d7a").pack(side=tk.TOP, anchor="w", padx=20, pady=5)
        self.lbl_clock = tk.Label(top, text="", font=("times new roman", 12), bg="white")
        self.lbl_clock.pack(side=tk.TOP, anchor="w", padx=20)

        info_frame = tk.Frame(top, bg="white")
        info_frame.pack(side=tk.LEFT, padx=20, pady=5)
        tk.Label(info_frame, text="Customer Name", font=("times new roman", 12), bg="white").grid(row=0, column=0, sticky="w")
        tk.Entry(info_frame, textvariable=self.var_cname, font=("times new roman", 12), width=20).grid(row=0, column=1, padx=10)
        tk.Label(info_frame, text="Contact No", font=("times new roman", 12), bg="white").grid(row=0, column=2, sticky="w")
        tk.Entry(info_frame, textvariable=self.var_contact, font=("times new roman", 12), width=15).grid(row=0, column=3, padx=10)

        search_frame = tk.Frame(top, bg="white")
        search_frame.pack(side=tk.RIGHT, padx=20, pady=5)
        tk.Label(search_frame, text="Search Product", font=("times new roman", 12), bg="white").pack(side=tk.LEFT)
        tk.Entry(search_frame, textvariable=self.var_search, font=("times new roman", 12), width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", command=self.search, font=("times new roman", 10)).pack(side=tk.LEFT, padx=5)

    def bill_middle(self):
        mid = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        mid.pack(fill=tk.BOTH, expand=1, padx=10, pady=10)

        # Product Table
        prod_frame = tk.LabelFrame(mid, text="Available Products", font=("times new roman", 12), bg="white")
        prod_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=1, padx=5, pady=5)
        scroll_y = tk.Scrollbar(prod_frame, orient=tk.VERTICAL)
        self.product_Table = ttk.Treeview(prod_frame, columns=("pid", "name", "price", "stock"),
                                          yscrollcommand=scroll_y.set, height=8)
        scroll_y.config(command=self.product_Table.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.product_Table.heading("pid", text="PID")
        self.product_Table.heading("name", text="Name")
        self.product_Table.heading("price", text="Price")
        self.product_Table.heading("stock", text="Stock")
        self.product_Table['show'] = 'headings'
        self.product_Table.column("pid", width=60)
        self.product_Table.column("name", width=120)
        self.product_Table.column("price", width=60)
        self.product_Table.column("stock", width=60)
        self.product_Table.pack(fill=tk.BOTH, expand=1)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)
        self.product_Table.bind("<Double-1>", self.get_data)

        # Cart Table
        cart_frame = tk.LabelFrame(mid, text="Cart", font=("times new roman", 12), bg="white")
        cart_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1, padx=5, pady=5)
        self.cartTitle = tk.Label(cart_frame, text="Cart Items", font=("times new roman", 12, "bold"), bg="white")
        self.cartTitle.pack(side=tk.TOP, anchor="w")
        scroll_y2 = tk.Scrollbar(cart_frame, orient=tk.VERTICAL)
        self.CartTable = ttk.Treeview(cart_frame, columns=("pid", "name", "price", "qty", "total"),
                                      yscrollcommand=scroll_y2.set, height=8)
        scroll_y2.config(command=self.CartTable.yview)
        scroll_y2.pack(side=tk.RIGHT, fill=tk.Y)
        self.CartTable.heading("pid", text="PID")
        self.CartTable.heading("name", text="Name")
        self.CartTable.heading("price", text="Price")
        self.CartTable.heading("qty", text="Qty")
        self.CartTable.heading("total", text="Total")
        self.CartTable['show'] = 'headings'
        self.CartTable.column("pid", width=60)
        self.CartTable.column("name", width=100)
        self.CartTable.column("price", width=60)
        self.CartTable.column("qty", width=40)
        self.CartTable.column("total", width=70)
        self.CartTable.pack(fill=tk.BOTH, expand=1)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)
        self.CartTable.bind("<Double-1>", self.get_data_cart)

        # Cart item entry
        item_frame = tk.Frame(mid, bg="white")
        item_frame.pack(fill=tk.X, pady=5)
        fields = [
            ("PID", self.var_pid, True),
            ("Name", self.var_pname, True),
            ("Price", self.var_price, True),
            ("Qty", self.var_qty, False),
            ("Stock", self.var_stock, True),
        ]
        for i, (label, var, ro) in enumerate(fields):
            tk.Label(item_frame, text=label, font=("times new roman", 10), bg="white").grid(row=0, column=i*2, padx=5)
            ent = tk.Entry(item_frame, textvariable=var, font=("times new roman", 10), width=10)
            if ro:
                ent.configure(state='readonly')
            ent.grid(row=0, column=i*2+1, padx=5)

        btn_item = tk.Frame(mid, bg="white")
        btn_item.pack(fill=tk.X, pady=5)
        tk.Button(btn_item, text="Add to Cart", command=self.add_update_cart).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_item, text="Clear Cart", command=self.clear_cart).pack(side=tk.LEFT, padx=5)

    def bill_bottom(self):
        bottom = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        bottom.pack(fill=tk.BOTH, padx=10, pady=10)

        # Calculator
        calc_frame = tk.LabelFrame(bottom, text="Calculator", font=("times new roman", 12), bg="white")
        calc_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
        self.txt_cal_input = tk.Entry(calc_frame, textvariable=self.var_cal_input, font=("times new roman", 14), width=15, justify='right')
        self.txt_cal_input.pack(pady=5, padx=5)
        btn_frame = tk.Frame(calc_frame, bg="white")
        btn_frame.pack()
        buttons = [
            ['7','8','9','/'],
            ['4','5','6','*'],
            ['1','2','3','-'],
            ['C','0','=','+']
        ]
        for row in buttons:
            f = tk.Frame(btn_frame, bg="white")
            f.pack()
            for char in row:
                cmd = lambda x=char: self.get_input(x)
                tk.Button(f, text=char, width=5, command=cmd).pack(side=tk.LEFT, padx=2, pady=2)

        # Bill summary
        summary_frame = tk.LabelFrame(bottom, text="Bill Summary", font=("times new roman", 12), bg="white")
        summary_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=1, padx=5, pady=5)
        self.lbl_amnt = tk.Label(summary_frame, text="Bill Amount: 0", font=("times new roman", 12), bg="white")
        self.lbl_amnt.pack(anchor="w", padx=10, pady=2)
        self.lbl_discount = tk.Label(summary_frame, text="Discount: 0", font=("times new roman", 12), bg="white")
        self.lbl_discount.pack(anchor="w", padx=10, pady=2)
        self.lbl_net_pay = tk.Label(summary_frame, text="Net Pay: 0", font=("times new roman", 12, "bold"), bg="white")
        self.lbl_net_pay.pack(anchor="w", padx=10, pady=2)
        tk.Button(summary_frame, text="Generate Bill", command=self.generate_bill, font=("times new roman", 12), bg="green", fg="white").pack(pady=5)
        tk.Button(summary_frame, text="Print Bill", command=self.print_bill, font=("times new roman", 12), bg="blue", fg="white").pack(pady=5)

        # Bill text display
        bill_frame = tk.LabelFrame(bottom, text="Bill Preview", font=("times new roman", 12), bg="white")
        bill_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1, padx=5, pady=5)
        self.txt_bill_area = tk.Text(bill_frame, font=("courier", 10), width=50, height=10)
        self.txt_bill_area.pack(fill=tk.BOTH, expand=1, padx=5, pady=5)

    def search(self):
        q = self.var_search.get().strip()
        if not q:
            self.show_cart()  # maybe refresh products
            return
        conn = Database.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT pid, name, price, qty FROM product WHERE pid LIKE ? OR name LIKE ?", ('%'+q+'%', '%'+q+'%'))
        rows = cur.fetchall()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert('', tk.END, values=row)

    def get_data(self, ev):
        selected = self.product_Table.focus()
        if selected:
            vals = self.product_Table.item(selected)['values']
            self.var_pid.set(vals[0])
            self.var_pname.set(vals[1])
            self.var_price.set(vals[2])
            self.var_stock.set(vals[3])

    def get_data_cart(self, ev):
        selected = self.CartTable.focus()
        if selected:
            vals = self.CartTable.item(selected)['values']
            self.var_pid.set(vals[0])
            self.var_pname.set(vals[1])
            self.var_price.set(vals[2])
            # qty? We don't set var_qty from cart to avoid confusion, but could.
            self.var_stock.set("")  # no stock info

    def add_update_cart(self):
        pid = self.var_pid.get()
        qty_str = self.var_qty.get()
        if not pid or not qty_str:
            messagebox.showerror("Error", "Select product and enter quantity", parent=self.root)
            return
        try:
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError
        except:
            messagebox.showerror("Error", "Invalid quantity", parent=self.root)
            return
        stock = int(self.var_stock.get() or 0)
        if qty > stock:
            messagebox.showerror("Error", f"Not enough stock. Available: {stock}", parent=self.root)
            return
        price = float(self.var_price.get() or 0)
        total = price * qty
        # Check if already in cart
        found = False
        for i, item in enumerate(self.cart_list):
            if item[0] == pid:
                new_qty = item[3] + qty
                if new_qty > stock:
                    messagebox.showerror("Error", "Total quantity exceeds stock", parent=self.root)
                    return
                self.cart_list[i] = (pid, self.var_pname.get(), price, new_qty, price*new_qty)
                found = True
                break
        if not found:
            self.cart_list.append((pid, self.var_pname.get(), price, qty, total))
        self.show_cart()
        self.clear_all()

    def show_cart(self):
        self.CartTable.delete(*self.CartTable.get_children())
        for item in self.cart_list:
            self.CartTable.insert('', tk.END, values=item)
        self.bill_update()

    def bill_update(self):
        self.bill_amnt = sum(item[4] for item in self.cart_list)
        self.lbl_amnt.config(text=f"Bill Amount: {self.bill_amnt:.2f}")
        # Discount based on some rule? We'll keep 0 for now; user can adjust via calculator? Not specified.
        self.discount = 0.0
        self.net_pay = self.bill_amnt - self.discount
        self.lbl_discount.config(text=f"Discount: {self.discount:.2f}")
        self.lbl_net_pay.config(text=f"Net Pay: {self.net_pay:.2f}")

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty", parent=self.root)
            return
        # Generate invoice number
        now = datetime.now()
        inv = f"INV-{now.strftime('%Y%m%d%H%M%S')}"
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")
        # Build bill text
        bill_text = f"{'='*50}\n"
        bill_text += f"Invoice: {inv}\nDate: {date_str}\n"
        bill_text += f"Customer: {self.var_cname.get()}  Contact: {self.var_contact.get()}\n"
        bill_text += f"{'-'*50}\n"
        bill_text += f"{'PID':<10}{'Name':<15}{'Price':<8}{'Qty':<5}{'Total':<10}\n"
        for item in self.cart_list:
            bill_text += f"{item[0]:<10}{item[1][:15]:<15}{item[2]:<8.2f}{item[3]:<5}{item[4]:<10.2f}\n"
        bill_text += f"{'-'*50}\n"
        bill_text += f"{'Total':>30}{self.bill_amnt:>10.2f}\n"
        bill_text += f"{'Discount':>30}{self.discount:>10.2f}\n"
        bill_text += f"{'Net Pay':>30}{self.net_pay:>10.2f}\n"
        bill_text += f"{'='*50}\n"
        self.txt_bill_area.delete("1.0", tk.END)
        self.txt_bill_area.insert(tk.END, bill_text)
        # Save to sales table and update stock
        conn = Database.get_connection()
        try:
            conn.execute("INSERT INTO sales (invoice, bill_data, date) VALUES (?,?,?)", (inv, bill_text, date_str))
            for item in self.cart_list:
                conn.execute("UPDATE product SET qty = qty - ? WHERE pid=?", (item[3], item[0]))
            conn.commit()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Error", f"Failed to save bill: {e}", parent=self.root)
            return
        messagebox.showinfo("Success", "Bill generated and saved", parent=self.root)
        self.clear_cart()

    def print_bill(self):
        bill_content = self.txt_bill_area.get("1.0", tk.END).strip()
        if not bill_content:
            messagebox.showerror("Error", "No bill to print", parent=self.root)
            return
        # Save to text file as simple print
        from tkinter import filedialog
        f_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if f_path:
            with open(f_path, 'w') as f:
                f.write(bill_content)
            messagebox.showinfo("Printed", f"Bill saved to {f_path}", parent=self.root)

    def clear_all(self):
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")

    def clear_cart(self):
        self.cart_list.clear()
        self.show_cart()
        self.clear_all()
        self.txt_bill_area.delete("1.0", tk.END)
        self.var_cname.set("")
        self.var_contact.set("")

    def perform_cal(self):
        try:
            expr = self.var_cal_input.get()
            result = eval(expr)  # simple; for demo only
            self.var_cal_input.set(str(result))
        except:
            self.var_cal_input.set("Error")

    def get_input(self, num):
        if num == 'C':
            self.var_cal_input.set("")
        elif num == '=':
            self.perform_cal()
        else:
            self.var_cal_input.set(self.var_cal_input.get() + num)

class IMS:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Inventory Management System")
        self.root.geometry("1366x768")
        self.MenuLogo = tk.PhotoImage()  # placeholder
        self.icon_side = tk.PhotoImage()
        self.icon_title = tk.PhotoImage()
        self.new_win = None
        self.new_obj = None
        self.lbl_category = None
        self.lbl_employee = None
        self.lbl_product = None
        self.lbl_sales = None
        self.lbl_supplier = None
        self.lbl_clock = None
        self.setup_dashboard()
        self.update_content()

    def setup_dashboard(self):
        # Header
        header = tk.Frame(self.root, bg="#0f4d7a", height=100)
        header.pack(side=tk.TOP, fill=tk.X)
        tk.Label(header, text="Inventory Management System", font=("times new roman", 30, "bold"), bg="#0f4d7a", fg="white").pack(side=tk.LEFT, padx=20)
        self.lbl_clock = tk.Label(header, text="", font=("times new roman", 15), bg="#0f4d7a", fg="white")
        self.lbl_clock.pack(side=tk.RIGHT, padx=20)

        # Sidebar
        sidebar = tk.Frame(self.root, bg="#2c3e50", width=200, height=700)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        btn_config = {'font': ("times new roman", 14, "bold"), 'bg': "#2c3e50", 'fg': "white",
                      'activebackground': "#1abc9c", 'bd': 0, 'width': 18, 'anchor': "w", 'padx': 20}

        self.lbl_category = tk.Button(sidebar, text="📁 Category", command=self.category, **btn_config)
        self.lbl_category.pack(fill=tk.X, pady=5)
        self.lbl_employee = tk.Button(sidebar, text="👥 Employee", command=self.employee, **btn_config)
        self.lbl_employee.pack(fill=tk.X, pady=5)
        self.lbl_product = tk.Button(sidebar, text="📦 Product", command=self.product, **btn_config)
        self.lbl_product.pack(fill=tk.X, pady=5)
        self.lbl_supplier = tk.Button(sidebar, text="🚚 Supplier", command=self.supplier, **btn_config)
        self.lbl_supplier.pack(fill=tk.X, pady=5)
        self.lbl_sales = tk.Button(sidebar, text="💰 Sales History", command=self.sales, **btn_config)
        self.lbl_sales.pack(fill=tk.X, pady=5)
        # Extra billing button (not in original diagram but needed to show billClass)
        tk.Button(sidebar, text="🛒 Billing", command=self.billing, **btn_config).pack(fill=tk.X, pady=5)

        # Main content area (optional, for future use)
        self.content = tk.Frame(self.root, bg="white")
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def open_window(self, cls, title):
        if self.new_win is not None and self.new_win.winfo_exists():
            self.new_win.destroy()
        self.new_win = tk.Toplevel(self.root)
        self.new_win.title(title)
        self.new_obj = cls(self.new_win)

    def category(self):
        self.open_window(categoryClass, "Category Management")

    def employee(self):
        self.open_window(employeeClass, "Employee Management")

    def product(self):
        self.open_window(productClass, "Product Management")

    def sales(self):
        self.open_window(salesClass, "Sales History")

    def supplier(self):
        self.open_window(supplierClass, "Supplier Management")

    def billing(self):
        self.open_window(billClass, "Billing System")

    def update_content(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.lbl_clock:
            self.lbl_clock.config(text=now)
        self.root.after(1000, self.update_content)

def main():
    init_db()
    app = IMS()
    app.root.mainloop()
    Database.close()

if __name__ == "__main__":
    main()