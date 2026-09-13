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
        password TEXT,
        address TEXT
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

        # Main frame
        main_frame = Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=BOTH, expand=True)

        title = Label(main_frame, text="Category Management", font=("Arial", 18, "bold"),
                      bg="#2c3e50", fg="white", pady=10)
        title.pack(fill=X)

        form_frame = Frame(main_frame, bg="#f0f0f0", pady=10)
        form_frame.pack(fill=X, padx=20)

        Label(form_frame, text="Category ID:", bg="#f0f0f0", font=("Arial", 11)).grid(row=0, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_cat_id, font=("Arial", 11), width=25).grid(row=0, column=1, padx=10, pady=5)

        Label(form_frame, text="Category Name:", bg="#f0f0f0", font=("Arial", 11)).grid(row=1, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_name, font=("Arial", 11), width=25).grid(row=1, column=1, padx=10, pady=5)

        # Image labels (placeholder)
        self.lbl_im1 = Label(form_frame, text="[Image 1]", bg="#ddd", width=10, height=5)
        self.lbl_im1.grid(row=0, column=2, rowspan=2, padx=20)
        self.lbl_im2 = Label(form_frame, text="[Image 2]", bg="#ddd", width=10, height=5)
        self.lbl_im2.grid(row=0, column=3, rowspan=2, padx=20)

        btn_frame = Frame(main_frame, bg="#f0f0f0")
        btn_frame.pack(pady=10)

        Button(btn_frame, text="Add", command=self.add, bg="#27ae60", fg="white",
               font=("Arial", 11), width=10).grid(row=0, column=0, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, bg="#e74c3c", fg="white",
               font=("Arial", 11), width=10).grid(row=0, column=1, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, bg="#3498db", fg="white",
               font=("Arial", 11), width=10).grid(row=0, column=2, padx=5)

        # Table
        table_frame = Frame(main_frame)
        table_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)

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
            cur.execute("INSERT INTO category VALUES (?, ?)",
                        (self.var_cat_id.get(), self.var_name.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category added successfully", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

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
            messagebox.showinfo("Success", "Category deleted successfully", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

    def clear(self):
        self.var_cat_id.set("")
        self.var_name.set("")

    def get_data(self, ev):
        selected = self.CategoryTable.focus()
        content = self.CategoryTable.item(selected)
        row = content["values"]
        if row:
            self.var_cat_id.set(row[0])
            self.var_name.set(row[1])

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM category")
        rows = cur.fetchall()
        conn.close()
        self.CategoryTable.delete(*self.CategoryTable.get_children())
        for row in rows:
            self.CategoryTable.insert("", END, values=row)


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

        main_frame = Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=BOTH, expand=True)

        title = Label(main_frame, text="Supplier Management", font=("Arial", 18, "bold"),
                      bg="#2c3e50", fg="white", pady=10)
        title.pack(fill=X)

        form_frame = Frame(main_frame, bg="#f0f0f0", pady=10)
        form_frame.pack(fill=X, padx=20)

        Label(form_frame, text="Supplier Invoice:", bg="#f0f0f0", font=("Arial", 11)).grid(row=0, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_sup_invoice, font=("Arial", 11), width=25).grid(row=0, column=1, padx=10, pady=5)

        Label(form_frame, text="Name:", bg="#f0f0f0", font=("Arial", 11)).grid(row=1, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_name, font=("Arial", 11), width=25).grid(row=1, column=1, padx=10, pady=5)

        Label(form_frame, text="Contact:", bg="#f0f0f0", font=("Arial", 11)).grid(row=2, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_contact, font=("Arial", 11), width=25).grid(row=2, column=1, padx=10, pady=5)

        Label(form_frame, text="Description:", bg="#f0f0f0", font=("Arial", 11)).grid(row=3, column=0, padx=10, pady=5, sticky=W)
        self.txt_desc = Text(form_frame, font=("Arial", 11), width=25, height=4)
        self.txt_desc.grid(row=3, column=1, padx=10, pady=5)

        # Search
        search_frame = Frame(main_frame, bg="#f0f0f0")
        search_frame.pack(fill=X, padx=20, pady=5)

        Label(search_frame, text="Search By:", bg="#f0f0f0", font=("Arial", 11)).grid(row=0, column=0, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Invoice", "Name", "Contact"],
                     font=("Arial", 11), width=15).grid(row=0, column=1, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt, font=("Arial", 11), width=20).grid(row=0, column=2, padx=5)
        Button(search_frame, text="Search", command=self.search, bg="#8e44ad", fg="white",
               font=("Arial", 11)).grid(row=0, column=3, padx=5)
        Button(search_frame, text="Show All", command=self.show, bg="#16a085", fg="white",
               font=("Arial", 11)).grid(row=0, column=4, padx=5)

        btn_frame = Frame(main_frame, bg="#f0f0f0")
        btn_frame.pack(pady=10)

        Button(btn_frame, text="Add", command=self.add, bg="#27ae60", fg="white",
               font=("Arial", 11), width=10).grid(row=0, column=0, padx=5)
        Button(btn_frame, text="Update", command=self.update, bg="#f39c12", fg="white",
               font=("Arial", 11), width=10).grid(row=0, column=1, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, bg="#e74c3c", fg="white",
               font=("Arial", 11), width=10).grid(row=0, column=2, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, bg="#3498db", fg="white",
               font=("Arial", 11), width=10).grid(row=0, column=3, padx=5)

        table_frame = Frame(main_frame)
        table_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)

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

        self.SupplierTable.heading("invoice", text="Invoice")
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
            cur.execute("INSERT INTO supplier VALUES (?, ?, ?, ?)",
                        (self.var_sup_invoice.get(), self.var_name.get(),
                         self.var_contact.get(), self.txt_desc.get("1.0", END).strip()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier added successfully", parent=self.root)
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
                         self.txt_desc.get("1.0", END).strip(), self.var_sup_invoice.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier updated successfully", parent=self.root)
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
            messagebox.showinfo("Success", "Supplier deleted successfully", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

    def clear(self):
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete("1.0", END)

    def get_data(self, ev):
        selected = self.SupplierTable.focus()
        content = self.SupplierTable.item(selected)
        row = content["values"]
        if row:
            self.var_sup_invoice.set(row[0])
            self.var_name.set(row[1])
            self.var_contact.set(row[2])
            self.txt_desc.delete("1.0", END)
            self.txt_desc.insert(END, row[3] if row[3] else "")

    def search(self):
        if self.var_searchby.get() == "" or self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Select search criteria", parent=self.root)
            return
        col_map = {"Invoice": "sup_invoice", "Name": "name", "Contact": "contact"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM supplier WHERE {col} LIKE ?", (f"%{self.var_searchtxt.get()}%",))
        rows = cur.fetchall()
        conn.close()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert("", END, values=row)

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM supplier")
        rows = cur.fetchall()
        conn.close()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert("", END, values=row)


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

        main_frame = Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=BOTH, expand=True)

        title = Label(main_frame, text="Employee Management", font=("Arial", 18, "bold"),
                      bg="#2c3e50", fg="white", pady=10)
        title.pack(fill=X)

        form_frame = Frame(main_frame, bg="#f0f0f0", pady=10)
        form_frame.pack(fill=X, padx=20)

        fields = [
            ("Employee ID:", self.var_emp_id, 0, 0),
            ("Name:", self.var_name, 1, 0),
            ("Date of Birth:", self.var_dob, 2, 0),
            ("Date of Joining:", self.var_doj, 3, 0),
            ("Contact:", self.var_contact, 0, 2),
            ("Email:", self.var_email, 1, 2),
            ("Salary:", self.var_salary, 2, 2),
        ]

        for lbl, var, row, col in fields:
            Label(form_frame, text=lbl, bg="#f0f0f0", font=("Arial", 11)).grid(row=row, column=col, padx=10, pady=5, sticky=W)
            Entry(form_frame, textvariable=var, font=("Arial", 11), width=20).grid(row=row, column=col+1, padx=10, pady=5)

        Label(form_frame, text="Gender:", bg="#f0f0f0", font=("Arial", 11)).grid(row=4, column=0, padx=10, pady=5, sticky=W)
        ttk.Combobox(form_frame, textvariable=self.var_gender,
                     values=["Male", "Female", "Other"],
                     font=("Arial", 11), width=18).grid(row=4, column=1, padx=10, pady=5)

        Label(form_frame, text="User Type:", bg="#f0f0f0", font=("Arial", 11)).grid(row=3, column=2, padx=10, pady=5, sticky=W)
        ttk.Combobox(form_frame, textvariable=self.var_utype,
                     values=["Admin", "Employee"],
                     font=("Arial", 11), width=18).grid(row=3, column=3, padx=10, pady=5)

        Label(form_frame, text="Password:", bg="#f0f0f0", font=("Arial", 11)).grid(row=4, column=2, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_pass, font=("Arial", 11), width=20, show="*").grid(row=4, column=3, padx=10, pady=5)

        Label(form_frame, text="Address:", bg="#f0f0f0", font=("Arial", 11)).grid(row=5, column=0, padx=10, pady=5, sticky=W)
        self.txt_address = Text(form_frame, font=("Arial", 11), width=20, height=3)
        self.txt_address.grid(row=5, column=1, padx=10, pady=5)

        # Search
        search_frame = Frame(main_frame, bg="#f0f0f0")
        search_frame.pack(fill=X, padx=20, pady=5)

        Label(search_frame, text="Search By:", bg="#f0f0f0", font=("Arial", 11)).grid(row=0, column=0, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Employee ID", "Name", "Contact", "Email"],
                     font=("Arial", 11), width=15).grid(row=0, column=1, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt, font=("Arial", 11), width=20).grid(row=0, column=2, padx=5)
        Button(search_frame, text="Search", command=self.search, bg="#8e44ad", fg="white",
               font=("Arial", 11)).grid(row=0, column=3, padx=5)
        Button(search_frame, text="Show All", command=self.show, bg="#16a085", fg="white",
               font=("Arial", 11)).grid(row=0, column=4, padx=5)

        btn_frame = Frame(main_frame, bg="#f0f0f0")
        btn_frame.pack(pady=10)

        Button(btn_frame, text="Add", command=self.add, bg="#27ae60", fg="white",
               font=("Arial", 11), width=10).grid(row=0, column=0, padx=5)
        Button(btn_frame, text="Update", command=self.update, bg="#f39c12", fg="white",
               font=("Arial", 11), width=10).grid(row=0, column=1, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, bg="#e74c3c", fg="white",
               font=("Arial", 11), width=10).grid(row=0, column=2, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, bg="#3498db", fg="white",
               font=("Arial", 11), width=10).grid(row=0, column=3, padx=5)

        table_frame = Frame(main_frame)
        table_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)

        scroll_x = Scrollbar(table_frame, orient=HORIZONTAL)
        scroll_y = Scrollbar(table_frame, orient=VERTICAL)

        cols = ("emp_id", "name", "dob", "doj", "gender", "contact", "email", "salary", "utype", "password", "address")
        self.EmployeeTable = ttk.Treeview(table_frame, columns=cols,
                                          xscrollcommand=scroll_x.set,
                                          yscrollcommand=scroll_y.set)
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.config(command=self.EmployeeTable.xview)
        scroll_y.config(command=self.EmployeeTable.yview)

        headings = ["Emp ID", "Name", "DOB", "DOJ", "Gender", "Contact", "Email", "Salary", "User Type", "Password", "Address"]
        for col, heading in zip(cols, headings):
            self.EmployeeTable.heading(col, text=heading)
            self.EmployeeTable.column(col, width=100)
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
            cur.execute("INSERT INTO employee VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (self.var_emp_id.get(), self.var_name.get(), self.var_dob.get(),
                         self.var_doj.get(), self.var_gender.get(), self.var_contact.get(),
                         self.var_email.get(), self.var_salary.get(), self.var_utype.get(),
                         self.var_pass.get(), self.txt_address.get("1.0", END).strip()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee added successfully", parent=self.root)
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
            cur.execute("""UPDATE employee SET name=?, dob=?, doj=?, gender=?, contact=?,
                           email=?, salary=?, utype=?, password=?, address=? WHERE emp_id=?""",
                        (self.var_name.get(), self.var_dob.get(), self.var_doj.get(),
                         self.var_gender.get(), self.var_contact.get(), self.var_email.get(),
                         self.var_salary.get(), self.var_utype.get(), self.var_pass.get(),
                         self.txt_address.get("1.0", END).strip(), self.var_emp_id.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee updated successfully", parent=self.root)
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
            messagebox.showinfo("Success", "Employee deleted successfully", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

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
            self.var_pass.set(row[9])
            self.txt_address.delete("1.0", END)
            self.txt_address.insert(END, row[10] if len(row) > 10 else "")

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

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM employee")
        rows = cur.fetchall()
        conn.close()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for row in rows:
            self.EmployeeTable.insert("", END, values=row)


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

        main_frame = Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=BOTH, expand=True)

        title = Label(main_frame, text="Product Management", font=("Arial", 18, "bold"),
                      bg="#2c3e50", fg="white", pady=10)
        title.pack(fill=X)

        form_frame = Frame(main_frame, bg="#f0f0f0", pady=10)
        form_frame.pack(fill=X, padx=20)

        Label(form_frame, text="Product ID:", bg="#f0f0f0", font=("Arial", 11)).grid(row=0, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_pid, font=("Arial", 11), width=20).grid(row=0, column=1, padx=10, pady=5)

        Label(form_frame, text="Name:", bg="#f0f0f0", font=("Arial", 11)).grid(row=1, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_name, font=("Arial", 11), width=20).grid(row=1, column=1, padx=10, pady=5)

        Label(form_frame, text="Price:", bg="#f0f0f0", font=("Arial", 11)).grid(row=2, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_price, font=("Arial", 11), width=20).grid(row=2, column=1, padx=10, pady=5)

        Label(form_frame, text="Quantity:", bg="#f0f0f0", font=("Arial", 11)).grid(row=3, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_qty, font=("Arial", 11), width=20).grid(row=3, column=1, padx=10, pady=5)

        Label(form_frame, text="Status:", bg="#f0f0f0", font=("Arial", 11)).grid(row=0, column=2, padx=10, pady=5, sticky=W)
        ttk.Combobox(form_frame, textvariable=self.var_status,
                     values=["Active", "Inactive"],
                     font=("Arial", 11), width=18).grid(row=0, column=3, padx=10, pady=5)

        Label(form_frame, text="Category:", bg="#f0f0f0", font=("Arial", 11)).grid(row=1, column=2, padx=10, pady=5, sticky=W)
        self.cat_combo = ttk.Combobox(form_frame, textvariable=self.var_cat,
                                       font=("Arial", 11), width=18)
        self.cat_combo.grid(row=1, column=3, padx=10, pady=5)

        Label(form_frame, text="Supplier:", bg="#f0f0f0", font=("Arial", 11)).grid(row=2, column=2, padx=10, pady=5, sticky=W)
        self.sup_combo = ttk.Combobox(form_frame, textvariable=self.var_sup,
                                       font=("Arial", 11), width=18)
        self.sup_combo.grid(row=2, column=3, padx=10, pady=5)

        # Search
        search_frame = Frame(main_frame, bg="#f0f0f0")
        search_frame.pack(fill=X, padx=20, pady=5)

        Label(search_frame, text="Search By:", bg="#f0f0f0", font=("Arial", 11)).grid(row=0, column=0, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Product ID", "Name", "Status", "Category"],
                     font=("Arial", 11), width=15).grid(row=0, column=1, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt, font=("Arial", 11), width=20).grid(row=0, column=2, padx=5)
        Button(search_frame, text="Search", command=self.search, bg="#8e44ad", fg="white",
               font=("Arial", 11)).grid(row=0, column=3, padx=5)
        Button(search_frame, text="Show All", command=self.show, bg="#16a085", fg="white",
               font=("Arial", 11)).grid(row=0, column=4, padx=5)

        btn_frame = Frame(main_frame, bg="#f0f0f0")
        btn_frame.pack(pady=10)

        Button(btn_frame, text="Add", command=self.add, bg="#27ae60", fg="white",
               font=("Arial", 11), width=10).grid(row=0, column=0, padx=5)
        Button(btn_frame, text="Update", command=self.update, bg="#f39c12", fg="white",
               font=("Arial", 11), width=10).grid(row=0, column=1, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, bg="#e74c3c", fg="white",
               font=("Arial", 11), width=10).grid(row=0, column=2, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, bg="#3498db", fg="white",
               font=("Arial", 11), width=10).grid(row=0, column=3, padx=5)

        table_frame = Frame(main_frame)
        table_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)

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

        headings = ["Product ID", "Name", "Price", "Quantity", "Status", "Category", "Supplier"]
        for col, heading in zip(cols, headings):
            self.ProductTable.heading(col, text=heading)
            self.ProductTable.column(col, width=100)
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
            cur.execute("INSERT INTO product VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (self.var_pid.get(), self.var_name.get(), self.var_price.get(),
                         self.var_qty.get(), self.var_status.get(), self.var_cat.get(),
                         self.var_sup.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product added successfully", parent=self.root)
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
            cur.execute("UPDATE product SET name=?, price=?, qty=?, status=?, cat=?, sup=? WHERE pid=?",
                        (self.var_name.get(), self.var_price.get(), self.var_qty.get(),
                         self.var_status.get(), self.var_cat.get(), self.var_sup.get(),
                         self.var_pid.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product updated successfully", parent=self.root)
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
            messagebox.showinfo("Success", "Product deleted successfully", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self.root)

    def clear(self):
        self.var_pid.set("")
        self.var_name.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("")
        self.var_cat.set("")
        self.var_sup.set("")

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
        col_map = {"Product ID": "pid", "Name": "name", "Status": "status", "Category": "cat"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM product WHERE {col} LIKE ?", (f"%{self.var_searchtxt.get()}%",))
        rows = cur.fetchall()
        conn.close()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for row in rows:
            self.ProductTable.insert("", END, values=row)

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM product")
        rows = cur.fetchall()
        conn.close()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for row in rows:
            self.ProductTable.insert("", END, values=row)


# ─────────────────────────────────────────────
# sales module
# ─────────────────────────────────────────────
class salesClass:
    def __init__(self, root):
        self.root = root
        self.var_invoice = StringVar()
        self.blll_list = []
        self.bill_photo = None

        main_frame = Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=BOTH, expand=True)

        title = Label(main_frame, text="Sales / Billing Records", font=("Arial", 18, "bold"),
                      bg="#2c3e50", fg="white", pady=10)
        title.pack(fill=X)

        top_frame = Frame(main_frame, bg="#f0f0f0")
        top_frame.pack(fill=X, padx=20, pady=10)

        Label(top_frame, text="Search Invoice:", bg="#f0f0f0", font=("Arial", 11)).grid(row=0, column=0, padx=5)
        Entry(top_frame, textvariable=self.var_invoice, font=("Arial", 11), width=20).grid(row=0, column=1, padx=5)
        Button(top_frame, text="Search", command=self.search, bg="#8e44ad", fg="white",
               font=("Arial", 11)).grid(row=0, column=2, padx=5)
        Button(top_frame, text="Show All", command=self.show, bg="#16a085", fg="white",
               font=("Arial", 11)).grid(row=0, column=3, padx=5)
        Button(top_frame, text="Clear", command=self.clear, bg="#3498db", fg="white",
               font=("Arial", 11)).grid(row=0, column=4, padx=5)

        content_frame = Frame(main_frame, bg="#f0f0f0")
        content_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)

        # List frame
        list_frame = Frame(content_frame, bg="#f0f0f0")
        list_frame.pack(side=LEFT, fill=Y)

        Label(list_frame, text="Invoices", bg="#2c3e50", fg="white",
              font=("Arial", 12, "bold"), pady=5).pack(fill=X)

        scroll_y = Scrollbar(list_frame, orient=VERTICAL)
        self.Sales_List = Listbox(list_frame, font=("Arial", 11), width=25,
                                  yscrollcommand=scroll_y.set, bg="#ecf0f1")
        scroll_y.config(command=self.Sales_List.yview)
        scroll_y.pack(side=RIGHT, fill=Y)
        self.Sales_List.pack(fill=Y, expand=True)
        self.Sales_List.bind("<ButtonRelease-1>", self.get_data)

        # Bill area
        bill_frame = Frame(content_frame, bg="#f0f0f0")
        bill_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=10)

        Label(bill_frame, text="Bill Details", bg="#2c3e50", fg="white",
              font=("Arial", 12, "bold"), pady=5).pack(fill=X)

        scroll_bill = Scrollbar(bill_frame, orient=VERTICAL)
        self.bill_area = Text(bill_frame, font=("Courier", 11), yscrollcommand=scroll_bill.set,
                              bg="#fdfefe", state=DISABLED)
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
            bill_text = f"""
{'='*40}
        INVENTORY MANAGEMENT SYSTEM
{'='*40}
Invoice   : {row[0]}
Customer  : {row[1]}
Contact   : {row[2]}
Date      : {row[5]}
{'='*40}
{row[3]}
{'='*40}
Net Pay   : {row[4]}
{'='*40}
"""
            self.bill_area.insert(END, bill_text)
            self.bill_area.config(state=DISABLED)

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
        self.var_pid = StringVar()
        self.var_pname = StringVar()
        self.var_price = StringVar()
        self.var_qty = StringVar()
        self.var_stock = StringVar()
        self.var_cname = StringVar()
        self.var_contact = StringVar()
        self.var_search = StringVar()
        self.var_cal_input = StringVar()

        self.cart_list = []
        self.bill_amnt = 0
        self.discount = 5.0
        self.siscount = 0
        self.net_pay = 0
        self.invoice = None
        self.chk_print = 0

        main_frame = Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=BOTH, expand=True)

        # Title
        title = Label(main_frame, text="Billing / Point of Sale", font=("Arial", 18, "bold"),
                      bg="#2c3e50", fg="white", pady=10)
        title.pack(fill=X)

        # Clock
        self.lbl_clock = Label(main_frame, text="", font=("Arial", 11), bg="#2c3e50", fg="white")
        self.lbl_clock.pack(fill=X)
        self.update_date_time()

        # Top section
        self.bill_top()
        self.bill_middle()
        self.bill_bottom()

    def bill_top(self):
        top_frame = Frame(self.root, bg="#f0f0f0", pady=5)
        top_frame.pack(fill=X, padx=20)

        Label(top_frame, text="Customer Name:", bg="#f0f0f0", font=("Arial", 11)).grid(row=0, column=0, padx=5, sticky=W)
        Entry(top_frame, textvariable=self.var_cname, font=("Arial", 11), width=20).grid(row=0, column=1, padx=5)

        Label(top_frame, text="Contact:", bg="#f0f0f0", font=("Arial", 11)).grid(row=0, column=2, padx=5, sticky=W)
        Entry(top_frame, textvariable=self.var_contact, font=("Arial", 11), width=20).grid(row=0, column=3, padx=5)

        Label(top_frame, text="Search Product:", bg="#f0f0f0", font=("Arial", 11)).grid(row=1, column=0, padx=5, sticky=W)
        Entry(top_frame, textvariable=self.var_search, font=("Arial", 11), width=20).grid(row=1, column=1, padx=5)
        Button(top_frame, text="Search", command=self.search, bg="#8e44ad", fg="white",
               font=("Arial", 11)).grid(row=1, column=2, padx=5)

    def bill_middle(self):
        mid_frame = Frame(self.root, bg="#f0f0f0")
        mid_frame.pack(fill=BOTH, expand=True, padx=20, pady=5)

        # Product table
        left_frame = Frame(mid_frame, bg="#f0f0f0")
        left_frame.pack(side=LEFT, fill=BOTH, expand=True)

        Label(left_frame, text="Products", bg="#2c3e50", fg="white",
              font=("Arial", 12, "bold"), pady=3).pack(fill=X)

        prod_scroll_y = Scrollbar(left_frame, orient=VERTICAL)
        prod_scroll_x = Scrollbar(left_frame, orient=HORIZONTAL)

        prod_cols = ("pid", "name", "price", "qty", "status")
        self.product_Table = ttk.Treeview(left_frame, columns=prod_cols,
                                          yscrollcommand=prod_scroll_y.set,
                                          xscrollcommand=prod_scroll_x.set)
        prod_scroll_y.config(command=self.product_Table.yview)
        prod_scroll_x.config(command=self.product_Table.xview)
        prod_scroll_x.pack(side=BOTTOM, fill=X)
        prod_scroll_y.pack(side=RIGHT, fill=Y)

        prod_headings = ["PID", "Name", "Price", "Qty", "Status"]
        for col, heading in zip(prod_cols, prod_headings):
            self.product_Table.heading(col, text=heading)
            self.product_Table.column(col, width=80)
        self.product_Table["show"] = "headings"
        self.product_Table.pack(fill=BOTH, expand=True)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)

        # Product detail & add to cart
        detail_frame = Frame(left_frame, bg="#f0f0f0", pady=5)
        detail_frame.pack(fill=X)

        Label(detail_frame, text="PID:", bg="#f0f0f0", font=("Arial", 10)).grid(row=0, column=0, padx=3)
        Entry(detail_frame, textvariable=self.var_pid, font=("Arial", 10), width=10, state="readonly").grid(row=0, column=1, padx=3)

        Label(detail_frame, text="Name:", bg="#f0f0f0", font=("Arial", 10)).grid(row=0, column=2, padx=3)
        Entry(detail_frame, textvariable=self.var_pname, font=("Arial", 10), width=15, state="readonly").grid(row=0, column=3, padx=3)

        Label(detail_frame, text="Price:", bg="#f0f0f0", font=("Arial", 10)).grid(row=0, column=4, padx=3)
        Entry(detail_frame, textvariable=self.var_price, font=("Arial", 10), width=10, state="readonly").grid(row=0, column=5, padx=3)

        Label(detail_frame, text="Qty:", bg="#f0f0f0", font=("Arial", 10)).grid(row=1, column=0, padx=3)
        Entry(detail_frame, textvariable=self.var_qty, font=("Arial", 10), width=10).grid(row=1, column=1, padx=3)

        self.lbl_inStock = Label(detail_frame, text="In Stock: 0", bg="#f0f0f0", font=("Arial", 10))
        self.lbl_inStock.grid(row=1, column=2, padx=3)

        Button(detail_frame, text="Add to Cart", command=self.add_update_cart,
               bg="#27ae60", fg="white", font=("Arial", 10)).grid(row=1, column=3, padx=5)

        # Cart table
        right_frame = Frame(mid_frame, bg="#f0f0f0")
        right_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=10)

        self.cartTitle = Label(right_frame, text="Cart (0 items)", bg="#2c3e50", fg="white",
                               font=("Arial", 12, "bold"), pady=3)
        self.cartTitle.pack(fill=X)

        cart_scroll_y = Scrollbar(right_frame, orient=VERTICAL)
        cart_scroll_x = Scrollbar(right_frame, orient=HORIZONTAL)

        cart_cols = ("pid", "name", "price", "qty", "total")
        self.CartTable = ttk.Treeview(right_frame, columns=cart_cols,
                                      yscrollcommand=cart_scroll_y.set,
                                      xscrollcommand=cart_scroll_x.set)
        cart_scroll_y.config(command=self.CartTable.yview)
        cart_scroll_x.config(command=self.CartTable.xview)
        cart_scroll_x.pack(side=BOTTOM, fill=X)
        cart_scroll_y.pack(side=RIGHT, fill=Y)

        cart_headings = ["PID", "Name", "Price", "Qty", "Total"]
        for col, heading in zip(cart_cols, cart_headings):
            self.CartTable.heading(col, text=heading)
            self.CartTable.column(col, width=80)
        self.CartTable["show"] = "headings"
        self.CartTable.pack(fill=BOTH, expand=True)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        cart_btn_frame = Frame(right_frame, bg="#f0f0f0")
        cart_btn_frame.pack(fill=X, pady=3)

        Button(cart_btn_frame, text="Remove Item", command=self.clear_cart,
               bg="#e74c3c", fg="white", font=("Arial", 10)).pack(side=LEFT, padx=5)
        Button(cart_btn_frame, text="Clear All", command=self.clear_all,
               bg="#95a5a6", fg="white", font=("Arial", 10)).pack(side=LEFT, padx=5)

        self.show()

    def bill_bottom(self):
        bottom_frame = Frame(self.root, bg="#f0f0f0")
        bottom_frame.pack(fill=X, padx=20, pady=5)

        # Amount labels
        amt_frame = Frame(bottom_frame, bg="#f0f0f0")
        amt_frame.pack(side=LEFT, fill=Y)

        self.lbl_amnt = Label(amt_frame, text="Bill Amount: 0.00", bg="#f0f0f0",
                              font=("Arial", 12, "bold"))
        self.lbl_amnt.pack(anchor=W)

        self.lbl_discount = Label(amt_frame, text=f"Discount: {self.discount}%", bg="#f0f0f0",
                                  font=("Arial", 12))
        self.lbl_discount.pack(anchor=W)

        self.lbl_net_pay = Label(amt_frame, text="Net Pay: 0.00", bg="#f0f0f0",
                                 font=("Arial", 12, "bold"), fg="#27ae60")
        self.lbl_net_pay.pack(anchor=W)

        # Bill text area
        bill_text_frame = Frame(bottom_frame, bg="#f0f0f0")
        bill_text_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=10)

        self.txt_bill_area = Text(bill_text_frame, font=("Courier", 10), height=8,
                                  bg="#fdfefe", state=DISABLED)
        self.txt_bill_area.pack(fill=BOTH, expand=True)

        # Calculator
        cal_frame = Frame(bottom_frame, bg="#f0f0f0")
        cal_frame.pack(side=LEFT, fill=Y, padx=10)

        Label(cal_frame, text="Calculator", bg="#2c3e50", fg="white",
              font=("Arial", 11, "bold"), pady=3).pack(fill=X)

        self.txt_cal_input = Entry(cal_frame, textvariable=self.var_cal_input,
                                   font=("Arial", 12), width=15, justify=RIGHT)
        self.txt_cal_input.pack(pady=3)

        cal_buttons = [
            ["7", "8", "9", "/"],
            ["4", "5", "6", "*"],
            ["1", "2", "3", "-"],
            ["0", ".", "=", "+"],
        ]

        for row_btns in cal_buttons:
            row_frame = Frame(cal_frame, bg="#f0f0f0")
            row_frame.pack()
            for btn_text in row_btns:
                Button(row_frame, text=btn_text, font=("Arial", 11), width=4,
                       command=lambda t=btn_text: self.get_input(t),
                       bg="#ecf0f1").pack(side=LEFT, padx=1, pady=1)

        Button(cal_frame, text="Clear", command=self.clear_cal,
               bg="#e74c3c", fg="white", font=("Arial", 10), width=15).pack(pady=2)

        # Action buttons
        action_frame = Frame(bottom_frame, bg="#f0f0f0")
        action_frame.pack(side=LEFT, fill=Y, padx=10)

        Button(action_frame, text="Generate Bill", command=self.generate_bill,
               bg="#27ae60", fg="white", font=("Arial", 11), width=15).pack(pady=3)
        Button(action_frame, text="Print Bill", command=self.print_bill,
               bg="#2980b9", fg="white", font=("Arial", 11), width=15).pack(pady=3)
        Button(action_frame, text="Clear All", command=self.clear_all,
               bg="#95a5a6", fg="white", font=("Arial", 11), width=15).pack(pady=3)

    def update_date_time(self):
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("  Date: %d/%m/%Y    Time: %H:%M:%S"))
        self.root.after(1000, self.update_date_time)

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT pid, name, price, qty, status FROM product WHERE status='Active'")
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
        cur.execute("SELECT pid, name, price, qty, status FROM product WHERE name LIKE ? OR pid LIKE ?",
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
            self.lbl_inStock.config(text=f"In Stock: {row[3]}")

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
            messagebox.showerror("Error", "Quantity must be greater than 0", parent=self.root)
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
        self.cartTitle.config(text=f"Cart ({len(self.cart_list)} items)")

    def bill_update(self):
        self.bill_amnt = sum(item[4] for item in self.cart_list)
        self.siscount = self.bill_amnt * self.discount / 100
        self.net_pay = self.bill_amnt - self.siscount

        self.lbl_amnt.config(text=f"Bill Amount: {self.bill_amnt:.2f}")
        self.lbl_discount.config(text=f"Discount ({self.discount}%): {self.siscount:.2f}")
        self.lbl_net_pay.config(text=f"Net Pay: {self.net_pay:.2f}")

    def clear_cart(self):
        selected = self.CartTable.focus()
        content = self.CartTable.item(selected)
        row = content["values"]
        if row:
            self.cart_list = [item for item in self.cart_list if item[0] != str(row[0])]
            self.show_cart()
            self.bill_update()

    def clear_all(self):
        self.cart_list = []
        self.show_cart()
        self.bill_update()
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")
        self.var_cname.set("")
        self.var_contact.set("")
        self.txt_bill_area.config(state=NORMAL)
        self.txt_bill_area.delete("1.0", END)
        self.txt_bill_area.config(state=DISABLED)
        self.invoice = None

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty", parent=self.root)
            return
        if self.var_cname.get() == "":
            messagebox.showerror("Error", "Customer name is required", parent=self.root)
            return

        self.invoice = f"INV{random.randint(1000, 9999)}"
        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        bill_text = f"""
{'='*40}
    INVENTORY MANAGEMENT SYSTEM
{'='*40}
Invoice  : {self.invoice}
Customer : {self.var_cname.get()}
Contact  : {self.var_contact.get()}
Date     : {now}
{'='*40}
{'Item':<15} {'Qty':>5} {'Price':>8} {'Total':>8}
{'-'*40}
"""
        items_text = ""
        for item in self.cart_list:
            items_text += f"{str(item[1]):<15} {item[3]:>5} {item[2]:>8.2f} {item[4]:>8.2f}\n"

        bill_text += items_text
        bill_text += f"""{'='*40}
Bill Amount : {self.bill_amnt:.2f}
Discount    : {self.siscount:.2f} ({self.discount}%)
Net Pay     : {self.net_pay:.2f}
{'='*40}
     Thank you for shopping!
{'='*40}
"""
        self.txt_bill_area.config(state=NORMAL)
        self.txt_bill_area.delete("1.0", END)
        self.txt_bill_area.insert(END, bill_text)
        self.txt_bill_area.config(state=DISABLED)

        # Save to DB
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?)",
                        (self.invoice, self.var_cname.get(), self.var_contact.get(),
                         items_text, str(self.net_pay), now))
            # Update product quantities
            for item in self.cart_list:
                cur.execute("UPDATE product SET qty = qty - ? WHERE pid=?",
                            (item[3], item[0]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Bill generated! Invoice: {self.invoice}", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Error saving bill: {e}", parent=self.root)

    def print_bill(self):
        if self.invoice is None:
            messagebox.showerror("Error", "Generate bill first", parent=self.root)
            return
        messagebox.showinfo("Print", f"Bill {self.invoice} sent to printer (simulated)", parent=self.root)

    def get_input(self, num):
        if num == "=":
            self.perform_cal()
        else:
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


# ─────────────────────────────────────────────
# dashboard / IMS module
# ─────────────────────────────────────────────
class IMS:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("1200x700+0+0")
        self.root.config(bg="#f0f0f0")

        self.new_win = None
        self.new_obj = None

        # Try to load icons (graceful fallback)
        self.MenuLogo = None
        self.icon_side = None
        self.icon_title = None

        # Title bar
        title_frame = Frame(self.root, bg="#2c3e50", pady=10)
        title_frame.pack(fill=X)

        Label(title_frame, text="INVENTORY MANAGEMENT SYSTEM",
              font=("Arial", 22, "bold"), bg="#2c3e50", fg="white").pack()

        # Clock label
        self.lbl_clock = Label(title_frame, text="", font=("Arial", 11),
                               bg="#2c3e50", fg="#bdc3c7")
        self.lbl_clock.pack()
        self.update_content()

        # Sidebar
        sidebar = Frame(self.root, bg="#34495e", width=200)
        sidebar.pack(side=LEFT, fill=Y)
        sidebar.pack_propagate(False)

        Label(sidebar, text="MENU", font=("Arial", 14, "bold"),
              bg="#34495e", fg="white", pady=15).pack(fill=X)

        menu_items = [
            ("Category", self.category, "#1abc9c"),
            ("Employee", self.employee, "#3498db"),
            ("Supplier", self.supplier, "#9b59b6"),
            ("Product", self.product, "#e67e22"),
            ("Sales", self.sales, "#e74c3c"),
            ("Billing", self.billing, "#27ae60"),
        ]

        for text, cmd, color in menu_items:
            btn = Button(sidebar, text=text, command=cmd,
                         font=("Arial", 12), bg=color, fg="white",
                         relief=FLAT, pady=10, cursor="hand2")
            btn.pack(fill=X, padx=10, pady=3)

        # Main content area
        self.content_frame = Frame(self.root, bg="#ecf0f1")
        self.content_frame.pack(side=LEFT, fill=BOTH, expand=True)

        # Dashboard stats
        self.show_dashboard()

    def show_dashboard(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        Label(self.content_frame, text="Dashboard", font=("Arial", 18, "bold"),
              bg="#ecf0f1", fg="#2c3e50").pack(pady=20)

        stats_frame = Frame(self.content_frame, bg="#ecf0f1")
        stats_frame.pack(pady=20)

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM category")
        cat_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM employee")
        emp_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM product")
        prod_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM sales")
        sales_count = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM supplier")
        sup_count = cur.fetchone()[0]

        conn.close()

        stats = [
            ("Categories", cat_count, "#1abc9c"),
            ("Employees", emp_count, "#3498db"),
            ("Products", prod_count, "#e67e22"),
            ("Sales", sales_count, "#e74c3c"),
            ("Suppliers", sup_count, "#9b59b6"),
        ]

        for i, (label, count, color) in enumerate(stats):
            card = Frame(stats_frame, bg=color, width=150, height=100)
            card.grid(row=0, column=i, padx=10, pady=10)
            card.pack_propagate(False)
            Label(card, text=str(count), font=("Arial", 28, "bold"),
                  bg=color, fg="white").pack(expand=True)
            Label(card, text=label, font=("Arial", 12),
                  bg=color, fg="white").pack()

        # Stat labels referenced in spec
        self.lbl_category = Label(self.content_frame, text=f"Total Categories: {cat_count}",
                                  font=("Arial", 12), bg="#ecf0f1")
        self.lbl_category.pack()
        self.lbl_employee = Label(self.content_frame, text=f"Total Employees: {emp_count}",
                                  font=("Arial", 12), bg="#ecf0f1")
        self.lbl_employee.pack()
        self.lbl_product = Label(self.content_frame, text=f"Total Products: {prod_count}",
                                 font=("Arial", 12), bg="#ecf0f1")
        self.lbl_product.pack()
        self.lbl_sales = Label(self.content_frame, text=f"Total Sales: {sales_count}",
                               font=("Arial", 12), bg="#ecf0f1")
        self.lbl_sales.pack()
        self.lbl_supplier = Label(self.content_frame, text=f"Total Suppliers: {sup_count}",
                                  font=("Arial", 12), bg="#ecf0f1")
        self.lbl_supplier.pack()

    def update_content(self):
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("  %A, %d %B %Y    %H:%M:%S"))
        self.root.after(1000, self.update_content)

    def open_window(self, title, cls):
        if self.new_win is not None:
            try:
                self.new_win.destroy()
            except Exception:
                pass

        self.new_win = Toplevel(self.root)
        self.new_win.title(title)
        self.new_win.geometry("1100x650+50+50")
        self.new_win.config(bg="#f0f0f0")
        self.new_obj = cls(self.new_win)

    def category(self):
        self.open_window("Category Management", categoryClass)

    def employee(self):
        self.open_window("Employee Management", employeeClass)

    def supplier(self):
        self.open_window("Supplier Management", supplierClass)

    def product(self):
        self.open_window("Product Management", productClass)

    def sales(self):
        self.open_window("Sales Records", salesClass)

    def billing(self):
        self.open_window("Billing / POS", billClass)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    root = Tk()
    app = IMS(root)
    root.mainloop()