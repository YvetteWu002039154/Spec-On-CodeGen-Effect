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
        name   TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS supplier (
        sup_invoice TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        contact     TEXT,
        desc        TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS employee (
        emp_id  TEXT PRIMARY KEY,
        name    TEXT,
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
    c.execute("""CREATE TABLE IF NOT EXISTS product (
        pid    TEXT PRIMARY KEY,
        name   TEXT,
        price  TEXT,
        qty    TEXT,
        status TEXT,
        cat    TEXT,
        sup    TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        invoice TEXT PRIMARY KEY,
        bill    TEXT,
        date    TEXT
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
        self.var_name   = tk.StringVar()
        self.im1  = None
        self.im2  = None

        win = tk.Toplevel(self.root)
        win.title("Category Management")
        win.geometry("800x500")
        win.grab_set()

        tk.Label(win, text="Category Management", font=("Arial", 16, "bold"),
                 bg="#0f4d7d", fg="white").pack(fill=tk.X)

        frame_top = tk.Frame(win, bd=2, relief=tk.RIDGE)
        frame_top.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(frame_top, text="Category ID:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        tk.Entry(frame_top, textvariable=self.var_cat_id).grid(row=0, column=1, padx=5, pady=5)
        tk.Label(frame_top, text="Category Name:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        tk.Entry(frame_top, textvariable=self.var_name).grid(row=0, column=3, padx=5, pady=5)

        btn_frame = tk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="Add",    command=self.add,    bg="#0f4d7d", fg="white", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete, bg="red",     fg="white", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear",  command=self.clear,  bg="gray",    fg="white", width=10).pack(side=tk.LEFT, padx=5)

        # image labels (placeholder)
        img_frame = tk.Frame(win)
        img_frame.pack(fill=tk.X, padx=10, pady=5)
        self.lbl_im1 = tk.Label(img_frame, text="[Image 1]", width=20, height=5, relief=tk.RIDGE)
        self.lbl_im1.pack(side=tk.LEFT, padx=5)
        self.lbl_im2 = tk.Label(img_frame, text="[Image 2]", width=20, height=5, relief=tk.RIDGE)
        self.lbl_im2.pack(side=tk.LEFT, padx=5)

        frame_table = tk.Frame(win, bd=2, relief=tk.RIDGE)
        frame_table.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scroll_x = tk.Scrollbar(frame_table, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(frame_table, orient=tk.VERTICAL)
        self.CategoryTable = ttk.Treeview(
            frame_table,
            columns=("cat_id", "name"),
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set
        )
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT,  fill=tk.Y)
        scroll_x.config(command=self.CategoryTable.xview)
        scroll_y.config(command=self.CategoryTable.yview)

        self.CategoryTable.heading("cat_id", text="Category ID")
        self.CategoryTable.heading("name",   text="Category Name")
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
            c = conn.cursor()
            c.execute("INSERT INTO category VALUES (?,?)",
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
            c = conn.cursor()
            c.execute("DELETE FROM category WHERE cat_id=?", (self.var_cat_id.get(),))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Category deleted")
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clear(self):
        self.var_cat_id.set("")
        self.var_name.set("")

    def get_data(self, ev):
        selected = self.CategoryTable.focus()
        content  = self.CategoryTable.item(selected)
        row = content["values"]
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
        self.var_name        = tk.StringVar()
        self.var_contact     = tk.StringVar()
        self.var_searchby    = tk.StringVar()
        self.var_searchtxt   = tk.StringVar()

        win = tk.Toplevel(self.root)
        win.title("Supplier Management")
        win.geometry("900x550")
        win.grab_set()

        tk.Label(win, text="Supplier Management", font=("Arial", 16, "bold"),
                 bg="#0f4d7d", fg="white").pack(fill=tk.X)

        frame_top = tk.Frame(win, bd=2, relief=tk.RIDGE)
        frame_top.pack(fill=tk.X, padx=10, pady=5)

        labels = ["Invoice No:", "Name:", "Contact:"]
        vars_  = [self.var_sup_invoice, self.var_name, self.var_contact]
        for i, (lbl, var) in enumerate(zip(labels, vars_)):
            tk.Label(frame_top, text=lbl).grid(row=0, column=i*2, padx=5, pady=5, sticky=tk.W)
            tk.Entry(frame_top, textvariable=var).grid(row=0, column=i*2+1, padx=5, pady=5)

        tk.Label(frame_top, text="Description:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.txt_desc = tk.Text(frame_top, height=3, width=60)
        self.txt_desc.grid(row=1, column=1, columnspan=5, padx=5, pady=5)

        btn_frame = tk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="Add",    command=self.add,    bg="#0f4d7d", fg="white", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Update", command=self.update, bg="green",   fg="white", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete, bg="red",     fg="white", width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear",  command=self.clear,  bg="gray",    fg="white", width=10).pack(side=tk.LEFT, padx=5)

        search_frame = tk.Frame(win, bd=2, relief=tk.RIDGE)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="Search By:").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Invoice No", "Name", "Contact"], width=15).pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, width=20).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", command=self.search, bg="#0f4d7d", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All", command=self.show, bg="gray", fg="white").pack(side=tk.LEFT, padx=5)

        frame_table = tk.Frame(win, bd=2, relief=tk.RIDGE)
        frame_table.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scroll_x = tk.Scrollbar(frame_table, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(frame_table, orient=tk.VERTICAL)
        self.SupplierTable = ttk.Treeview(
            frame_table,
            columns=("invoice", "name", "contact", "desc"),
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set
        )
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT,  fill=tk.Y)
        scroll_x.config(command=self.SupplierTable.xview)
        scroll_y.config(command=self.SupplierTable.yview)

        for col, heading in zip(("invoice","name","contact","desc"),
                                 ("Invoice No","Name","Contact","Description")):
            self.SupplierTable.heading(col, text=heading)
            self.SupplierTable.column(col, width=150)
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
            c = conn.cursor()
            c.execute("INSERT INTO supplier VALUES (?,?,?,?)",
                      (self.var_sup_invoice.get(), self.var_name.get(),
                       self.var_contact.get(), self.txt_desc.get("1.0", tk.END).strip()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier added")
            self.clear(); self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update(self):
        if self.var_sup_invoice.get() == "":
            messagebox.showerror("Error", "Select a supplier to update")
            return
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("UPDATE supplier SET name=?,contact=?,desc=? WHERE sup_invoice=?",
                      (self.var_name.get(), self.var_contact.get(),
                       self.txt_desc.get("1.0", tk.END).strip(), self.var_sup_invoice.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier updated")
            self.clear(); self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete(self):
        if self.var_sup_invoice.get() == "":
            messagebox.showerror("Error", "Select a supplier to delete")
            return
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("DELETE FROM supplier WHERE sup_invoice=?", (self.var_sup_invoice.get(),))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier deleted")
            self.clear(); self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clear(self):
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete("1.0", tk.END)

    def get_data(self, ev):
        selected = self.SupplierTable.focus()
        content  = self.SupplierTable.item(selected)
        row = content["values"]
        if row:
            self.var_sup_invoice.set(row[0])
            self.var_name.set(row[1])
            self.var_contact.set(row[2])
            self.txt_desc.delete("1.0", tk.END)
            self.txt_desc.insert(tk.END, row[3] if row[3] else "")

    def search(self):
        if self.var_searchby.get() == "" or self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Select search criteria and enter text")
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
        self.var_emp_id    = tk.StringVar()
        self.var_name      = tk.StringVar()
        self.var_email     = tk.StringVar()
        self.var_gender    = tk.StringVar()
        self.var_contact   = tk.StringVar()
        self.var_dob       = tk.StringVar()
        self.var_doj       = tk.StringVar()
        self.var_utype     = tk.StringVar()
        self.var_salary    = tk.StringVar()
        self.var_pass      = tk.StringVar()
        self.var_searchby  = tk.StringVar()
        self.var_searchtxt = tk.StringVar()

        win = tk.Toplevel(self.root)
        win.title("Employee Management")
        win.geometry("1000x600")
        win.grab_set()

        tk.Label(win, text="Employee Management", font=("Arial", 16, "bold"),
                 bg="#0f4d7d", fg="white").pack(fill=tk.X)

        frame_top = tk.Frame(win, bd=2, relief=tk.RIDGE)
        frame_top.pack(fill=tk.X, padx=10, pady=5)

        fields = [
            ("Emp ID:", self.var_emp_id, 0, 0),
            ("Name:",   self.var_name,   0, 2),
            ("Email:",  self.var_email,  0, 4),
            ("Gender:", self.var_gender, 1, 0),
            ("Contact:",self.var_contact,1, 2),
            ("DOB:",    self.var_dob,    1, 4),
            ("DOJ:",    self.var_doj,    2, 0),
            ("User Type:", self.var_utype, 2, 2),
            ("Salary:", self.var_salary, 2, 4),
            ("Password:", self.var_pass, 3, 0),
        ]
        for lbl_text, var, row, col in fields:
            tk.Label(frame_top, text=lbl_text).grid(row=row, column=col,   padx=5, pady=3, sticky=tk.W)
            tk.Entry(frame_top, textvariable=var).grid(row=row, column=col+1, padx=5, pady=3)

        tk.Label(frame_top, text="Address:").grid(row=3, column=2, padx=5, pady=3, sticky=tk.W)
        self.txt_address = tk.Text(frame_top, height=3, width=40)
        self.txt_address.grid(row=3, column=3, columnspan=3, padx=5, pady=3)

        btn_frame = tk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=10)
        for text, cmd, color in [("Add", self.add, "#0f4d7d"), ("Update", self.update, "green"),
                                   ("Delete", self.delete, "red"), ("Clear", self.clear, "gray")]:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white", width=10).pack(side=tk.LEFT, padx=5)

        search_frame = tk.Frame(win, bd=2, relief=tk.RIDGE)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="Search By:").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Emp ID", "Name", "Email", "Contact"], width=15).pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, width=20).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search",   command=self.search, bg="#0f4d7d", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All", command=self.show,   bg="gray",    fg="white").pack(side=tk.LEFT, padx=5)

        frame_table = tk.Frame(win, bd=2, relief=tk.RIDGE)
        frame_table.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = ("emp_id","name","email","gender","contact","dob","doj","utype","salary","address","password")
        scroll_x = tk.Scrollbar(frame_table, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(frame_table, orient=tk.VERTICAL)
        self.EmployeeTable = ttk.Treeview(frame_table, columns=cols,
                                          xscrollcommand=scroll_x.set,
                                          yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT,  fill=tk.Y)
        scroll_x.config(command=self.EmployeeTable.xview)
        scroll_y.config(command=self.EmployeeTable.yview)

        headings = ("Emp ID","Name","Email","Gender","Contact","DOB","DOJ","User Type","Salary","Address","Password")
        for col, heading in zip(cols, headings):
            self.EmployeeTable.heading(col, text=heading)
            self.EmployeeTable.column(col, width=100)
        self.EmployeeTable["show"] = "headings"
        self.EmployeeTable.pack(fill=tk.BOTH, expand=True)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def add(self):
        if self.var_emp_id.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "Emp ID and Name are required")
            return
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO employee VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (self.var_emp_id.get(), self.var_name.get(), self.var_email.get(),
                       self.var_gender.get(), self.var_contact.get(), self.var_dob.get(),
                       self.var_doj.get(), self.var_utype.get(), self.var_salary.get(),
                       self.txt_address.get("1.0", tk.END).strip(), self.var_pass.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee added")
            self.clear(); self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update(self):
        if self.var_emp_id.get() == "":
            messagebox.showerror("Error", "Select an employee to update")
            return
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("""UPDATE employee SET name=?,email=?,gender=?,contact=?,dob=?,
                         doj=?,utype=?,salary=?,address=?,password=? WHERE emp_id=?""",
                      (self.var_name.get(), self.var_email.get(), self.var_gender.get(),
                       self.var_contact.get(), self.var_dob.get(), self.var_doj.get(),
                       self.var_utype.get(), self.var_salary.get(),
                       self.txt_address.get("1.0", tk.END).strip(),
                       self.var_pass.get(), self.var_emp_id.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee updated")
            self.clear(); self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete(self):
        if self.var_emp_id.get() == "":
            messagebox.showerror("Error", "Select an employee to delete")
            return
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("DELETE FROM employee WHERE emp_id=?", (self.var_emp_id.get(),))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee deleted")
            self.clear(); self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clear(self):
        for var in [self.var_emp_id, self.var_name, self.var_email, self.var_gender,
                    self.var_contact, self.var_dob, self.var_doj, self.var_utype,
                    self.var_salary, self.var_pass]:
            var.set("")
        self.txt_address.delete("1.0", tk.END)

    def get_data(self, ev):
        selected = self.EmployeeTable.focus()
        content  = self.EmployeeTable.item(selected)
        row = content["values"]
        if row:
            self.var_emp_id.set(row[0]);  self.var_name.set(row[1])
            self.var_email.set(row[2]);   self.var_gender.set(row[3])
            self.var_contact.set(row[4]); self.var_dob.set(row[5])
            self.var_doj.set(row[6]);     self.var_utype.set(row[7])
            self.var_salary.set(row[8])
            self.txt_address.delete("1.0", tk.END)
            self.txt_address.insert(tk.END, row[9] if row[9] else "")
            self.var_pass.set(row[10] if len(row) > 10 else "")

    def search(self):
        if self.var_searchby.get() == "" or self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Select search criteria and enter text")
            return
        col_map = {"Emp ID": "emp_id", "Name": "name", "Email": "email", "Contact": "contact"}
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
        self.var_pid       = tk.StringVar()
        self.var_name      = tk.StringVar()
        self.var_price     = tk.StringVar()
        self.var_qty       = tk.StringVar()
        self.var_status    = tk.StringVar()
        self.var_cat       = tk.StringVar()
        self.var_sup       = tk.StringVar()
        self.var_searchby  = tk.StringVar()
        self.var_searchtxt = tk.StringVar()
        self.cat_list      = []
        self.sup_list      = []

        win = tk.Toplevel(self.root)
        win.title("Product Management")
        win.geometry("1000x600")
        win.grab_set()

        tk.Label(win, text="Product Management", font=("Arial", 16, "bold"),
                 bg="#0f4d7d", fg="white").pack(fill=tk.X)

        frame_top = tk.Frame(win, bd=2, relief=tk.RIDGE)
        frame_top.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(frame_top, text="Product ID:").grid(row=0, column=0, padx=5, pady=3, sticky=tk.W)
        tk.Entry(frame_top, textvariable=self.var_pid).grid(row=0, column=1, padx=5, pady=3)
        tk.Label(frame_top, text="Name:").grid(row=0, column=2, padx=5, pady=3, sticky=tk.W)
        tk.Entry(frame_top, textvariable=self.var_name).grid(row=0, column=3, padx=5, pady=3)
        tk.Label(frame_top, text="Price:").grid(row=0, column=4, padx=5, pady=3, sticky=tk.W)
        tk.Entry(frame_top, textvariable=self.var_price).grid(row=0, column=5, padx=5, pady=3)

        tk.Label(frame_top, text="Quantity:").grid(row=1, column=0, padx=5, pady=3, sticky=tk.W)
        tk.Entry(frame_top, textvariable=self.var_qty).grid(row=1, column=1, padx=5, pady=3)
        tk.Label(frame_top, text="Status:").grid(row=1, column=2, padx=5, pady=3, sticky=tk.W)
        ttk.Combobox(frame_top, textvariable=self.var_status,
                     values=["Active", "Inactive"], width=17).grid(row=1, column=3, padx=5, pady=3)

        tk.Label(frame_top, text="Category:").grid(row=1, column=4, padx=5, pady=3, sticky=tk.W)
        self.cat_combo = ttk.Combobox(frame_top, textvariable=self.var_cat, width=17)
        self.cat_combo.grid(row=1, column=5, padx=5, pady=3)

        tk.Label(frame_top, text="Supplier:").grid(row=2, column=0, padx=5, pady=3, sticky=tk.W)
        self.sup_combo = ttk.Combobox(frame_top, textvariable=self.var_sup, width=17)
        self.sup_combo.grid(row=2, column=1, padx=5, pady=3)

        btn_frame = tk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=10)
        for text, cmd, color in [("Add", self.add, "#0f4d7d"), ("Update", self.update, "green"),
                                   ("Delete", self.delete, "red"), ("Clear", self.clear, "gray")]:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white", width=10).pack(side=tk.LEFT, padx=5)

        search_frame = tk.Frame(win, bd=2, relief=tk.RIDGE)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="Search By:").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Product ID", "Name", "Status", "Category"], width=15).pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, width=20).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search",   command=self.search, bg="#0f4d7d", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All", command=self.show,   bg="gray",    fg="white").pack(side=tk.LEFT, padx=5)

        frame_table = tk.Frame(win, bd=2, relief=tk.RIDGE)
        frame_table.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        cols = ("pid","name","price","qty","status","cat","sup")
        scroll_x = tk.Scrollbar(frame_table, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(frame_table, orient=tk.VERTICAL)
        self.ProductTable = ttk.Treeview(frame_table, columns=cols,
                                         xscrollcommand=scroll_x.set,
                                         yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT,  fill=tk.Y)
        scroll_x.config(command=self.ProductTable.xview)
        scroll_y.config(command=self.ProductTable.yview)

        headings = ("Product ID","Name","Price","Quantity","Status","Category","Supplier")
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
        c = conn.cursor()
        c.execute("SELECT name FROM category")
        self.cat_list = [row[0] for row in c.fetchall()]
        c.execute("SELECT name FROM supplier")
        self.sup_list = [row[0] for row in c.fetchall()]
        conn.close()
        self.cat_combo["values"] = self.cat_list
        self.sup_combo["values"] = self.sup_list

    def add(self):
        if self.var_pid.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "Product ID and Name are required")
            return
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO product VALUES (?,?,?,?,?,?,?)",
                      (self.var_pid.get(), self.var_name.get(), self.var_price.get(),
                       self.var_qty.get(), self.var_status.get(),
                       self.var_cat.get(), self.var_sup.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product added")
            self.clear(); self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update(self):
        if self.var_pid.get() == "":
            messagebox.showerror("Error", "Select a product to update")
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
            messagebox.showinfo("Success", "Product updated")
            self.clear(); self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete(self):
        if self.var_pid.get() == "":
            messagebox.showerror("Error", "Select a product to delete")
            return
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("DELETE FROM product WHERE pid=?", (self.var_pid.get(),))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product deleted")
            self.clear(); self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clear(self):
        for var in [self.var_pid, self.var_name, self.var_price, self.var_qty,
                    self.var_status, self.var_cat, self.var_sup]:
            var.set("")

    def get_data(self, ev):
        selected = self.ProductTable.focus()
        content  = self.ProductTable.item(selected)
        row = content["values"]
        if row:
            self.var_pid.set(row[0]);    self.var_name.set(row[1])
            self.var_price.set(row[2]);  self.var_qty.set(row[3])
            self.var_status.set(row[4]); self.var_cat.set(row[5])
            self.var_sup.set(row[6])

    def search(self):
        if self.var_searchby.get() == "" or self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Select search criteria and enter text")
            return
        col_map = {"Product ID": "pid", "Name": "name", "Status": "status", "Category": "cat"}
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
        self.blll_list   = []
        self.bill_photo  = None

        win = tk.Toplevel(self.root)
        win.title("Sales Records")
        win.geometry("900x550")
        win.grab_set()

        tk.Label(win, text="Sales Records", font=("Arial", 16, "bold"),
                 bg="#0f4d7d", fg="white").pack(fill=tk.X)

        search_frame = tk.Frame(win, bd=2, relief=tk.RIDGE)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="Invoice No:").pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_invoice, width=20).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search",   command=self.search, bg="#0f4d7d", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All", command=self.show,   bg="gray",    fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Clear",    command=self.clear,  bg="red",     fg="white").pack(side=tk.LEFT, padx=5)

        main_frame = tk.Frame(win)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        list_frame = tk.Frame(main_frame, bd=2, relief=tk.RIDGE)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(list_frame, text="Invoice List", font=("Arial", 12, "bold")).pack()
        scroll_y = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.Sales_List = tk.Listbox(list_frame, yscrollcommand=scroll_y.set, width=30)
        scroll_y.config(command=self.Sales_List.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.Sales_List.pack(fill=tk.BOTH, expand=True)
        self.Sales_List.bind("<ButtonRelease-1>", self.get_data)

        bill_frame = tk.Frame(main_frame, bd=2, relief=tk.RIDGE)
        bill_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(bill_frame, text="Bill Details", font=("Arial", 12, "bold")).pack()
        scroll_b = tk.Scrollbar(bill_frame, orient=tk.VERTICAL)
        self.bill_area = tk.Text(bill_frame, yscrollcommand=scroll_b.set, width=50)
        scroll_b.config(command=self.bill_area.yview)
        scroll_b.pack(side=tk.RIGHT, fill=tk.Y)
        self.bill_area.pack(fill=tk.BOTH, expand=True)

        self.show()

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

    def get_data(self, ev):
        selected = self.Sales_List.curselection()
        if not selected:
            return
        invoice = self.Sales_List.get(selected[0])
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT bill FROM sales WHERE invoice=?", (invoice,))
        row = c.fetchone()
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
        c = conn.cursor()
        c.execute("SELECT invoice FROM sales WHERE invoice LIKE ?",
                  (f"%{self.var_invoice.get()}%",))
        rows = c.fetchall()
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
        self.var_search   = tk.StringVar()
        self.var_pid      = tk.StringVar()
        self.var_pname    = tk.StringVar()
        self.var_price    = tk.StringVar()
        self.var_qty      = tk.StringVar()
        self.var_stock    = tk.StringVar()
        self.var_cname    = tk.StringVar()
        self.var_contact  = tk.StringVar()
        self.var_cal_input = tk.StringVar()

        self.cart_list  = []
        self.bill_amnt  = 0
        self.discount   = 0.0
        self.net_pay    = 0
        self.siscount   = 0
        self.chk_print  = 0
        self.invoice    = None

        win = tk.Toplevel(self.root)
        win.title("Billing")
        win.geometry("1200x700")
        win.grab_set()

        self.bill_top(win)
        self.bill_middle(win)
        self.bill_bottom(win)
        self.update_date_time()
        self.show()

    def bill_top(self, win):
        top_frame = tk.Frame(win, bd=2, relief=tk.RIDGE, bg="#0f4d7d")
        top_frame.pack(fill=tk.X)

        tk.Label(top_frame, text="Inventory Management System - Billing",
                 font=("Arial", 18, "bold"), bg="#0f4d7d", fg="white").pack(side=tk.LEFT, padx=10)

        self.lbl_clock = tk.Label(top_frame, text="", font=("Arial", 12),
                                   bg="#0f4d7d", fg="white")
        self.lbl_clock.pack(side=tk.RIGHT, padx=10)

        self.icon_title = None

    def bill_middle(self, win):
        mid_frame = tk.Frame(win)
        mid_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left: product search
        left_frame = tk.Frame(mid_frame, bd=2, relief=tk.RIDGE)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left_frame, text="Product Search", font=("Arial", 12, "bold"),
                 bg="#0f4d7d", fg="white").pack(fill=tk.X)

        search_frame = tk.Frame(left_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        tk.Entry(search_frame, textvariable=self.var_search, width=20).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", command=self.search,
                  bg="#0f4d7d", fg="white").pack(side=tk.LEFT)

        prod_frame = tk.Frame(left_frame, bd=2, relief=tk.RIDGE)
        prod_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        cols = ("pid","name","price","qty","status","cat","sup")
        scroll_x = tk.Scrollbar(prod_frame, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(prod_frame, orient=tk.VERTICAL)
        self.product_Table = ttk.Treeview(prod_frame, columns=cols,
                                           xscrollcommand=scroll_x.set,
                                           yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT,  fill=tk.Y)
        scroll_x.config(command=self.product_Table.xview)
        scroll_y.config(command=self.product_Table.yview)

        headings = ("PID","Name","Price","Qty","Status","Category","Supplier")
        for col, heading in zip(cols, headings):
            self.product_Table.heading(col, text=heading)
            self.product_Table.column(col, width=90)
        self.product_Table["show"] = "headings"
        self.product_Table.pack(fill=tk.BOTH, expand=True)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)

        # Product detail + add to cart
        detail_frame = tk.Frame(left_frame, bd=2, relief=tk.RIDGE)
        detail_frame.pack(fill=tk.X, padx=5, pady=5)

        fields = [("PID:", self.var_pid), ("Name:", self.var_pname),
                  ("Price:", self.var_price), ("Qty:", self.var_qty)]
        for i, (lbl, var) in enumerate(fields):
            tk.Label(detail_frame, text=lbl).grid(row=0, column=i*2, padx=3, pady=3, sticky=tk.W)
            tk.Entry(detail_frame, textvariable=var, width=12).grid(row=0, column=i*2+1, padx=3, pady=3)

        self.lbl_inStock = tk.Label(detail_frame, text="In Stock: 0", fg="green")
        self.lbl_inStock.grid(row=1, column=0, columnspan=2, padx=3, pady=3)

        tk.Button(detail_frame, text="Add to Cart", command=self.add_update_cart,
                  bg="green", fg="white").grid(row=1, column=2, columnspan=2, padx=5, pady=3)

        # Right: cart
        right_frame = tk.Frame(mid_frame, bd=2, relief=tk.RIDGE)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.cartTitle = tk.Label(right_frame, text="Cart", font=("Arial", 12, "bold"),
                                   bg="#0f4d7d", fg="white")
        self.cartTitle.pack(fill=tk.X)

        cart_frame = tk.Frame(right_frame, bd=2, relief=tk.RIDGE)
        cart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        cart_cols = ("pid","name","price","qty","total")
        scroll_cx = tk.Scrollbar(cart_frame, orient=tk.HORIZONTAL)
        scroll_cy = tk.Scrollbar(cart_frame, orient=tk.VERTICAL)
        self.CartTable = ttk.Treeview(cart_frame, columns=cart_cols,
                                       xscrollcommand=scroll_cx.set,
                                       yscrollcommand=scroll_cy.set)
        scroll_cx.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_cy.pack(side=tk.RIGHT,  fill=tk.Y)
        scroll_cx.config(command=self.CartTable.xview)
        scroll_cy.config(command=self.CartTable.yview)

        cart_headings = ("PID","Name","Price","Qty","Total")
        for col, heading in zip(cart_cols, cart_headings):
            self.CartTable.heading(col, text=heading)
            self.CartTable.column(col, width=90)
        self.CartTable["show"] = "headings"
        self.CartTable.pack(fill=tk.BOTH, expand=True)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        # Amount labels
        amt_frame = tk.Frame(right_frame)
        amt_frame.pack(fill=tk.X, padx=5, pady=5)

        self.lbl_amnt     = tk.Label(amt_frame, text="Total Amount: 0.00", font=("Arial", 11))
        self.lbl_amnt.pack(anchor=tk.W)
        self.lbl_discount = tk.Label(amt_frame, text="Discount (0%): 0.00", font=("Arial", 11))
        self.lbl_discount.pack(anchor=tk.W)
        self.lbl_net_pay  = tk.Label(amt_frame, text="Net Payable: 0.00", font=("Arial", 11, "bold"))
        self.lbl_net_pay.pack(anchor=tk.W)

        # Customer info
        cust_frame = tk.Frame(right_frame)
        cust_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(cust_frame, text="Customer Name:").grid(row=0, column=0, padx=3, pady=3, sticky=tk.W)
        tk.Entry(cust_frame, textvariable=self.var_cname, width=20).grid(row=0, column=1, padx=3, pady=3)
        tk.Label(cust_frame, text="Contact:").grid(row=0, column=2, padx=3, pady=3, sticky=tk.W)
        tk.Entry(cust_frame, textvariable=self.var_contact, width=15).grid(row=0, column=3, padx=3, pady=3)

        btn_frame = tk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(btn_frame, text="Generate Bill", command=self.generate_bill,
                  bg="#0f4d7d", fg="white", width=14).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="Clear Cart", command=self.clear_cart,
                  bg="orange", fg="white", width=12).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="Clear All", command=self.clear_all,
                  bg="red", fg="white", width=12).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame, text="Print Bill", command=self.print_bill,
                  bg="green", fg="white", width=12).pack(side=tk.LEFT, padx=3)

    def bill_bottom(self, win):
        bottom_frame = tk.Frame(win, bd=2, relief=tk.RIDGE)
        bottom_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tk.Label(bottom_frame, text="Bill Area", font=("Arial", 12, "bold"),
                 bg="#0f4d7d", fg="white").pack(fill=tk.X)

        scroll_b = tk.Scrollbar(bottom_frame, orient=tk.VERTICAL)
        self.txt_bill_area = tk.Text(bottom_frame, height=10, yscrollcommand=scroll_b.set)
        scroll_b.config(command=self.txt_bill_area.yview)
        scroll_b.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_bill_area.pack(fill=tk.BOTH, expand=True)

        # Calculator
        cal_frame = tk.Frame(win, bd=2, relief=tk.RIDGE)
        cal_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(cal_frame, text="Calculator:", font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
        self.txt_cal_input = tk.Entry(cal_frame, textvariable=self.var_cal_input, width=30)
        self.txt_cal_input.pack(side=tk.LEFT, padx=5)

        for num in ["7","8","9","/","4","5","6","*","1","2","3","-","0",".","=","+"]:
            tk.Button(cal_frame, text=num, width=3,
                      command=lambda n=num: self.get_input(n)).pack(side=tk.LEFT, padx=1)
        tk.Button(cal_frame, text="C", width=3, command=self.clear_cal,
                  bg="red", fg="white").pack(side=tk.LEFT, padx=1)

    def update_date_time(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.config(text=now)
        self.lbl_clock.after(1000, self.update_date_time)

    def show(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM product WHERE status='Active'")
        rows = c.fetchall()
        conn.close()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", tk.END, values=row)

    def search(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM product WHERE name LIKE ? OR pid LIKE ?",
                  (f"%{self.var_search.get()}%", f"%{self.var_search.get()}%"))
        rows = c.fetchall()
        conn.close()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", tk.END, values=row)

    def get_data(self, ev):
        selected = self.product_Table.focus()
        content  = self.product_Table.item(selected)
        row = content["values"]
        if row:
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_stock.set(row[3])
            self.lbl_inStock.config(text=f"In Stock: {row[3]}")

    def get_data_cart(self, ev):
        selected = self.CartTable.focus()
        content  = self.CartTable.item(selected)
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
            qty   = int(self.var_qty.get())
            price = float(self.var_price.get())
            stock = int(self.var_stock.get()) if self.var_stock.get() else 0
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity or price")
            return

        if qty <= 0:
            messagebox.showerror("Error", "Quantity must be positive")
            return
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
            self.CartTable.insert("", tk.END, values=item)
            self.bill_amnt += item[4]

        self.discount = self.bill_amnt * 0.05  # 5% discount
        self.net_pay  = self.bill_amnt - self.discount

        self.lbl_amnt.config(text=f"Total Amount: {self.bill_amnt:.2f}")
        self.lbl_discount.config(text=f"Discount (5%): {self.discount:.2f}")
        self.lbl_net_pay.config(text=f"Net Payable: {self.net_pay:.2f}")

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty")
            return
        if self.var_cname.get() == "":
            messagebox.showerror("Error", "Enter customer name")
            return

        self.invoice = f"INV{random.randint(1000, 9999)}"
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
        bill_text += f"{'Total Amount':>35}: {self.bill_amnt:>10.2f}\n"
        bill_text += f"{'Discount (5%)':>35}: {self.discount:>10.2f}\n"
        bill_text += f"{'Net Payable':>35}: {self.net_pay:>10.2f}\n"
        bill_text += "=" * 50 + "\n"
        bill_text += "       Thank you for shopping!\n"
        bill_text += "=" * 50 + "\n"

        self.txt_bill_area.delete("1.0", tk.END)
        self.txt_bill_area.insert(tk.END, bill_text)

        # Save to DB
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO sales VALUES (?,?,?)", (self.invoice, bill_text, now))
            # Update stock
            for item in self.cart_list:
                c.execute("UPDATE product SET qty=qty-? WHERE pid=?", (item[3], item[0]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Bill generated! Invoice: {self.invoice}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def bill_update(self):
        self.show_cart()

    def clear_cart(self):
        self.cart_list = []
        self.show_cart()
        self.var_pid.set(""); self.var_pname.set("")
        self.var_price.set(""); self.var_qty.set("")

    def clear_all(self):
        self.clear_cart()
        self.var_cname.set(""); self.var_contact.set("")
        self.txt_bill_area.delete("1.0", tk.END)
        self.invoice = None

    def print_bill(self):
        if self.txt_bill_area.get("1.0", tk.END).strip() == "":
            messagebox.showerror("Error", "No bill to print")
            return
        messagebox.showinfo("Print", "Bill sent to printer (simulated)")
        self.chk_print = 1

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
# dashboard module
# ─────────────────────────────────────────────
class IMS:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("1100x650")
        self.root.config(bg="#f0f0f0")

        self.new_obj = None
        self.new_win = None

        self.MenuLogo  = None
        self.icon_side  = None
        self.icon_title = None

        self._build_ui()
        self.update_content()

    def _build_ui(self):
        # Title bar
        title_bar = tk.Frame(self.root, bg="#0f4d7d", bd=0)
        title_bar.pack(fill=tk.X)
        tk.Label(title_bar, text="Inventory Management System",
                 font=("Arial", 20, "bold"), bg="#0f4d7d", fg="white",
                 pady=10).pack(side=tk.LEFT, padx=20)
        self.lbl_clock = tk.Label(title_bar, text="", font=("Arial", 12),
                                   bg="#0f4d7d", fg="white")
        self.lbl_clock.pack(side=tk.RIGHT, padx=20)

        # Side menu
        side_menu = tk.Frame(self.root, bg="#1a1a2e", width=200)
        side_menu.pack(side=tk.LEFT, fill=tk.Y)
        side_menu.pack_propagate(False)

        tk.Label(side_menu, text="MENU", font=("Arial", 14, "bold"),
                 bg="#1a1a2e", fg="white", pady=15).pack(fill=tk.X)

        menu_items = [
            ("Category",  self.category),
            ("Employee",  self.employee),
            ("Product",   self.product),
            ("Sales",     self.sales),
            ("Supplier",  self.supplier),
            ("Billing",   self._open_billing),
        ]
        for text, cmd in menu_items:
            tk.Button(side_menu, text=text, command=cmd,
                      bg="#16213e", fg="white", font=("Arial", 12),
                      bd=0, pady=10, activebackground="#0f4d7d",
                      activeforeground="white", cursor="hand2").pack(fill=tk.X, pady=2)

        # Main content area
        content_frame = tk.Frame(self.root, bg="#f0f0f0")
        content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20, pady=20)

        tk.Label(content_frame, text="Dashboard", font=("Arial", 18, "bold"),
                 bg="#f0f0f0").pack(anchor=tk.W)

        stats_frame = tk.Frame(content_frame, bg="#f0f0f0")
        stats_frame.pack(fill=tk.X, pady=10)

        self.lbl_category = self._stat_card(stats_frame, "Categories", "0", "#e74c3c")
        self.lbl_employee = self._stat_card(stats_frame, "Employees",  "0", "#3498db")
        self.lbl_product  = self._stat_card(stats_frame, "Products",   "0", "#2ecc71")
        self.lbl_sales    = self._stat_card(stats_frame, "Sales",      "0", "#f39c12")
        self.lbl_supplier = self._stat_card(stats_frame, "Suppliers",  "0", "#9b59b6")

    def _stat_card(self, parent, title, value, color):
        card = tk.Frame(parent, bg=color, bd=2, relief=tk.RIDGE, width=150, height=100)
        card.pack(side=tk.LEFT, padx=10, pady=10)
        card.pack_propagate(False)
        tk.Label(card, text=title, font=("Arial", 12, "bold"),
                 bg=color, fg="white").pack(pady=5)
        lbl = tk.Label(card, text=value, font=("Arial", 20, "bold"),
                       bg=color, fg="white")
        lbl.pack()
        return lbl

    def update_content(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.config(text=now)

        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM category");  self.lbl_category.config(text=str(c.fetchone()[0]))
            c.execute("SELECT COUNT(*) FROM employee");  self.lbl_employee.config(text=str(c.fetchone()[0]))
            c.execute("SELECT COUNT(*) FROM product");   self.lbl_product.config(text=str(c.fetchone()[0]))
            c.execute("SELECT COUNT(*) FROM sales");     self.lbl_sales.config(text=str(c.fetchone()[0]))
            c.execute("SELECT COUNT(*) FROM supplier");  self.lbl_supplier.config(text=str(c.fetchone()[0]))
            conn.close()
        except Exception:
            pass

        self.root.after(1000, self.update_content)

    def category(self):
        self.new_obj = categoryClass(self.root)

    def employee(self):
        self.new_obj = employeeClass(self.root)

    def product(self):
        self.new_obj = productClass(self.root)

    def sales(self):
        self.new_obj = salesClass(self.root)

    def supplier(self):
        self.new_obj = supplierClass(self.root)

    def _open_billing(self):
        self.new_obj = billClass(self.root)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app  = IMS(root)
    root.mainloop()