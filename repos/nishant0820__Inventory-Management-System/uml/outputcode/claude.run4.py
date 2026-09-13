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
def get_connection():
    conn = sqlite3.connect("ims.db")
    return conn


def initialize_db():
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
        email TEXT,
        gender TEXT,
        contact TEXT,
        dob TEXT,
        doj TEXT,
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

        # Main frame
        main_frame = Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=BOTH, expand=True)

        title = Label(main_frame, text="Category Management",
                      font=("Arial", 18, "bold"), bg="#2c3e50", fg="white",
                      pady=10)
        title.pack(fill=X)

        # Form frame
        form_frame = Frame(main_frame, bg="#f0f0f0", pady=10)
        form_frame.pack(fill=X, padx=20)

        Label(form_frame, text="Category ID:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=0, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_cat_id,
              font=("Arial", 11), width=20).grid(row=0, column=1, padx=10, pady=5)

        Label(form_frame, text="Category Name:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=1, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_name,
              font=("Arial", 11), width=20).grid(row=1, column=1, padx=10, pady=5)

        # Image labels (placeholders)
        self.lbl_im1 = Label(form_frame, text="[Image 1]", bg="#ddd", width=10, height=4)
        self.lbl_im1.grid(row=0, column=2, rowspan=2, padx=20)
        self.lbl_im2 = Label(form_frame, text="[Image 2]", bg="#ddd", width=10, height=4)
        self.lbl_im2.grid(row=0, column=3, rowspan=2, padx=20)

        # Buttons
        btn_frame = Frame(main_frame, bg="#f0f0f0")
        btn_frame.pack(fill=X, padx=20, pady=5)

        Button(btn_frame, text="Add", command=self.add,
               bg="#27ae60", fg="white", font=("Arial", 11), width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete,
               bg="#e74c3c", fg="white", font=("Arial", 11), width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear,
               bg="#95a5a6", fg="white", font=("Arial", 11), width=10).pack(side=LEFT, padx=5)

        # Table
        table_frame = Frame(main_frame, bg="#f0f0f0")
        table_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)

        scroll_x = Scrollbar(table_frame, orient=HORIZONTAL)
        scroll_y = Scrollbar(table_frame, orient=VERTICAL)

        self.CategoryTable = ttk.Treeview(
            table_frame,
            columns=("cat_id", "name"),
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set
        )
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

        title = Label(main_frame, text="Supplier Management",
                      font=("Arial", 18, "bold"), bg="#2c3e50", fg="white", pady=10)
        title.pack(fill=X)

        form_frame = Frame(main_frame, bg="#f0f0f0", pady=10)
        form_frame.pack(fill=X, padx=20)

        Label(form_frame, text="Supplier Invoice:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=0, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_sup_invoice,
              font=("Arial", 11), width=20).grid(row=0, column=1, padx=10, pady=5)

        Label(form_frame, text="Name:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=1, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_name,
              font=("Arial", 11), width=20).grid(row=1, column=1, padx=10, pady=5)

        Label(form_frame, text="Contact:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=2, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_contact,
              font=("Arial", 11), width=20).grid(row=2, column=1, padx=10, pady=5)

        Label(form_frame, text="Description:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=3, column=0, padx=10, pady=5, sticky=W)
        self.txt_desc = Text(form_frame, font=("Arial", 11), width=30, height=4)
        self.txt_desc.grid(row=3, column=1, padx=10, pady=5)

        # Search
        search_frame = Frame(main_frame, bg="#f0f0f0")
        search_frame.pack(fill=X, padx=20, pady=5)

        Label(search_frame, text="Search By:", bg="#f0f0f0",
              font=("Arial", 11)).pack(side=LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Invoice", "Name", "Contact"],
                     font=("Arial", 11), width=12).pack(side=LEFT, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt,
              font=("Arial", 11), width=20).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search,
               bg="#2980b9", fg="white", font=("Arial", 11)).pack(side=LEFT, padx=5)
        Button(search_frame, text="Show All", command=self.show,
               bg="#8e44ad", fg="white", font=("Arial", 11)).pack(side=LEFT, padx=5)

        # Buttons
        btn_frame = Frame(main_frame, bg="#f0f0f0")
        btn_frame.pack(fill=X, padx=20, pady=5)

        Button(btn_frame, text="Add", command=self.add,
               bg="#27ae60", fg="white", font=("Arial", 11), width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update,
               bg="#f39c12", fg="white", font=("Arial", 11), width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete,
               bg="#e74c3c", fg="white", font=("Arial", 11), width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear,
               bg="#95a5a6", fg="white", font=("Arial", 11), width=10).pack(side=LEFT, padx=5)

        # Table
        table_frame = Frame(main_frame, bg="#f0f0f0")
        table_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)

        scroll_x = Scrollbar(table_frame, orient=HORIZONTAL)
        scroll_y = Scrollbar(table_frame, orient=VERTICAL)

        self.SupplierTable = ttk.Treeview(
            table_frame,
            columns=("sup_invoice", "name", "contact", "desc"),
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set
        )
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.config(command=self.SupplierTable.xview)
        scroll_y.config(command=self.SupplierTable.yview)

        self.SupplierTable.heading("sup_invoice", text="Invoice")
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
        if self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Enter search text", parent=self.root)
            return
        col_map = {"Invoice": "sup_invoice", "Name": "name", "Contact": "contact"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM supplier WHERE {col} LIKE ?",
                    (f"%{self.var_searchtxt.get()}%",))
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
        self.var_email = StringVar()
        self.var_gender = StringVar()
        self.var_contact = StringVar()
        self.var_dob = StringVar()
        self.var_doj = StringVar()
        self.var_salary = StringVar()
        self.var_utype = StringVar()
        self.var_pass = StringVar()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()

        main_frame = Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=BOTH, expand=True)

        title = Label(main_frame, text="Employee Management",
                      font=("Arial", 18, "bold"), bg="#2c3e50", fg="white", pady=10)
        title.pack(fill=X)

        form_frame = Frame(main_frame, bg="#f0f0f0", pady=10)
        form_frame.pack(fill=X, padx=20)

        fields = [
            ("Employee ID:", self.var_emp_id, 0, 0),
            ("Name:", self.var_name, 1, 0),
            ("Email:", self.var_email, 2, 0),
            ("Gender:", self.var_gender, 3, 0),
            ("Contact:", self.var_contact, 0, 2),
            ("DOB:", self.var_dob, 1, 2),
            ("DOJ:", self.var_doj, 2, 2),
            ("Salary:", self.var_salary, 3, 2),
        ]

        for label, var, row, col in fields:
            Label(form_frame, text=label, bg="#f0f0f0",
                  font=("Arial", 11)).grid(row=row, column=col, padx=10, pady=5, sticky=W)
            Entry(form_frame, textvariable=var,
                  font=("Arial", 11), width=18).grid(row=row, column=col + 1, padx=10, pady=5)

        Label(form_frame, text="User Type:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=4, column=0, padx=10, pady=5, sticky=W)
        ttk.Combobox(form_frame, textvariable=self.var_utype,
                     values=["Admin", "Employee"],
                     font=("Arial", 11), width=16).grid(row=4, column=1, padx=10, pady=5)

        Label(form_frame, text="Password:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=4, column=2, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_pass,
              font=("Arial", 11), width=18, show="*").grid(row=4, column=3, padx=10, pady=5)

        Label(form_frame, text="Address:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=5, column=0, padx=10, pady=5, sticky=W)
        self.txt_address = Text(form_frame, font=("Arial", 11), width=40, height=3)
        self.txt_address.grid(row=5, column=1, columnspan=3, padx=10, pady=5)

        # Search
        search_frame = Frame(main_frame, bg="#f0f0f0")
        search_frame.pack(fill=X, padx=20, pady=5)

        Label(search_frame, text="Search By:", bg="#f0f0f0",
              font=("Arial", 11)).pack(side=LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Employee ID", "Name", "Email", "Contact"],
                     font=("Arial", 11), width=14).pack(side=LEFT, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt,
              font=("Arial", 11), width=20).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search,
               bg="#2980b9", fg="white", font=("Arial", 11)).pack(side=LEFT, padx=5)
        Button(search_frame, text="Show All", command=self.show,
               bg="#8e44ad", fg="white", font=("Arial", 11)).pack(side=LEFT, padx=5)

        # Buttons
        btn_frame = Frame(main_frame, bg="#f0f0f0")
        btn_frame.pack(fill=X, padx=20, pady=5)

        Button(btn_frame, text="Add", command=self.add,
               bg="#27ae60", fg="white", font=("Arial", 11), width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update,
               bg="#f39c12", fg="white", font=("Arial", 11), width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete,
               bg="#e74c3c", fg="white", font=("Arial", 11), width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear,
               bg="#95a5a6", fg="white", font=("Arial", 11), width=10).pack(side=LEFT, padx=5)

        # Table
        table_frame = Frame(main_frame, bg="#f0f0f0")
        table_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)

        scroll_x = Scrollbar(table_frame, orient=HORIZONTAL)
        scroll_y = Scrollbar(table_frame, orient=VERTICAL)

        cols = ("emp_id", "name", "email", "gender", "contact", "dob", "doj",
                "salary", "utype", "address", "password")
        self.EmployeeTable = ttk.Treeview(
            table_frame,
            columns=cols,
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set
        )
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.config(command=self.EmployeeTable.xview)
        scroll_y.config(command=self.EmployeeTable.yview)

        for col in cols:
            self.EmployeeTable.heading(col, text=col.replace("_", " ").title())
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
            cur.execute("INSERT INTO employee VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (self.var_emp_id.get(), self.var_name.get(), self.var_email.get(),
                         self.var_gender.get(), self.var_contact.get(), self.var_dob.get(),
                         self.var_doj.get(), self.var_salary.get(), self.var_utype.get(),
                         self.txt_address.get("1.0", END).strip(), self.var_pass.get()))
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
            cur.execute("""UPDATE employee SET name=?,email=?,gender=?,contact=?,dob=?,
                           doj=?,salary=?,utype=?,address=?,password=? WHERE emp_id=?""",
                        (self.var_name.get(), self.var_email.get(), self.var_gender.get(),
                         self.var_contact.get(), self.var_dob.get(), self.var_doj.get(),
                         self.var_salary.get(), self.var_utype.get(),
                         self.txt_address.get("1.0", END).strip(),
                         self.var_pass.get(), self.var_emp_id.get()))
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
        self.var_email.set("")
        self.var_gender.set("")
        self.var_contact.set("")
        self.var_dob.set("")
        self.var_doj.set("")
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
            self.var_email.set(row[2])
            self.var_gender.set(row[3])
            self.var_contact.set(row[4])
            self.var_dob.set(row[5])
            self.var_doj.set(row[6])
            self.var_salary.set(row[7])
            self.var_utype.set(row[8])
            self.txt_address.delete("1.0", END)
            self.txt_address.insert(END, row[9] if row[9] else "")
            self.var_pass.set(row[10] if len(row) > 10 else "")

    def search(self):
        if self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Enter search text", parent=self.root)
            return
        col_map = {"Employee ID": "emp_id", "Name": "name",
                   "Email": "email", "Contact": "contact"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM employee WHERE {col} LIKE ?",
                    (f"%{self.var_searchtxt.get()}%",))
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
        self.cat_list: list = []
        self.sup_list: list = []

        main_frame = Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=BOTH, expand=True)

        title = Label(main_frame, text="Product Management",
                      font=("Arial", 18, "bold"), bg="#2c3e50", fg="white", pady=10)
        title.pack(fill=X)

        form_frame = Frame(main_frame, bg="#f0f0f0", pady=10)
        form_frame.pack(fill=X, padx=20)

        Label(form_frame, text="Product ID:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=0, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_pid,
              font=("Arial", 11), width=18).grid(row=0, column=1, padx=10, pady=5)

        Label(form_frame, text="Name:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=1, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_name,
              font=("Arial", 11), width=18).grid(row=1, column=1, padx=10, pady=5)

        Label(form_frame, text="Price:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=2, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_price,
              font=("Arial", 11), width=18).grid(row=2, column=1, padx=10, pady=5)

        Label(form_frame, text="Quantity:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=3, column=0, padx=10, pady=5, sticky=W)
        Entry(form_frame, textvariable=self.var_qty,
              font=("Arial", 11), width=18).grid(row=3, column=1, padx=10, pady=5)

        Label(form_frame, text="Status:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=0, column=2, padx=10, pady=5, sticky=W)
        ttk.Combobox(form_frame, textvariable=self.var_status,
                     values=["Active", "Inactive"],
                     font=("Arial", 11), width=16).grid(row=0, column=3, padx=10, pady=5)

        Label(form_frame, text="Category:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=1, column=2, padx=10, pady=5, sticky=W)
        self.cat_combo = ttk.Combobox(form_frame, textvariable=self.var_cat,
                                       font=("Arial", 11), width=16)
        self.cat_combo.grid(row=1, column=3, padx=10, pady=5)

        Label(form_frame, text="Supplier:", bg="#f0f0f0",
              font=("Arial", 11)).grid(row=2, column=2, padx=10, pady=5, sticky=W)
        self.sup_combo = ttk.Combobox(form_frame, textvariable=self.var_sup,
                                       font=("Arial", 11), width=16)
        self.sup_combo.grid(row=2, column=3, padx=10, pady=5)

        # Search
        search_frame = Frame(main_frame, bg="#f0f0f0")
        search_frame.pack(fill=X, padx=20, pady=5)

        Label(search_frame, text="Search By:", bg="#f0f0f0",
              font=("Arial", 11)).pack(side=LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Product ID", "Name", "Status", "Category"],
                     font=("Arial", 11), width=12).pack(side=LEFT, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt,
              font=("Arial", 11), width=20).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search,
               bg="#2980b9", fg="white", font=("Arial", 11)).pack(side=LEFT, padx=5)
        Button(search_frame, text="Show All", command=self.show,
               bg="#8e44ad", fg="white", font=("Arial", 11)).pack(side=LEFT, padx=5)

        # Buttons
        btn_frame = Frame(main_frame, bg="#f0f0f0")
        btn_frame.pack(fill=X, padx=20, pady=5)

        Button(btn_frame, text="Add", command=self.add,
               bg="#27ae60", fg="white", font=("Arial", 11), width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update,
               bg="#f39c12", fg="white", font=("Arial", 11), width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete,
               bg="#e74c3c", fg="white", font=("Arial", 11), width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear,
               bg="#95a5a6", fg="white", font=("Arial", 11), width=10).pack(side=LEFT, padx=5)

        # Table
        table_frame = Frame(main_frame, bg="#f0f0f0")
        table_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)

        scroll_x = Scrollbar(table_frame, orient=HORIZONTAL)
        scroll_y = Scrollbar(table_frame, orient=VERTICAL)

        cols = ("pid", "name", "price", "qty", "status", "cat", "sup")
        self.ProductTable = ttk.Treeview(
            table_frame,
            columns=cols,
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set
        )
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.config(command=self.ProductTable.xview)
        scroll_y.config(command=self.ProductTable.yview)

        headers = ("Product ID", "Name", "Price", "Quantity", "Status", "Category", "Supplier")
        for col, hdr in zip(cols, headers):
            self.ProductTable.heading(col, text=hdr)
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
            cur.execute("INSERT INTO product VALUES (?,?,?,?,?,?,?)",
                        (self.var_pid.get(), self.var_name.get(), self.var_price.get(),
                         self.var_qty.get(), self.var_status.get(),
                         self.var_cat.get(), self.var_sup.get()))
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
            cur.execute("""UPDATE product SET name=?,price=?,qty=?,status=?,cat=?,sup=?
                           WHERE pid=?""",
                        (self.var_name.get(), self.var_price.get(), self.var_qty.get(),
                         self.var_status.get(), self.var_cat.get(),
                         self.var_sup.get(), self.var_pid.get()))
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
        if self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Enter search text", parent=self.root)
            return
        col_map = {"Product ID": "pid", "Name": "name", "Status": "status", "Category": "cat"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM product WHERE {col} LIKE ?",
                    (f"%{self.var_searchtxt.get()}%",))
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
        self.blll_list: list = []
        self.bill_photo = None

        main_frame = Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=BOTH, expand=True)

        title = Label(main_frame, text="Sales / Billing Records",
                      font=("Arial", 18, "bold"), bg="#2c3e50", fg="white", pady=10)
        title.pack(fill=X)

        top_frame = Frame(main_frame, bg="#f0f0f0")
        top_frame.pack(fill=X, padx=20, pady=5)

        Label(top_frame, text="Search Invoice:", bg="#f0f0f0",
              font=("Arial", 11)).pack(side=LEFT, padx=5)
        Entry(top_frame, textvariable=self.var_invoice,
              font=("Arial", 11), width=20).pack(side=LEFT, padx=5)
        Button(top_frame, text="Search", command=self.search,
               bg="#2980b9", fg="white", font=("Arial", 11)).pack(side=LEFT, padx=5)
        Button(top_frame, text="Show All", command=self.show,
               bg="#8e44ad", fg="white", font=("Arial", 11)).pack(side=LEFT, padx=5)
        Button(top_frame, text="Clear", command=self.clear,
               bg="#95a5a6", fg="white", font=("Arial", 11)).pack(side=LEFT, padx=5)

        content_frame = Frame(main_frame, bg="#f0f0f0")
        content_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)

        # Left: list of invoices
        left_frame = Frame(content_frame, bg="#f0f0f0")
        left_frame.pack(side=LEFT, fill=Y)

        Label(left_frame, text="Invoice List", bg="#2c3e50", fg="white",
              font=("Arial", 12, "bold")).pack(fill=X)

        scroll_y = Scrollbar(left_frame, orient=VERTICAL)
        self.Sales_List = Listbox(left_frame, font=("Arial", 11), width=25,
                                   yscrollcommand=scroll_y.set)
        scroll_y.config(command=self.Sales_List.yview)
        scroll_y.pack(side=RIGHT, fill=Y)
        self.Sales_List.pack(fill=Y, expand=True)
        self.Sales_List.bind("<ButtonRelease-1>", self.get_data)

        # Right: bill area
        right_frame = Frame(content_frame, bg="#f0f0f0")
        right_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=10)

        Label(right_frame, text="Bill Details", bg="#2c3e50", fg="white",
              font=("Arial", 12, "bold")).pack(fill=X)

        scroll_bill = Scrollbar(right_frame, orient=VERTICAL)
        self.bill_area = Text(right_frame, font=("Courier", 10), width=60,
                               yscrollcommand=scroll_bill.set)
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
            self.bill_area.insert(END, row[3] if row[3] else "")
            self.bill_area.config(state=DISABLED)

    def search(self):
        if self.var_invoice.get() == "":
            messagebox.showerror("Error", "Enter invoice number", parent=self.root)
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
        self.var_pid = StringVar()
        self.var_pname = StringVar()
        self.var_price = StringVar()
        self.var_qty = StringVar()
        self.var_stock = StringVar()
        self.var_search = StringVar()
        self.var_cname = StringVar()
        self.var_contact = StringVar()
        self.var_cal_input = StringVar()

        self.cart_list: list = []
        self.bill_amnt: int = 0
        self.discount: float = 0.0
        self.net_pay = 0
        self.siscount: int = 0
        self.chk_print: int = 0
        self.invoice = None

        self.root.title("Billing System")
        self.root.geometry("1200x700")
        self.root.config(bg="#f0f0f0")

        # Title
        title_frame = Frame(self.root, bg="#2c3e50")
        title_frame.pack(fill=X)

        try:
            self.icon_title = PhotoImage(file="images/logo.png")
        except Exception:
            self.icon_title = None

        Label(title_frame, text="Billing / Point of Sale",
              font=("Arial", 20, "bold"), bg="#2c3e50", fg="white",
              pady=10).pack(side=LEFT, padx=20)

        self.lbl_clock = Label(title_frame, text="", font=("Arial", 12),
                                bg="#2c3e50", fg="white")
        self.lbl_clock.pack(side=RIGHT, padx=20)
        self.update_date_time()

        # Main content
        main_frame = Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=BOTH, expand=True)

        # Left panel
        left_frame = Frame(main_frame, bg="#f0f0f0", width=400)
        left_frame.pack(side=LEFT, fill=Y, padx=10, pady=10)

        self.bill_top(left_frame)
        self.bill_middle(left_frame)
        self.bill_bottom(left_frame)

        # Right panel
        right_frame = Frame(main_frame, bg="#f0f0f0")
        right_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=10)

        self.show(right_frame)
        self.show_cart(right_frame)

    def update_date_time(self):
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%d-%m-%Y  %H:%M:%S"))
        self.root.after(1000, self.update_date_time)

    def bill_top(self, parent):
        frame = LabelFrame(parent, text="Customer Info", bg="#f0f0f0",
                           font=("Arial", 11, "bold"))
        frame.pack(fill=X, pady=5)

        Label(frame, text="Customer Name:", bg="#f0f0f0",
              font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=3, sticky=W)
        Entry(frame, textvariable=self.var_cname,
              font=("Arial", 10), width=20).grid(row=0, column=1, padx=5, pady=3)

        Label(frame, text="Contact:", bg="#f0f0f0",
              font=("Arial", 10)).grid(row=1, column=0, padx=5, pady=3, sticky=W)
        Entry(frame, textvariable=self.var_contact,
              font=("Arial", 10), width=20).grid(row=1, column=1, padx=5, pady=3)

    def bill_middle(self, parent):
        frame = LabelFrame(parent, text="Product Search", bg="#f0f0f0",
                           font=("Arial", 11, "bold"))
        frame.pack(fill=X, pady=5)

        Label(frame, text="Search:", bg="#f0f0f0",
              font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=3, sticky=W)
        Entry(frame, textvariable=self.var_search,
              font=("Arial", 10), width=20).grid(row=0, column=1, padx=5, pady=3)
        Button(frame, text="Search", command=self.search,
               bg="#2980b9", fg="white", font=("Arial", 10)).grid(row=0, column=2, padx=5)

        Label(frame, text="Product ID:", bg="#f0f0f0",
              font=("Arial", 10)).grid(row=1, column=0, padx=5, pady=3, sticky=W)
        Entry(frame, textvariable=self.var_pid,
              font=("Arial", 10), width=20, state="readonly").grid(row=1, column=1, padx=5, pady=3)

        Label(frame, text="Product Name:", bg="#f0f0f0",
              font=("Arial", 10)).grid(row=2, column=0, padx=5, pady=3, sticky=W)
        Entry(frame, textvariable=self.var_pname,
              font=("Arial", 10), width=20, state="readonly").grid(row=2, column=1, padx=5, pady=3)

        Label(frame, text="Price:", bg="#f0f0f0",
              font=("Arial", 10)).grid(row=3, column=0, padx=5, pady=3, sticky=W)
        Entry(frame, textvariable=self.var_price,
              font=("Arial", 10), width=20, state="readonly").grid(row=3, column=1, padx=5, pady=3)

        Label(frame, text="Quantity:", bg="#f0f0f0",
              font=("Arial", 10)).grid(row=4, column=0, padx=5, pady=3, sticky=W)
        Entry(frame, textvariable=self.var_qty,
              font=("Arial", 10), width=20).grid(row=4, column=1, padx=5, pady=3)

        self.lbl_inStock = Label(frame, text="In Stock: 0", bg="#f0f0f0",
                                  font=("Arial", 10))
        self.lbl_inStock.grid(row=4, column=2, padx=5)

        Button(frame, text="Add to Cart", command=self.add_update_cart,
               bg="#27ae60", fg="white", font=("Arial", 10)).grid(row=5, column=0,
                                                                    columnspan=3, pady=5)

    def bill_bottom(self, parent):
        frame = LabelFrame(parent, text="Bill Summary", bg="#f0f0f0",
                           font=("Arial", 11, "bold"))
        frame.pack(fill=X, pady=5)

        self.lbl_amnt = Label(frame, text="Total: $0.00", bg="#f0f0f0",
                               font=("Arial", 11, "bold"))
        self.lbl_amnt.pack(pady=3)

        self.lbl_discount = Label(frame, text="Discount: 0%", bg="#f0f0f0",
                                   font=("Arial", 11))
        self.lbl_discount.pack(pady=3)

        self.lbl_net_pay = Label(frame, text="Net Pay: $0.00", bg="#f0f0f0",
                                  font=("Arial", 12, "bold"), fg="#e74c3c")
        self.lbl_net_pay.pack(pady=3)

        btn_frame = Frame(frame, bg="#f0f0f0")
        btn_frame.pack(pady=5)

        Button(btn_frame, text="Generate Bill", command=self.generate_bill,
               bg="#27ae60", fg="white", font=("Arial", 10)).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear Cart", command=self.clear_cart,
               bg="#e74c3c", fg="white", font=("Arial", 10)).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear All", command=self.clear_all,
               bg="#95a5a6", fg="white", font=("Arial", 10)).pack(side=LEFT, padx=5)

        # Calculator
        cal_frame = LabelFrame(parent, text="Calculator", bg="#f0f0f0",
                                font=("Arial", 11, "bold"))
        cal_frame.pack(fill=X, pady=5)

        self.txt_cal_input = Entry(cal_frame, textvariable=self.var_cal_input,
                                    font=("Arial", 12), width=20, justify=RIGHT)
        self.txt_cal_input.pack(fill=X, padx=5, pady=3)

        cal_btn_frame = Frame(cal_frame, bg="#f0f0f0")
        cal_btn_frame.pack()

        buttons = [
            "7", "8", "9", "/",
            "4", "5", "6", "*",
            "1", "2", "3", "-",
            "0", ".", "=", "+"
        ]
        row, col = 0, 0
        for btn in buttons:
            Button(cal_btn_frame, text=btn, width=4, height=2,
                   font=("Arial", 10),
                   command=lambda b=btn: self.get_input(b)).grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col == 4:
                col = 0
                row += 1

        Button(cal_frame, text="Clear", command=self.clear_cal,
               bg="#e74c3c", fg="white", font=("Arial", 10), width=10).pack(pady=3)

        # Bill text area
        bill_frame = LabelFrame(parent, text="Bill Preview", bg="#f0f0f0",
                                 font=("Arial", 11, "bold"))
        bill_frame.pack(fill=BOTH, expand=True, pady=5)

        scroll = Scrollbar(bill_frame)
        self.txt_bill_area = Text(bill_frame, font=("Courier", 9),
                                   yscrollcommand=scroll.set, height=10)
        scroll.config(command=self.txt_bill_area.yview)
        scroll.pack(side=RIGHT, fill=Y)
        self.txt_bill_area.pack(fill=BOTH, expand=True)

        Button(parent, text="Print Bill", command=self.print_bill,
               bg="#2980b9", fg="white", font=("Arial", 11), width=15).pack(pady=5)

    def show(self, parent):
        frame = LabelFrame(parent, text="Products", bg="#f0f0f0",
                           font=("Arial", 11, "bold"))
        frame.pack(fill=BOTH, expand=True, pady=5)

        scroll_x = Scrollbar(frame, orient=HORIZONTAL)
        scroll_y = Scrollbar(frame, orient=VERTICAL)

        cols = ("pid", "name", "price", "qty", "status", "cat", "sup")
        self.product_Table = ttk.Treeview(
            frame,
            columns=cols,
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set,
            height=8
        )
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

        self._load_products()

    def _load_products(self, query=""):
        conn = get_connection()
        cur = conn.cursor()
        if query:
            cur.execute("SELECT * FROM product WHERE name LIKE ? OR pid LIKE ?",
                        (f"%{query}%", f"%{query}%"))
        else:
            cur.execute("SELECT * FROM product")
        rows = cur.fetchall()
        conn.close()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", END, values=row)

    def show_cart(self, parent):
        frame = LabelFrame(parent, text="Cart", bg="#f0f0f0",
                           font=("Arial", 11, "bold"))
        frame.pack(fill=BOTH, expand=True, pady=5)

        self.cartTitle = Label(frame, text="Cart Items: 0", bg="#f0f0f0",
                                font=("Arial", 10, "bold"))
        self.cartTitle.pack()

        scroll_x = Scrollbar(frame, orient=HORIZONTAL)
        scroll_y = Scrollbar(frame, orient=VERTICAL)

        cols = ("pid", "name", "price", "qty", "total")
        self.CartTable = ttk.Treeview(
            frame,
            columns=cols,
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set,
            height=6
        )
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.config(command=self.CartTable.xview)
        scroll_y.config(command=self.CartTable.yview)

        headers = ("PID", "Name", "Price", "Qty", "Total")
        for col, hdr in zip(cols, headers):
            self.CartTable.heading(col, text=hdr)
            self.CartTable.column(col, width=80)
        self.CartTable["show"] = "headings"
        self.CartTable.pack(fill=BOTH, expand=True)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

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

    def search(self):
        self._load_products(self.var_search.get())

    def add_update_cart(self):
        if self.var_pid.get() == "":
            messagebox.showerror("Error", "Select a product", parent=self.root)
            return
        if self.var_qty.get() == "" or not self.var_qty.get().isdigit():
            messagebox.showerror("Error", "Enter valid quantity", parent=self.root)
            return

        qty = int(self.var_qty.get())
        stock = int(self.var_stock.get()) if self.var_stock.get().isdigit() else 0

        if qty > stock:
            messagebox.showerror("Error", "Quantity exceeds stock", parent=self.root)
            return

        price = float(self.var_price.get()) if self.var_price.get() else 0.0
        total = price * qty

        # Check if already in cart
        for i, item in enumerate(self.cart_list):
            if item[0] == self.var_pid.get():
                self.cart_list[i] = (self.var_pid.get(), self.var_pname.get(),
                                      price, qty, total)
                self._refresh_cart()
                return

        self.cart_list.append((self.var_pid.get(), self.var_pname.get(), price, qty, total))
        self._refresh_cart()

    def _refresh_cart(self):
        self.CartTable.delete(*self.CartTable.get_children())
        self.bill_amnt = 0
        for item in self.cart_list:
            self.CartTable.insert("", END, values=item)
            self.bill_amnt += item[4]

        self.cartTitle.config(text=f"Cart Items: {len(self.cart_list)}")
        self.discount = 5.0 if self.bill_amnt > 1000 else 0.0
        self.net_pay = self.bill_amnt - (self.bill_amnt * self.discount / 100)
        self.lbl_amnt.config(text=f"Total: ${self.bill_amnt:.2f}")
        self.lbl_discount.config(text=f"Discount: {self.discount}%")
        self.lbl_net_pay.config(text=f"Net Pay: ${self.net_pay:.2f}")

    def bill_update(self):
        self._refresh_cart()

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty", parent=self.root)
            return
        if self.var_cname.get() == "":
            messagebox.showerror("Error", "Enter customer name", parent=self.root)
            return

        self.invoice = f"INV{random.randint(1000, 9999)}"
        now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

        bill_text = "=" * 45 + "\n"
        bill_text += "       INVENTORY MANAGEMENT SYSTEM\n"
        bill_text += "=" * 45 + "\n"
        bill_text += f"Invoice: {self.invoice}\n"
        bill_text += f"Date: {now}\n"
        bill_text += f"Customer: {self.var_cname.get()}\n"
        bill_text += f"Contact: {self.var_contact.get()}\n"
        bill_text += "-" * 45 + "\n"
        bill_text += f"{'Product':<20}{'Qty':>5}{'Price':>10}{'Total':>10}\n"
        bill_text += "-" * 45 + "\n"

        for item in self.cart_list:
            bill_text += f"{str(item[1]):<20}{str(item[3]):>5}{str(item[2]):>10}{str(item[4]):>10}\n"

        bill_text += "-" * 45 + "\n"
        bill_text += f"{'Total Amount:':<30}${self.bill_amnt:.2f}\n"
        bill_text += f"{'Discount:':<30}{self.discount}%\n"
        bill_text += f"{'Net Payable:':<30}${self.net_pay:.2f}\n"
        bill_text += "=" * 45 + "\n"
        bill_text += "     Thank you for your purchase!\n"
        bill_text += "=" * 45 + "\n"

        self.txt_bill_area.delete("1.0", END)
        self.txt_bill_area.insert(END, bill_text)

        # Save to DB
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO sales VALUES (?,?,?,?,?,?)",
                        (self.invoice, self.var_cname.get(), self.var_contact.get(),
                         bill_text, str(self.net_pay), now))
            # Update stock
            for item in self.cart_list:
                cur.execute("UPDATE product SET qty=qty-? WHERE pid=?",
                            (item[3], item[0]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Bill generated! Invoice: {self.invoice}",
                                parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Error saving bill: {e}", parent=self.root)

    def clear_cart(self):
        self.cart_list = []
        self.CartTable.delete(*self.CartTable.get_children())
        self.bill_amnt = 0
        self.net_pay = 0
        self.discount = 0.0
        self.lbl_amnt.config(text="Total: $0.00")
        self.lbl_discount.config(text="Discount: 0%")
        self.lbl_net_pay.config(text="Net Pay: $0.00")
        self.cartTitle.config(text="Cart Items: 0")

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

    def print_bill(self):
        bill_content = self.txt_bill_area.get("1.0", END)
        if bill_content.strip() == "":
            messagebox.showerror("Error", "No bill to print", parent=self.root)
            return
        messagebox.showinfo("Print", "Bill sent to printer (simulated)", parent=self.root)


# ─────────────────────────────────────────────
# dashboard / IMS module
# ─────────────────────────────────────────────
class IMS:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("1100x650")
        self.root.config(bg="#f0f0f0")

        self.new_obj = None
        self.new_win = None

        # Try to load images (graceful fallback)
        try:
            self.MenuLogo = PhotoImage(file="images/logo.png")
        except Exception:
            self.MenuLogo = None

        try:
            self.icon_side = PhotoImage(file="images/side_icon.png")
        except Exception:
            self.icon_side = None

        try:
            self.icon_title = PhotoImage(file="images/title_icon.png")
        except Exception:
            self.icon_title = None

        # Header
        header = Frame(self.root, bg="#2c3e50", pady=10)
        header.pack(fill=X)

        Label(header, text="Inventory Management System",
              font=("Arial", 22, "bold"), bg="#2c3e50", fg="white").pack(side=LEFT, padx=20)

        self.lbl_clock = Label(header, text="", font=("Arial", 12),
                                bg="#2c3e50", fg="white")
        self.lbl_clock.pack(side=RIGHT, padx=20)

        # Sidebar
        sidebar = Frame(self.root, bg="#34495e", width=200)
        sidebar.pack(side=LEFT, fill=Y)
        sidebar.pack_propagate(False)

        Label(sidebar, text="MENU", font=("Arial", 14, "bold"),
              bg="#34495e", fg="white", pady=15).pack(fill=X)

        menu_items = [
            ("Category", self.category),
            ("Employee", self.employee),
            ("Supplier", self.supplier),
            ("Product", self.product),
            ("Sales", self.sales),
            ("Billing", self.open_billing),
        ]

        for text, cmd in menu_items:
            btn = Button(sidebar, text=text, command=cmd,
                         font=("Arial", 12), bg="#34495e", fg="white",
                         activebackground="#2c3e50", activeforeground="white",
                         bd=0, pady=10, cursor="hand2")
            btn.pack(fill=X, padx=5, pady=2)

        # Main content area
        self.content_frame = Frame(self.root, bg="#ecf0f1")
        self.content_frame.pack(side=LEFT, fill=BOTH, expand=True)

        # Dashboard summary
        self._show_dashboard()
        self.update_content()

    def _show_dashboard(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        Label(self.content_frame, text="Dashboard",
              font=("Arial", 18, "bold"), bg="#ecf0f1").pack(pady=20)

        stats_frame = Frame(self.content_frame, bg="#ecf0f1")
        stats_frame.pack(pady=20)

        # Stat cards
        stats = self._get_stats()

        card_data = [
            ("Products", stats.get("products", 0), "#3498db"),
            ("Categories", stats.get("categories", 0), "#2ecc71"),
            ("Employees", stats.get("employees", 0), "#e74c3c"),
            ("Suppliers", stats.get("suppliers", 0), "#f39c12"),
            ("Sales", stats.get("sales", 0), "#9b59b6"),
        ]

        for i, (label, value, color) in enumerate(card_data):
            card = Frame(stats_frame, bg=color, width=150, height=100)
            card.grid(row=0, column=i, padx=10, pady=10)
            card.pack_propagate(False)
            Label(card, text=label, font=("Arial", 12, "bold"),
                  bg=color, fg="white").pack(pady=10)
            Label(card, text=str(value), font=("Arial", 20, "bold"),
                  bg=color, fg="white").pack()

        # Store label references
        self.lbl_product = Label(self.content_frame, text=f"Products: {stats.get('products', 0)}",
                                  font=("Arial", 11), bg="#ecf0f1")
        self.lbl_category = Label(self.content_frame, text=f"Categories: {stats.get('categories', 0)}",
                                   font=("Arial", 11), bg="#ecf0f1")
        self.lbl_employee = Label(self.content_frame, text=f"Employees: {stats.get('employees', 0)}",
                                   font=("Arial", 11), bg="#ecf0f1")
        self.lbl_supplier = Label(self.content_frame, text=f"Suppliers: {stats.get('suppliers', 0)}",
                                   font=("Arial", 11), bg="#ecf0f1")
        self.lbl_sales = Label(self.content_frame, text=f"Sales: {stats.get('sales', 0)}",
                                font=("Arial", 11), bg="#ecf0f1")

    def _get_stats(self):
        stats = {}
        try:
            conn = get_connection()
            cur = conn.cursor()
            for table, key in [("product", "products"), ("category", "categories"),
                                ("employee", "employees"), ("supplier", "suppliers"),
                                ("sales", "sales")]:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                stats[key] = cur.fetchone()[0]
            conn.close()
        except Exception:
            pass
        return stats

    def update_content(self):
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%d-%m-%Y  %H:%M:%S"))
        self.root.after(1000, self.update_content)

    def _open_module(self, cls):
        if self.new_win is not None:
            try:
                self.new_win.destroy()
            except Exception:
                pass

        self.new_win = Toplevel(self.root)
        self.new_win.geometry("900x600")
        self.new_win.title(cls.__name__)
        self.new_obj = cls(self.new_win)

    def category(self):
        self._open_module(categoryClass)

    def employee(self):
        self._open_module(employeeClass)

    def supplier(self):
        self._open_module(supplierClass)

    def product(self):
        self._open_module(productClass)

    def sales(self):
        self._open_module(salesClass)

    def open_billing(self):
        if self.new_win is not None:
            try:
                self.new_win.destroy()
            except Exception:
                pass
        self.new_win = Toplevel(self.root)
        self.new_win.geometry("1200x700")
        self.new_win.title("Billing")
        self.new_obj = billClass(self.new_win)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    initialize_db()
    root = Tk()
    app = IMS(root)
    root.mainloop()