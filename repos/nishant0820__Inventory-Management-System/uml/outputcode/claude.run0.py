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
        email TEXT,
        contact TEXT,
        dob TEXT,
        doj TEXT,
        salary TEXT,
        gender TEXT,
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
        bill_data TEXT,
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

        win = Toplevel(self.root)
        win.title("Category Management")
        win.geometry("800x500")
        win.grab_set()

        Label(win, text="Category Management", font=("Arial", 16, "bold")).pack(pady=10)

        form = Frame(win)
        form.pack(pady=5)

        Label(form, text="Category ID:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        Entry(form, textvariable=self.var_cat_id).grid(row=0, column=1, padx=5, pady=5)

        Label(form, text="Category Name:").grid(row=1, column=0, padx=5, pady=5, sticky=W)
        Entry(form, textvariable=self.var_name).grid(row=1, column=1, padx=5, pady=5)

        btn_frame = Frame(win)
        btn_frame.pack(pady=5)
        Button(btn_frame, text="Add", width=10, command=self.add).grid(row=0, column=0, padx=5)
        Button(btn_frame, text="Delete", width=10, command=self.delete).grid(row=0, column=1, padx=5)
        Button(btn_frame, text="Clear", width=10, command=self.clear).grid(row=0, column=2, padx=5)

        img_frame = Frame(win)
        img_frame.pack(pady=5)
        self.lbl_im1 = Label(img_frame, text="[Image 1]", width=15, height=5, relief=RIDGE)
        self.lbl_im1.grid(row=0, column=0, padx=10)
        self.lbl_im2 = Label(img_frame, text="[Image 2]", width=15, height=5, relief=RIDGE)
        self.lbl_im2.grid(row=0, column=1, padx=10)

        table_frame = Frame(win)
        table_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

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
            cur.execute("INSERT INTO category VALUES (?,?)",
                        (self.var_cat_id.get(), self.var_name.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category added successfully")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

    def delete(self):
        if self.var_cat_id.get() == "":
            messagebox.showerror("Error", "Select a category to delete")
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM category WHERE cat_id=?", (self.var_cat_id.get(),))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category deleted successfully")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

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

        win = Toplevel(self.root)
        win.title("Supplier Management")
        win.geometry("900x550")
        win.grab_set()

        Label(win, text="Supplier Management", font=("Arial", 16, "bold")).pack(pady=10)

        form = Frame(win)
        form.pack(pady=5)

        Label(form, text="Supplier Invoice:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        Entry(form, textvariable=self.var_sup_invoice).grid(row=0, column=1, padx=5, pady=5)

        Label(form, text="Name:").grid(row=0, column=2, padx=5, pady=5, sticky=W)
        Entry(form, textvariable=self.var_name).grid(row=0, column=3, padx=5, pady=5)

        Label(form, text="Contact:").grid(row=1, column=0, padx=5, pady=5, sticky=W)
        Entry(form, textvariable=self.var_contact).grid(row=1, column=1, padx=5, pady=5)

        Label(form, text="Description:").grid(row=1, column=2, padx=5, pady=5, sticky=W)
        self.txt_desc = Text(form, width=20, height=3)
        self.txt_desc.grid(row=1, column=3, padx=5, pady=5)

        btn_frame = Frame(win)
        btn_frame.pack(pady=5)
        Button(btn_frame, text="Add", width=10, command=self.add).grid(row=0, column=0, padx=5)
        Button(btn_frame, text="Update", width=10, command=self.update).grid(row=0, column=1, padx=5)
        Button(btn_frame, text="Delete", width=10, command=self.delete).grid(row=0, column=2, padx=5)
        Button(btn_frame, text="Clear", width=10, command=self.clear).grid(row=0, column=3, padx=5)

        search_frame = Frame(win)
        search_frame.pack(pady=5)
        Label(search_frame, text="Search By:").grid(row=0, column=0, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Invoice", "Name", "Contact"], width=12).grid(row=0, column=1, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt, width=20).grid(row=0, column=2, padx=5)
        Button(search_frame, text="Search", command=self.search).grid(row=0, column=3, padx=5)
        Button(search_frame, text="Show All", command=self.show).grid(row=0, column=4, padx=5)

        table_frame = Frame(win)
        table_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        scroll_x = Scrollbar(table_frame, orient=HORIZONTAL)
        scroll_y = Scrollbar(table_frame, orient=VERTICAL)
        self.SupplierTable = ttk.Treeview(
            table_frame,
            columns=("invoice", "name", "contact", "desc"),
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set
        )
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.config(command=self.SupplierTable.xview)
        scroll_y.config(command=self.SupplierTable.yview)

        for col, heading in zip(("invoice", "name", "contact", "desc"),
                                ("Invoice", "Name", "Contact", "Description")):
            self.SupplierTable.heading(col, text=heading)
        self.SupplierTable["show"] = "headings"
        self.SupplierTable.pack(fill=BOTH, expand=True)
        self.SupplierTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def add(self):
        if self.var_sup_invoice.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "Invoice and Name are required")
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO supplier VALUES (?,?,?,?)",
                        (self.var_sup_invoice.get(), self.var_name.get(),
                         self.var_contact.get(), self.txt_desc.get("1.0", END).strip()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier added successfully")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

    def update(self):
        if self.var_sup_invoice.get() == "":
            messagebox.showerror("Error", "Select a supplier to update")
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE supplier SET name=?, contact=?, desc=? WHERE sup_invoice=?",
                        (self.var_name.get(), self.var_contact.get(),
                         self.txt_desc.get("1.0", END).strip(), self.var_sup_invoice.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier updated successfully")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

    def delete(self):
        if self.var_sup_invoice.get() == "":
            messagebox.showerror("Error", "Select a supplier to delete")
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM supplier WHERE sup_invoice=?", (self.var_sup_invoice.get(),))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier deleted successfully")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

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
            messagebox.showerror("Error", "Select search criteria and enter search text")
            return
        col_map = {"Invoice": "sup_invoice", "Name": "name", "Contact": "contact"}
        col = col_map.get(self.var_searchby.get(), "name")
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM supplier WHERE {col} LIKE ?",
                        (f"%{self.var_searchtxt.get()}%",))
            rows = cur.fetchall()
            conn.close()
            self.SupplierTable.delete(*self.SupplierTable.get_children())
            for row in rows:
                self.SupplierTable.insert("", END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

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
        self.var_contact = StringVar()
        self.var_dob = StringVar()
        self.var_doj = StringVar()
        self.var_salary = StringVar()
        self.var_gender = StringVar()
        self.var_utype = StringVar()
        self.var_pass = StringVar()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()

        win = Toplevel(self.root)
        win.title("Employee Management")
        win.geometry("1000x600")
        win.grab_set()

        Label(win, text="Employee Management", font=("Arial", 16, "bold")).pack(pady=10)

        form = Frame(win)
        form.pack(pady=5)

        fields = [
            ("Employee ID", self.var_emp_id, 0, 0),
            ("Name", self.var_name, 0, 2),
            ("Email", self.var_email, 1, 0),
            ("Contact", self.var_contact, 1, 2),
            ("DOB", self.var_dob, 2, 0),
            ("DOJ", self.var_doj, 2, 2),
            ("Salary", self.var_salary, 3, 0),
            ("Password", self.var_pass, 3, 2),
        ]
        for label, var, r, c in fields:
            Label(form, text=f"{label}:").grid(row=r, column=c, padx=5, pady=3, sticky=W)
            Entry(form, textvariable=var).grid(row=r, column=c+1, padx=5, pady=3)

        Label(form, text="Gender:").grid(row=4, column=0, padx=5, pady=3, sticky=W)
        ttk.Combobox(form, textvariable=self.var_gender,
                     values=["Male", "Female", "Other"], width=17).grid(row=4, column=1, padx=5, pady=3)

        Label(form, text="User Type:").grid(row=4, column=2, padx=5, pady=3, sticky=W)
        ttk.Combobox(form, textvariable=self.var_utype,
                     values=["Admin", "Employee"], width=17).grid(row=4, column=3, padx=5, pady=3)

        Label(form, text="Address:").grid(row=5, column=0, padx=5, pady=3, sticky=W)
        self.txt_address = Text(form, width=40, height=3)
        self.txt_address.grid(row=5, column=1, columnspan=3, padx=5, pady=3)

        btn_frame = Frame(win)
        btn_frame.pack(pady=5)
        Button(btn_frame, text="Add", width=10, command=self.add).grid(row=0, column=0, padx=5)
        Button(btn_frame, text="Update", width=10, command=self.update).grid(row=0, column=1, padx=5)
        Button(btn_frame, text="Delete", width=10, command=self.delete).grid(row=0, column=2, padx=5)
        Button(btn_frame, text="Clear", width=10, command=self.clear).grid(row=0, column=3, padx=5)

        search_frame = Frame(win)
        search_frame.pack(pady=5)
        Label(search_frame, text="Search By:").grid(row=0, column=0, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Employee ID", "Name", "Contact", "Email"], width=12).grid(row=0, column=1, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt, width=20).grid(row=0, column=2, padx=5)
        Button(search_frame, text="Search", command=self.search).grid(row=0, column=3, padx=5)
        Button(search_frame, text="Show All", command=self.show).grid(row=0, column=4, padx=5)

        table_frame = Frame(win)
        table_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        cols = ("emp_id", "name", "email", "contact", "dob", "doj", "salary", "gender", "utype", "address")
        headings = ("ID", "Name", "Email", "Contact", "DOB", "DOJ", "Salary", "Gender", "Type", "Address")
        scroll_x = Scrollbar(table_frame, orient=HORIZONTAL)
        scroll_y = Scrollbar(table_frame, orient=VERTICAL)
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
        for col, heading in zip(cols, headings):
            self.EmployeeTable.heading(col, text=heading)
            self.EmployeeTable.column(col, width=90)
        self.EmployeeTable["show"] = "headings"
        self.EmployeeTable.pack(fill=BOTH, expand=True)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def add(self):
        if self.var_emp_id.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "Employee ID and Name are required")
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO employee VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (self.var_emp_id.get(), self.var_name.get(), self.var_email.get(),
                         self.var_contact.get(), self.var_dob.get(), self.var_doj.get(),
                         self.var_salary.get(), self.var_gender.get(), self.var_utype.get(),
                         self.txt_address.get("1.0", END).strip(), self.var_pass.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee added successfully")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

    def update(self):
        if self.var_emp_id.get() == "":
            messagebox.showerror("Error", "Select an employee to update")
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""UPDATE employee SET name=?, email=?, contact=?, dob=?, doj=?,
                           salary=?, gender=?, utype=?, address=?, password=? WHERE emp_id=?""",
                        (self.var_name.get(), self.var_email.get(), self.var_contact.get(),
                         self.var_dob.get(), self.var_doj.get(), self.var_salary.get(),
                         self.var_gender.get(), self.var_utype.get(),
                         self.txt_address.get("1.0", END).strip(), self.var_pass.get(),
                         self.var_emp_id.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee updated successfully")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

    def delete(self):
        if self.var_emp_id.get() == "":
            messagebox.showerror("Error", "Select an employee to delete")
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM employee WHERE emp_id=?", (self.var_emp_id.get(),))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee deleted successfully")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

    def clear(self):
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_email.set("")
        self.var_contact.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_salary.set("")
        self.var_gender.set("")
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
            self.var_contact.set(row[3])
            self.var_dob.set(row[4])
            self.var_doj.set(row[5])
            self.var_salary.set(row[6])
            self.var_gender.set(row[7])
            self.var_utype.set(row[8])
            self.txt_address.delete("1.0", END)
            self.txt_address.insert(END, row[9] if len(row) > 9 else "")

    def search(self):
        if self.var_searchby.get() == "" or self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Select search criteria and enter search text")
            return
        col_map = {"Employee ID": "emp_id", "Name": "name", "Contact": "contact", "Email": "email"}
        col = col_map.get(self.var_searchby.get(), "name")
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM employee WHERE {col} LIKE ?",
                        (f"%{self.var_searchtxt.get()}%",))
            rows = cur.fetchall()
            conn.close()
            self.EmployeeTable.delete(*self.EmployeeTable.get_children())
            for row in rows:
                self.EmployeeTable.insert("", END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT emp_id, name, email, contact, dob, doj, salary, gender, utype, address FROM employee")
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

        win = Toplevel(self.root)
        win.title("Product Management")
        win.geometry("1000x600")
        win.grab_set()

        Label(win, text="Product Management", font=("Arial", 16, "bold")).pack(pady=10)

        form = Frame(win)
        form.pack(pady=5)

        Label(form, text="Product ID:").grid(row=0, column=0, padx=5, pady=3, sticky=W)
        Entry(form, textvariable=self.var_pid).grid(row=0, column=1, padx=5, pady=3)

        Label(form, text="Name:").grid(row=0, column=2, padx=5, pady=3, sticky=W)
        Entry(form, textvariable=self.var_name).grid(row=0, column=3, padx=5, pady=3)

        Label(form, text="Price:").grid(row=1, column=0, padx=5, pady=3, sticky=W)
        Entry(form, textvariable=self.var_price).grid(row=1, column=1, padx=5, pady=3)

        Label(form, text="Quantity:").grid(row=1, column=2, padx=5, pady=3, sticky=W)
        Entry(form, textvariable=self.var_qty).grid(row=1, column=3, padx=5, pady=3)

        Label(form, text="Status:").grid(row=2, column=0, padx=5, pady=3, sticky=W)
        ttk.Combobox(form, textvariable=self.var_status,
                     values=["Active", "Inactive"], width=17).grid(row=2, column=1, padx=5, pady=3)

        Label(form, text="Category:").grid(row=2, column=2, padx=5, pady=3, sticky=W)
        self.cat_combo = ttk.Combobox(form, textvariable=self.var_cat, width=17)
        self.cat_combo.grid(row=2, column=3, padx=5, pady=3)

        Label(form, text="Supplier:").grid(row=3, column=0, padx=5, pady=3, sticky=W)
        self.sup_combo = ttk.Combobox(form, textvariable=self.var_sup, width=17)
        self.sup_combo.grid(row=3, column=1, padx=5, pady=3)

        btn_frame = Frame(win)
        btn_frame.pack(pady=5)
        Button(btn_frame, text="Add", width=10, command=self.add).grid(row=0, column=0, padx=5)
        Button(btn_frame, text="Update", width=10, command=self.update).grid(row=0, column=1, padx=5)
        Button(btn_frame, text="Delete", width=10, command=self.delete).grid(row=0, column=2, padx=5)
        Button(btn_frame, text="Clear", width=10, command=self.clear).grid(row=0, column=3, padx=5)

        search_frame = Frame(win)
        search_frame.pack(pady=5)
        Label(search_frame, text="Search By:").grid(row=0, column=0, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Product ID", "Name", "Status", "Category", "Supplier"],
                     width=12).grid(row=0, column=1, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt, width=20).grid(row=0, column=2, padx=5)
        Button(search_frame, text="Search", command=self.search).grid(row=0, column=3, padx=5)
        Button(search_frame, text="Show All", command=self.show).grid(row=0, column=4, padx=5)

        table_frame = Frame(win)
        table_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        cols = ("pid", "name", "price", "qty", "status", "cat", "sup")
        headings = ("Product ID", "Name", "Price", "Quantity", "Status", "Category", "Supplier")
        scroll_x = Scrollbar(table_frame, orient=HORIZONTAL)
        scroll_y = Scrollbar(table_frame, orient=VERTICAL)
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
        for col, heading in zip(cols, headings):
            self.ProductTable.heading(col, text=heading)
            self.ProductTable.column(col, width=110)
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
            messagebox.showerror("Error", "Product ID and Name are required")
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
            messagebox.showinfo("Success", "Product added successfully")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

    def update(self):
        if self.var_pid.get() == "":
            messagebox.showerror("Error", "Select a product to update")
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
            messagebox.showinfo("Success", "Product updated successfully")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

    def delete(self):
        if self.var_pid.get() == "":
            messagebox.showerror("Error", "Select a product to delete")
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM product WHERE pid=?", (self.var_pid.get(),))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product deleted successfully")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

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
            messagebox.showerror("Error", "Select search criteria and enter search text")
            return
        col_map = {"Product ID": "pid", "Name": "name", "Status": "status",
                   "Category": "cat", "Supplier": "sup"}
        col = col_map.get(self.var_searchby.get(), "name")
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM product WHERE {col} LIKE ?",
                        (f"%{self.var_searchtxt.get()}%",))
            rows = cur.fetchall()
            conn.close()
            self.ProductTable.delete(*self.ProductTable.get_children())
            for row in rows:
                self.ProductTable.insert("", END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}")

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

        win = Toplevel(self.root)
        win.title("Sales / Bills")
        win.geometry("900x550")
        win.grab_set()

        Label(win, text="Sales Records", font=("Arial", 16, "bold")).pack(pady=10)

        search_frame = Frame(win)
        search_frame.pack(pady=5)
        Label(search_frame, text="Invoice No:").grid(row=0, column=0, padx=5)
        Entry(search_frame, textvariable=self.var_invoice, width=20).grid(row=0, column=1, padx=5)
        Button(search_frame, text="Search", command=self.search).grid(row=0, column=2, padx=5)
        Button(search_frame, text="Show All", command=self.show).grid(row=0, column=3, padx=5)
        Button(search_frame, text="Clear", command=self.clear).grid(row=0, column=4, padx=5)

        main_frame = Frame(win)
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        list_frame = Frame(main_frame, width=200)
        list_frame.pack(side=LEFT, fill=Y)
        Label(list_frame, text="Invoice List").pack()
        scroll_y = Scrollbar(list_frame, orient=VERTICAL)
        self.Sales_List = Listbox(list_frame, yscrollcommand=scroll_y.set, width=25)
        scroll_y.config(command=self.Sales_List.yview)
        scroll_y.pack(side=RIGHT, fill=Y)
        self.Sales_List.pack(fill=BOTH, expand=True)
        self.Sales_List.bind("<ButtonRelease-1>", self.get_data)

        bill_frame = Frame(main_frame)
        bill_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=10)
        Label(bill_frame, text="Bill Details").pack()
        self.bill_area = Text(bill_frame, width=60, height=25)
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
            messagebox.showerror("Error", "Enter invoice number to search")
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
        cur.execute("SELECT bill_data FROM sales WHERE invoice=?", (invoice,))
        row = cur.fetchone()
        conn.close()
        self.bill_area.delete("1.0", END)
        if row:
            self.bill_area.insert(END, row[0])

    def clear(self):
        self.var_invoice.set("")
        self.bill_area.delete("1.0", END)
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

        self.var_pid = StringVar()
        self.var_pname = StringVar()
        self.var_price = StringVar()
        self.var_qty = StringVar()
        self.var_stock = StringVar()
        self.var_search = StringVar()
        self.var_cname = StringVar()
        self.var_contact = StringVar()
        self.var_cal_input = StringVar()

        win = Toplevel(self.root)
        win.title("Billing")
        win.geometry("1200x700")
        win.grab_set()

        # Top section
        top_frame = Frame(win, bg="#2c3e50", pady=5)
        top_frame.pack(fill=X)
        Label(top_frame, text="Billing System", font=("Arial", 18, "bold"),
              bg="#2c3e50", fg="white").pack(side=LEFT, padx=20)
        self.lbl_clock = Label(top_frame, text="", font=("Arial", 12),
                               bg="#2c3e50", fg="white")
        self.lbl_clock.pack(side=RIGHT, padx=20)
        self.icon_title = None

        # Customer info
        cust_frame = Frame(win, pady=5)
        cust_frame.pack(fill=X, padx=10)
        Label(cust_frame, text="Customer Name:").grid(row=0, column=0, padx=5)
        Entry(cust_frame, textvariable=self.var_cname, width=20).grid(row=0, column=1, padx=5)
        Label(cust_frame, text="Contact:").grid(row=0, column=2, padx=5)
        Entry(cust_frame, textvariable=self.var_contact, width=15).grid(row=0, column=3, padx=5)

        # Search
        Label(cust_frame, text="Search Product:").grid(row=0, column=4, padx=5)
        Entry(cust_frame, textvariable=self.var_search, width=20).grid(row=0, column=5, padx=5)
        Button(cust_frame, text="Search", command=self.search).grid(row=0, column=6, padx=5)

        # Main area
        main_frame = Frame(win)
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        # Product table
        left_frame = Frame(main_frame)
        left_frame.pack(side=LEFT, fill=BOTH, expand=True)

        Label(left_frame, text="Products", font=("Arial", 12, "bold")).pack()
        prod_cols = ("pid", "name", "price", "qty", "status", "cat", "sup")
        prod_headings = ("ID", "Name", "Price", "Qty", "Status", "Category", "Supplier")
        scroll_y1 = Scrollbar(left_frame, orient=VERTICAL)
        scroll_x1 = Scrollbar(left_frame, orient=HORIZONTAL)
        self.product_Table = ttk.Treeview(
            left_frame,
            columns=prod_cols,
            yscrollcommand=scroll_y1.set,
            xscrollcommand=scroll_x1.set,
            height=10
        )
        scroll_y1.pack(side=RIGHT, fill=Y)
        scroll_x1.pack(side=BOTTOM, fill=X)
        scroll_y1.config(command=self.product_Table.yview)
        scroll_x1.config(command=self.product_Table.xview)
        for col, heading in zip(prod_cols, prod_headings):
            self.product_Table.heading(col, text=heading)
            self.product_Table.column(col, width=80)
        self.product_Table["show"] = "headings"
        self.product_Table.pack(fill=BOTH, expand=True)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)

        # Product input
        prod_input = Frame(left_frame)
        prod_input.pack(pady=5)
        Label(prod_input, text="PID:").grid(row=0, column=0, padx=3)
        Entry(prod_input, textvariable=self.var_pid, width=8).grid(row=0, column=1, padx=3)
        Label(prod_input, text="Name:").grid(row=0, column=2, padx=3)
        Entry(prod_input, textvariable=self.var_pname, width=12).grid(row=0, column=3, padx=3)
        Label(prod_input, text="Price:").grid(row=0, column=4, padx=3)
        Entry(prod_input, textvariable=self.var_price, width=8).grid(row=0, column=5, padx=3)
        Label(prod_input, text="Qty:").grid(row=0, column=6, padx=3)
        Entry(prod_input, textvariable=self.var_qty, width=6).grid(row=0, column=7, padx=3)

        self.lbl_inStock = Label(prod_input, text="In Stock: 0", fg="blue")
        self.lbl_inStock.grid(row=0, column=8, padx=5)

        Button(prod_input, text="Add to Cart", command=self.add_update_cart,
               bg="#27ae60", fg="white").grid(row=0, column=9, padx=5)

        # Cart table
        right_frame = Frame(main_frame, width=400)
        right_frame.pack(side=LEFT, fill=BOTH, padx=10)

        self.cartTitle = Label(right_frame, text="Cart", font=("Arial", 12, "bold"))
        self.cartTitle.pack()

        cart_cols = ("pid", "name", "price", "qty", "total")
        cart_headings = ("PID", "Name", "Price", "Qty", "Total")
        scroll_y2 = Scrollbar(right_frame, orient=VERTICAL)
        self.CartTable = ttk.Treeview(
            right_frame,
            columns=cart_cols,
            yscrollcommand=scroll_y2.set,
            height=10
        )
        scroll_y2.pack(side=RIGHT, fill=Y)
        scroll_y2.config(command=self.CartTable.yview)
        for col, heading in zip(cart_cols, cart_headings):
            self.CartTable.heading(col, text=heading)
            self.CartTable.column(col, width=70)
        self.CartTable["show"] = "headings"
        self.CartTable.pack(fill=BOTH, expand=True)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        # Bill area
        bill_frame = Frame(win)
        bill_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        self.bill_top()
        self.bill_middle()
        self.bill_bottom()

        # Amount labels
        amt_frame = Frame(win)
        amt_frame.pack(fill=X, padx=10, pady=5)
        self.lbl_amnt = Label(amt_frame, text="Bill Amount: 0", font=("Arial", 11))
        self.lbl_amnt.grid(row=0, column=0, padx=10)
        self.lbl_discount = Label(amt_frame, text="Discount: 0%", font=("Arial", 11))
        self.lbl_discount.grid(row=0, column=1, padx=10)
        self.lbl_net_pay = Label(amt_frame, text="Net Pay: 0", font=("Arial", 11, "bold"))
        self.lbl_net_pay.grid(row=0, column=2, padx=10)

        # Buttons
        btn_frame = Frame(win)
        btn_frame.pack(pady=5)
        Button(btn_frame, text="Generate Bill", command=self.generate_bill,
               bg="#2980b9", fg="white", width=14).grid(row=0, column=0, padx=5)
        Button(btn_frame, text="Clear Cart", command=self.clear_cart,
               width=12).grid(row=0, column=1, padx=5)
        Button(btn_frame, text="Clear All", command=self.clear_all,
               width=12).grid(row=0, column=2, padx=5)
        Button(btn_frame, text="Print Bill", command=self.print_bill,
               bg="#8e44ad", fg="white", width=12).grid(row=0, column=3, padx=5)

        # Calculator
        cal_frame = Frame(win, relief=RIDGE, bd=2)
        cal_frame.pack(pady=5)
        Label(cal_frame, text="Calculator", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=4)
        self.txt_cal_input = Entry(cal_frame, textvariable=self.var_cal_input, width=20, justify=RIGHT)
        self.txt_cal_input.grid(row=1, column=0, columnspan=4, padx=5, pady=3)

        cal_buttons = [
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2), ('/', 2, 3),
            ('4', 3, 0), ('5', 3, 1), ('6', 3, 2), ('*', 3, 3),
            ('1', 4, 0), ('2', 4, 1), ('3', 4, 2), ('-', 4, 3),
            ('0', 5, 0), ('.', 5, 1), ('=', 5, 2), ('+', 5, 3),
        ]
        for (text, r, c) in cal_buttons:
            Button(cal_frame, text=text, width=4,
                   command=lambda t=text: self.get_input(t)).grid(row=r, column=c, padx=2, pady=2)
        Button(cal_frame, text="C", width=4, command=self.clear_cal).grid(row=6, column=0, columnspan=4, pady=2)

        self.update_date_time()
        self.show()

    def bill_top(self):
        pass

    def bill_middle(self):
        pass

    def bill_bottom(self):
        pass

    def bill_update(self):
        self.lbl_amnt.config(text=f"Bill Amount: {self.bill_amnt}")
        self.lbl_discount.config(text=f"Discount: {self.discount}%")
        self.lbl_net_pay.config(text=f"Net Pay: {self.net_pay}")

    def update_date_time(self):
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))
        self.lbl_clock.after(1000, self.update_date_time)

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
        cur.execute("SELECT * FROM product WHERE name LIKE ? OR pid LIKE ?",
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
            self.lbl_inStock.config(text=f"In Stock: {row[3]}")
            self.var_stock.set(str(row[3]))

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
            messagebox.showerror("Error", "Product and quantity are required")
            return
        try:
            qty = int(self.var_qty.get())
            price = float(self.var_price.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity or price")
            return

        stock = int(self.var_stock.get()) if self.var_stock.get() else 0
        if qty > stock:
            messagebox.showerror("Error", f"Only {stock} items in stock")
            return

        total = qty * price
        # Check if already in cart
        for i, item in enumerate(self.cart_list):
            if item[0] == self.var_pid.get():
                self.cart_list[i] = (self.var_pid.get(), self.var_pname.get(),
                                     price, qty, total)
                self.show_cart()
                return

        self.cart_list.append((self.var_pid.get(), self.var_pname.get(), price, qty, total))
        self.show_cart()

    def show_cart(self):
        self.CartTable.delete(*self.CartTable.get_children())
        self.bill_amnt = 0
        for item in self.cart_list:
            self.CartTable.insert("", END, values=item)
            self.bill_amnt += item[4]
        self.discount = 5.0 if self.bill_amnt > 1000 else 0.0
        self.net_pay = self.bill_amnt - (self.bill_amnt * self.discount / 100)
        self.bill_update()

    def clear_cart(self):
        self.cart_list = []
        self.CartTable.delete(*self.CartTable.get_children())
        self.bill_amnt = 0
        self.net_pay = 0
        self.discount = 0.0
        self.bill_update()

    def clear_all(self):
        self.clear_cart()
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")
        self.var_cname.set("")
        self.var_contact.set("")
        self.var_search.set("")
        self.lbl_inStock.config(text="In Stock: 0")

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty")
            return
        self.invoice = f"INV{random.randint(10000, 99999)}"
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        bill_text = "=" * 50 + "\n"
        bill_text += "       INVENTORY MANAGEMENT SYSTEM\n"
        bill_text += "=" * 50 + "\n"
        bill_text += f"Invoice No : {self.invoice}\n"
        bill_text += f"Date/Time  : {now}\n"
        bill_text += f"Customer   : {self.var_cname.get()}\n"
        bill_text += f"Contact    : {self.var_contact.get()}\n"
        bill_text += "-" * 50 + "\n"
        bill_text += f"{'Product':<20}{'Qty':>5}{'Price':>10}{'Total':>12}\n"
        bill_text += "-" * 50 + "\n"
        for item in self.cart_list:
            bill_text += f"{item[1]:<20}{item[3]:>5}{item[2]:>10.2f}{item[4]:>12.2f}\n"
        bill_text += "-" * 50 + "\n"
        bill_text += f"{'Bill Amount':>35} : {self.bill_amnt:.2f}\n"
        bill_text += f"{'Discount':>35} : {self.discount:.1f}%\n"
        bill_text += f"{'Net Pay':>35} : {self.net_pay:.2f}\n"
        bill_text += "=" * 50 + "\n"
        bill_text += "       Thank you for shopping!\n"
        bill_text += "=" * 50 + "\n"

        # Save to DB
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO sales VALUES (?,?,?)",
                        (self.invoice, bill_text, now))
            # Update stock
            for item in self.cart_list:
                cur.execute("UPDATE product SET qty=qty-? WHERE pid=?",
                            (item[3], item[0]))
            conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Error saving bill: {e}")
            return

        messagebox.showinfo("Bill Generated", f"Invoice {self.invoice} generated successfully!")
        self.clear_all()

    def print_bill(self):
        messagebox.showinfo("Print", "Bill sent to printer (simulated)")

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
        self.root.geometry("1100x650")
        self.root.config(bg="#ecf0f1")

        self.new_obj = None
        self.new_win = None
        self.MenuLogo = None
        self.icon_side = None
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

        Label(sidebar, text="Navigation", font=("Arial", 13, "bold"),
              bg="#34495e", fg="white", pady=10).pack(fill=X)

        nav_buttons = [
            ("Category", self.category),
            ("Employee", self.employee),
            ("Supplier", self.supplier),
            ("Product", self.product),
            ("Sales", self.sales),
            ("Billing", self.billing),
        ]
        for text, cmd in nav_buttons:
            Button(sidebar, text=text, font=("Arial", 11), bg="#2c3e50", fg="white",
                   activebackground="#1abc9c", activeforeground="white",
                   relief=FLAT, pady=8, command=cmd).pack(fill=X, padx=5, pady=3)

        # Main content
        content = Frame(self.root, bg="#ecf0f1")
        content.pack(side=LEFT, fill=BOTH, expand=True, padx=20, pady=20)

        Label(content, text="Dashboard", font=("Arial", 18, "bold"),
              bg="#ecf0f1").pack(anchor=W)

        # Stats cards
        cards_frame = Frame(content, bg="#ecf0f1")
        cards_frame.pack(fill=X, pady=20)

        card_data = [
            ("lbl_category", "Categories", "#3498db"),
            ("lbl_employee", "Employees", "#2ecc71"),
            ("lbl_supplier", "Suppliers", "#e74c3c"),
            ("lbl_product", "Products", "#f39c12"),
            ("lbl_sales", "Sales", "#9b59b6"),
        ]
        for attr, title, color in card_data:
            card = Frame(cards_frame, bg=color, width=150, height=100, relief=RIDGE, bd=2)
            card.pack(side=LEFT, padx=10)
            card.pack_propagate(False)
            Label(card, text=title, font=("Arial", 11, "bold"),
                  bg=color, fg="white").pack(pady=5)
            lbl = Label(card, text="0", font=("Arial", 20, "bold"),
                        bg=color, fg="white")
            lbl.pack()
            setattr(self, attr, lbl)

        self.update_content()

    def update_content(self):
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM category")
            self.lbl_category.config(text=str(cur.fetchone()[0]))
            cur.execute("SELECT COUNT(*) FROM employee")
            self.lbl_employee.config(text=str(cur.fetchone()[0]))
            cur.execute("SELECT COUNT(*) FROM supplier")
            self.lbl_supplier.config(text=str(cur.fetchone()[0]))
            cur.execute("SELECT COUNT(*) FROM product")
            self.lbl_product.config(text=str(cur.fetchone()[0]))
            cur.execute("SELECT COUNT(*) FROM sales")
            self.lbl_sales.config(text=str(cur.fetchone()[0]))
            conn.close()
        except Exception:
            pass

        self.root.after(1000, self.update_content)

    def category(self):
        self.new_obj = categoryClass(self.root)

    def employee(self):
        self.new_obj = employeeClass(self.root)

    def supplier(self):
        self.new_obj = supplierClass(self.root)

    def product(self):
        self.new_obj = productClass(self.root)

    def sales(self):
        self.new_obj = salesClass(self.root)

    def billing(self):
        self.new_obj = billClass(self.root)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    root = Tk()
    app = IMS(root)
    root.mainloop()