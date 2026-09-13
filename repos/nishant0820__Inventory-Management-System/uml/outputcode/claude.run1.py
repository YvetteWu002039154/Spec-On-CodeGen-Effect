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
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS category (
        cat_id TEXT PRIMARY KEY,
        name   TEXT NOT NULL
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS supplier (
        sup_invoice TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        contact     TEXT,
        desc        TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS employee (
        emp_id  TEXT PRIMARY KEY,
        name    TEXT NOT NULL,
        email   TEXT,
        gender  TEXT,
        contact TEXT,
        dob     TEXT,
        doj     TEXT,
        utype   TEXT,
        salary  TEXT,
        address TEXT,
        password TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS product (
        pid    TEXT PRIMARY KEY,
        name   TEXT NOT NULL,
        price  TEXT,
        qty    TEXT,
        status TEXT,
        cat    TEXT,
        sup    TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS sales (
        invoice TEXT PRIMARY KEY,
        bill    TEXT
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

        win = tk.Toplevel(self.root)
        win.title("Category Management")
        win.geometry("900x500")
        win.grab_set()

        tk.Label(win, text="Category Management", font=("Arial", 16, "bold"),
                 bg="#2c3e50", fg="white").pack(fill=tk.X)

        form = tk.Frame(win, bg="#ecf0f1", pady=10)
        form.pack(fill=tk.X, padx=10)

        tk.Label(form, text="Category ID:", bg="#ecf0f1").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        tk.Entry(form, textvariable=self.var_cat_id, width=20).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(form, text="Category Name:", bg="#ecf0f1").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        tk.Entry(form, textvariable=self.var_name, width=20).grid(row=0, column=3, padx=5, pady=5)

        btn_frame = tk.Frame(win, bg="#ecf0f1")
        btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="Add", width=10, bg="#27ae60", fg="white",
                  command=self.add).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", width=10, bg="#e74c3c", fg="white",
                  command=self.delete).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", width=10, bg="#95a5a6", fg="white",
                  command=self.clear).pack(side=tk.LEFT, padx=5)

        img_frame = tk.Frame(win, bg="#ecf0f1")
        img_frame.pack(fill=tk.X, padx=10, pady=5)
        self.lbl_im1 = tk.Label(img_frame, text="[Image 1]", bg="#bdc3c7", width=15, height=5)
        self.lbl_im1.pack(side=tk.LEFT, padx=5)
        self.lbl_im2 = tk.Label(img_frame, text="[Image 2]", bg="#bdc3c7", width=15, height=5)
        self.lbl_im2.pack(side=tk.LEFT, padx=5)

        table_frame = tk.Frame(win)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scroll_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)

        self.CategoryTable = ttk.Treeview(
            table_frame,
            columns=("cat_id", "name"),
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.config(command=self.CategoryTable.yview)
        scroll_x.config(command=self.CategoryTable.xview)

        self.CategoryTable.heading("cat_id", text="Category ID")
        self.CategoryTable.heading("name", text="Name")
        self.CategoryTable["show"] = "headings"
        self.CategoryTable.pack(fill=tk.BOTH, expand=True)
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
            messagebox.showerror("Error", str(e))

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
            messagebox.showerror("Error", str(e))

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

        win = tk.Toplevel(self.root)
        win.title("Supplier Management")
        win.geometry("1000x600")
        win.grab_set()

        tk.Label(win, text="Supplier Management", font=("Arial", 16, "bold"),
                 bg="#2c3e50", fg="white").pack(fill=tk.X)

        form = tk.Frame(win, bg="#ecf0f1", pady=10)
        form.pack(fill=tk.X, padx=10)

        tk.Label(form, text="Invoice No:", bg="#ecf0f1").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        tk.Entry(form, textvariable=self.var_sup_invoice, width=20).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(form, text="Name:", bg="#ecf0f1").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        tk.Entry(form, textvariable=self.var_name, width=20).grid(row=0, column=3, padx=5, pady=5)

        tk.Label(form, text="Contact:", bg="#ecf0f1").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        tk.Entry(form, textvariable=self.var_contact, width=20).grid(row=1, column=1, padx=5, pady=5)

        tk.Label(form, text="Description:", bg="#ecf0f1").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.txt_desc = tk.Text(form, width=30, height=4)
        self.txt_desc.grid(row=1, column=3, padx=5, pady=5)

        btn_frame = tk.Frame(win, bg="#ecf0f1")
        btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="Add", width=10, bg="#27ae60", fg="white",
                  command=self.add).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", width=10, bg="#2980b9", fg="white",
                  command=self.update).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", width=10, bg="#e74c3c", fg="white",
                  command=self.delete).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", width=10, bg="#95a5a6", fg="white",
                  command=self.clear).pack(side=tk.LEFT, padx=5)

        search_frame = tk.Frame(win, bg="#ecf0f1")
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="Search By:", bg="#ecf0f1").pack(side=tk.LEFT)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Invoice No", "Name", "Contact"], width=15).pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, width=20).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", bg="#8e44ad", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All", bg="#16a085", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=5)

        table_frame = tk.Frame(win)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scroll_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)

        self.SupplierTable = ttk.Treeview(
            table_frame,
            columns=("invoice", "name", "contact", "desc"),
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.config(command=self.SupplierTable.yview)
        scroll_x.config(command=self.SupplierTable.xview)

        self.SupplierTable.heading("invoice", text="Invoice No")
        self.SupplierTable.heading("name", text="Name")
        self.SupplierTable.heading("contact", text="Contact")
        self.SupplierTable.heading("desc", text="Description")
        self.SupplierTable["show"] = "headings"
        self.SupplierTable.pack(fill=tk.BOTH, expand=True)
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
                         self.var_contact.get(), self.txt_desc.get("1.0", tk.END).strip()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier added successfully")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update(self):
        if self.var_sup_invoice.get() == "":
            messagebox.showerror("Error", "Select a supplier to update")
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("UPDATE supplier SET name=?, contact=?, desc=? WHERE sup_invoice=?",
                        (self.var_name.get(), self.var_contact.get(),
                         self.txt_desc.get("1.0", tk.END).strip(), self.var_sup_invoice.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier updated successfully")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))

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
            messagebox.showerror("Error", str(e))

    def clear(self):
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete("1.0", tk.END)

    def get_data(self, ev):
        selected = self.SupplierTable.focus()
        content = self.SupplierTable.item(selected)
        row = content["values"]
        if row:
            self.var_sup_invoice.set(row[0])
            self.var_name.set(row[1])
            self.var_contact.set(row[2])
            self.txt_desc.delete("1.0", tk.END)
            self.txt_desc.insert(tk.END, row[3] if row[3] else "")

    def search(self):
        if self.var_searchby.get() == "" or self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Select search criteria and enter search text")
            return
        col_map = {"Invoice No": "sup_invoice", "Name": "name", "Contact": "contact"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM supplier WHERE {col} LIKE ?",
                    (f"%{self.var_searchtxt.get()}%",))
        rows = cur.fetchall()
        conn.close()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert("", tk.END, values=row)

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM supplier")
        rows = cur.fetchall()
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
        self.var_email = tk.StringVar()
        self.var_gender = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_dob = tk.StringVar()
        self.var_doj = tk.StringVar()
        self.var_utype = tk.StringVar()
        self.var_salary = tk.StringVar()
        self.var_pass = tk.StringVar()
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()

        win = tk.Toplevel(self.root)
        win.title("Employee Management")
        win.geometry("1100x650")
        win.grab_set()

        tk.Label(win, text="Employee Management", font=("Arial", 16, "bold"),
                 bg="#2c3e50", fg="white").pack(fill=tk.X)

        form = tk.Frame(win, bg="#ecf0f1", pady=10)
        form.pack(fill=tk.X, padx=10)

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
            tk.Label(form, text=f"{label}:", bg="#ecf0f1").grid(row=r, column=c, padx=5, pady=3, sticky="e")
            tk.Entry(form, textvariable=var, width=20).grid(row=r, column=c + 1, padx=5, pady=3)

        tk.Label(form, text="Gender:", bg="#ecf0f1").grid(row=4, column=0, padx=5, pady=3, sticky="e")
        ttk.Combobox(form, textvariable=self.var_gender,
                     values=["Male", "Female", "Other"], width=18).grid(row=4, column=1, padx=5, pady=3)

        tk.Label(form, text="User Type:", bg="#ecf0f1").grid(row=4, column=2, padx=5, pady=3, sticky="e")
        ttk.Combobox(form, textvariable=self.var_utype,
                     values=["Admin", "Employee"], width=18).grid(row=4, column=3, padx=5, pady=3)

        tk.Label(form, text="Address:", bg="#ecf0f1").grid(row=5, column=0, padx=5, pady=3, sticky="e")
        self.txt_address = tk.Text(form, width=50, height=3)
        self.txt_address.grid(row=5, column=1, columnspan=3, padx=5, pady=3)

        btn_frame = tk.Frame(win, bg="#ecf0f1")
        btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="Add", width=10, bg="#27ae60", fg="white",
                  command=self.add).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", width=10, bg="#2980b9", fg="white",
                  command=self.update).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", width=10, bg="#e74c3c", fg="white",
                  command=self.delete).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", width=10, bg="#95a5a6", fg="white",
                  command=self.clear).pack(side=tk.LEFT, padx=5)

        search_frame = tk.Frame(win, bg="#ecf0f1")
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="Search By:", bg="#ecf0f1").pack(side=tk.LEFT)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Employee ID", "Name", "Email", "Contact"], width=15).pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, width=20).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", bg="#8e44ad", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All", bg="#16a085", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=5)

        table_frame = tk.Frame(win)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = ("emp_id", "name", "email", "gender", "contact", "dob", "doj", "utype", "salary", "address")
        scroll_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)

        self.EmployeeTable = ttk.Treeview(
            table_frame, columns=cols,
            yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set
        )
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.config(command=self.EmployeeTable.yview)
        scroll_x.config(command=self.EmployeeTable.xview)

        headings = ["Emp ID", "Name", "Email", "Gender", "Contact", "DOB", "DOJ", "User Type", "Salary", "Address"]
        for col, heading in zip(cols, headings):
            self.EmployeeTable.heading(col, text=heading)
            self.EmployeeTable.column(col, width=100)
        self.EmployeeTable["show"] = "headings"
        self.EmployeeTable.pack(fill=tk.BOTH, expand=True)
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
                         self.var_gender.get(), self.var_contact.get(), self.var_dob.get(),
                         self.var_doj.get(), self.var_utype.get(), self.var_salary.get(),
                         self.txt_address.get("1.0", tk.END).strip(), self.var_pass.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee added successfully")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update(self):
        if self.var_emp_id.get() == "":
            messagebox.showerror("Error", "Select an employee to update")
            return
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""UPDATE employee SET name=?, email=?, gender=?, contact=?,
                           dob=?, doj=?, utype=?, salary=?, address=?, password=?
                           WHERE emp_id=?""",
                        (self.var_name.get(), self.var_email.get(), self.var_gender.get(),
                         self.var_contact.get(), self.var_dob.get(), self.var_doj.get(),
                         self.var_utype.get(), self.var_salary.get(),
                         self.txt_address.get("1.0", tk.END).strip(),
                         self.var_pass.get(), self.var_emp_id.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee updated successfully")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))

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
            messagebox.showerror("Error", str(e))

    def clear(self):
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_email.set("")
        self.var_gender.set("")
        self.var_contact.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_utype.set("")
        self.var_salary.set("")
        self.var_pass.set("")
        self.txt_address.delete("1.0", tk.END)

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
            self.var_utype.set(row[7])
            self.var_salary.set(row[8])
            self.txt_address.delete("1.0", tk.END)
            self.txt_address.insert(tk.END, row[9] if row[9] else "")

    def search(self):
        if self.var_searchby.get() == "" or self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Select search criteria and enter search text")
            return
        col_map = {"Employee ID": "emp_id", "Name": "name", "Email": "email", "Contact": "contact"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT emp_id,name,email,gender,contact,dob,doj,utype,salary,address FROM employee WHERE {col} LIKE ?",
                    (f"%{self.var_searchtxt.get()}%",))
        rows = cur.fetchall()
        conn.close()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for row in rows:
            self.EmployeeTable.insert("", tk.END, values=row)

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT emp_id,name,email,gender,contact,dob,doj,utype,salary,address FROM employee")
        rows = cur.fetchall()
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

        win = tk.Toplevel(self.root)
        win.title("Product Management")
        win.geometry("1100x650")
        win.grab_set()

        tk.Label(win, text="Product Management", font=("Arial", 16, "bold"),
                 bg="#2c3e50", fg="white").pack(fill=tk.X)

        form = tk.Frame(win, bg="#ecf0f1", pady=10)
        form.pack(fill=tk.X, padx=10)

        tk.Label(form, text="Product ID:", bg="#ecf0f1").grid(row=0, column=0, padx=5, pady=3, sticky="e")
        tk.Entry(form, textvariable=self.var_pid, width=20).grid(row=0, column=1, padx=5, pady=3)

        tk.Label(form, text="Name:", bg="#ecf0f1").grid(row=0, column=2, padx=5, pady=3, sticky="e")
        tk.Entry(form, textvariable=self.var_name, width=20).grid(row=0, column=3, padx=5, pady=3)

        tk.Label(form, text="Price:", bg="#ecf0f1").grid(row=1, column=0, padx=5, pady=3, sticky="e")
        tk.Entry(form, textvariable=self.var_price, width=20).grid(row=1, column=1, padx=5, pady=3)

        tk.Label(form, text="Quantity:", bg="#ecf0f1").grid(row=1, column=2, padx=5, pady=3, sticky="e")
        tk.Entry(form, textvariable=self.var_qty, width=20).grid(row=1, column=3, padx=5, pady=3)

        tk.Label(form, text="Status:", bg="#ecf0f1").grid(row=2, column=0, padx=5, pady=3, sticky="e")
        ttk.Combobox(form, textvariable=self.var_status,
                     values=["Active", "Inactive"], width=18).grid(row=2, column=1, padx=5, pady=3)

        tk.Label(form, text="Category:", bg="#ecf0f1").grid(row=2, column=2, padx=5, pady=3, sticky="e")
        self.cat_combo = ttk.Combobox(form, textvariable=self.var_cat, width=18)
        self.cat_combo.grid(row=2, column=3, padx=5, pady=3)

        tk.Label(form, text="Supplier:", bg="#ecf0f1").grid(row=3, column=0, padx=5, pady=3, sticky="e")
        self.sup_combo = ttk.Combobox(form, textvariable=self.var_sup, width=18)
        self.sup_combo.grid(row=3, column=1, padx=5, pady=3)

        btn_frame = tk.Frame(win, bg="#ecf0f1")
        btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="Add", width=10, bg="#27ae60", fg="white",
                  command=self.add).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", width=10, bg="#2980b9", fg="white",
                  command=self.update).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", width=10, bg="#e74c3c", fg="white",
                  command=self.delete).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", width=10, bg="#95a5a6", fg="white",
                  command=self.clear).pack(side=tk.LEFT, padx=5)

        search_frame = tk.Frame(win, bg="#ecf0f1")
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="Search By:", bg="#ecf0f1").pack(side=tk.LEFT)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Product ID", "Name", "Status", "Category"], width=15).pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, width=20).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", bg="#8e44ad", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All", bg="#16a085", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=5)

        table_frame = tk.Frame(win)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = ("pid", "name", "price", "qty", "status", "cat", "sup")
        scroll_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)

        self.ProductTable = ttk.Treeview(
            table_frame, columns=cols,
            yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set
        )
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.config(command=self.ProductTable.yview)
        scroll_x.config(command=self.ProductTable.xview)

        headings = ["Product ID", "Name", "Price", "Quantity", "Status", "Category", "Supplier"]
        for col, heading in zip(cols, headings):
            self.ProductTable.heading(col, text=heading)
            self.ProductTable.column(col, width=120)
        self.ProductTable["show"] = "headings"
        self.ProductTable.pack(fill=tk.BOTH, expand=True)
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
            messagebox.showerror("Error", str(e))

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
            messagebox.showerror("Error", str(e))

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
            messagebox.showerror("Error", str(e))

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
            self.ProductTable.insert("", tk.END, values=row)

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM product")
        rows = cur.fetchall()
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

        win = tk.Toplevel(self.root)
        win.title("Sales Records")
        win.geometry("1000x600")
        win.grab_set()

        tk.Label(win, text="Sales Records", font=("Arial", 16, "bold"),
                 bg="#2c3e50", fg="white").pack(fill=tk.X)

        search_frame = tk.Frame(win, bg="#ecf0f1")
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="Invoice No:", bg="#ecf0f1").pack(side=tk.LEFT)
        tk.Entry(search_frame, textvariable=self.var_invoice, width=20).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", bg="#8e44ad", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All", bg="#16a085", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Clear", bg="#95a5a6", fg="white",
                  command=self.clear).pack(side=tk.LEFT, padx=5)

        main_frame = tk.Frame(win)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        list_frame = tk.Frame(main_frame, width=250)
        list_frame.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(list_frame, text="Invoice List", font=("Arial", 12, "bold")).pack()

        scroll_y = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.Sales_List = tk.Listbox(list_frame, yscrollcommand=scroll_y.set, width=30)
        scroll_y.config(command=self.Sales_List.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.Sales_List.pack(fill=tk.BOTH, expand=True)
        self.Sales_List.bind("<ButtonRelease-1>", self.get_data)

        bill_frame = tk.Frame(main_frame)
        bill_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        tk.Label(bill_frame, text="Bill Details", font=("Arial", 12, "bold")).pack()

        scroll_y2 = tk.Scrollbar(bill_frame, orient=tk.VERTICAL)
        self.bill_area = tk.Text(bill_frame, yscrollcommand=scroll_y2.set, state=tk.DISABLED)
        scroll_y2.config(command=self.bill_area.yview)
        scroll_y2.pack(side=tk.RIGHT, fill=tk.Y)
        self.bill_area.pack(fill=tk.BOTH, expand=True)

        self.show()

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT invoice FROM sales")
        rows = cur.fetchall()
        conn.close()
        self.blll_list = [row[0] for row in rows]
        self.Sales_List.delete(0, tk.END)
        for inv in self.blll_list:
            self.Sales_List.insert(tk.END, inv)

    def get_data(self, ev):
        selected = self.Sales_List.curselection()
        if not selected:
            return
        invoice = self.Sales_List.get(selected[0])
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT bill FROM sales WHERE invoice=?", (invoice,))
        row = cur.fetchone()
        conn.close()
        self.bill_area.config(state=tk.NORMAL)
        self.bill_area.delete("1.0", tk.END)
        if row:
            self.bill_area.insert(tk.END, row[0])
        self.bill_area.config(state=tk.DISABLED)

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
        self.Sales_List.delete(0, tk.END)
        for row in rows:
            self.Sales_List.insert(tk.END, row[0])

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
        self.cart_list = []
        self.bill_amnt = 0
        self.discount = 5.0
        self.net_pay = 0
        self.siscount = 0
        self.chk_print = 0
        self.invoice = None

        self.var_pid = tk.StringVar()
        self.var_pname = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_stock = tk.StringVar()
        self.var_search = tk.StringVar()
        self.var_cname = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_cal_input = tk.StringVar()

        win = tk.Toplevel(self.root)
        win.title("Billing")
        win.geometry("1200x700")
        win.grab_set()

        self.icon_title = None

        # Top section
        top_frame = tk.Frame(win, bg="#2c3e50", pady=5)
        top_frame.pack(fill=tk.X)
        tk.Label(top_frame, text="Billing System", font=("Arial", 18, "bold"),
                 bg="#2c3e50", fg="white").pack(side=tk.LEFT, padx=10)
        self.lbl_clock = tk.Label(top_frame, text="", font=("Arial", 12),
                                  bg="#2c3e50", fg="white")
        self.lbl_clock.pack(side=tk.RIGHT, padx=10)
        self.update_date_time()

        # Main area
        main = tk.Frame(win)
        main.pack(fill=tk.BOTH, expand=True)

        # Left: product search
        left = tk.Frame(main, bg="#ecf0f1", width=350)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        tk.Label(left, text="Customer Info", font=("Arial", 11, "bold"), bg="#ecf0f1").pack(pady=5)
        tk.Label(left, text="Name:", bg="#ecf0f1").pack(anchor="w", padx=5)
        tk.Entry(left, textvariable=self.var_cname, width=30).pack(padx=5, pady=2)
        tk.Label(left, text="Contact:", bg="#ecf0f1").pack(anchor="w", padx=5)
        tk.Entry(left, textvariable=self.var_contact, width=30).pack(padx=5, pady=2)

        tk.Label(left, text="Product Search", font=("Arial", 11, "bold"), bg="#ecf0f1").pack(pady=5)
        tk.Entry(left, textvariable=self.var_search, width=30).pack(padx=5, pady=2)
        tk.Button(left, text="Search", bg="#8e44ad", fg="white",
                  command=self.search).pack(pady=2)

        prod_frame = tk.Frame(left)
        prod_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scroll_y = tk.Scrollbar(prod_frame, orient=tk.VERTICAL)
        self.product_Table = ttk.Treeview(
            prod_frame,
            columns=("pid", "name", "price", "qty", "status"),
            yscrollcommand=scroll_y.set
        )
        scroll_y.config(command=self.product_Table.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        for col, heading in zip(("pid", "name", "price", "qty", "status"),
                                ("PID", "Name", "Price", "Qty", "Status")):
            self.product_Table.heading(col, text=heading)
            self.product_Table.column(col, width=60)
        self.product_Table["show"] = "headings"
        self.product_Table.pack(fill=tk.BOTH, expand=True)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)

        # Middle: cart
        mid = tk.Frame(main, bg="#f9f9f9", width=400)
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(mid, text="Selected Product", font=("Arial", 11, "bold"), bg="#f9f9f9").pack(pady=5)
        info_frame = tk.Frame(mid, bg="#f9f9f9")
        info_frame.pack(fill=tk.X, padx=5)

        tk.Label(info_frame, text="PID:", bg="#f9f9f9").grid(row=0, column=0, sticky="e")
        tk.Entry(info_frame, textvariable=self.var_pid, width=15, state="readonly").grid(row=0, column=1, padx=3)
        tk.Label(info_frame, text="Name:", bg="#f9f9f9").grid(row=0, column=2, sticky="e")
        tk.Entry(info_frame, textvariable=self.var_pname, width=15, state="readonly").grid(row=0, column=3, padx=3)

        tk.Label(info_frame, text="Price:", bg="#f9f9f9").grid(row=1, column=0, sticky="e")
        tk.Entry(info_frame, textvariable=self.var_price, width=15, state="readonly").grid(row=1, column=1, padx=3)
        tk.Label(info_frame, text="Qty:", bg="#f9f9f9").grid(row=1, column=2, sticky="e")
        tk.Entry(info_frame, textvariable=self.var_qty, width=15).grid(row=1, column=3, padx=3)

        self.lbl_inStock = tk.Label(mid, text="In Stock: 0", bg="#f9f9f9", fg="#e74c3c")
        self.lbl_inStock.pack()

        tk.Button(mid, text="Add to Cart", bg="#27ae60", fg="white",
                  command=self.add_update_cart).pack(pady=5)

        self.cartTitle = tk.Label(mid, text="Cart", font=("Arial", 11, "bold"), bg="#f9f9f9")
        self.cartTitle.pack()

        cart_frame = tk.Frame(mid)
        cart_frame.pack(fill=tk.BOTH, expand=True, padx=5)
        scroll_y2 = tk.Scrollbar(cart_frame, orient=tk.VERTICAL)
        self.CartTable = ttk.Treeview(
            cart_frame,
            columns=("pid", "name", "price", "qty", "total"),
            yscrollcommand=scroll_y2.set
        )
        scroll_y2.config(command=self.CartTable.yview)
        scroll_y2.pack(side=tk.RIGHT, fill=tk.Y)
        for col, heading in zip(("pid", "name", "price", "qty", "total"),
                                ("PID", "Name", "Price", "Qty", "Total")):
            self.CartTable.heading(col, text=heading)
            self.CartTable.column(col, width=70)
        self.CartTable["show"] = "headings"
        self.CartTable.pack(fill=tk.BOTH, expand=True)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        amnt_frame = tk.Frame(mid, bg="#f9f9f9")
        amnt_frame.pack(fill=tk.X, padx=5, pady=5)
        self.lbl_amnt = tk.Label(amnt_frame, text="Total: $0.00", bg="#f9f9f9", font=("Arial", 11))
        self.lbl_amnt.pack(side=tk.LEFT)
        self.lbl_discount = tk.Label(amnt_frame, text=f"Discount: {self.discount}%", bg="#f9f9f9")
        self.lbl_discount.pack(side=tk.LEFT, padx=10)
        self.lbl_net_pay = tk.Label(amnt_frame, text="Net Pay: $0.00", bg="#f9f9f9", font=("Arial", 11, "bold"))
        self.lbl_net_pay.pack(side=tk.LEFT)

        btn_frame2 = tk.Frame(mid, bg="#f9f9f9")
        btn_frame2.pack(fill=tk.X, padx=5)
        tk.Button(btn_frame2, text="Generate Bill", bg="#2980b9", fg="white",
                  command=self.generate_bill).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame2, text="Clear Cart", bg="#e74c3c", fg="white",
                  command=self.clear_cart).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame2, text="Clear All", bg="#95a5a6", fg="white",
                  command=self.clear_all).pack(side=tk.LEFT, padx=3)

        # Right: bill area + calculator
        right = tk.Frame(main, bg="#ecf0f1", width=350)
        right.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        tk.Label(right, text="Bill", font=("Arial", 11, "bold"), bg="#ecf0f1").pack(pady=5)
        self.txt_bill_area = tk.Text(right, width=40, height=20, state=tk.DISABLED)
        self.txt_bill_area.pack(padx=5, pady=5)

        tk.Button(right, text="Print Bill", bg="#16a085", fg="white",
                  command=self.print_bill).pack(pady=3)

        # Calculator
        tk.Label(right, text="Calculator", font=("Arial", 11, "bold"), bg="#ecf0f1").pack(pady=5)
        self.txt_cal_input = tk.Entry(right, textvariable=self.var_cal_input, width=30, justify="right")
        self.txt_cal_input.pack(padx=5, pady=3)

        cal_frame = tk.Frame(right, bg="#ecf0f1")
        cal_frame.pack(padx=5)
        buttons = [
            ("7", "8", "9", "/"),
            ("4", "5", "6", "*"),
            ("1", "2", "3", "-"),
            ("0", ".", "C", "+"),
            ("=",),
        ]
        for row_btns in buttons:
            row_frame = tk.Frame(cal_frame, bg="#ecf0f1")
            row_frame.pack()
            for btn_text in row_btns:
                tk.Button(row_frame, text=btn_text, width=5, height=2,
                          command=lambda t=btn_text: self.get_input(t)).pack(side=tk.LEFT, padx=2, pady=2)

        self.show()

    def update_date_time(self):
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))
        self.lbl_clock.after(1000, self.update_date_time)

    def show(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT pid, name, price, qty, status FROM product WHERE status='Active'")
        rows = cur.fetchall()
        conn.close()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", tk.END, values=row)

    def search(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT pid, name, price, qty, status FROM product WHERE name LIKE ? OR pid LIKE ?",
                    (f"%{self.var_search.get()}%", f"%{self.var_search.get()}%"))
        rows = cur.fetchall()
        conn.close()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", tk.END, values=row)

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
            messagebox.showerror("Error", "Select a product and enter quantity")
            return
        try:
            qty = int(self.var_qty.get())
            price = float(self.var_price.get())
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
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity or price")

    def show_cart(self):
        self.CartTable.delete(*self.CartTable.get_children())
        self.bill_amnt = 0
        for item in self.cart_list:
            self.CartTable.insert("", tk.END, values=item)
            self.bill_amnt += item[4]
        self.siscount = (self.bill_amnt * self.discount) / 100
        self.net_pay = self.bill_amnt - self.siscount
        self.lbl_amnt.config(text=f"Total: ${self.bill_amnt:.2f}")
        self.lbl_discount.config(text=f"Discount({self.discount}%): ${self.siscount:.2f}")
        self.lbl_net_pay.config(text=f"Net Pay: ${self.net_pay:.2f}")

    def clear_cart(self):
        self.cart_list = []
        self.show_cart()

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
        self.txt_bill_area.config(state=tk.NORMAL)
        self.txt_bill_area.delete("1.0", tk.END)
        self.txt_bill_area.config(state=tk.DISABLED)

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty")
            return
        if self.var_cname.get() == "":
            messagebox.showerror("Error", "Enter customer name")
            return

        self.invoice = f"INV{random.randint(1000, 9999)}"
        now = datetime.datetime.now()

        bill_text = "=" * 40 + "\n"
        bill_text += "       INVENTORY MANAGEMENT SYSTEM\n"
        bill_text += "=" * 40 + "\n"
        bill_text += f"Invoice No : {self.invoice}\n"
        bill_text += f"Date       : {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        bill_text += f"Customer   : {self.var_cname.get()}\n"
        bill_text += f"Contact    : {self.var_contact.get()}\n"
        bill_text += "-" * 40 + "\n"
        bill_text += f"{'Name':<15}{'Qty':>5}{'Price':>10}{'Total':>10}\n"
        bill_text += "-" * 40 + "\n"
        for item in self.cart_list:
            bill_text += f"{str(item[1]):<15}{str(item[3]):>5}{str(item[2]):>10}{str(item[4]):>10}\n"
        bill_text += "-" * 40 + "\n"
        bill_text += f"{'Total Amount':>30}: ${self.bill_amnt:.2f}\n"
        bill_text += f"{'Discount':>30}: ${self.siscount:.2f}\n"
        bill_text += f"{'Net Pay':>30}: ${self.net_pay:.2f}\n"
        bill_text += "=" * 40 + "\n"
        bill_text += "      Thank you for shopping!\n"
        bill_text += "=" * 40 + "\n"

        self.txt_bill_area.config(state=tk.NORMAL)
        self.txt_bill_area.delete("1.0", tk.END)
        self.txt_bill_area.insert(tk.END, bill_text)
        self.txt_bill_area.config(state=tk.DISABLED)

        # Save to DB
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO sales VALUES (?,?)", (self.invoice, bill_text))
            # Update stock
            for item in self.cart_list:
                cur.execute("UPDATE product SET qty=qty-? WHERE pid=?", (item[3], item[0]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Bill generated! Invoice: {self.invoice}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def print_bill(self):
        if self.invoice is None:
            messagebox.showerror("Error", "Generate a bill first")
            return
        messagebox.showinfo("Print", f"Bill {self.invoice} sent to printer (simulated)")

    def bill_top(self):
        pass

    def bill_middle(self):
        pass

    def bill_bottom(self):
        pass

    def bill_update(self):
        pass

    def get_input(self, num):
        if num == "C":
            self.clear_cal()
        elif num == "=":
            self.perform_cal()
        else:
            current = self.var_cal_input.get()
            self.var_cal_input.set(current + str(num))

    def clear_cal(self):
        self.var_cal_input.set("")

    def perform_cal(self):
        try:
            result = eval(self.var_cal_input.get())
            self.var_cal_input.set(str(result))
        except Exception:
            self.var_cal_input.set("Error")


# ─────────────────────────────────────────────
# dashboard module
# ─────────────────────────────────────────────

class IMS:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("1100x650")
        self.root.config(bg="#2c3e50")

        self.new_obj = None
        self.new_win = None
        self.MenuLogo = None
        self.icon_side = None
        self.icon_title = None

        # Header
        header = tk.Frame(self.root, bg="#1a252f", pady=10)
        header.pack(fill=tk.X)
        tk.Label(header, text="INVENTORY MANAGEMENT SYSTEM",
                 font=("Arial", 22, "bold"), bg="#1a252f", fg="white").pack(side=tk.LEFT, padx=20)
        self.lbl_clock = tk.Label(header, text="", font=("Arial", 12),
                                  bg="#1a252f", fg="white")
        self.lbl_clock.pack(side=tk.RIGHT, padx=20)

        # Sidebar
        sidebar = tk.Frame(self.root, bg="#2c3e50", width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(sidebar, text="MENU", font=("Arial", 14, "bold"),
                 bg="#2c3e50", fg="#ecf0f1", pady=10).pack(fill=tk.X)

        menu_items = [
            ("Category", self.category),
            ("Employee", self.employee),
            ("Supplier", self.supplier),
            ("Product", self.product),
            ("Sales", self.sales),
            ("Billing", self.billing),
        ]
        for text, cmd in menu_items:
            tk.Button(sidebar, text=text, font=("Arial", 12), bg="#34495e", fg="white",
                      activebackground="#1abc9c", activeforeground="white",
                      bd=0, pady=10, command=cmd).pack(fill=tk.X, padx=5, pady=2)

        # Main content area
        content = tk.Frame(self.root, bg="#ecf0f1")
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(content, text="Dashboard", font=("Arial", 18, "bold"),
                 bg="#ecf0f1", fg="#2c3e50").pack(pady=20)

        stats_frame = tk.Frame(content, bg="#ecf0f1")
        stats_frame.pack(fill=tk.X, padx=20)

        self.lbl_category = self._stat_card(stats_frame, "Categories", "#3498db", 0)
        self.lbl_employee = self._stat_card(stats_frame, "Employees", "#e74c3c", 1)
        self.lbl_supplier = self._stat_card(stats_frame, "Suppliers", "#2ecc71", 2)
        self.lbl_product = self._stat_card(stats_frame, "Products", "#f39c12", 3)
        self.lbl_sales = self._stat_card(stats_frame, "Sales", "#9b59b6", 4)

        self.update_content()

    def _stat_card(self, parent, title, color, col):
        frame = tk.Frame(parent, bg=color, padx=20, pady=20)
        frame.grid(row=0, column=col, padx=10, pady=10)
        tk.Label(frame, text=title, font=("Arial", 12, "bold"),
                 bg=color, fg="white").pack()
        lbl = tk.Label(frame, text="0", font=("Arial", 20, "bold"),
                       bg=color, fg="white")
        lbl.pack()
        return lbl

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
        self.new_win = tk.Toplevel(self.root)
        self.new_win.withdraw()
        self.new_obj = categoryClass(self.root)

    def employee(self):
        self.new_win = tk.Toplevel(self.root)
        self.new_win.withdraw()
        self.new_obj = employeeClass(self.root)

    def supplier(self):
        self.new_win = tk.Toplevel(self.root)
        self.new_win.withdraw()
        self.new_obj = supplierClass(self.root)

    def product(self):
        self.new_win = tk.Toplevel(self.root)
        self.new_win.withdraw()
        self.new_obj = productClass(self.root)

    def sales(self):
        self.new_win = tk.Toplevel(self.root)
        self.new_win.withdraw()
        self.new_obj = salesClass(self.root)

    def billing(self):
        self.new_win = tk.Toplevel(self.root)
        self.new_win.withdraw()
        self.new_obj = billClass(self.root)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = IMS(root)
    root.mainloop()