import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import random
import sqlite3
import os

# ─────────────────────────────────────────────
# Database helper
# ─────────────────────────────────────────────
DB_FILE = "ims.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS category (
        cat_id TEXT PRIMARY KEY,
        name TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS supplier (
        sup_invoice TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        contact TEXT,
        desc TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS employee (
        emp_id TEXT PRIMARY KEY,
        name TEXT,
        dob TEXT,
        doj TEXT,
        gender TEXT,
        contact TEXT,
        email TEXT,
        salary TEXT,
        utype TEXT,
        password TEXT,
        address TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS product (
        pid TEXT PRIMARY KEY,
        name TEXT,
        price TEXT,
        qty TEXT,
        status TEXT,
        cat TEXT,
        sup TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        invoice TEXT PRIMARY KEY,
        customer_name TEXT,
        contact TEXT,
        bill_data TEXT,
        net_pay TEXT,
        date TEXT
    )""")
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# category module
# ─────────────────────────────────────────────
class categoryClass:
    def __init__(self, root):
        self.root = root
        self.var_cat_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.im1 = None
        self.im2 = None
        self.CategoryTable = None
        self.lbl_im1 = None
        self.lbl_im2 = None
        self._build_ui()
        self.show()

    def _build_ui(self):
        self.root.title("Category Management")
        self.root.geometry("900x500")
        self.root.resizable(False, False)

        title = tk.Label(self.root, text="Category Management",
                         font=("Arial", 20, "bold"), bg="#4a90d9", fg="white",
                         pady=10)
        title.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left frame – form
        left = tk.LabelFrame(main_frame, text="Category Details",
                             font=("Arial", 12, "bold"), bg="white")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        tk.Label(left, text="Category ID", bg="white").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(left, textvariable=self.var_cat_id).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(left, text="Name", bg="white").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(left, textvariable=self.var_name).grid(row=1, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(left, bg="white")
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="Add", width=8, bg="#4a90d9", fg="white",
                  command=self.add).grid(row=0, column=0, padx=3)
        tk.Button(btn_frame, text="Delete", width=8, bg="#e74c3c", fg="white",
                  command=self.delete).grid(row=0, column=1, padx=3)
        tk.Button(btn_frame, text="Clear", width=8, bg="#95a5a6", fg="white",
                  command=self.clear).grid(row=0, column=2, padx=3)

        self.lbl_im1 = tk.Label(left, bg="white", text="[Image 1]")
        self.lbl_im1.grid(row=3, column=0, columnspan=2, pady=5)
        self.lbl_im2 = tk.Label(left, bg="white", text="[Image 2]")
        self.lbl_im2.grid(row=4, column=0, columnspan=2, pady=5)

        # Right frame – table
        right = tk.Frame(main_frame, bg="white")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        scroll_x = tk.Scrollbar(right, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(right, orient=tk.VERTICAL)
        self.CategoryTable = ttk.Treeview(right,
                                          columns=("cat_id", "name"),
                                          xscrollcommand=scroll_x.set,
                                          yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.CategoryTable.xview)
        scroll_y.config(command=self.CategoryTable.yview)

        self.CategoryTable.heading("cat_id", text="Category ID")
        self.CategoryTable.heading("name", text="Name")
        self.CategoryTable["show"] = "headings"
        self.CategoryTable.pack(fill=tk.BOTH, expand=True)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)

    def add(self):
        if not self.var_cat_id.get() or not self.var_name.get():
            messagebox.showerror("Error", "All fields are required", parent=self.root)
            return
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO category VALUES (?,?)",
                      (self.var_cat_id.get(), self.var_name.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category added successfully", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)

    def delete(self):
        if not self.var_cat_id.get():
            messagebox.showerror("Error", "Select a category to delete", parent=self.root)
            return
        if messagebox.askyesno("Confirm", "Delete this category?", parent=self.root):
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute("DELETE FROM category WHERE cat_id=?", (self.var_cat_id.get(),))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Category deleted", parent=self.root)
                self.clear()
                self.show()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)

    def clear(self):
        self.var_cat_id.set("")
        self.var_name.set("")

    def get_data(self, ev):
        selected = self.CategoryTable.focus()
        if not selected:
            return
        row = self.CategoryTable.item(selected)["values"]
        if row:
            self.var_cat_id.set(row[0])
            self.var_name.set(row[1])

    def show(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM category")
        rows = c.fetchall()
        conn.close()
        self.CategoryTable.delete(*self.CategoryTable.get_children())
        for row in rows:
            self.CategoryTable.insert("", tk.END, values=row)


# ─────────────────────────────────────────────
# supplier module
# ─────────────────────────────────────────────
class supplierClass:
    def __init__(self, root):
        self.root = root
        self.var_sup_invoice = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()
        self.txt_desc = None
        self.SupplierTable = None
        self._build_ui()
        self.show()

    def _build_ui(self):
        self.root.title("Supplier Management")
        self.root.geometry("1000x550")
        self.root.resizable(False, False)

        title = tk.Label(self.root, text="Supplier Management",
                         font=("Arial", 20, "bold"), bg="#4a90d9", fg="white", pady=10)
        title.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.LabelFrame(main_frame, text="Supplier Details",
                             font=("Arial", 12, "bold"), bg="white")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        fields = [("Invoice No", self.var_sup_invoice),
                  ("Name", self.var_name),
                  ("Contact", self.var_contact)]
        for i, (lbl, var) in enumerate(fields):
            tk.Label(left, text=lbl, bg="white").grid(row=i, column=0, padx=5, pady=5, sticky="w")
            tk.Entry(left, textvariable=var).grid(row=i, column=1, padx=5, pady=5)

        tk.Label(left, text="Description", bg="white").grid(row=3, column=0, padx=5, pady=5, sticky="nw")
        self.txt_desc = tk.Text(left, width=25, height=5)
        self.txt_desc.grid(row=3, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(left, bg="white")
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        for text, cmd, color in [("Add", self.add, "#4a90d9"),
                                  ("Update", self.update, "#27ae60"),
                                  ("Delete", self.delete, "#e74c3c"),
                                  ("Clear", self.clear, "#95a5a6")]:
            tk.Button(btn_frame, text=text, width=7, bg=color, fg="white",
                      command=cmd).pack(side=tk.LEFT, padx=2)

        # Search
        search_frame = tk.Frame(left, bg="white")
        search_frame.grid(row=5, column=0, columnspan=2, pady=5)
        tk.Label(search_frame, text="Search By", bg="white").pack(side=tk.LEFT)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Invoice No", "Name", "Contact"], width=10).pack(side=tk.LEFT, padx=3)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, width=12).pack(side=tk.LEFT, padx=3)
        tk.Button(search_frame, text="Search", bg="#4a90d9", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=2)
        tk.Button(search_frame, text="Show All", bg="#95a5a6", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=2)

        # Table
        right = tk.Frame(main_frame, bg="white")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        cols = ("sup_invoice", "name", "contact", "desc")
        scroll_x = tk.Scrollbar(right, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(right, orient=tk.VERTICAL)
        self.SupplierTable = ttk.Treeview(right, columns=cols,
                                          xscrollcommand=scroll_x.set,
                                          yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.SupplierTable.xview)
        scroll_y.config(command=self.SupplierTable.yview)
        self.SupplierTable["show"] = "headings"
        for col in cols:
            self.SupplierTable.heading(col, text=col.replace("_", " ").title())
            self.SupplierTable.column(col, width=120)
        self.SupplierTable.pack(fill=tk.BOTH, expand=True)
        self.SupplierTable.bind("<ButtonRelease-1>", self.get_data)

    def add(self):
        if not self.var_sup_invoice.get() or not self.var_name.get():
            messagebox.showerror("Error", "Invoice and Name are required", parent=self.root)
            return
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO supplier VALUES (?,?,?,?)",
                      (self.var_sup_invoice.get(), self.var_name.get(),
                       self.var_contact.get(), self.txt_desc.get("1.0", tk.END).strip()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier added", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)

    def update(self):
        if not self.var_sup_invoice.get():
            messagebox.showerror("Error", "Select a supplier to update", parent=self.root)
            return
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("UPDATE supplier SET name=?, contact=?, desc=? WHERE sup_invoice=?",
                      (self.var_name.get(), self.var_contact.get(),
                       self.txt_desc.get("1.0", tk.END).strip(), self.var_sup_invoice.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier updated", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)

    def delete(self):
        if not self.var_sup_invoice.get():
            messagebox.showerror("Error", "Select a supplier to delete", parent=self.root)
            return
        if messagebox.askyesno("Confirm", "Delete this supplier?", parent=self.root):
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute("DELETE FROM supplier WHERE sup_invoice=?", (self.var_sup_invoice.get(),))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Supplier deleted", parent=self.root)
                self.clear()
                self.show()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)

    def clear(self):
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete("1.0", tk.END)

    def get_data(self, ev):
        selected = self.SupplierTable.focus()
        if not selected:
            return
        row = self.SupplierTable.item(selected)["values"]
        if row:
            self.var_sup_invoice.set(row[0])
            self.var_name.set(row[1])
            self.var_contact.set(row[2])
            self.txt_desc.delete("1.0", tk.END)
            self.txt_desc.insert(tk.END, row[3] if row[3] else "")

    def search(self):
        if not self.var_searchtxt.get():
            messagebox.showerror("Error", "Enter search text", parent=self.root)
            return
        col_map = {"Invoice No": "sup_invoice", "Name": "name", "Contact": "contact"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        c = conn.cursor()
        c.execute(f"SELECT * FROM supplier WHERE {col} LIKE ?",
                  (f"%{self.var_searchtxt.get()}%",))
        rows = c.fetchall()
        conn.close()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert("", tk.END, values=row)

    def show(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM supplier")
        rows = c.fetchall()
        conn.close()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert("", tk.END, values=row)


# ─────────────────────────────────────────────
# employee module
# ─────────────────────────────────────────────
class employeeClass:
    def __init__(self, root):
        self.root = root
        self.var_emp_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_dob = tk.StringVar()
        self.var_doj = tk.StringVar()
        self.var_gender = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_salary = tk.StringVar()
        self.var_utype = tk.StringVar()
        self.var_pass = tk.StringVar()
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()
        self.txt_address = None
        self.EmployeeTable = None
        self._build_ui()
        self.show()

    def _build_ui(self):
        self.root.title("Employee Management")
        self.root.geometry("1100x600")
        self.root.resizable(False, False)

        title = tk.Label(self.root, text="Employee Management",
                         font=("Arial", 20, "bold"), bg="#4a90d9", fg="white", pady=10)
        title.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.LabelFrame(main_frame, text="Employee Details",
                             font=("Arial", 12, "bold"), bg="white")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        fields = [
            ("Employee ID", self.var_emp_id),
            ("Name", self.var_name),
            ("DOB", self.var_dob),
            ("DOJ", self.var_doj),
            ("Contact", self.var_contact),
            ("Email", self.var_email),
            ("Salary", self.var_salary),
            ("Password", self.var_pass),
        ]
        for i, (lbl, var) in enumerate(fields):
            tk.Label(left, text=lbl, bg="white").grid(row=i, column=0, padx=5, pady=3, sticky="w")
            tk.Entry(left, textvariable=var).grid(row=i, column=1, padx=5, pady=3)

        row_offset = len(fields)
        tk.Label(left, text="Gender", bg="white").grid(row=row_offset, column=0, padx=5, pady=3, sticky="w")
        ttk.Combobox(left, textvariable=self.var_gender,
                     values=["Male", "Female", "Other"], width=17).grid(row=row_offset, column=1, padx=5, pady=3)

        tk.Label(left, text="User Type", bg="white").grid(row=row_offset+1, column=0, padx=5, pady=3, sticky="w")
        ttk.Combobox(left, textvariable=self.var_utype,
                     values=["Admin", "Employee"], width=17).grid(row=row_offset+1, column=1, padx=5, pady=3)

        tk.Label(left, text="Address", bg="white").grid(row=row_offset+2, column=0, padx=5, pady=3, sticky="nw")
        self.txt_address = tk.Text(left, width=20, height=4)
        self.txt_address.grid(row=row_offset+2, column=1, padx=5, pady=3)

        btn_frame = tk.Frame(left, bg="white")
        btn_frame.grid(row=row_offset+3, column=0, columnspan=2, pady=8)
        for text, cmd, color in [("Add", self.add, "#4a90d9"),
                                  ("Update", self.update, "#27ae60"),
                                  ("Delete", self.delete, "#e74c3c"),
                                  ("Clear", self.clear, "#95a5a6")]:
            tk.Button(btn_frame, text=text, width=7, bg=color, fg="white",
                      command=cmd).pack(side=tk.LEFT, padx=2)

        search_frame = tk.Frame(left, bg="white")
        search_frame.grid(row=row_offset+4, column=0, columnspan=2, pady=5)
        tk.Label(search_frame, text="Search By", bg="white").pack(side=tk.LEFT)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Employee ID", "Name", "Contact"], width=10).pack(side=tk.LEFT, padx=2)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(search_frame, text="Search", bg="#4a90d9", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=2)
        tk.Button(search_frame, text="Show All", bg="#95a5a6", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=2)

        right = tk.Frame(main_frame, bg="white")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        cols = ("emp_id", "name", "dob", "doj", "gender", "contact", "email", "salary", "utype", "password", "address")
        scroll_x = tk.Scrollbar(right, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(right, orient=tk.VERTICAL)
        self.EmployeeTable = ttk.Treeview(right, columns=cols,
                                          xscrollcommand=scroll_x.set,
                                          yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.EmployeeTable.xview)
        scroll_y.config(command=self.EmployeeTable.yview)
        self.EmployeeTable["show"] = "headings"
        for col in cols:
            self.EmployeeTable.heading(col, text=col.replace("_", " ").title())
            self.EmployeeTable.column(col, width=90)
        self.EmployeeTable.pack(fill=tk.BOTH, expand=True)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)

    def add(self):
        if not self.var_emp_id.get() or not self.var_name.get():
            messagebox.showerror("Error", "Employee ID and Name are required", parent=self.root)
            return
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO employee VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (self.var_emp_id.get(), self.var_name.get(), self.var_dob.get(),
                       self.var_doj.get(), self.var_gender.get(), self.var_contact.get(),
                       self.var_email.get(), self.var_salary.get(), self.var_utype.get(),
                       self.var_pass.get(), self.txt_address.get("1.0", tk.END).strip()))
            conn.commit()
            conn.close()
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
            conn = get_connection()
            c = conn.cursor()
            c.execute("""UPDATE employee SET name=?,dob=?,doj=?,gender=?,contact=?,
                         email=?,salary=?,utype=?,password=?,address=? WHERE emp_id=?""",
                      (self.var_name.get(), self.var_dob.get(), self.var_doj.get(),
                       self.var_gender.get(), self.var_contact.get(), self.var_email.get(),
                       self.var_salary.get(), self.var_utype.get(), self.var_pass.get(),
                       self.txt_address.get("1.0", tk.END).strip(), self.var_emp_id.get()))
            conn.commit()
            conn.close()
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
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute("DELETE FROM employee WHERE emp_id=?", (self.var_emp_id.get(),))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Employee deleted", parent=self.root)
                self.clear()
                self.show()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)

    def clear(self):
        for var in [self.var_emp_id, self.var_name, self.var_dob, self.var_doj,
                    self.var_gender, self.var_contact, self.var_email, self.var_salary,
                    self.var_utype, self.var_pass]:
            var.set("")
        self.txt_address.delete("1.0", tk.END)

    def get_data(self, ev):
        selected = self.EmployeeTable.focus()
        if not selected:
            return
        row = self.EmployeeTable.item(selected)["values"]
        if row:
            self.var_emp_id.set(row[0])
            self.var_name.set(row[1])
            self.var_dob.set(row[2])
            self.var_doj.set(row[3])
            self.var_gender.set(row[4])
            self.var_contact.set(row[5])
            self.var_email.set(row[6])
            self.var_salary.set(row[7])
            self.var_utype.set(row[8])
            self.var_pass.set(row[9])
            self.txt_address.delete("1.0", tk.END)
            self.txt_address.insert(tk.END, row[10] if row[10] else "")

    def search(self):
        if not self.var_searchtxt.get():
            messagebox.showerror("Error", "Enter search text", parent=self.root)
            return
        col_map = {"Employee ID": "emp_id", "Name": "name", "Contact": "contact"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        c = conn.cursor()
        c.execute(f"SELECT * FROM employee WHERE {col} LIKE ?",
                  (f"%{self.var_searchtxt.get()}%",))
        rows = c.fetchall()
        conn.close()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for row in rows:
            self.EmployeeTable.insert("", tk.END, values=row)

    def show(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM employee")
        rows = c.fetchall()
        conn.close()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for row in rows:
            self.EmployeeTable.insert("", tk.END, values=row)


# ─────────────────────────────────────────────
# product module
# ─────────────────────────────────────────────
class productClass:
    def __init__(self, root):
        self.root = root
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
        self.ProductTable = None
        self._build_ui()
        self.fetch_cat_sup()
        self.show()

    def _build_ui(self):
        self.root.title("Product Management")
        self.root.geometry("1100x580")
        self.root.resizable(False, False)

        title = tk.Label(self.root, text="Product Management",
                         font=("Arial", 20, "bold"), bg="#4a90d9", fg="white", pady=10)
        title.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.LabelFrame(main_frame, text="Product Details",
                             font=("Arial", 12, "bold"), bg="white")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        tk.Label(left, text="Product ID", bg="white").grid(row=0, column=0, padx=5, pady=4, sticky="w")
        tk.Entry(left, textvariable=self.var_pid).grid(row=0, column=1, padx=5, pady=4)

        tk.Label(left, text="Name", bg="white").grid(row=1, column=0, padx=5, pady=4, sticky="w")
        tk.Entry(left, textvariable=self.var_name).grid(row=1, column=1, padx=5, pady=4)

        tk.Label(left, text="Price", bg="white").grid(row=2, column=0, padx=5, pady=4, sticky="w")
        tk.Entry(left, textvariable=self.var_price).grid(row=2, column=1, padx=5, pady=4)

        tk.Label(left, text="Quantity", bg="white").grid(row=3, column=0, padx=5, pady=4, sticky="w")
        tk.Entry(left, textvariable=self.var_qty).grid(row=3, column=1, padx=5, pady=4)

        tk.Label(left, text="Status", bg="white").grid(row=4, column=0, padx=5, pady=4, sticky="w")
        self.cmb_status = ttk.Combobox(left, textvariable=self.var_status,
                                       values=["Active", "Inactive"], width=17)
        self.cmb_status.grid(row=4, column=1, padx=5, pady=4)

        tk.Label(left, text="Category", bg="white").grid(row=5, column=0, padx=5, pady=4, sticky="w")
        self.cmb_cat = ttk.Combobox(left, textvariable=self.var_cat, width=17)
        self.cmb_cat.grid(row=5, column=1, padx=5, pady=4)

        tk.Label(left, text="Supplier", bg="white").grid(row=6, column=0, padx=5, pady=4, sticky="w")
        self.cmb_sup = ttk.Combobox(left, textvariable=self.var_sup, width=17)
        self.cmb_sup.grid(row=6, column=1, padx=5, pady=4)

        btn_frame = tk.Frame(left, bg="white")
        btn_frame.grid(row=7, column=0, columnspan=2, pady=8)
        for text, cmd, color in [("Add", self.add, "#4a90d9"),
                                  ("Update", self.update, "#27ae60"),
                                  ("Delete", self.delete, "#e74c3c"),
                                  ("Clear", self.clear, "#95a5a6")]:
            tk.Button(btn_frame, text=text, width=7, bg=color, fg="white",
                      command=cmd).pack(side=tk.LEFT, padx=2)

        search_frame = tk.Frame(left, bg="white")
        search_frame.grid(row=8, column=0, columnspan=2, pady=5)
        tk.Label(search_frame, text="Search By", bg="white").pack(side=tk.LEFT)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Product ID", "Name", "Status"], width=10).pack(side=tk.LEFT, padx=2)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(search_frame, text="Search", bg="#4a90d9", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=2)
        tk.Button(search_frame, text="Show All", bg="#95a5a6", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=2)

        right = tk.Frame(main_frame, bg="white")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        cols = ("pid", "name", "price", "qty", "status", "cat", "sup")
        scroll_x = tk.Scrollbar(right, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(right, orient=tk.VERTICAL)
        self.ProductTable = ttk.Treeview(right, columns=cols,
                                         xscrollcommand=scroll_x.set,
                                         yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.ProductTable.xview)
        scroll_y.config(command=self.ProductTable.yview)
        self.ProductTable["show"] = "headings"
        for col in cols:
            self.ProductTable.heading(col, text=col.replace("_", " ").title())
            self.ProductTable.column(col, width=100)
        self.ProductTable.pack(fill=tk.BOTH, expand=True)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)

    def fetch_cat_sup(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM category")
        self.cat_list = [row[0] for row in c.fetchall()]
        c.execute("SELECT name FROM supplier")
        self.sup_list = [row[0] for row in c.fetchall()]
        conn.close()
        self.cmb_cat["values"] = self.cat_list
        self.cmb_sup["values"] = self.sup_list

    def add(self):
        if not self.var_pid.get() or not self.var_name.get():
            messagebox.showerror("Error", "Product ID and Name are required", parent=self.root)
            return
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO product VALUES (?,?,?,?,?,?,?)",
                      (self.var_pid.get(), self.var_name.get(), self.var_price.get(),
                       self.var_qty.get(), self.var_status.get(), self.var_cat.get(),
                       self.var_sup.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product added", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)

    def update(self):
        if not self.var_pid.get():
            messagebox.showerror("Error", "Select a product to update", parent=self.root)
            return
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("UPDATE product SET name=?,price=?,qty=?,status=?,cat=?,sup=? WHERE pid=?",
                      (self.var_name.get(), self.var_price.get(), self.var_qty.get(),
                       self.var_status.get(), self.var_cat.get(), self.var_sup.get(),
                       self.var_pid.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product updated", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)

    def delete(self):
        if not self.var_pid.get():
            messagebox.showerror("Error", "Select a product to delete", parent=self.root)
            return
        if messagebox.askyesno("Confirm", "Delete this product?", parent=self.root):
            try:
                conn = get_connection()
                c = conn.cursor()
                c.execute("DELETE FROM product WHERE pid=?", (self.var_pid.get(),))
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "Product deleted", parent=self.root)
                self.clear()
                self.show()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)

    def clear(self):
        for var in [self.var_pid, self.var_name, self.var_price, self.var_qty,
                    self.var_status, self.var_cat, self.var_sup]:
            var.set("")

    def get_data(self, ev):
        selected = self.ProductTable.focus()
        if not selected:
            return
        row = self.ProductTable.item(selected)["values"]
        if row:
            self.var_pid.set(row[0])
            self.var_name.set(row[1])
            self.var_price.set(row[2])
            self.var_qty.set(row[3])
            self.var_status.set(row[4])
            self.var_cat.set(row[5])
            self.var_sup.set(row[6])

    def search(self):
        if not self.var_searchtxt.get():
            messagebox.showerror("Error", "Enter search text", parent=self.root)
            return
        col_map = {"Product ID": "pid", "Name": "name", "Status": "status"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        c = conn.cursor()
        c.execute(f"SELECT * FROM product WHERE {col} LIKE ?",
                  (f"%{self.var_searchtxt.get()}%",))
        rows = c.fetchall()
        conn.close()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for row in rows:
            self.ProductTable.insert("", tk.END, values=row)

    def show(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM product")
        rows = c.fetchall()
        conn.close()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for row in rows:
            self.ProductTable.insert("", tk.END, values=row)


# ─────────────────────────────────────────────
# sales module
# ─────────────────────────────────────────────
class salesClass:
    def __init__(self, root):
        self.root = root
        self.var_invoice = tk.StringVar()
        self.blll_list = []
        self.bill_photo = None
        self.Sales_List = None
        self.bill_area = None
        self._build_ui()
        self.show()

    def _build_ui(self):
        self.root.title("Sales Records")
        self.root.geometry("900x550")
        self.root.resizable(False, False)

        title = tk.Label(self.root, text="Sales Records",
                         font=("Arial", 20, "bold"), bg="#4a90d9", fg="white", pady=10)
        title.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.LabelFrame(main_frame, text="Sales List",
                             font=("Arial", 12, "bold"), bg="white")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        search_frame = tk.Frame(left, bg="white")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Invoice No", bg="white").pack(side=tk.LEFT)
        tk.Entry(search_frame, textvariable=self.var_invoice, width=15).pack(side=tk.LEFT, padx=3)
        tk.Button(search_frame, text="Search", bg="#4a90d9", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=2)
        tk.Button(search_frame, text="Show All", bg="#95a5a6", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=2)
        tk.Button(search_frame, text="Clear", bg="#e74c3c", fg="white",
                  command=self.clear).pack(side=tk.LEFT, padx=2)

        scroll_y = tk.Scrollbar(left, orient=tk.VERTICAL)
        self.Sales_List = tk.Listbox(left, yscrollcommand=scroll_y.set,
                                     width=30, height=20, font=("Arial", 11))
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_y.config(command=self.Sales_List.yview)
        self.Sales_List.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.Sales_List.bind("<ButtonRelease-1>", self.get_data)

        right = tk.LabelFrame(main_frame, text="Bill Details",
                              font=("Arial", 12, "bold"), bg="white")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        scroll_y2 = tk.Scrollbar(right, orient=tk.VERTICAL)
        self.bill_area = tk.Text(right, yscrollcommand=scroll_y2.set,
                                 font=("Courier", 11), state=tk.DISABLED)
        scroll_y2.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_y2.config(command=self.bill_area.yview)
        self.bill_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def show(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT invoice FROM sales")
        rows = c.fetchall()
        conn.close()
        self.blll_list = [row[0] for row in rows]
        self.Sales_List.delete(0, tk.END)
        for inv in self.blll_list:
            self.Sales_List.insert(tk.END, inv)

    def search(self):
        if not self.var_invoice.get():
            messagebox.showerror("Error", "Enter invoice number", parent=self.root)
            return
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT invoice FROM sales WHERE invoice LIKE ?",
                  (f"%{self.var_invoice.get()}%",))
        rows = c.fetchall()
        conn.close()
        self.Sales_List.delete(0, tk.END)
        for row in rows:
            self.Sales_List.insert(tk.END, row[0])

    def get_data(self, ev):
        selected = self.Sales_List.curselection()
        if not selected:
            return
        invoice = self.Sales_List.get(selected[0])
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM sales WHERE invoice=?", (invoice,))
        row = c.fetchone()
        conn.close()
        if row:
            self.bill_area.config(state=tk.NORMAL)
            self.bill_area.delete("1.0", tk.END)
            self.bill_area.insert(tk.END, row[3] if row[3] else "")
            self.bill_area.config(state=tk.DISABLED)

    def clear(self):
        self.var_invoice.set("")
        self.bill_area.config(state=tk.NORMAL)
        self.bill_area.delete("1.0", tk.END)
        self.bill_area.config(state=tk.DISABLED)
        self.show()


# ─────────────────────────────────────────────
# billing module
# ─────────────────────────────────────────────
class billClass:
    def __init__(self, root):
        self.root = root
        self.var_pid = tk.StringVar()
        self.var_pname = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_stock = tk.StringVar()
        self.var_search = tk.StringVar()
        self.var_cname = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_cal_input = tk.StringVar()

        self.bill_amnt: int = 0
        self.discount: float = 5.0
        self.siscount: int = 0
        self.net_pay = 0
        self.chk_print: int = 0
        self.cart_list: list = []
        self.invoice = None

        self.product_Table = None
        self.CartTable = None
        self.txt_bill_area = None
        self.txt_cal_input = None
        self.lbl_amnt = None
        self.lbl_discount = None
        self.lbl_net_pay = None
        self.lbl_inStock = None
        self.lbl_clock = None
        self.cartTitle = None
        self.icon_title = None

        self._build_ui()
        self.show()
        self.update_date_time()

    def _build_ui(self):
        self.root.title("Billing System")
        self.root.geometry("1300x700")
        self.root.resizable(False, False)

        # Top bar
        top = tk.Frame(self.root, bg="#4a90d9", pady=5)
        top.pack(fill=tk.X)
        tk.Label(top, text="Billing / POS System", font=("Arial", 20, "bold"),
                 bg="#4a90d9", fg="white").pack(side=tk.LEFT, padx=10)
        self.lbl_clock = tk.Label(top, text="", font=("Arial", 12),
                                  bg="#4a90d9", fg="white")
        self.lbl_clock.pack(side=tk.RIGHT, padx=10)

        main = tk.Frame(self.root, bg="white")
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ── Left: product search + table ──
        left = tk.LabelFrame(main, text="Products", font=("Arial", 11, "bold"), bg="white")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        sf = tk.Frame(left, bg="white")
        sf.pack(fill=tk.X, padx=5, pady=3)
        tk.Label(sf, text="Search", bg="white").pack(side=tk.LEFT)
        tk.Entry(sf, textvariable=self.var_search, width=18).pack(side=tk.LEFT, padx=3)
        tk.Button(sf, text="Search", bg="#4a90d9", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=2)
        tk.Button(sf, text="Show All", bg="#95a5a6", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=2)

        cols_p = ("pid", "name", "price", "qty", "status")
        scroll_yp = tk.Scrollbar(left, orient=tk.VERTICAL)
        self.product_Table = ttk.Treeview(left, columns=cols_p,
                                          yscrollcommand=scroll_yp.set, height=12)
        scroll_yp.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_yp.config(command=self.product_Table.yview)
        self.product_Table["show"] = "headings"
        for col in cols_p:
            self.product_Table.heading(col, text=col.title())
            self.product_Table.column(col, width=80)
        self.product_Table.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)

        # Product detail + add to cart
        detail = tk.Frame(left, bg="white")
        detail.pack(fill=tk.X, padx=5, pady=3)
        for i, (lbl, var) in enumerate([("PID", self.var_pid), ("Name", self.var_pname),
                                         ("Price", self.var_price), ("Qty", self.var_qty)]):
            tk.Label(detail, text=lbl, bg="white", width=5, anchor="w").grid(row=i, column=0, padx=3, pady=2)
            tk.Entry(detail, textvariable=var, width=15).grid(row=i, column=1, padx=3, pady=2)

        self.lbl_inStock = tk.Label(detail, text="In Stock: 0", bg="white", fg="#27ae60",
                                    font=("Arial", 10, "bold"))
        self.lbl_inStock.grid(row=4, column=0, columnspan=2, pady=3)

        tk.Button(detail, text="Add to Cart", bg="#27ae60", fg="white", width=18,
                  command=self.add_update_cart).grid(row=5, column=0, columnspan=2, pady=5)

        # ── Middle: cart ──
        mid = tk.LabelFrame(main, text="Cart", font=("Arial", 11, "bold"), bg="white")
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Customer info
        cust = tk.Frame(mid, bg="white")
        cust.pack(fill=tk.X, padx=5, pady=3)
        tk.Label(cust, text="Customer Name", bg="white").grid(row=0, column=0, padx=3, pady=2, sticky="w")
        tk.Entry(cust, textvariable=self.var_cname, width=20).grid(row=0, column=1, padx=3, pady=2)
        tk.Label(cust, text="Contact", bg="white").grid(row=0, column=2, padx=3, pady=2, sticky="w")
        tk.Entry(cust, textvariable=self.var_contact, width=15).grid(row=0, column=3, padx=3, pady=2)

        self.cartTitle = tk.Label(mid, text="Cart Items", font=("Arial", 11, "bold"), bg="white")
        self.cartTitle.pack()

        cols_c = ("pid", "name", "price", "qty", "total")
        scroll_yc = tk.Scrollbar(mid, orient=tk.VERTICAL)
        self.CartTable = ttk.Treeview(mid, columns=cols_c,
                                      yscrollcommand=scroll_yc.set, height=10)
        scroll_yc.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_yc.config(command=self.CartTable.yview)
        self.CartTable["show"] = "headings"
        for col in cols_c:
            self.CartTable.heading(col, text=col.title())
            self.CartTable.column(col, width=90)
        self.CartTable.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        # Totals
        tot = tk.Frame(mid, bg="white")
        tot.pack(fill=tk.X, padx=5, pady=3)
        self.lbl_amnt = tk.Label(tot, text="Total: $0.00", bg="white",
                                 font=("Arial", 11, "bold"))
        self.lbl_amnt.grid(row=0, column=0, padx=10)
        self.lbl_discount = tk.Label(tot, text=f"Discount: {self.discount}%", bg="white",
                                     font=("Arial", 11, "bold"))
        self.lbl_discount.grid(row=0, column=1, padx=10)
        self.lbl_net_pay = tk.Label(tot, text="Net Pay: $0.00", bg="white",
                                    font=("Arial", 11, "bold"), fg="#e74c3c")
        self.lbl_net_pay.grid(row=0, column=2, padx=10)

        btn_cart = tk.Frame(mid, bg="white")
        btn_cart.pack(fill=tk.X, padx=5, pady=3)
        for text, cmd, color in [("Generate Bill", self.generate_bill, "#4a90d9"),
                                  ("Clear Cart", self.clear_cart, "#e74c3c"),
                                  ("Clear All", self.clear_all, "#95a5a6"),
                                  ("Print Bill", self.print_bill, "#27ae60")]:
            tk.Button(btn_cart, text=text, bg=color, fg="white",
                      command=cmd).pack(side=tk.LEFT, padx=3)

        # ── Right: bill area + calculator ──
        right = tk.LabelFrame(main, text="Bill", font=("Arial", 11, "bold"), bg="white")
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        self.txt_bill_area = tk.Text(right, width=38, height=22, font=("Courier", 10))
        self.txt_bill_area.pack(padx=5, pady=5)

        # Calculator
        cal_frame = tk.LabelFrame(right, text="Calculator", bg="white",
                                  font=("Arial", 10, "bold"))
        cal_frame.pack(fill=tk.X, padx=5, pady=3)

        self.txt_cal_input = tk.Entry(cal_frame, textvariable=self.var_cal_input,
                                      font=("Arial", 13), justify="right")
        self.txt_cal_input.grid(row=0, column=0, columnspan=4, padx=5, pady=3, sticky="ew")

        buttons = [
            ("7", "8", "9", "/"),
            ("4", "5", "6", "*"),
            ("1", "2", "3", "-"),
            ("0", ".", "=", "+"),
        ]
        for r, row in enumerate(buttons):
            for col_i, btn_text in enumerate(row):
                if btn_text == "=":
                    tk.Button(cal_frame, text=btn_text, width=4, bg="#4a90d9", fg="white",
                              command=self.perform_cal).grid(row=r+1, column=col_i, padx=2, pady=2)
                else:
                    tk.Button(cal_frame, text=btn_text, width=4,
                              command=lambda t=btn_text: self.get_input(t)).grid(row=r+1, column=col_i, padx=2, pady=2)

        tk.Button(cal_frame, text="Clear", width=18, bg="#e74c3c", fg="white",
                  command=self.clear_cal).grid(row=5, column=0, columnspan=4, padx=2, pady=2)

    # ── Bill sections ──
    def bill_top(self):
        self.txt_bill_area.delete("1.0", tk.END)
        self.invoice = f"INV{random.randint(1000, 9999)}"
        now = datetime.datetime.now()
        top = f"""
{'='*40}
      INVENTORY MANAGEMENT SYSTEM
{'='*40}
Invoice No : {self.invoice}
Date       : {now.strftime('%d/%m/%Y')}
Time       : {now.strftime('%H:%M:%S')}
Customer   : {self.var_cname.get()}
Contact    : {self.var_contact.get()}
{'='*40}
{'Item':<15}{'Qty':>5}{'Price':>8}{'Total':>10}
{'-'*40}
"""
        self.txt_bill_area.insert(tk.END, top)

    def bill_middle(self):
        for item in self.cart_list:
            line = f"{item[1]:<15}{item[3]:>5}{float(item[2]):>8.2f}{float(item[4]):>10.2f}\n"
            self.txt_bill_area.insert(tk.END, line)

    def bill_bottom(self):
        bottom = f"""
{'-'*40}
{'Sub Total':>30} : ${self.bill_amnt:.2f}
{'Discount':>30} : {self.discount}%
{'Net Pay':>30} : ${self.net_pay:.2f}
{'='*40}
     Thank you for shopping with us!
{'='*40}
"""
        self.txt_bill_area.insert(tk.END, bottom)

    def bill_update(self):
        self.bill_amnt = sum(float(item[4]) for item in self.cart_list)
        self.siscount = self.bill_amnt * self.discount / 100
        self.net_pay = self.bill_amnt - self.siscount
        self.lbl_amnt.config(text=f"Total: ${self.bill_amnt:.2f}")
        self.lbl_discount.config(text=f"Discount({self.discount}%): ${self.siscount:.2f}")
        self.lbl_net_pay.config(text=f"Net Pay: ${self.net_pay:.2f}")

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty", parent=self.root)
            return
        if not self.var_cname.get():
            messagebox.showerror("Error", "Enter customer name", parent=self.root)
            return
        self.bill_top()
        self.bill_middle()
        self.bill_bottom()
        # Save to DB
        bill_data = self.txt_bill_area.get("1.0", tk.END)
        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO sales VALUES (?,?,?,?,?,?)",
                      (self.invoice, self.var_cname.get(), self.var_contact.get(),
                       bill_data, str(self.net_pay), now))
            # Update product quantities
            for item in self.cart_list:
                c.execute("UPDATE product SET qty=qty-? WHERE pid=?",
                          (int(item[3]), item[0]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Bill generated and saved", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)

    def print_bill(self):
        if not self.txt_bill_area.get("1.0", tk.END).strip():
            messagebox.showerror("Error", "Generate bill first", parent=self.root)
            return
        messagebox.showinfo("Print", "Bill sent to printer (simulated)", parent=self.root)

    def add_update_cart(self):
        if not self.var_pid.get() or not self.var_qty.get():
            messagebox.showerror("Error", "Select a product and enter quantity", parent=self.root)
            return
        try:
            qty = int(self.var_qty.get())
            price = float(self.var_price.get())
            stock = int(self.var_stock.get()) if self.var_stock.get() else 0
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity or price", parent=self.root)
            return

        if qty > stock:
            messagebox.showerror("Error", f"Only {stock} items in stock", parent=self.root)
            return

        total = qty * price
        # Check if already in cart
        for i, item in enumerate(self.cart_list):
            if item[0] == self.var_pid.get():
                self.cart_list[i] = (self.var_pid.get(), self.var_pname.get(),
                                     str(price), str(qty), str(total))
                self.show_cart()
                self.bill_update()
                return

        self.cart_list.append((self.var_pid.get(), self.var_pname.get(),
                               str(price), str(qty), str(total)))
        self.show_cart()
        self.bill_update()

    def show_cart(self):
        self.CartTable.delete(*self.CartTable.get_children())
        for item in self.cart_list:
            self.CartTable.insert("", tk.END, values=item)

    def clear_cart(self):
        self.cart_list = []
        self.show_cart()
        self.bill_amnt = 0
        self.net_pay = 0
        self.lbl_amnt.config(text="Total: $0.00")
        self.lbl_discount.config(text=f"Discount: {self.discount}%")
        self.lbl_net_pay.config(text="Net Pay: $0.00")

    def clear_all(self):
        self.clear_cart()
        self.var_cname.set("")
        self.var_contact.set("")
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")
        self.txt_bill_area.delete("1.0", tk.END)

    def get_data(self, ev):
        selected = self.product_Table.focus()
        if not selected:
            return
        row = self.product_Table.item(selected)["values"]
        if row:
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_stock.set(row[3])
            self.lbl_inStock.config(text=f"In Stock: {row[3]}")
            self.var_qty.set("")

    def get_data_cart(self, ev):
        selected = self.CartTable.focus()
        if not selected:
            return
        row = self.CartTable.item(selected)["values"]
        if row:
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_qty.set(row[3])

    def search(self):
        if not self.var_search.get():
            self.show()
            return
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT pid,name,price,qty,status FROM product WHERE name LIKE ? OR pid LIKE ?",
                  (f"%{self.var_search.get()}%", f"%{self.var_search.get()}%"))
        rows = c.fetchall()
        conn.close()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", tk.END, values=row)

    def show(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT pid,name,price,qty,status FROM product WHERE status='Active'")
        rows = c.fetchall()
        conn.close()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", tk.END, values=row)

    def get_input(self, num):
        current = self.var_cal_input.get()
        self.var_cal_input.set(current + str(num))

    def perform_cal(self):
        try:
            result = eval(self.var_cal_input.get())
            self.var_cal_input.set(str(result))
        except Exception:
            self.var_cal_input.set("Error")

    def clear_cal(self):
        self.var_cal_input.set("")

    def update_date_time(self):
        now = datetime.datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
        self.lbl_clock.config(text=now)
        self.root.after(1000, self.update_date_time)


# ─────────────────────────────────────────────
# dashboard module
# ─────────────────────────────────────────────
class IMS:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("1100x650")
        self.root.resizable(False, False)
        self.root.config(bg="#f0f0f0")

        self.MenuLogo = None
        self.icon_side = None
        self.icon_title = None
        self.new_obj = None
        self.new_win = None

        self.lbl_clock = None
        self.lbl_category = None
        self.lbl_employee = None
        self.lbl_product = None
        self.lbl_sales = None
        self.lbl_supplier = None

        self._build_ui()
        self.update_content()

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#4a90d9", pady=10)
        header.pack(fill=tk.X)
        tk.Label(header, text="Inventory Management System",
                 font=("Arial", 24, "bold"), bg="#4a90d9", fg="white").pack(side=tk.LEFT, padx=20)
        self.lbl_clock = tk.Label(header, text="", font=("Arial", 12),
                                  bg="#4a90d9", fg="white")
        self.lbl_clock.pack(side=tk.RIGHT, padx=20)

        # Sidebar
        sidebar = tk.Frame(self.root, bg="#2c3e50", width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="MENU", font=("Arial", 14, "bold"),
                 bg="#2c3e50", fg="white", pady=15).pack(fill=tk.X)

        menu_items = [
            ("Category", self.category),
            ("Employee", self.employee),
            ("Supplier", self.supplier),
            ("Product", self.product),
            ("Sales", self.sales),
            ("Billing", self._open_billing),
        ]
        for text, cmd in menu_items:
            btn = tk.Button(sidebar, text=text, font=("Arial", 12),
                            bg="#34495e", fg="white", bd=0, pady=10,
                            activebackground="#4a90d9", activeforeground="white",
                            command=cmd)
            btn.pack(fill=tk.X, padx=5, pady=2)

        # Main content area
        content = tk.Frame(self.root, bg="#f0f0f0")
        content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Summary cards
        cards_frame = tk.Frame(content, bg="#f0f0f0")
        cards_frame.pack(fill=tk.X, pady=10)

        card_data = [
            ("Categories", "#3498db"),
            ("Employees", "#27ae60"),
            ("Suppliers", "#e67e22"),
            ("Products", "#9b59b6"),
            ("Sales", "#e74c3c"),
        ]
        self.lbl_category = tk.Label(cards_frame, text="Categories\n0",
                                     font=("Arial", 13, "bold"), bg="#3498db",
                                     fg="white", width=12, pady=15)
        self.lbl_category.grid(row=0, column=0, padx=5, pady=5)

        self.lbl_employee = tk.Label(cards_frame, text="Employees\n0",
                                     font=("Arial", 13, "bold"), bg="#27ae60",
                                     fg="white", width=12, pady=15)
        self.lbl_employee.grid(row=0, column=1, padx=5, pady=5)

        self.lbl_supplier = tk.Label(cards_frame, text="Suppliers\n0",
                                     font=("Arial", 13, "bold"), bg="#e67e22",
                                     fg="white", width=12, pady=15)
        self.lbl_supplier.grid(row=0, column=2, padx=5, pady=5)

        self.lbl_product = tk.Label(cards_frame, text="Products\n0",
                                    font=("Arial", 13, "bold"), bg="#9b59b6",
                                    fg="white", width=12, pady=15)
        self.lbl_product.grid(row=0, column=3, padx=5, pady=5)

        self.lbl_sales = tk.Label(cards_frame, text="Sales\n0",
                                  font=("Arial", 13, "bold"), bg="#e74c3c",
                                  fg="white", width=12, pady=15)
        self.lbl_sales.grid(row=0, column=4, padx=5, pady=5)

        # Welcome label
        tk.Label(content, text="Welcome to Inventory Management System",
                 font=("Arial", 16), bg="#f0f0f0", fg="#2c3e50").pack(pady=30)

        self._tick()

    def _tick(self):
        now = datetime.datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
        self.lbl_clock.config(text=now)
        self.root.after(1000, self._tick)

    def update_content(self):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM category")
            cat_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM employee")
            emp_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM supplier")
            sup_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM product")
            prod_count = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM sales")
            sales_count = c.fetchone()[0]
            conn.close()
            self.lbl_category.config(text=f"Categories\n{cat_count}")
            self.lbl_employee.config(text=f"Employees\n{emp_count}")
            self.lbl_supplier.config(text=f"Suppliers\n{sup_count}")
            self.lbl_product.config(text=f"Products\n{prod_count}")
            self.lbl_sales.config(text=f"Sales\n{sales_count}")
        except Exception:
            pass
        self.root.after(5000, self.update_content)

    def _open_window(self, title, cls):
        self.new_win = tk.Toplevel(self.root)
        self.new_win.title(title)
        self.new_obj = cls(self.new_win)

    def category(self):
        self._open_window("Category Management", categoryClass)

    def employee(self):
        self._open_window("Employee Management", employeeClass)

    def supplier(self):
        self._open_window("Supplier Management", supplierClass)

    def product(self):
        self._open_window("Product Management", productClass)

    def sales(self):
        self._open_window("Sales Records", salesClass)

    def _open_billing(self):
        self._open_window("Billing System", billClass)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = IMS(root)
    root.mainloop()