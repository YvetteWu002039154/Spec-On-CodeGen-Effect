import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import random
import sqlite3
import os

# Database setup
def get_connection():
    conn = sqlite3.connect("ims.db")
    return conn

def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS category (
        cat_id TEXT PRIMARY KEY,
        name TEXT NOT NULL
    )""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS supplier (
        sup_invoice TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        contact TEXT,
        desc TEXT
    )""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS employee (
        emp_id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        gender TEXT,
        contact TEXT,
        dob TEXT,
        doj TEXT,
        address TEXT,
        salary TEXT,
        utype TEXT,
        password TEXT
    )""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS product (
        pid TEXT PRIMARY KEY,
        name TEXT,
        price TEXT,
        qty TEXT,
        status TEXT,
        cat TEXT,
        sup TEXT
    )""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS sales (
        invoice TEXT PRIMARY KEY,
        bill_data TEXT,
        date TEXT
    )""")
    
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# category.py
# ─────────────────────────────────────────────
class categoryClass:
    def __init__(self, root):
        self.root = root
        self.var_cat_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.im1 = None
        self.im2 = None
        self.lbl_im1 = None
        self.lbl_im2 = None
        self.CategoryTable = None
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

        frame = tk.Frame(self.root, bg="white")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left form
        left = tk.LabelFrame(frame, text="Category Details", bg="white",
                             font=("Arial", 12, "bold"))
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)

        tk.Label(left, text="Category ID", bg="white").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(left, textvariable=self.var_cat_id).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(left, text="Category Name", bg="white").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(left, textvariable=self.var_name).grid(row=1, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(left, bg="white")
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="Add", width=10, bg="#4a90d9", fg="white",
                  command=self.add).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Delete", width=10, bg="#e74c3c", fg="white",
                  command=self.delete).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Clear", width=10, bg="#95a5a6", fg="white",
                  command=self.clear).grid(row=0, column=2, padx=5)

        self.lbl_im1 = tk.Label(left, bg="white", text="[Image 1]")
        self.lbl_im1.grid(row=3, column=0, padx=5, pady=5)
        self.lbl_im2 = tk.Label(left, bg="white", text="[Image 2]")
        self.lbl_im2.grid(row=3, column=1, padx=5, pady=5)

        # Right table
        right = tk.LabelFrame(frame, text="Category List", bg="white",
                              font=("Arial", 12, "bold"))
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        scroll_y = tk.Scrollbar(right, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(right, orient=tk.HORIZONTAL)

        self.CategoryTable = ttk.Treeview(right,
                                          columns=("cat_id", "name"),
                                          yscrollcommand=scroll_y.set,
                                          xscrollcommand=scroll_x.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.config(command=self.CategoryTable.yview)
        scroll_x.config(command=self.CategoryTable.xview)

        self.CategoryTable.heading("cat_id", text="Category ID")
        self.CategoryTable.heading("name", text="Name")
        self.CategoryTable["show"] = "headings"
        self.CategoryTable.pack(fill=tk.BOTH, expand=True)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)

    def add(self):
        if self.var_cat_id.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "All fields are required", parent=self.root)
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO category VALUES (?, ?)",
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
            cursor = conn.cursor()
            cursor.execute("DELETE FROM category WHERE cat_id=?", (self.var_cat_id.get(),))
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
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM category")
        rows = cursor.fetchall()
        conn.close()
        self.CategoryTable.delete(*self.CategoryTable.get_children())
        for row in rows:
            self.CategoryTable.insert("", tk.END, values=row)


# ─────────────────────────────────────────────
# supplier.py
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
        self.root.geometry("1100x600")
        self.root.resizable(False, False)

        title = tk.Label(self.root, text="Supplier Management",
                         font=("Arial", 20, "bold"), bg="#4a90d9", fg="white", pady=10)
        title.pack(fill=tk.X)

        frame = tk.Frame(self.root, bg="white")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.LabelFrame(frame, text="Supplier Details", bg="white",
                             font=("Arial", 12, "bold"))
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)

        fields = [("Invoice No", self.var_sup_invoice),
                  ("Name", self.var_name),
                  ("Contact", self.var_contact)]

        for i, (label, var) in enumerate(fields):
            tk.Label(left, text=label, bg="white").grid(row=i, column=0, padx=5, pady=5, sticky="w")
            tk.Entry(left, textvariable=var).grid(row=i, column=1, padx=5, pady=5)

        tk.Label(left, text="Description", bg="white").grid(row=3, column=0, padx=5, pady=5, sticky="nw")
        self.txt_desc = tk.Text(left, width=25, height=5)
        self.txt_desc.grid(row=3, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(left, bg="white")
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="Add", width=8, bg="#4a90d9", fg="white",
                  command=self.add).grid(row=0, column=0, padx=3)
        tk.Button(btn_frame, text="Update", width=8, bg="#27ae60", fg="white",
                  command=self.update).grid(row=0, column=1, padx=3)
        tk.Button(btn_frame, text="Delete", width=8, bg="#e74c3c", fg="white",
                  command=self.delete).grid(row=0, column=2, padx=3)
        tk.Button(btn_frame, text="Clear", width=8, bg="#95a5a6", fg="white",
                  command=self.clear).grid(row=0, column=3, padx=3)

        right = tk.LabelFrame(frame, text="Supplier List", bg="white",
                              font=("Arial", 12, "bold"))
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        search_frame = tk.Frame(right, bg="white")
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(search_frame, text="Search By:", bg="white").pack(side=tk.LEFT)
        search_combo = ttk.Combobox(search_frame, textvariable=self.var_searchby,
                                    values=["Invoice No", "Name", "Contact"], width=12)
        search_combo.pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", bg="#4a90d9", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All", bg="#27ae60", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=5)

        scroll_y = tk.Scrollbar(right, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(right, orient=tk.HORIZONTAL)

        self.SupplierTable = ttk.Treeview(right,
                                          columns=("invoice", "name", "contact", "desc"),
                                          yscrollcommand=scroll_y.set,
                                          xscrollcommand=scroll_x.set)
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

    def add(self):
        if self.var_sup_invoice.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "Invoice and Name are required", parent=self.root)
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO supplier VALUES (?, ?, ?, ?)",
                           (self.var_sup_invoice.get(), self.var_name.get(),
                            self.var_contact.get(), self.txt_desc.get("1.0", tk.END).strip()))
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
            cursor = conn.cursor()
            cursor.execute("UPDATE supplier SET name=?, contact=?, desc=? WHERE sup_invoice=?",
                           (self.var_name.get(), self.var_contact.get(),
                            self.txt_desc.get("1.0", tk.END).strip(),
                            self.var_sup_invoice.get()))
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
            cursor = conn.cursor()
            cursor.execute("DELETE FROM supplier WHERE sup_invoice=?", (self.var_sup_invoice.get(),))
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
        if self.txt_desc:
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
            messagebox.showerror("Error", "Select search criteria and enter search text", parent=self.root)
            return
        col_map = {"Invoice No": "sup_invoice", "Name": "name", "Contact": "contact"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM supplier WHERE {col} LIKE ?",
                       (f"%{self.var_searchtxt.get()}%",))
        rows = cursor.fetchall()
        conn.close()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert("", tk.END, values=row)

    def show(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM supplier")
        rows = cursor.fetchall()
        conn.close()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert("", tk.END, values=row)


# ─────────────────────────────────────────────
# employee.py
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
        self.root.geometry("1200x650")
        self.root.resizable(False, False)

        title = tk.Label(self.root, text="Employee Management",
                         font=("Arial", 20, "bold"), bg="#4a90d9", fg="white", pady=10)
        title.pack(fill=tk.X)

        frame = tk.Frame(self.root, bg="white")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.LabelFrame(frame, text="Employee Details", bg="white",
                             font=("Arial", 12, "bold"))
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)

        fields = [
            ("Employee ID", self.var_emp_id, False),
            ("Name", self.var_name, False),
            ("Email", self.var_email, False),
            ("Contact", self.var_contact, False),
            ("DOB (YYYY-MM-DD)", self.var_dob, False),
            ("DOJ (YYYY-MM-DD)", self.var_doj, False),
            ("Salary", self.var_salary, False),
            ("Password", self.var_pass, True),
        ]

        for i, (label, var, is_pass) in enumerate(fields):
            tk.Label(left, text=label, bg="white").grid(row=i, column=0, padx=5, pady=3, sticky="w")
            show = "*" if is_pass else ""
            tk.Entry(left, textvariable=var, show=show).grid(row=i, column=1, padx=5, pady=3)

        tk.Label(left, text="Gender", bg="white").grid(row=8, column=0, padx=5, pady=3, sticky="w")
        ttk.Combobox(left, textvariable=self.var_gender,
                     values=["Male", "Female", "Other"], width=17).grid(row=8, column=1, padx=5, pady=3)

        tk.Label(left, text="User Type", bg="white").grid(row=9, column=0, padx=5, pady=3, sticky="w")
        ttk.Combobox(left, textvariable=self.var_utype,
                     values=["Admin", "Employee"], width=17).grid(row=9, column=1, padx=5, pady=3)

        tk.Label(left, text="Address", bg="white").grid(row=10, column=0, padx=5, pady=3, sticky="nw")
        self.txt_address = tk.Text(left, width=20, height=4)
        self.txt_address.grid(row=10, column=1, padx=5, pady=3)

        btn_frame = tk.Frame(left, bg="white")
        btn_frame.grid(row=11, column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="Add", width=8, bg="#4a90d9", fg="white",
                  command=self.add).grid(row=0, column=0, padx=3)
        tk.Button(btn_frame, text="Update", width=8, bg="#27ae60", fg="white",
                  command=self.update).grid(row=0, column=1, padx=3)
        tk.Button(btn_frame, text="Delete", width=8, bg="#e74c3c", fg="white",
                  command=self.delete).grid(row=0, column=2, padx=3)
        tk.Button(btn_frame, text="Clear", width=8, bg="#95a5a6", fg="white",
                  command=self.clear).grid(row=0, column=3, padx=3)

        right = tk.LabelFrame(frame, text="Employee List", bg="white",
                              font=("Arial", 12, "bold"))
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        search_frame = tk.Frame(right, bg="white")
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(search_frame, text="Search By:", bg="white").pack(side=tk.LEFT)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Employee ID", "Name", "Email", "Contact"], width=12).pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", bg="#4a90d9", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All", bg="#27ae60", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=5)

        cols = ("emp_id", "name", "email", "gender", "contact", "dob", "doj", "salary", "utype")
        scroll_y = tk.Scrollbar(right, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(right, orient=tk.HORIZONTAL)

        self.EmployeeTable = ttk.Treeview(right, columns=cols,
                                          yscrollcommand=scroll_y.set,
                                          xscrollcommand=scroll_x.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.config(command=self.EmployeeTable.yview)
        scroll_x.config(command=self.EmployeeTable.xview)

        headings = ["Emp ID", "Name", "Email", "Gender", "Contact", "DOB", "DOJ", "Salary", "User Type"]
        for col, heading in zip(cols, headings):
            self.EmployeeTable.heading(col, text=heading)
            self.EmployeeTable.column(col, width=90)
        self.EmployeeTable["show"] = "headings"
        self.EmployeeTable.pack(fill=tk.BOTH, expand=True)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)

    def add(self):
        if self.var_emp_id.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "Employee ID and Name are required", parent=self.root)
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO employee VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (self.var_emp_id.get(), self.var_name.get(), self.var_email.get(),
                            self.var_gender.get(), self.var_contact.get(), self.var_dob.get(),
                            self.var_doj.get(), self.txt_address.get("1.0", tk.END).strip(),
                            self.var_salary.get(), self.var_utype.get(), self.var_pass.get()))
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
            cursor = conn.cursor()
            cursor.execute("""UPDATE employee SET name=?, email=?, gender=?, contact=?,
                              dob=?, doj=?, address=?, salary=?, utype=?, password=?
                              WHERE emp_id=?""",
                           (self.var_name.get(), self.var_email.get(), self.var_gender.get(),
                            self.var_contact.get(), self.var_dob.get(), self.var_doj.get(),
                            self.txt_address.get("1.0", tk.END).strip(), self.var_salary.get(),
                            self.var_utype.get(), self.var_pass.get(), self.var_emp_id.get()))
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
            cursor = conn.cursor()
            cursor.execute("DELETE FROM employee WHERE emp_id=?", (self.var_emp_id.get(),))
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
        if self.txt_address:
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
            self.var_salary.set(row[7])
            self.var_utype.set(row[8])

    def search(self):
        if self.var_searchby.get() == "" or self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Select search criteria and enter search text", parent=self.root)
            return
        col_map = {"Employee ID": "emp_id", "Name": "name", "Email": "email", "Contact": "contact"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT emp_id, name, email, gender, contact, dob, doj, salary, utype FROM employee WHERE {col} LIKE ?",
                       (f"%{self.var_searchtxt.get()}%",))
        rows = cursor.fetchall()
        conn.close()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for row in rows:
            self.EmployeeTable.insert("", tk.END, values=row)

    def show(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT emp_id, name, email, gender, contact, dob, doj, salary, utype FROM employee")
        rows = cursor.fetchall()
        conn.close()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for row in rows:
            self.EmployeeTable.insert("", tk.END, values=row)


# ─────────────────────────────────────────────
# product.py
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
        self.root.geometry("1200x600")
        self.root.resizable(False, False)

        title = tk.Label(self.root, text="Product Management",
                         font=("Arial", 20, "bold"), bg="#4a90d9", fg="white", pady=10)
        title.pack(fill=tk.X)

        frame = tk.Frame(self.root, bg="white")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.LabelFrame(frame, text="Product Details", bg="white",
                             font=("Arial", 12, "bold"))
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)

        tk.Label(left, text="Product ID", bg="white").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(left, textvariable=self.var_pid).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(left, text="Name", bg="white").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(left, textvariable=self.var_name).grid(row=1, column=1, padx=5, pady=5)

        tk.Label(left, text="Price", bg="white").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(left, textvariable=self.var_price).grid(row=2, column=1, padx=5, pady=5)

        tk.Label(left, text="Quantity", bg="white").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        tk.Entry(left, textvariable=self.var_qty).grid(row=3, column=1, padx=5, pady=5)

        tk.Label(left, text="Status", bg="white").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.status_combo = ttk.Combobox(left, textvariable=self.var_status,
                                         values=["Active", "Inactive"], width=17)
        self.status_combo.grid(row=4, column=1, padx=5, pady=5)

        tk.Label(left, text="Category", bg="white").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.cat_combo = ttk.Combobox(left, textvariable=self.var_cat, width=17)
        self.cat_combo.grid(row=5, column=1, padx=5, pady=5)

        tk.Label(left, text="Supplier", bg="white").grid(row=6, column=0, padx=5, pady=5, sticky="w")
        self.sup_combo = ttk.Combobox(left, textvariable=self.var_sup, width=17)
        self.sup_combo.grid(row=6, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(left, bg="white")
        btn_frame.grid(row=7, column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="Add", width=8, bg="#4a90d9", fg="white",
                  command=self.add).grid(row=0, column=0, padx=3)
        tk.Button(btn_frame, text="Update", width=8, bg="#27ae60", fg="white",
                  command=self.update).grid(row=0, column=1, padx=3)
        tk.Button(btn_frame, text="Delete", width=8, bg="#e74c3c", fg="white",
                  command=self.delete).grid(row=0, column=2, padx=3)
        tk.Button(btn_frame, text="Clear", width=8, bg="#95a5a6", fg="white",
                  command=self.clear).grid(row=0, column=3, padx=3)

        right = tk.LabelFrame(frame, text="Product List", bg="white",
                              font=("Arial", 12, "bold"))
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        search_frame = tk.Frame(right, bg="white")
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(search_frame, text="Search By:", bg="white").pack(side=tk.LEFT)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Product ID", "Name", "Status", "Category", "Supplier"],
                     width=12).pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", bg="#4a90d9", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All", bg="#27ae60", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=5)

        cols = ("pid", "name", "price", "qty", "status", "cat", "sup")
        scroll_y = tk.Scrollbar(right, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(right, orient=tk.HORIZONTAL)

        self.ProductTable = ttk.Treeview(right, columns=cols,
                                         yscrollcommand=scroll_y.set,
                                         xscrollcommand=scroll_x.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.config(command=self.ProductTable.yview)
        scroll_x.config(command=self.ProductTable.xview)

        headings = ["Product ID", "Name", "Price", "Qty", "Status", "Category", "Supplier"]
        for col, heading in zip(cols, headings):
            self.ProductTable.heading(col, text=heading)
            self.ProductTable.column(col, width=100)
        self.ProductTable["show"] = "headings"
        self.ProductTable.pack(fill=tk.BOTH, expand=True)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)

    def fetch_cat_sup(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM category")
        self.cat_list = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT name FROM supplier")
        self.sup_list = [row[0] for row in cursor.fetchall()]
        conn.close()
        self.cat_combo["values"] = self.cat_list
        self.sup_combo["values"] = self.sup_list

    def add(self):
        if self.var_pid.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "Product ID and Name are required", parent=self.root)
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO product VALUES (?, ?, ?, ?, ?, ?, ?)",
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
            cursor = conn.cursor()
            cursor.execute("""UPDATE product SET name=?, price=?, qty=?, status=?, cat=?, sup=?
                              WHERE pid=?""",
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
            cursor = conn.cursor()
            cursor.execute("DELETE FROM product WHERE pid=?", (self.var_pid.get(),))
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
            messagebox.showerror("Error", "Select search criteria and enter search text", parent=self.root)
            return
        col_map = {"Product ID": "pid", "Name": "name", "Status": "status",
                   "Category": "cat", "Supplier": "sup"}
        col = col_map.get(self.var_searchby.get(), "name")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM product WHERE {col} LIKE ?",
                       (f"%{self.var_searchtxt.get()}%",))
        rows = cursor.fetchall()
        conn.close()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for row in rows:
            self.ProductTable.insert("", tk.END, values=row)

    def show(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM product")
        rows = cursor.fetchall()
        conn.close()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for row in rows:
            self.ProductTable.insert("", tk.END, values=row)


# ─────────────────────────────────────────────
# sales.py
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
        self.root.geometry("1000x600")
        self.root.resizable(False, False)

        title = tk.Label(self.root, text="Sales Records",
                         font=("Arial", 20, "bold"), bg="#4a90d9", fg="white", pady=10)
        title.pack(fill=tk.X)

        frame = tk.Frame(self.root, bg="white")
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.LabelFrame(frame, text="Sales List", bg="white",
                             font=("Arial", 12, "bold"))
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)

        search_frame = tk.Frame(left, bg="white")
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(search_frame, text="Invoice:", bg="white").pack(side=tk.LEFT)
        tk.Entry(search_frame, textvariable=self.var_invoice, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", bg="#4a90d9", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All", bg="#27ae60", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Clear", bg="#95a5a6", fg="white",
                  command=self.clear).pack(side=tk.LEFT, padx=5)

        scroll_y = tk.Scrollbar(left, orient=tk.VERTICAL)
        self.Sales_List = tk.Listbox(left, yscrollcommand=scroll_y.set, width=30, height=25)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_y.config(command=self.Sales_List.yview)
        self.Sales_List.pack(fill=tk.BOTH, expand=True)
        self.Sales_List.bind("<ButtonRelease-1>", self.get_data)

        right = tk.LabelFrame(frame, text="Bill Details", bg="white",
                              font=("Arial", 12, "bold"))
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        scroll_y2 = tk.Scrollbar(right, orient=tk.VERTICAL)
        self.bill_area = tk.Text(right, yscrollcommand=scroll_y2.set, width=50, height=30,
                                 font=("Courier", 10))
        scroll_y2.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_y2.config(command=self.bill_area.yview)
        self.bill_area.pack(fill=tk.BOTH, expand=True)

    def show(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT invoice FROM sales")
        rows = cursor.fetchall()
        conn.close()
        self.blll_list = [row[0] for row in rows]
        self.Sales_List.delete(0, tk.END)
        for inv in self.blll_list:
            self.Sales_List.insert(tk.END, inv)

    def search(self):
        if self.var_invoice.get() == "":
            messagebox.showerror("Error", "Enter invoice number to search", parent=self.root)
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT invoice FROM sales WHERE invoice LIKE ?",
                       (f"%{self.var_invoice.get()}%",))
        rows = cursor.fetchall()
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
        cursor = conn.cursor()
        cursor.execute("SELECT bill_data FROM sales WHERE invoice=?", (invoice,))
        row = cursor.fetchone()
        conn.close()
        if row:
            self.bill_area.config(state=tk.NORMAL)
            self.bill_area.delete("1.0", tk.END)
            self.bill_area.insert(tk.END, row[0])

    def clear(self):
        self.var_invoice.set("")
        self.bill_area.delete("1.0", tk.END)
        self.show()


# ─────────────────────────────────────────────
# billing.py
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
        self.cart_list = []
        self.bill_amnt = 0
        self.discount = 5.0
        self.siscount = 0
        self.net_pay = 0
        self.chk_print = 0
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
        self.root.geometry("1400x700")
        self.root.resizable(False, False)

        title = tk.Label(self.root, text="Billing System",
                         font=("Arial", 20, "bold"), bg="#4a90d9", fg="white", pady=10)
        title.pack(fill=tk.X)

        self.lbl_clock = tk.Label(self.root, text="", font=("Arial", 12), bg="#4a90d9", fg="white")
        self.lbl_clock.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left: Product search
        left = tk.LabelFrame(main_frame, text="Products", bg="white", font=("Arial", 11, "bold"))
        left.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)

        search_frame = tk.Frame(left, bg="white")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="white").pack(side=tk.LEFT)
        tk.Entry(search_frame, textvariable=self.var_search, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", bg="#4a90d9", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=3)
        tk.Button(search_frame, text="Show All", bg="#27ae60", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=3)

        cols = ("pid", "name", "price", "qty", "status")
        scroll_y = tk.Scrollbar(left, orient=tk.VERTICAL)
        self.product_Table = ttk.Treeview(left, columns=cols,
                                          yscrollcommand=scroll_y.set, height=12)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_y.config(command=self.product_Table.yview)
        headings = ["PID", "Name", "Price", "Qty", "Status"]
        for col, heading in zip(cols, headings):
            self.product_Table.heading(col, text=heading)
            self.product_Table.column(col, width=80)
        self.product_Table["show"] = "headings"
        self.product_Table.pack(fill=tk.BOTH, expand=True)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)

        # Product detail
        detail_frame = tk.Frame(left, bg="white")
        detail_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(detail_frame, text="PID:", bg="white").grid(row=0, column=0, sticky="w")
        tk.Entry(detail_frame, textvariable=self.var_pid, width=10, state="readonly").grid(row=0, column=1, padx=3)
        tk.Label(detail_frame, text="Name:", bg="white").grid(row=0, column=2, sticky="w")
        tk.Entry(detail_frame, textvariable=self.var_pname, width=15, state="readonly").grid(row=0, column=3, padx=3)

        tk.Label(detail_frame, text="Price:", bg="white").grid(row=1, column=0, sticky="w")
        tk.Entry(detail_frame, textvariable=self.var_price, width=10, state="readonly").grid(row=1, column=1, padx=3)
        tk.Label(detail_frame, text="Qty:", bg="white").grid(row=1, column=2, sticky="w")
        tk.Entry(detail_frame, textvariable=self.var_qty, width=10).grid(row=1, column=3, padx=3)

        self.lbl_inStock = tk.Label(detail_frame, text="In Stock: 0", bg="white", fg="blue")
        self.lbl_inStock.grid(row=2, column=0, columnspan=2, sticky="w")

        tk.Button(detail_frame, text="Add to Cart", bg="#4a90d9", fg="white",
                  command=self.add_update_cart).grid(row=2, column=2, columnspan=2, padx=3, pady=3)

        # Middle: Cart
        mid = tk.LabelFrame(main_frame, text="Cart", bg="white", font=("Arial", 11, "bold"))
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.cartTitle = tk.Label(mid, text="Cart Items", bg="#4a90d9", fg="white",
                                  font=("Arial", 12, "bold"))
        self.cartTitle.pack(fill=tk.X)

        cart_cols = ("pid", "name", "price", "qty", "total")
        scroll_y2 = tk.Scrollbar(mid, orient=tk.VERTICAL)
        self.CartTable = ttk.Treeview(mid, columns=cart_cols,
                                      yscrollcommand=scroll_y2.set, height=12)
        scroll_y2.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_y2.config(command=self.CartTable.yview)
        cart_headings = ["PID", "Name", "Price", "Qty", "Total"]
        for col, heading in zip(cart_cols, cart_headings):
            self.CartTable.heading(col, text=heading)
            self.CartTable.column(col, width=80)
        self.CartTable["show"] = "headings"
        self.CartTable.pack(fill=tk.BOTH, expand=True)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        # Customer info
        cust_frame = tk.Frame(mid, bg="white")
        cust_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(cust_frame, text="Customer Name:", bg="white").grid(row=0, column=0, sticky="w")
        tk.Entry(cust_frame, textvariable=self.var_cname, width=15).grid(row=0, column=1, padx=3)
        tk.Label(cust_frame, text="Contact:", bg="white").grid(row=0, column=2, sticky="w")
        tk.Entry(cust_frame, textvariable=self.var_contact, width=12).grid(row=0, column=3, padx=3)

        # Amount info
        amt_frame = tk.Frame(mid, bg="white")
        amt_frame.pack(fill=tk.X, padx=5, pady=5)
        self.lbl_amnt = tk.Label(amt_frame, text="Total: $0.00", bg="white", font=("Arial", 11, "bold"))
        self.lbl_amnt.pack(side=tk.LEFT, padx=10)
        self.lbl_discount = tk.Label(amt_frame, text=f"Discount: {self.discount}%", bg="white")
        self.lbl_discount.pack(side=tk.LEFT, padx=10)
        self.lbl_net_pay = tk.Label(amt_frame, text="Net Pay: $0.00", bg="white",
                                    font=("Arial", 11, "bold"), fg="green")
        self.lbl_net_pay.pack(side=tk.LEFT, padx=10)

        btn_frame2 = tk.Frame(mid, bg="white")
        btn_frame2.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(btn_frame2, text="Generate Bill", bg="#4a90d9", fg="white",
                  command=self.generate_bill).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame2, text="Clear Cart", bg="#e74c3c", fg="white",
                  command=self.clear_cart).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame2, text="Clear All", bg="#95a5a6", fg="white",
                  command=self.clear_all).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame2, text="Print Bill", bg="#27ae60", fg="white",
                  command=self.print_bill).pack(side=tk.LEFT, padx=5)

        # Right: Bill area + Calculator
        right = tk.Frame(main_frame, bg="white")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)

        bill_frame = tk.LabelFrame(right, text="Bill Area", bg="white", font=("Arial", 11, "bold"))
        bill_frame.pack(fill=tk.BOTH, expand=True)

        scroll_y3 = tk.Scrollbar(bill_frame, orient=tk.VERTICAL)
        self.txt_bill_area = tk.Text(bill_frame, width=40, height=20,
                                     yscrollcommand=scroll_y3.set, font=("Courier", 9))
        scroll_y3.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_y3.config(command=self.txt_bill_area.yview)
        self.txt_bill_area.pack(fill=tk.BOTH, expand=True)

        # Calculator
        cal_frame = tk.LabelFrame(right, text="Calculator", bg="white", font=("Arial", 11, "bold"))
        cal_frame.pack(fill=tk.X, pady=5)

        self.txt_cal_input = tk.Entry(cal_frame, textvariable=self.var_cal_input,
                                      font=("Arial", 14), justify=tk.RIGHT)
        self.txt_cal_input.pack(fill=tk.X, padx=5, pady=5)

        cal_buttons = [
            ["7", "8", "9", "/"],
            ["4", "5", "6", "*"],
            ["1", "2", "3", "-"],
            ["0", ".", "=", "+"],
            ["C", "", "", ""],
        ]

        for row_data in cal_buttons:
            row_frame = tk.Frame(cal_frame, bg="white")
            row_frame.pack(fill=tk.X)
            for btn_text in row_data:
                if btn_text == "":
                    tk.Label(row_frame, text="", width=5, bg="white").pack(side=tk.LEFT, padx=2, pady=2)
                elif btn_text == "=":
                    tk.Button(row_frame, text=btn_text, width=5, bg="#4a90d9", fg="white",
                              command=self.perform_cal).pack(side=tk.LEFT, padx=2, pady=2)
                elif btn_text == "C":
                    tk.Button(row_frame, text=btn_text, width=5, bg="#e74c3c", fg="white",
                              command=self.clear_cal).pack(side=tk.LEFT, padx=2, pady=2)
                else:
                    tk.Button(row_frame, text=btn_text, width=5,
                              command=lambda t=btn_text: self.get_input(t)).pack(side=tk.LEFT, padx=2, pady=2)

    def update_date_time(self):
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self.update_date_time)

    def show(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT pid, name, price, qty, status FROM product WHERE status='Active'")
        rows = cursor.fetchall()
        conn.close()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", tk.END, values=row)

    def search(self):
        if self.var_search.get() == "":
            self.show()
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT pid, name, price, qty, status FROM product WHERE name LIKE ? OR pid LIKE ?",
                       (f"%{self.var_search.get()}%", f"%{self.var_search.get()}%"))
        rows = cursor.fetchall()
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
            messagebox.showerror("Error", "Select a product and enter quantity", parent=self.root)
            return
        try:
            qty = int(self.var_qty.get())
            price = float(self.var_price.get())
            stock = int(self.var_stock.get()) if self.var_stock.get() else 0
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
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity or price", parent=self.root)

    def show_cart(self):
        self.CartTable.delete(*self.CartTable.get_children())
        for item in self.cart_list:
            self.CartTable.insert("", tk.END, values=item)

    def bill_update(self):
        self.bill_amnt = sum(item[4] for item in self.cart_list)
        self.siscount = self.bill_amnt * self.discount / 100
        self.net_pay = self.bill_amnt - self.siscount
        self.lbl_amnt.config(text=f"Total: ${self.bill_amnt:.2f}")
        self.lbl_discount.config(text=f"Discount ({self.discount}%): ${self.siscount:.2f}")
        self.lbl_net_pay.config(text=f"Net Pay: ${self.net_pay:.2f}")

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty", parent=self.root)
            return
        if self.var_cname.get() == "":
            messagebox.showerror("Error", "Enter customer name", parent=self.root)
            return

        self.invoice = f"INV{random.randint(10000, 99999)}"
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        bill_text = "=" * 40 + "\n"
        bill_text += "     INVENTORY MANAGEMENT SYSTEM\n"
        bill_text += "=" * 40 + "\n"
        bill_text += f"Invoice: {self.invoice}\n"
        bill_text += f"Date: {now}\n"
        bill_text += f"Customer: {self.var_cname.get()}\n"
        bill_text += f"Contact: {self.var_contact.get()}\n"
        bill_text += "-" * 40 + "\n"
        bill_text += f"{'Item':<15}{'Qty':>5}{'Price':>8}{'Total':>10}\n"
        bill_text += "-" * 40 + "\n"

        for item in self.cart_list:
            bill_text += f"{str(item[1])[:14]:<15}{item[3]:>5}{item[2]:>8.2f}{item[4]:>10.2f}\n"

        bill_text += "=" * 40 + "\n"
        bill_text += f"{'Sub Total:':>25} ${self.bill_amnt:>10.2f}\n"
        bill_text += f"{'Discount:':>25} ${self.siscount:>10.2f}\n"
        bill_text += f"{'Net Pay:':>25} ${self.net_pay:>10.2f}\n"
        bill_text += "=" * 40 + "\n"
        bill_text += "     Thank you for your purchase!\n"
        bill_text += "=" * 40 + "\n"

        self.txt_bill_area.config(state=tk.NORMAL)
        self.txt_bill_area.delete("1.0", tk.END)
        self.txt_bill_area.insert(tk.END, bill_text)

        # Save to DB
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO sales VALUES (?, ?, ?)",
                           (self.invoice, bill_text, now))
            # Update stock
            for item in self.cart_list:
                cursor.execute("UPDATE product SET qty = qty - ? WHERE pid=?",
                               (item[3], item[0]))
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
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")
        self.var_cname.set("")
        self.var_contact.set("")
        self.var_search.set("")
        self.txt_bill_area.delete("1.0", tk.END)
        self.lbl_inStock.config(text="In Stock: 0")
        self.show()

    def print_bill(self):
        if self.txt_bill_area.get("1.0", tk.END).strip() == "":
            messagebox.showerror("Error", "Generate a bill first", parent=self.root)
            return
        messagebox.showinfo("Print", "Bill sent to printer (simulated)", parent=self.root)

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

    def bill_top(self):
        pass

    def bill_middle(self):
        pass

    def bill_bottom(self):
        pass


# ─────────────────────────────────────────────
# dashboard.py
# ─────────────────────────────────────────────
class IMS:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("1100x650")
        self.root.resizable(False, False)

        self.MenuLogo = None
        self.icon_side = None
        self.icon_title = None
        self.new_obj = None
        self.new_win = None

        self._build_ui()
        self.update_content()

    def _build_ui(self):
        # Top bar
        top_bar = tk.Frame(self.root, bg="#2c3e50", height=60)
        top_bar.pack(fill=tk.X)
        top_bar.pack_propagate(False)

        tk.Label(top_bar, text="Inventory Management System",
                 font=("Arial", 22, "bold"), bg="#2c3e50", fg="white").pack(side=tk.LEFT, padx=20)

        self.lbl_clock = tk.Label(top_bar, text="", font=("Arial", 12),
                                  bg="#2c3e50", fg="white")
        self.lbl_clock.pack(side=tk.RIGHT, padx=20)

        # Side bar
        side_bar = tk.Frame(self.root, bg="#34495e", width=200)
        side_bar.pack(side=tk.LEFT, fill=tk.Y)
        side_bar.pack_propagate(False)

        tk.Label(side_bar, text="MENU", font=("Arial", 14, "bold"),
                 bg="#34495e", fg="white", pady=15).pack(fill=tk.X)

        menu_items = [
            ("Category", self.category),
            ("Employee", self.employee),
            ("Product", self.product),
            ("Sales", self.sales),
            ("Supplier", self.supplier),
            ("Billing", self._open_billing),
        ]

        for text, cmd in menu_items:
            btn = tk.Button(side_bar, text=text, font=("Arial", 12),
                            bg="#34495e", fg="white", bd=0, pady=10,
                            activebackground="#4a90d9", activeforeground="white",
                            command=cmd, anchor="w", padx=20)
            btn.pack(fill=tk.X)

        # Main content area
        self.content_frame = tk.Frame(self.root, bg="#ecf0f1")
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Dashboard summary labels
        summary_frame = tk.Frame(self.content_frame, bg="#ecf0f1")
        summary_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        tk.Label(summary_frame, text="Dashboard",
                 font=("Arial", 20, "bold"), bg="#ecf0f1").pack(pady=10)

        cards_frame = tk.Frame(summary_frame, bg="#ecf0f1")
        cards_frame.pack(fill=tk.BOTH, expand=True)

        self.lbl_product = self._create_card(cards_frame, "Products", "0", "#3498db", 0, 0)
        self.lbl_category = self._create_card(cards_frame, "Categories", "0", "#2ecc71", 0, 1)
        self.lbl_employee = self._create_card(cards_frame, "Employees", "0", "#e74c3c", 0, 2)
        self.lbl_supplier = self._create_card(cards_frame, "Suppliers", "0", "#f39c12", 1, 0)
        self.lbl_sales = self._create_card(cards_frame, "Sales", "0", "#9b59b6", 1, 1)

        self._update_clock()

    def _create_card(self, parent, title, value, color, row, col):
        card = tk.Frame(parent, bg=color, width=200, height=120, relief=tk.RAISED, bd=2)
        card.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")
        card.pack_propagate(False)
        tk.Label(card, text=title, font=("Arial", 14, "bold"),
                 bg=color, fg="white").pack(pady=10)
        lbl = tk.Label(card, text=value, font=("Arial", 24, "bold"),
                       bg=color, fg="white")
        lbl.pack()
        return lbl

    def _update_clock(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.config(text=now)
        self.root.after(1000, self._update_clock)

    def update_content(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM product")
            self.lbl_product.config(text=str(cursor.fetchone()[0]))

            cursor.execute("SELECT COUNT(*) FROM category")
            self.lbl_category.config(text=str(cursor.fetchone()[0]))

            cursor.execute("SELECT COUNT(*) FROM employee")
            self.lbl_employee.config(text=str(cursor.fetchone()[0]))

            cursor.execute("SELECT COUNT(*) FROM supplier")
            self.lbl_supplier.config(text=str(cursor.fetchone()[0]))

            cursor.execute("SELECT COUNT(*) FROM sales")
            self.lbl_sales.config(text=str(cursor.fetchone()[0]))

            conn.close()
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

    def product(self):
        self._open_window("Product Management", productClass)

    def sales(self):
        self._open_window("Sales Records", salesClass)

    def supplier(self):
        self._open_window("Supplier Management", supplierClass)

    def _open_billing(self):
        self._open_window("Billing System", billClass)


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    initialize_db()
    root = tk.Tk()
    app = IMS(root)
    root.mainloop()