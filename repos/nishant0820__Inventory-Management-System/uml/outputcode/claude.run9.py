import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import *
import datetime
import random
import sqlite3
import os

# ─────────────────────────────────────────────
# Database helper
# ─────────────────────────────────────────────
DB_PATH = "ims.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS category (
        cat_id TEXT PRIMARY KEY,
        name TEXT NOT NULL
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS supplier (
        sup_invoice TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        contact TEXT,
        desc TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS employee (
        emp_id TEXT PRIMARY KEY,
        name TEXT,
        dob TEXT,
        doj TEXT,
        gender TEXT,
        contact TEXT,
        email TEXT,
        salary TEXT,
        utype TEXT,
        address TEXT,
        password TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS product (
        pid TEXT PRIMARY KEY,
        name TEXT,
        price TEXT,
        qty TEXT,
        status TEXT,
        cat TEXT,
        sup TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS sales (
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
        self.var_cat_id = StringVar()
        self.var_name = StringVar()
        self.im1 = None
        self.im2 = None

        # Build UI
        title = Label(self.root, text="Category Management", font=("Arial", 16, "bold"),
                      bg="#1a1a2e", fg="white")
        title.pack(fill=X)

        form_frame = Frame(self.root, bg="#16213e")
        form_frame.pack(fill=X, padx=10, pady=5)

        Label(form_frame, text="Category ID:", bg="#16213e", fg="white").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_cat_id).grid(row=0, column=1, padx=5, pady=5)

        Label(form_frame, text="Category Name:", bg="#16213e", fg="white").grid(row=1, column=0, padx=5, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_name).grid(row=1, column=1, padx=5, pady=5)

        btn_frame = Frame(self.root, bg="#16213e")
        btn_frame.pack(fill=X, padx=10, pady=5)

        Button(btn_frame, text="Add", command=self.add, bg="#0f3460", fg="white", width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, bg="#e94560", fg="white", width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, bg="#533483", fg="white", width=10).pack(side=LEFT, padx=5)

        # Image labels (placeholder)
        img_frame = Frame(self.root, bg="#16213e")
        img_frame.pack(fill=X, padx=10, pady=5)
        self.lbl_im1 = Label(img_frame, bg="#16213e", text="[Image 1]", fg="white")
        self.lbl_im1.pack(side=LEFT, padx=5)
        self.lbl_im2 = Label(img_frame, bg="#16213e", text="[Image 2]", fg="white")
        self.lbl_im2.pack(side=LEFT, padx=5)

        # Table
        table_frame = Frame(self.root)
        table_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        scroll_x = Scrollbar(table_frame, orient=HORIZONTAL)
        scroll_y = Scrollbar(table_frame, orient=VERTICAL)

        self.CategoryTable = ttk.Treeview(table_frame,
                                          columns=("cat_id", "name"),
                                          xscrollcommand=scroll_x.set,
                                          yscrollcommand=scroll_y.set)
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.config(command=self.CategoryTable.xview)
        scroll_y.config(command=self.CategoryTable.yview)

        self.CategoryTable.heading("cat_id", text="Category ID")
        self.CategoryTable.heading("name", text="Name")
        self.CategoryTable["show"] = "headings"
        self.CategoryTable.pack(fill=BOTH, expand=True)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def add(self):
        if self.var_cat_id.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "All fields are required", parent=self.root)
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO category VALUES (?,?)",
                        (self.var_cat_id.get(), self.var_name.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category added successfully", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM category")
        rows = cur.fetchall()
        conn.close()
        self.CategoryTable.delete(*self.CategoryTable.get_children())
        for row in rows:
            self.CategoryTable.insert("", END, values=row)

    def get_data(self, ev):
        selected = self.CategoryTable.focus()
        content = self.CategoryTable.item(selected)
        row = content["values"]
        if row:
            self.var_cat_id.set(row[0])
            self.var_name.set(row[1])

    def delete(self):
        if self.var_cat_id.get() == "":
            messagebox.showerror("Error", "Select a category to delete", parent=self.root)
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM category WHERE cat_id=?", (self.var_cat_id.get(),))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category deleted", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

    def clear(self):
        self.var_cat_id.set("")
        self.var_name.set("")


# ─────────────────────────────────────────────
# supplier module
# ─────────────────────────────────────────────
class supplierClass:
    def __init__(self, root):
        self.root = root
        self.var_sup_invoice = StringVar()
        self.var_name = StringVar()
        self.var_contact = StringVar()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()

        title = Label(self.root, text="Supplier Management", font=("Arial", 16, "bold"),
                      bg="#1a1a2e", fg="white")
        title.pack(fill=X)

        form_frame = Frame(self.root, bg="#16213e")
        form_frame.pack(fill=X, padx=10, pady=5)

        Label(form_frame, text="Invoice No:", bg="#16213e", fg="white").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_sup_invoice).grid(row=0, column=1, padx=5, pady=5)

        Label(form_frame, text="Name:", bg="#16213e", fg="white").grid(row=1, column=0, padx=5, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_name).grid(row=1, column=1, padx=5, pady=5)

        Label(form_frame, text="Contact:", bg="#16213e", fg="white").grid(row=2, column=0, padx=5, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_contact).grid(row=2, column=1, padx=5, pady=5)

        Label(form_frame, text="Description:", bg="#16213e", fg="white").grid(row=3, column=0, padx=5, pady=5, sticky=W)
        self.txt_desc = Text(form_frame, height=4, width=30)
        self.txt_desc.grid(row=3, column=1, padx=5, pady=5)

        btn_frame = Frame(self.root, bg="#16213e")
        btn_frame.pack(fill=X, padx=10, pady=5)

        Button(btn_frame, text="Add", command=self.add, bg="#0f3460", fg="white", width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update, bg="#533483", fg="white", width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, bg="#e94560", fg="white", width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, bg="#0f3460", fg="white", width=10).pack(side=LEFT, padx=5)

        # Search
        search_frame = Frame(self.root, bg="#16213e")
        search_frame.pack(fill=X, padx=10, pady=5)

        Label(search_frame, text="Search By:", bg="#16213e", fg="white").pack(side=LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Invoice No", "Name", "Contact"], width=15).pack(side=LEFT, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt, width=20).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search, bg="#0f3460", fg="white").pack(side=LEFT, padx=5)
        Button(search_frame, text="Show All", command=self.show, bg="#533483", fg="white").pack(side=LEFT, padx=5)

        # Table
        table_frame = Frame(self.root)
        table_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        scroll_x = Scrollbar(table_frame, orient=HORIZONTAL)
        scroll_y = Scrollbar(table_frame, orient=VERTICAL)

        self.SupplierTable = ttk.Treeview(table_frame,
                                          columns=("invoice", "name", "contact", "desc"),
                                          xscrollcommand=scroll_x.set,
                                          yscrollcommand=scroll_y.set)
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.config(command=self.SupplierTable.xview)
        scroll_y.config(command=self.SupplierTable.yview)

        self.SupplierTable.heading("invoice", text="Invoice No")
        self.SupplierTable.heading("name", text="Name")
        self.SupplierTable.heading("contact", text="Contact")
        self.SupplierTable.heading("desc", text="Description")
        self.SupplierTable["show"] = "headings"
        self.SupplierTable.pack(fill=BOTH, expand=True)
        self.SupplierTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def add(self):
        if self.var_sup_invoice.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "Invoice and Name are required", parent=self.root)
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO supplier VALUES (?,?,?,?)",
                        (self.var_sup_invoice.get(), self.var_name.get(),
                         self.var_contact.get(), self.txt_desc.get("1.0", END)))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier added", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

    def update(self):
        if self.var_sup_invoice.get() == "":
            messagebox.showerror("Error", "Select a supplier to update", parent=self.root)
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE supplier SET name=?, contact=?, desc=? WHERE sup_invoice=?",
                        (self.var_name.get(), self.var_contact.get(),
                         self.txt_desc.get("1.0", END), self.var_sup_invoice.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier updated", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

    def delete(self):
        if self.var_sup_invoice.get() == "":
            messagebox.showerror("Error", "Select a supplier to delete", parent=self.root)
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM supplier WHERE sup_invoice=?", (self.var_sup_invoice.get(),))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier deleted", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM supplier")
        rows = cur.fetchall()
        conn.close()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert("", END, values=row)

    def get_data(self, ev):
        selected = self.SupplierTable.focus()
        content = self.SupplierTable.item(selected)
        row = content["values"]
        if row:
            self.var_sup_invoice.set(row[0])
            self.var_name.set(row[1])
            self.var_contact.set(row[2])
            self.txt_desc.delete("1.0", END)
            self.txt_desc.insert("1.0", row[3] if row[3] else "")

    def search(self):
        if self.var_searchby.get() == "" or self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Select search criteria", parent=self.root)
            return
        col_map = {"Invoice No": "sup_invoice", "Name": "name", "Contact": "contact"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM supplier WHERE {col} LIKE ?", (f"%{self.var_searchtxt.get()}%",))
        rows = cur.fetchall()
        conn.close()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert("", END, values=row)

    def clear(self):
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete("1.0", END)


# ─────────────────────────────────────────────
# employee module
# ─────────────────────────────────────────────
class employeeClass:
    def __init__(self, root):
        self.root = root
        self.var_emp_id = StringVar()
        self.var_name = StringVar()
        self.var_dob = StringVar()
        self.var_doj = StringVar()
        self.var_gender = StringVar()
        self.var_contact = StringVar()
        self.var_email = StringVar()
        self.var_salary = StringVar()
        self.var_utype = StringVar()
        self.var_pass = StringVar()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()

        title = Label(self.root, text="Employee Management", font=("Arial", 16, "bold"),
                      bg="#1a1a2e", fg="white")
        title.pack(fill=X)

        form_frame = Frame(self.root, bg="#16213e")
        form_frame.pack(fill=X, padx=10, pady=5)

        fields = [
            ("Employee ID", self.var_emp_id),
            ("Name", self.var_name),
            ("DOB", self.var_dob),
            ("DOJ", self.var_doj),
            ("Gender", self.var_gender),
            ("Contact", self.var_contact),
            ("Email", self.var_email),
            ("Salary", self.var_salary),
            ("User Type", self.var_utype),
            ("Password", self.var_pass),
        ]

        for i, (lbl, var) in enumerate(fields):
            Label(form_frame, text=f"{lbl}:", bg="#16213e", fg="white").grid(
                row=i // 2, column=(i % 2) * 2, padx=5, pady=3, sticky=W)
            Entry(form_frame, textvariable=var).grid(
                row=i // 2, column=(i % 2) * 2 + 1, padx=5, pady=3)

        Label(form_frame, text="Address:", bg="#16213e", fg="white").grid(
            row=len(fields) // 2, column=0, padx=5, pady=3, sticky=W)
        self.txt_address = Text(form_frame, height=3, width=30)
        self.txt_address.grid(row=len(fields) // 2, column=1, padx=5, pady=3)

        btn_frame = Frame(self.root, bg="#16213e")
        btn_frame.pack(fill=X, padx=10, pady=5)

        Button(btn_frame, text="Add", command=self.add, bg="#0f3460", fg="white", width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update, bg="#533483", fg="white", width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, bg="#e94560", fg="white", width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, bg="#0f3460", fg="white", width=10).pack(side=LEFT, padx=5)

        # Search
        search_frame = Frame(self.root, bg="#16213e")
        search_frame.pack(fill=X, padx=10, pady=5)

        Label(search_frame, text="Search By:", bg="#16213e", fg="white").pack(side=LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Employee ID", "Name", "Contact", "Email"], width=15).pack(side=LEFT, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt, width=20).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search, bg="#0f3460", fg="white").pack(side=LEFT, padx=5)
        Button(search_frame, text="Show All", command=self.show, bg="#533483", fg="white").pack(side=LEFT, padx=5)

        # Table
        table_frame = Frame(self.root)
        table_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        scroll_x = Scrollbar(table_frame, orient=HORIZONTAL)
        scroll_y = Scrollbar(table_frame, orient=VERTICAL)

        cols = ("emp_id", "name", "dob", "doj", "gender", "contact", "email", "salary", "utype", "address", "password")
        self.EmployeeTable = ttk.Treeview(table_frame, columns=cols,
                                          xscrollcommand=scroll_x.set,
                                          yscrollcommand=scroll_y.set)
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.config(command=self.EmployeeTable.xview)
        scroll_y.config(command=self.EmployeeTable.yview)

        for col in cols:
            self.EmployeeTable.heading(col, text=col.replace("_", " ").title())
        self.EmployeeTable["show"] = "headings"
        self.EmployeeTable.pack(fill=BOTH, expand=True)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def add(self):
        if self.var_emp_id.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "Employee ID and Name are required", parent=self.root)
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO employee VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (self.var_emp_id.get(), self.var_name.get(), self.var_dob.get(),
                         self.var_doj.get(), self.var_gender.get(), self.var_contact.get(),
                         self.var_email.get(), self.var_salary.get(), self.var_utype.get(),
                         self.txt_address.get("1.0", END), self.var_pass.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee added", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

    def update(self):
        if self.var_emp_id.get() == "":
            messagebox.showerror("Error", "Select an employee to update", parent=self.root)
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""UPDATE employee SET name=?,dob=?,doj=?,gender=?,contact=?,
                           email=?,salary=?,utype=?,address=?,password=? WHERE emp_id=?""",
                        (self.var_name.get(), self.var_dob.get(), self.var_doj.get(),
                         self.var_gender.get(), self.var_contact.get(), self.var_email.get(),
                         self.var_salary.get(), self.var_utype.get(),
                         self.txt_address.get("1.0", END), self.var_pass.get(),
                         self.var_emp_id.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee updated", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

    def delete(self):
        if self.var_emp_id.get() == "":
            messagebox.showerror("Error", "Select an employee to delete", parent=self.root)
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM employee WHERE emp_id=?", (self.var_emp_id.get(),))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee deleted", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM employee")
        rows = cur.fetchall()
        conn.close()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for row in rows:
            self.EmployeeTable.insert("", END, values=row)

    def get_data(self, ev):
        selected = self.EmployeeTable.focus()
        content = self.EmployeeTable.item(selected)
        row = content["values"]
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
            self.txt_address.delete("1.0", END)
            self.txt_address.insert("1.0", row[9] if row[9] else "")
            self.var_pass.set(row[10] if len(row) > 10 else "")

    def search(self):
        if self.var_searchby.get() == "" or self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Select search criteria", parent=self.root)
            return
        col_map = {"Employee ID": "emp_id", "Name": "name", "Contact": "contact", "Email": "email"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM employee WHERE {col} LIKE ?", (f"%{self.var_searchtxt.get()}%",))
        rows = cur.fetchall()
        conn.close()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for row in rows:
            self.EmployeeTable.insert("", END, values=row)

    def clear(self):
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_gender.set("")
        self.var_contact.set("")
        self.var_email.set("")
        self.var_salary.set("")
        self.var_utype.set("")
        self.var_pass.set("")
        self.txt_address.delete("1.0", END)


# ─────────────────────────────────────────────
# product module
# ─────────────────────────────────────────────
class productClass:
    def __init__(self, root):
        self.root = root
        self.var_pid = StringVar()
        self.var_name = StringVar()
        self.var_price = StringVar()
        self.var_qty = StringVar()
        self.var_status = StringVar()
        self.var_cat = StringVar()
        self.var_sup = StringVar()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()
        self.cat_list = []
        self.sup_list = []

        title = Label(self.root, text="Product Management", font=("Arial", 16, "bold"),
                      bg="#1a1a2e", fg="white")
        title.pack(fill=X)

        form_frame = Frame(self.root, bg="#16213e")
        form_frame.pack(fill=X, padx=10, pady=5)

        Label(form_frame, text="Product ID:", bg="#16213e", fg="white").grid(row=0, column=0, padx=5, pady=3, sticky=W)
        Entry(form_frame, textvariable=self.var_pid).grid(row=0, column=1, padx=5, pady=3)

        Label(form_frame, text="Name:", bg="#16213e", fg="white").grid(row=1, column=0, padx=5, pady=3, sticky=W)
        Entry(form_frame, textvariable=self.var_name).grid(row=1, column=1, padx=5, pady=3)

        Label(form_frame, text="Price:", bg="#16213e", fg="white").grid(row=2, column=0, padx=5, pady=3, sticky=W)
        Entry(form_frame, textvariable=self.var_price).grid(row=2, column=1, padx=5, pady=3)

        Label(form_frame, text="Quantity:", bg="#16213e", fg="white").grid(row=3, column=0, padx=5, pady=3, sticky=W)
        Entry(form_frame, textvariable=self.var_qty).grid(row=3, column=1, padx=5, pady=3)

        Label(form_frame, text="Status:", bg="#16213e", fg="white").grid(row=4, column=0, padx=5, pady=3, sticky=W)
        ttk.Combobox(form_frame, textvariable=self.var_status,
                     values=["Active", "Inactive"], width=17).grid(row=4, column=1, padx=5, pady=3)

        Label(form_frame, text="Category:", bg="#16213e", fg="white").grid(row=0, column=2, padx=5, pady=3, sticky=W)
        self.cat_combo = ttk.Combobox(form_frame, textvariable=self.var_cat, width=17)
        self.cat_combo.grid(row=0, column=3, padx=5, pady=3)

        Label(form_frame, text="Supplier:", bg="#16213e", fg="white").grid(row=1, column=2, padx=5, pady=3, sticky=W)
        self.sup_combo = ttk.Combobox(form_frame, textvariable=self.var_sup, width=17)
        self.sup_combo.grid(row=1, column=3, padx=5, pady=3)

        btn_frame = Frame(self.root, bg="#16213e")
        btn_frame.pack(fill=X, padx=10, pady=5)

        Button(btn_frame, text="Add", command=self.add, bg="#0f3460", fg="white", width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update, bg="#533483", fg="white", width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, bg="#e94560", fg="white", width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, bg="#0f3460", fg="white", width=10).pack(side=LEFT, padx=5)

        # Search
        search_frame = Frame(self.root, bg="#16213e")
        search_frame.pack(fill=X, padx=10, pady=5)

        Label(search_frame, text="Search By:", bg="#16213e", fg="white").pack(side=LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Product ID", "Name", "Status", "Category", "Supplier"], width=15).pack(side=LEFT, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt, width=20).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search, bg="#0f3460", fg="white").pack(side=LEFT, padx=5)
        Button(search_frame, text="Show All", command=self.show, bg="#533483", fg="white").pack(side=LEFT, padx=5)

        # Table
        table_frame = Frame(self.root)
        table_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        scroll_x = Scrollbar(table_frame, orient=HORIZONTAL)
        scroll_y = Scrollbar(table_frame, orient=VERTICAL)

        cols = ("pid", "name", "price", "qty", "status", "cat", "sup")
        self.ProductTable = ttk.Treeview(table_frame, columns=cols,
                                         xscrollcommand=scroll_x.set,
                                         yscrollcommand=scroll_y.set)
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.config(command=self.ProductTable.xview)
        scroll_y.config(command=self.ProductTable.yview)

        headers = ("Product ID", "Name", "Price", "Quantity", "Status", "Category", "Supplier")
        for col, hdr in zip(cols, headers):
            self.ProductTable.heading(col, text=hdr)
        self.ProductTable["show"] = "headings"
        self.ProductTable.pack(fill=BOTH, expand=True)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)

        self.fetch_cat_sup()
        self.show()

    def fetch_cat_sup(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT name FROM category")
        self.cat_list = [row[0] for row in cur.fetchall()]
        cur.execute("SELECT name FROM supplier")
        self.sup_list = [row[0] for row in cur.fetchall()]
        conn.close()
        self.cat_combo["values"] = self.cat_list
        self.sup_combo["values"] = self.sup_list

    def add(self):
        if self.var_pid.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "Product ID and Name are required", parent=self.root)
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO product VALUES (?,?,?,?,?,?,?)",
                        (self.var_pid.get(), self.var_name.get(), self.var_price.get(),
                         self.var_qty.get(), self.var_status.get(),
                         self.var_cat.get(), self.var_sup.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product added", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

    def update(self):
        if self.var_pid.get() == "":
            messagebox.showerror("Error", "Select a product to update", parent=self.root)
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE product SET name=?,price=?,qty=?,status=?,cat=?,sup=? WHERE pid=?",
                        (self.var_name.get(), self.var_price.get(), self.var_qty.get(),
                         self.var_status.get(), self.var_cat.get(), self.var_sup.get(),
                         self.var_pid.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product updated", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

    def delete(self):
        if self.var_pid.get() == "":
            messagebox.showerror("Error", "Select a product to delete", parent=self.root)
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM product WHERE pid=?", (self.var_pid.get(),))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product deleted", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM product")
        rows = cur.fetchall()
        conn.close()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for row in rows:
            self.ProductTable.insert("", END, values=row)

    def get_data(self, ev):
        selected = self.ProductTable.focus()
        content = self.ProductTable.item(selected)
        row = content["values"]
        if row:
            self.var_pid.set(row[0])
            self.var_name.set(row[1])
            self.var_price.set(row[2])
            self.var_qty.set(row[3])
            self.var_status.set(row[4])
            self.var_cat.set(row[5])
            self.var_sup.set(row[6])

    def search(self):
        if self.var_searchby.get() == "" or self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Select search criteria", parent=self.root)
            return
        col_map = {"Product ID": "pid", "Name": "name", "Status": "status",
                   "Category": "cat", "Supplier": "sup"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM product WHERE {col} LIKE ?", (f"%{self.var_searchtxt.get()}%",))
        rows = cur.fetchall()
        conn.close()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for row in rows:
            self.ProductTable.insert("", END, values=row)

    def clear(self):
        self.var_pid.set("")
        self.var_name.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("")
        self.var_cat.set("")
        self.var_sup.set("")


# ─────────────────────────────────────────────
# sales module
# ─────────────────────────────────────────────
class salesClass:
    def __init__(self, root):
        self.root = root
        self.var_invoice = StringVar()
        self.blll_list = []
        self.bill_photo = None

        title = Label(self.root, text="Sales / Billing Records", font=("Arial", 16, "bold"),
                      bg="#1a1a2e", fg="white")
        title.pack(fill=X)

        search_frame = Frame(self.root, bg="#16213e")
        search_frame.pack(fill=X, padx=10, pady=5)

        Label(search_frame, text="Invoice No:", bg="#16213e", fg="white").pack(side=LEFT, padx=5)
        Entry(search_frame, textvariable=self.var_invoice, width=20).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search, bg="#0f3460", fg="white").pack(side=LEFT, padx=5)
        Button(search_frame, text="Show All", command=self.show, bg="#533483", fg="white").pack(side=LEFT, padx=5)
        Button(search_frame, text="Clear", command=self.clear, bg="#e94560", fg="white").pack(side=LEFT, padx=5)

        main_frame = Frame(self.root, bg="#16213e")
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        # Listbox
        list_frame = Frame(main_frame, bg="#16213e")
        list_frame.pack(side=LEFT, fill=Y)

        Label(list_frame, text="Invoice List", bg="#16213e", fg="white").pack()
        scroll_y = Scrollbar(list_frame, orient=VERTICAL)
        self.Sales_List = Listbox(list_frame, yscrollcommand=scroll_y.set, width=25, bg="#0f3460", fg="white")
        scroll_y.config(command=self.Sales_List.yview)
        scroll_y.pack(side=RIGHT, fill=Y)
        self.Sales_List.pack(fill=Y, expand=True)
        self.Sales_List.bind("<ButtonRelease-1>", self.get_data)

        # Bill area
        bill_frame = Frame(main_frame, bg="#16213e")
        bill_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=10)

        Label(bill_frame, text="Bill Details", bg="#16213e", fg="white").pack()
        scroll_bill = Scrollbar(bill_frame, orient=VERTICAL)
        self.bill_area = Text(bill_frame, yscrollcommand=scroll_bill.set, bg="#0f3460", fg="white")
        scroll_bill.config(command=self.bill_area.yview)
        scroll_bill.pack(side=RIGHT, fill=Y)
        self.bill_area.pack(fill=BOTH, expand=True)

        self.show()

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT invoice FROM sales")
        rows = cur.fetchall()
        conn.close()
        self.blll_list = [row[0] for row in rows]
        self.Sales_List.delete(0, END)
        for inv in self.blll_list:
            self.Sales_List.insert(END, inv)

    def get_data(self, ev):
        selected = self.Sales_List.curselection()
        if not selected:
            return
        invoice = self.Sales_List.get(selected[0])
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM sales WHERE invoice=?", (invoice,))
        row = cur.fetchone()
        conn.close()
        if row:
            self.bill_area.config(state=NORMAL)
            self.bill_area.delete("1.0", END)
            bill_text = (f"Invoice: {row[0]}\n"
                         f"Customer: {row[1]}\n"
                         f"Contact: {row[2]}\n"
                         f"Date: {row[5]}\n"
                         f"Net Pay: {row[4]}\n\n"
                         f"Bill Details:\n{row[3]}")
            self.bill_area.insert("1.0", bill_text)
            self.bill_area.config(state=DISABLED)

    def search(self):
        if self.var_invoice.get() == "":
            messagebox.showerror("Error", "Enter invoice number to search", parent=self.root)
            return
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT invoice FROM sales WHERE invoice LIKE ?",
                    (f"%{self.var_invoice.get()}%",))
        rows = cur.fetchall()
        conn.close()
        self.Sales_List.delete(0, END)
        for row in rows:
            self.Sales_List.insert(END, row[0])

    def clear(self):
        self.var_invoice.set("")
        self.bill_area.config(state=NORMAL)
        self.bill_area.delete("1.0", END)
        self.bill_area.config(state=DISABLED)
        self.show()


# ─────────────────────────────────────────────
# billing module
# ─────────────────────────────────────────────
class billClass:
    def __init__(self, root):
        self.root = root
        self.cart_list = []
        self.bill_amnt = 0
        self.discount = 0.0
        self.net_pay = 0
        self.siscount = 0
        self.chk_print = 0
        self.invoice = None

        self.var_search = StringVar()
        self.var_pid = StringVar()
        self.var_pname = StringVar()
        self.var_price = StringVar()
        self.var_qty = StringVar()
        self.var_stock = StringVar()
        self.var_cname = StringVar()
        self.var_contact = StringVar()
        self.var_cal_input = StringVar()

        self.icon_title = None

        self._build_ui()
        self.update_date_time()
        self.show()

    def _build_ui(self):
        # Top
        self.bill_top()
        # Middle
        self.bill_middle()
        # Bottom
        self.bill_bottom()

    def bill_top(self):
        top_frame = Frame(self.root, bg="#1a1a2e")
        top_frame.pack(fill=X)

        Label(top_frame, text="Inventory Management System - Billing",
              font=("Arial", 18, "bold"), bg="#1a1a2e", fg="white").pack(side=LEFT, padx=10, pady=5)

        self.lbl_clock = Label(top_frame, text="", font=("Arial", 12), bg="#1a1a2e", fg="white")
        self.lbl_clock.pack(side=RIGHT, padx=10)

    def bill_middle(self):
        mid_frame = Frame(self.root, bg="#16213e")
        mid_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)

        # Left: product search & cart
        left_frame = Frame(mid_frame, bg="#16213e")
        left_frame.pack(side=LEFT, fill=BOTH, expand=True)

        # Customer info
        cust_frame = Frame(left_frame, bg="#16213e")
        cust_frame.pack(fill=X, padx=5, pady=5)

        Label(cust_frame, text="Customer Name:", bg="#16213e", fg="white").grid(row=0, column=0, padx=5, pady=3, sticky=W)
        Entry(cust_frame, textvariable=self.var_cname, width=20).grid(row=0, column=1, padx=5, pady=3)

        Label(cust_frame, text="Contact:", bg="#16213e", fg="white").grid(row=0, column=2, padx=5, pady=3, sticky=W)
        Entry(cust_frame, textvariable=self.var_contact, width=20).grid(row=0, column=3, padx=5, pady=3)

        # Product search
        search_frame = Frame(left_frame, bg="#16213e")
        search_frame.pack(fill=X, padx=5, pady=5)

        Label(search_frame, text="Search Product:", bg="#16213e", fg="white").pack(side=LEFT, padx=5)
        Entry(search_frame, textvariable=self.var_search, width=20).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search, bg="#0f3460", fg="white").pack(side=LEFT, padx=5)

        # Product table
        prod_frame = Frame(left_frame)
        prod_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)

        scroll_x = Scrollbar(prod_frame, orient=HORIZONTAL)
        scroll_y = Scrollbar(prod_frame, orient=VERTICAL)

        cols = ("pid", "name", "price", "qty", "status", "cat", "sup")
        self.product_Table = ttk.Treeview(prod_frame, columns=cols,
                                          xscrollcommand=scroll_x.set,
                                          yscrollcommand=scroll_y.set, height=6)
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.config(command=self.product_Table.xview)
        scroll_y.config(command=self.product_Table.yview)

        headers = ("PID", "Name", "Price", "Qty", "Status", "Category", "Supplier")
        for col, hdr in zip(cols, headers):
            self.product_Table.heading(col, text=hdr)
            self.product_Table.column(col, width=80)
        self.product_Table["show"] = "headings"
        self.product_Table.pack(fill=BOTH, expand=True)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)

        # Product detail & add to cart
        detail_frame = Frame(left_frame, bg="#16213e")
        detail_frame.pack(fill=X, padx=5, pady=5)

        Label(detail_frame, text="PID:", bg="#16213e", fg="white").grid(row=0, column=0, padx=3, pady=3, sticky=W)
        Entry(detail_frame, textvariable=self.var_pid, width=10, state="readonly").grid(row=0, column=1, padx=3, pady=3)

        Label(detail_frame, text="Name:", bg="#16213e", fg="white").grid(row=0, column=2, padx=3, pady=3, sticky=W)
        Entry(detail_frame, textvariable=self.var_pname, width=15, state="readonly").grid(row=0, column=3, padx=3, pady=3)

        Label(detail_frame, text="Price:", bg="#16213e", fg="white").grid(row=0, column=4, padx=3, pady=3, sticky=W)
        Entry(detail_frame, textvariable=self.var_price, width=10, state="readonly").grid(row=0, column=5, padx=3, pady=3)

        Label(detail_frame, text="Qty:", bg="#16213e", fg="white").grid(row=1, column=0, padx=3, pady=3, sticky=W)
        Entry(detail_frame, textvariable=self.var_qty, width=10).grid(row=1, column=1, padx=3, pady=3)

        Label(detail_frame, text="In Stock:", bg="#16213e", fg="white").grid(row=1, column=2, padx=3, pady=3, sticky=W)
        self.lbl_inStock = Label(detail_frame, textvariable=self.var_stock, bg="#16213e", fg="yellow")
        self.lbl_inStock.grid(row=1, column=3, padx=3, pady=3, sticky=W)

        Button(detail_frame, text="Add to Cart", command=self.add_update_cart,
               bg="#0f3460", fg="white").grid(row=1, column=4, columnspan=2, padx=3, pady=3)

        # Cart table
        self.cartTitle = Label(left_frame, text="Cart", font=("Arial", 12, "bold"),
                               bg="#16213e", fg="white")
        self.cartTitle.pack()

        cart_frame = Frame(left_frame)
        cart_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)

        scroll_cx = Scrollbar(cart_frame, orient=HORIZONTAL)
        scroll_cy = Scrollbar(cart_frame, orient=VERTICAL)

        cart_cols = ("pid", "name", "price", "qty", "total")
        self.CartTable = ttk.Treeview(cart_frame, columns=cart_cols,
                                      xscrollcommand=scroll_cx.set,
                                      yscrollcommand=scroll_cy.set, height=6)
        scroll_cx.pack(side=BOTTOM, fill=X)
        scroll_cy.pack(side=RIGHT, fill=Y)
        scroll_cx.config(command=self.CartTable.xview)
        scroll_cy.config(command=self.CartTable.yview)

        cart_headers = ("PID", "Name", "Price", "Qty", "Total")
        for col, hdr in zip(cart_cols, cart_headers):
            self.CartTable.heading(col, text=hdr)
            self.CartTable.column(col, width=80)
        self.CartTable["show"] = "headings"
        self.CartTable.pack(fill=BOTH, expand=True)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        # Amount info
        amnt_frame = Frame(left_frame, bg="#16213e")
        amnt_frame.pack(fill=X, padx=5, pady=5)

        self.lbl_amnt = Label(amnt_frame, text="Bill Amount: 0", bg="#16213e", fg="white",
                              font=("Arial", 11))
        self.lbl_amnt.pack(side=LEFT, padx=10)

        self.lbl_discount = Label(amnt_frame, text="Discount: 0%", bg="#16213e", fg="white",
                                  font=("Arial", 11))
        self.lbl_discount.pack(side=LEFT, padx=10)

        self.lbl_net_pay = Label(amnt_frame, text="Net Pay: 0", bg="#16213e", fg="white",
                                 font=("Arial", 11, "bold"))
        self.lbl_net_pay.pack(side=LEFT, padx=10)

        # Buttons
        btn_frame = Frame(left_frame, bg="#16213e")
        btn_frame.pack(fill=X, padx=5, pady=5)

        Button(btn_frame, text="Generate Bill", command=self.generate_bill,
               bg="#0f3460", fg="white", width=14).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear Cart", command=self.clear_cart,
               bg="#e94560", fg="white", width=12).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear All", command=self.clear_all,
               bg="#533483", fg="white", width=12).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Print Bill", command=self.print_bill,
               bg="#0f3460", fg="white", width=12).pack(side=LEFT, padx=5)

        # Right: bill area + calculator
        right_frame = Frame(mid_frame, bg="#16213e", width=300)
        right_frame.pack(side=RIGHT, fill=Y, padx=5)

        Label(right_frame, text="Bill Area", font=("Arial", 12, "bold"),
              bg="#16213e", fg="white").pack()

        self.txt_bill_area = Text(right_frame, width=35, bg="#0f3460", fg="white")
        self.txt_bill_area.pack(fill=BOTH, expand=True, padx=5, pady=5)

        # Calculator
        Label(right_frame, text="Calculator", font=("Arial", 11, "bold"),
              bg="#16213e", fg="white").pack()

        self.txt_cal_input = Entry(right_frame, textvariable=self.var_cal_input,
                                   font=("Arial", 14), justify=RIGHT, bg="#0f3460", fg="white")
        self.txt_cal_input.pack(fill=X, padx=5, pady=3)

        cal_frame = Frame(right_frame, bg="#16213e")
        cal_frame.pack(padx=5, pady=3)

        buttons = [
            "7", "8", "9", "/",
            "4", "5", "6", "*",
            "1", "2", "3", "-",
            "0", ".", "=", "+",
        ]
        row_idx = 0
        col_idx = 0
        for btn_text in buttons:
            cmd = (lambda t=btn_text: self.perform_cal()) if btn_text == "=" else (lambda t=btn_text: self.get_input(t))
            Button(cal_frame, text=btn_text, width=5, command=cmd,
                   bg="#0f3460", fg="white").grid(row=row_idx, column=col_idx, padx=2, pady=2)
            col_idx += 1
            if col_idx == 4:
                col_idx = 0
                row_idx += 1

        Button(cal_frame, text="Clear", command=self.clear_cal,
               bg="#e94560", fg="white", width=22).grid(row=row_idx, column=0, columnspan=4, padx=2, pady=2)

    def bill_bottom(self):
        pass

    def update_date_time(self):
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%d-%m-%Y  %H:%M:%S"))
        self.root.after(1000, self.update_date_time)

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM product WHERE status='Active'")
        rows = cur.fetchall()
        conn.close()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", END, values=row)

    def search(self):
        if self.var_search.get() == "":
            self.show()
            return
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM product WHERE pid LIKE ? OR name LIKE ?",
                    (f"%{self.var_search.get()}%", f"%{self.var_search.get()}%"))
        rows = cur.fetchall()
        conn.close()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", END, values=row)

    def get_data(self, ev):
        selected = self.product_Table.focus()
        content = self.product_Table.item(selected)
        row = content["values"]
        if row:
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_stock.set(row[3])

    def get_data_cart(self, ev):
        selected = self.CartTable.focus()
        content = self.CartTable.item(selected)
        row = content["values"]
        if row:
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_qty.set(row[3])

    def add_update_cart(self):
        if self.var_pid.get() == "" or self.var_qty.get() == "":
            messagebox.showerror("Error", "Select a product and enter quantity", parent=self.root)
            return
        try:
            qty = int(self.var_qty.get())
            price = float(self.var_price.get())
            stock = int(self.var_stock.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity or price", parent=self.root)
            return

        if qty <= 0:
            messagebox.showerror("Error", "Quantity must be positive", parent=self.root)
            return
        if qty > stock:
            messagebox.showerror("Error", f"Only {stock} items in stock", parent=self.root)
            return

        total = qty * price

        # Check if already in cart
        for i, item in enumerate(self.cart_list):
            if item[0] == self.var_pid.get():
                self.cart_list[i] = (self.var_pid.get(), self.var_pname.get(),
                                     price, qty, total)
                self.show_cart()
                self.bill_update()
                return

        self.cart_list.append((self.var_pid.get(), self.var_pname.get(), price, qty, total))
        self.show_cart()
        self.bill_update()

    def show_cart(self):
        self.CartTable.delete(*self.CartTable.get_children())
        for item in self.cart_list:
            self.CartTable.insert("", END, values=item)

    def bill_update(self):
        self.bill_amnt = sum(item[4] for item in self.cart_list)
        self.discount = 5.0 if self.bill_amnt > 1000 else 0.0
        self.net_pay = self.bill_amnt - (self.bill_amnt * self.discount / 100)
        self.lbl_amnt.config(text=f"Bill Amount: {self.bill_amnt:.2f}")
        self.lbl_discount.config(text=f"Discount: {self.discount}%")
        self.lbl_net_pay.config(text=f"Net Pay: {self.net_pay:.2f}")

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty", parent=self.root)
            return
        if self.var_cname.get() == "" or self.var_contact.get() == "":
            messagebox.showerror("Error", "Customer name and contact are required", parent=self.root)
            return

        self.invoice = f"INV{random.randint(1000, 9999)}"
        now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        bill_text = "=" * 40 + "\n"
        bill_text += "     INVENTORY MANAGEMENT SYSTEM\n"
        bill_text += "=" * 40 + "\n"
        bill_text += f"Invoice: {self.invoice}\n"
        bill_text += f"Date: {now}\n"
        bill_text += f"Customer: {self.var_cname.get()}\n"
        bill_text += f"Contact: {self.var_contact.get()}\n"
        bill_text += "-" * 40 + "\n"
        bill_text += f"{'Item':<15}{'Qty':>5}{'Price':>10}{'Total':>10}\n"
        bill_text += "-" * 40 + "\n"

        bill_data = ""
        for item in self.cart_list:
            line = f"{item[1]:<15}{item[3]:>5}{item[2]:>10.2f}{item[4]:>10.2f}\n"
            bill_text += line
            bill_data += line

        bill_text += "-" * 40 + "\n"
        bill_text += f"{'Bill Amount:':<25}{self.bill_amnt:>15.2f}\n"
        bill_text += f"{'Discount:':<25}{self.discount:>14.1f}%\n"
        bill_text += f"{'Net Pay:':<25}{self.net_pay:>15.2f}\n"
        bill_text += "=" * 40 + "\n"
        bill_text += "     Thank you for shopping!\n"
        bill_text += "=" * 40 + "\n"

        self.txt_bill_area.delete("1.0", END)
        self.txt_bill_area.insert("1.0", bill_text)

        # Save to DB
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO sales VALUES (?,?,?,?,?,?)",
                        (self.invoice, self.var_cname.get(), self.var_contact.get(),
                         bill_data, str(self.net_pay), now))
            # Update stock
            for item in self.cart_list:
                cur.execute("UPDATE product SET qty=qty-? WHERE pid=?", (item[3], item[0]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Bill generated! Invoice: {self.invoice}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Error saving bill: {e}", parent=self.root)

    def clear_cart(self):
        self.cart_list = []
        self.show_cart()
        self.bill_update()

    def clear_all(self):
        self.clear_cart()
        self.var_cname.set("")
        self.var_contact.set("")
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")
        self.txt_bill_area.delete("1.0", END)
        self.invoice = None

    def print_bill(self):
        if self.txt_bill_area.get("1.0", END).strip() == "":
            messagebox.showerror("Error", "No bill to print", parent=self.root)
            return
        messagebox.showinfo("Print", "Bill sent to printer (simulated)", parent=self.root)

    def get_input(self, num: str):
        current = self.var_cal_input.get()
        self.var_cal_input.set(current + num)

    def perform_cal(self):
        try:
            result = eval(self.var_cal_input.get())
            self.var_cal_input.set(str(result))
        except Exception:
            self.var_cal_input.set("Error")

    def clear_cal(self):
        self.var_cal_input.set("")


# ─────────────────────────────────────────────
# dashboard module
# ─────────────────────────────────────────────
class IMS:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("1200x700+0+0")
        self.root.config(bg="#1a1a2e")

        self.MenuLogo = None
        self.icon_side = None
        self.icon_title = None
        self.new_obj = None
        self.new_win = None

        self._build_ui()
        self.update_content()

    def _build_ui(self):
        # Header
        header = Frame(self.root, bg="#0f3460", pady=5)
        header.pack(fill=X)

        Label(header, text="INVENTORY MANAGEMENT SYSTEM",
              font=("Arial", 22, "bold"), bg="#0f3460", fg="white").pack(side=LEFT, padx=20)

        self.lbl_clock = Label(header, text="", font=("Arial", 12), bg="#0f3460", fg="white")
        self.lbl_clock.pack(side=RIGHT, padx=20)

        # Sidebar
        sidebar = Frame(self.root, bg="#16213e", width=200)
        sidebar.pack(side=LEFT, fill=Y)
        sidebar.pack_propagate(False)

        Label(sidebar, text="MENU", font=("Arial", 14, "bold"),
              bg="#16213e", fg="white", pady=10).pack(fill=X)

        menu_items = [
            ("Category", self.category),
            ("Employee", self.employee),
            ("Supplier", self.supplier),
            ("Product", self.product),
            ("Sales", self.sales),
            ("Billing", self.billing),
        ]

        for text, cmd in menu_items:
            btn = Button(sidebar, text=text, command=cmd,
                         bg="#0f3460", fg="white", font=("Arial", 12),
                         relief=FLAT, pady=10, cursor="hand2")
            btn.pack(fill=X, padx=5, pady=2)

        # Stats frame
        stats_frame = Frame(self.root, bg="#1a1a2e")
        stats_frame.pack(side=TOP, fill=X, padx=10, pady=10)

        self.lbl_employee = Label(stats_frame, text="Employees\n0",
                                  font=("Arial", 14, "bold"), bg="#0f3460", fg="white",
                                  width=15, pady=10)
        self.lbl_employee.pack(side=LEFT, padx=5)

        self.lbl_category = Label(stats_frame, text="Categories\n0",
                                  font=("Arial", 14, "bold"), bg="#533483", fg="white",
                                  width=15, pady=10)
        self.lbl_category.pack(side=LEFT, padx=5)

        self.lbl_product = Label(stats_frame, text="Products\n0",
                                 font=("Arial", 14, "bold"), bg="#e94560", fg="white",
                                 width=15, pady=10)
        self.lbl_product.pack(side=LEFT, padx=5)

        self.lbl_supplier = Label(stats_frame, text="Suppliers\n0",
                                  font=("Arial", 14, "bold"), bg="#0f3460", fg="white",
                                  width=15, pady=10)
        self.lbl_supplier.pack(side=LEFT, padx=5)

        self.lbl_sales = Label(stats_frame, text="Sales\n0",
                               font=("Arial", 14, "bold"), bg="#533483", fg="white",
                               width=15, pady=10)
        self.lbl_sales.pack(side=LEFT, padx=5)

        # Content area
        self.content_frame = Frame(self.root, bg="#1a1a2e")
        self.content_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        Label(self.content_frame,
              text="Welcome to Inventory Management System\n\nSelect a module from the menu",
              font=("Arial", 16), bg="#1a1a2e", fg="white").pack(expand=True)

    def update_content(self):
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%d-%m-%Y  %H:%M:%S"))

        # Update stats
        try:
            conn = get_connection()
            cur = conn.cursor()

            cur.execute("SELECT COUNT(*) FROM employee")
            emp_count = cur.fetchone()[0]
            self.lbl_employee.config(text=f"Employees\n{emp_count}")

            cur.execute("SELECT COUNT(*) FROM category")
            cat_count = cur.fetchone()[0]
            self.lbl_category.config(text=f"Categories\n{cat_count}")

            cur.execute("SELECT COUNT(*) FROM product")
            prod_count = cur.fetchone()[0]
            self.lbl_product.config(text=f"Products\n{prod_count}")

            cur.execute("SELECT COUNT(*) FROM supplier")
            sup_count = cur.fetchone()[0]
            self.lbl_supplier.config(text=f"Suppliers\n{sup_count}")

            cur.execute("SELECT COUNT(*) FROM sales")
            sales_count = cur.fetchone()[0]
            self.lbl_sales.config(text=f"Sales\n{sales_count}")

            conn.close()
        except Exception:
            pass

        self.root.after(1000, self.update_content)

    def _open_window(self, title: str, cls):
        self.new_win = Toplevel(self.root)
        self.new_win.title(title)
        self.new_win.geometry("1100x650+50+50")
        self.new_win.config(bg="#1a1a2e")
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

    def billing(self):
        self._open_window("Billing", billClass)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = IMS(root)
    root.mainloop()