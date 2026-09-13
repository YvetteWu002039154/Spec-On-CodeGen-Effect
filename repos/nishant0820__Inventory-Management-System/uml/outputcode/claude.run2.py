import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime
import random
import sqlite3
import os

# Database setup
DB_NAME = "ims.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn

def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS category (
            cat_id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS supplier (
            sup_invoice TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            contact TEXT,
            desc TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee (
            emp_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            contact TEXT,
            email TEXT,
            gender TEXT,
            dob TEXT,
            doj TEXT,
            salary TEXT,
            utype TEXT,
            password TEXT,
            address TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product (
            pid TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            supplier TEXT,
            price TEXT,
            qty TEXT,
            status TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            invoice TEXT PRIMARY KEY,
            customer_name TEXT,
            contact TEXT,
            bill_data TEXT,
            net_pay TEXT,
            date TEXT
        )
    """)
    
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────
# category.py
# ─────────────────────────────────────────────
class categoryClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Category Management")
        self.root.geometry("900x500")
        self.root.config(bg="#f0f0f0")

        self.var_cat_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.im1 = None
        self.im2 = None

        self._build_ui()
        self.show()

    def _build_ui(self):
        # Title
        title = tk.Label(self.root, text="Category Management", font=("Arial", 18, "bold"),
                         bg="#2c3e50", fg="white", pady=10)
        title.pack(fill=tk.X)

        # Main frame
        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left frame - form
        left_frame = tk.LabelFrame(main_frame, text="Category Details", bg="#f0f0f0",
                                   font=("Arial", 12, "bold"))
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)

        tk.Label(left_frame, text="Category ID:", bg="#f0f0f0", font=("Arial", 11)).grid(
            row=0, column=0, padx=10, pady=8, sticky=tk.W)
        tk.Entry(left_frame, textvariable=self.var_cat_id, font=("Arial", 11), width=20).grid(
            row=0, column=1, padx=10, pady=8)

        tk.Label(left_frame, text="Category Name:", bg="#f0f0f0", font=("Arial", 11)).grid(
            row=1, column=0, padx=10, pady=8, sticky=tk.W)
        tk.Entry(left_frame, textvariable=self.var_name, font=("Arial", 11), width=20).grid(
            row=1, column=1, padx=10, pady=8)

        # Image labels
        self.lbl_im1 = tk.Label(left_frame, text="Image 1", bg="#f0f0f0", width=15, height=5,
                                relief=tk.SUNKEN)
        self.lbl_im1.grid(row=2, column=0, padx=10, pady=8)

        self.lbl_im2 = tk.Label(left_frame, text="Image 2", bg="#f0f0f0", width=15, height=5,
                                relief=tk.SUNKEN)
        self.lbl_im2.grid(row=2, column=1, padx=10, pady=8)

        # Buttons
        btn_frame = tk.Frame(left_frame, bg="#f0f0f0")
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="Add", command=self.add, bg="#27ae60", fg="white",
                  font=("Arial", 11), width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Delete", command=self.delete, bg="#e74c3c", fg="white",
                  font=("Arial", 11), width=8).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear, bg="#3498db", fg="white",
                  font=("Arial", 11), width=8).pack(side=tk.LEFT, padx=5)

        # Right frame - table
        right_frame = tk.LabelFrame(main_frame, text="Category List", bg="#f0f0f0",
                                    font=("Arial", 12, "bold"))
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        scroll_x = tk.Scrollbar(right_frame, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(right_frame, orient=tk.VERTICAL)

        self.CategoryTable = ttk.Treeview(right_frame,
                                          columns=("cat_id", "name"),
                                          xscrollcommand=scroll_x.set,
                                          yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.CategoryTable.xview)
        scroll_y.config(command=self.CategoryTable.yview)

        self.CategoryTable.heading("cat_id", text="Category ID")
        self.CategoryTable.heading("name", text="Category Name")
        self.CategoryTable["show"] = "headings"
        self.CategoryTable.column("cat_id", width=150)
        self.CategoryTable.column("name", width=200)
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
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

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
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

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
        self.root.title("Supplier Management")
        self.root.geometry("1000x550")
        self.root.config(bg="#f0f0f0")

        self.var_sup_invoice = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()

        self._build_ui()
        self.show()

    def _build_ui(self):
        title = tk.Label(self.root, text="Supplier Management", font=("Arial", 18, "bold"),
                         bg="#2c3e50", fg="white", pady=10)
        title.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left frame
        left_frame = tk.LabelFrame(main_frame, text="Supplier Details", bg="#f0f0f0",
                                   font=("Arial", 12, "bold"))
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)

        fields = [("Invoice No:", self.var_sup_invoice), ("Name:", self.var_name),
                  ("Contact:", self.var_contact)]
        for i, (label, var) in enumerate(fields):
            tk.Label(left_frame, text=label, bg="#f0f0f0", font=("Arial", 11)).grid(
                row=i, column=0, padx=10, pady=8, sticky=tk.W)
            tk.Entry(left_frame, textvariable=var, font=("Arial", 11), width=20).grid(
                row=i, column=1, padx=10, pady=8)

        tk.Label(left_frame, text="Description:", bg="#f0f0f0", font=("Arial", 11)).grid(
            row=3, column=0, padx=10, pady=8, sticky=tk.W)
        self.txt_desc = tk.Text(left_frame, font=("Arial", 11), width=20, height=4)
        self.txt_desc.grid(row=3, column=1, padx=10, pady=8)

        btn_frame = tk.Frame(left_frame, bg="#f0f0f0")
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)

        for text, cmd, color in [("Add", self.add, "#27ae60"), ("Update", self.update, "#f39c12"),
                                  ("Delete", self.delete, "#e74c3c"), ("Clear", self.clear, "#3498db")]:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 10), width=7).pack(side=tk.LEFT, padx=3)

        # Search frame
        search_frame = tk.Frame(left_frame, bg="#f0f0f0")
        search_frame.grid(row=5, column=0, columnspan=2, pady=5)

        tk.Label(search_frame, text="Search By:", bg="#f0f0f0", font=("Arial", 11)).pack(side=tk.LEFT)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Invoice No", "Name", "Contact"], width=10,
                     font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, font=("Arial", 10), width=12).pack(
            side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", command=self.search, bg="#8e44ad", fg="white",
                  font=("Arial", 10)).pack(side=tk.LEFT)

        # Right frame - table
        right_frame = tk.LabelFrame(main_frame, text="Supplier List", bg="#f0f0f0",
                                    font=("Arial", 12, "bold"))
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        scroll_x = tk.Scrollbar(right_frame, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(right_frame, orient=tk.VERTICAL)

        self.SupplierTable = ttk.Treeview(right_frame,
                                          columns=("inv", "name", "contact", "desc"),
                                          xscrollcommand=scroll_x.set,
                                          yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.SupplierTable.xview)
        scroll_y.config(command=self.SupplierTable.yview)

        self.SupplierTable.heading("inv", text="Invoice No")
        self.SupplierTable.heading("name", text="Name")
        self.SupplierTable.heading("contact", text="Contact")
        self.SupplierTable.heading("desc", text="Description")
        self.SupplierTable["show"] = "headings"
        for col, w in [("inv", 100), ("name", 150), ("contact", 100), ("desc", 200)]:
            self.SupplierTable.column(col, width=w)
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
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def update(self):
        if self.var_sup_invoice.get() == "":
            messagebox.showerror("Error", "Select a supplier to update", parent=self.root)
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE supplier SET name=?, contact=?, desc=? WHERE sup_invoice=?",
                           (self.var_name.get(), self.var_contact.get(),
                            self.txt_desc.get("1.0", tk.END).strip(), self.var_sup_invoice.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Supplier updated successfully", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

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
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

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
            messagebox.showerror("Error", "Select search criteria and enter search text",
                                 parent=self.root)
            return
        col_map = {"Invoice No": "sup_invoice", "Name": "name", "Contact": "contact"}
        col = col_map.get(self.var_searchby.get(), "name")
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM supplier WHERE {col} LIKE ?",
                           (f"%{self.var_searchtxt.get()}%",))
            rows = cursor.fetchall()
            conn.close()
            self.SupplierTable.delete(*self.SupplierTable.get_children())
            for row in rows:
                self.SupplierTable.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

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
        self.root.title("Employee Management")
        self.root.geometry("1100x600")
        self.root.config(bg="#f0f0f0")

        self.var_emp_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_gender = tk.StringVar()
        self.var_dob = tk.StringVar()
        self.var_doj = tk.StringVar()
        self.var_salary = tk.StringVar()
        self.var_utype = tk.StringVar()
        self.var_pass = tk.StringVar()
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()

        self._build_ui()
        self.show()

    def _build_ui(self):
        title = tk.Label(self.root, text="Employee Management", font=("Arial", 18, "bold"),
                         bg="#2c3e50", fg="white", pady=10)
        title.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = tk.LabelFrame(main_frame, text="Employee Details", bg="#f0f0f0",
                                   font=("Arial", 12, "bold"))
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)

        fields = [
            ("Employee ID:", self.var_emp_id, 0, 0),
            ("Name:", self.var_name, 1, 0),
            ("Contact:", self.var_contact, 2, 0),
            ("Email:", self.var_email, 3, 0),
            ("DOB:", self.var_dob, 0, 2),
            ("DOJ:", self.var_doj, 1, 2),
            ("Salary:", self.var_salary, 2, 2),
            ("Password:", self.var_pass, 3, 2),
        ]

        for label, var, row, col in fields:
            tk.Label(left_frame, text=label, bg="#f0f0f0", font=("Arial", 10)).grid(
                row=row, column=col, padx=5, pady=5, sticky=tk.W)
            tk.Entry(left_frame, textvariable=var, font=("Arial", 10), width=18).grid(
                row=row, column=col + 1, padx=5, pady=5)

        tk.Label(left_frame, text="Gender:", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=4, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Combobox(left_frame, textvariable=self.var_gender,
                     values=["Male", "Female", "Other"], width=16,
                     font=("Arial", 10)).grid(row=4, column=1, padx=5, pady=5)

        tk.Label(left_frame, text="User Type:", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=4, column=2, padx=5, pady=5, sticky=tk.W)
        ttk.Combobox(left_frame, textvariable=self.var_utype,
                     values=["Admin", "Employee"], width=16,
                     font=("Arial", 10)).grid(row=4, column=3, padx=5, pady=5)

        tk.Label(left_frame, text="Address:", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=5, column=0, padx=5, pady=5, sticky=tk.W)
        self.txt_address = tk.Text(left_frame, font=("Arial", 10), width=40, height=3)
        self.txt_address.grid(row=5, column=1, columnspan=3, padx=5, pady=5)

        btn_frame = tk.Frame(left_frame, bg="#f0f0f0")
        btn_frame.grid(row=6, column=0, columnspan=4, pady=10)

        for text, cmd, color in [("Add", self.add, "#27ae60"), ("Update", self.update, "#f39c12"),
                                  ("Delete", self.delete, "#e74c3c"), ("Clear", self.clear, "#3498db")]:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 10), width=7).pack(side=tk.LEFT, padx=3)

        search_frame = tk.Frame(left_frame, bg="#f0f0f0")
        search_frame.grid(row=7, column=0, columnspan=4, pady=5)

        tk.Label(search_frame, text="Search By:", bg="#f0f0f0", font=("Arial", 10)).pack(side=tk.LEFT)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Employee ID", "Name", "Contact", "Email"], width=12,
                     font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, font=("Arial", 10), width=15).pack(
            side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", command=self.search, bg="#8e44ad", fg="white",
                  font=("Arial", 10)).pack(side=tk.LEFT)

        # Right frame - table
        right_frame = tk.LabelFrame(main_frame, text="Employee List", bg="#f0f0f0",
                                    font=("Arial", 12, "bold"))
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        scroll_x = tk.Scrollbar(right_frame, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(right_frame, orient=tk.VERTICAL)

        cols = ("emp_id", "name", "contact", "email", "gender", "dob", "doj", "salary", "utype")
        self.EmployeeTable = ttk.Treeview(right_frame, columns=cols,
                                          xscrollcommand=scroll_x.set,
                                          yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.EmployeeTable.xview)
        scroll_y.config(command=self.EmployeeTable.yview)

        headers = ["Emp ID", "Name", "Contact", "Email", "Gender", "DOB", "DOJ", "Salary", "Type"]
        for col, header in zip(cols, headers):
            self.EmployeeTable.heading(col, text=header)
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
                           (self.var_emp_id.get(), self.var_name.get(), self.var_contact.get(),
                            self.var_email.get(), self.var_gender.get(), self.var_dob.get(),
                            self.var_doj.get(), self.var_salary.get(), self.var_utype.get(),
                            self.var_pass.get(), self.txt_address.get("1.0", tk.END).strip()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee added successfully", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def update(self):
        if self.var_emp_id.get() == "":
            messagebox.showerror("Error", "Select an employee to update", parent=self.root)
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""UPDATE employee SET name=?, contact=?, email=?, gender=?, dob=?,
                           doj=?, salary=?, utype=?, password=?, address=? WHERE emp_id=?""",
                           (self.var_name.get(), self.var_contact.get(), self.var_email.get(),
                            self.var_gender.get(), self.var_dob.get(), self.var_doj.get(),
                            self.var_salary.get(), self.var_utype.get(), self.var_pass.get(),
                            self.txt_address.get("1.0", tk.END).strip(), self.var_emp_id.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Employee updated successfully", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

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
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def clear(self):
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.var_email.set("")
        self.var_gender.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_salary.set("")
        self.var_utype.set("")
        self.var_pass.set("")
        self.txt_address.delete("1.0", tk.END)

    def get_data(self, ev):
        selected = self.EmployeeTable.focus()
        content = self.EmployeeTable.item(selected)
        row = content["values"]
        if row:
            self.var_emp_id.set(row[0])
            self.var_name.set(row[1])
            self.var_contact.set(row[2])
            self.var_email.set(row[3])
            self.var_gender.set(row[4])
            self.var_dob.set(row[5])
            self.var_doj.set(row[6])
            self.var_salary.set(row[7])
            self.var_utype.set(row[8])

    def search(self):
        if self.var_searchby.get() == "" or self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Select search criteria and enter search text",
                                 parent=self.root)
            return
        col_map = {"Employee ID": "emp_id", "Name": "name", "Contact": "contact", "Email": "email"}
        col = col_map.get(self.var_searchby.get(), "name")
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM employee WHERE {col} LIKE ?",
                           (f"%{self.var_searchtxt.get()}%",))
            rows = cursor.fetchall()
            conn.close()
            self.EmployeeTable.delete(*self.EmployeeTable.get_children())
            for row in rows:
                self.EmployeeTable.insert("", tk.END, values=row[:9])
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def show(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT emp_id, name, contact, email, gender, dob, doj, salary, utype FROM employee")
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
        self.root.title("Product Management")
        self.root.geometry("1100x600")
        self.root.config(bg="#f0f0f0")

        self.var_pid = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_cat = tk.StringVar()
        self.var_sup = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_status = tk.StringVar()
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()
        self.cat_list = []
        self.sup_list = []

        self._build_ui()
        self.fetch_cat_sup()
        self.show()

    def _build_ui(self):
        title = tk.Label(self.root, text="Product Management", font=("Arial", 18, "bold"),
                         bg="#2c3e50", fg="white", pady=10)
        title.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = tk.LabelFrame(main_frame, text="Product Details", bg="#f0f0f0",
                                   font=("Arial", 12, "bold"))
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)

        tk.Label(left_frame, text="Product ID:", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=0, column=0, padx=5, pady=5, sticky=tk.W)
        tk.Entry(left_frame, textvariable=self.var_pid, font=("Arial", 10), width=18).grid(
            row=0, column=1, padx=5, pady=5)

        tk.Label(left_frame, text="Product Name:", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=1, column=0, padx=5, pady=5, sticky=tk.W)
        tk.Entry(left_frame, textvariable=self.var_name, font=("Arial", 10), width=18).grid(
            row=1, column=1, padx=5, pady=5)

        tk.Label(left_frame, text="Category:", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.cat_combo = ttk.Combobox(left_frame, textvariable=self.var_cat,
                                      values=self.cat_list, width=16, font=("Arial", 10))
        self.cat_combo.grid(row=2, column=1, padx=5, pady=5)

        tk.Label(left_frame, text="Supplier:", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.sup_combo = ttk.Combobox(left_frame, textvariable=self.var_sup,
                                      values=self.sup_list, width=16, font=("Arial", 10))
        self.sup_combo.grid(row=3, column=1, padx=5, pady=5)

        tk.Label(left_frame, text="Price:", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=4, column=0, padx=5, pady=5, sticky=tk.W)
        tk.Entry(left_frame, textvariable=self.var_price, font=("Arial", 10), width=18).grid(
            row=4, column=1, padx=5, pady=5)

        tk.Label(left_frame, text="Quantity:", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=5, column=0, padx=5, pady=5, sticky=tk.W)
        tk.Entry(left_frame, textvariable=self.var_qty, font=("Arial", 10), width=18).grid(
            row=5, column=1, padx=5, pady=5)

        tk.Label(left_frame, text="Status:", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=6, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Combobox(left_frame, textvariable=self.var_status,
                     values=["Active", "Inactive"], width=16,
                     font=("Arial", 10)).grid(row=6, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(left_frame, bg="#f0f0f0")
        btn_frame.grid(row=7, column=0, columnspan=2, pady=10)

        for text, cmd, color in [("Add", self.add, "#27ae60"), ("Update", self.update, "#f39c12"),
                                  ("Delete", self.delete, "#e74c3c"), ("Clear", self.clear, "#3498db")]:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 10), width=7).pack(side=tk.LEFT, padx=3)

        search_frame = tk.Frame(left_frame, bg="#f0f0f0")
        search_frame.grid(row=8, column=0, columnspan=2, pady=5)

        tk.Label(search_frame, text="Search By:", bg="#f0f0f0", font=("Arial", 10)).pack(side=tk.LEFT)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Product ID", "Name", "Category", "Supplier"], width=10,
                     font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, font=("Arial", 10), width=12).pack(
            side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", command=self.search, bg="#8e44ad", fg="white",
                  font=("Arial", 10)).pack(side=tk.LEFT)

        # Right frame - table
        right_frame = tk.LabelFrame(main_frame, text="Product List", bg="#f0f0f0",
                                    font=("Arial", 12, "bold"))
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        scroll_x = tk.Scrollbar(right_frame, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(right_frame, orient=tk.VERTICAL)

        cols = ("pid", "name", "category", "supplier", "price", "qty", "status")
        self.ProductTable = ttk.Treeview(right_frame, columns=cols,
                                         xscrollcommand=scroll_x.set,
                                         yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.ProductTable.xview)
        scroll_y.config(command=self.ProductTable.yview)

        headers = ["Product ID", "Name", "Category", "Supplier", "Price", "Qty", "Status"]
        for col, header in zip(cols, headers):
            self.ProductTable.heading(col, text=header)
            self.ProductTable.column(col, width=100)
        self.ProductTable["show"] = "headings"
        self.ProductTable.pack(fill=tk.BOTH, expand=True)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)

    def fetch_cat_sup(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM category")
            self.cat_list = [row[0] for row in cursor.fetchall()]
            cursor.execute("SELECT name FROM supplier")
            self.sup_list = [row[0] for row in cursor.fetchall()]
            conn.close()
            self.cat_combo["values"] = self.cat_list
            self.sup_combo["values"] = self.sup_list
        except Exception as e:
            pass

    def add(self):
        if self.var_pid.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "Product ID and Name are required", parent=self.root)
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO product VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (self.var_pid.get(), self.var_name.get(), self.var_cat.get(),
                            self.var_sup.get(), self.var_price.get(), self.var_qty.get(),
                            self.var_status.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product added successfully", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def update(self):
        if self.var_pid.get() == "":
            messagebox.showerror("Error", "Select a product to update", parent=self.root)
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""UPDATE product SET name=?, category=?, supplier=?, price=?,
                           qty=?, status=? WHERE pid=?""",
                           (self.var_name.get(), self.var_cat.get(), self.var_sup.get(),
                            self.var_price.get(), self.var_qty.get(), self.var_status.get(),
                            self.var_pid.get()))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Product updated successfully", parent=self.root)
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

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
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def clear(self):
        self.var_pid.set("")
        self.var_name.set("")
        self.var_cat.set("")
        self.var_sup.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("")

    def get_data(self, ev):
        selected = self.ProductTable.focus()
        content = self.ProductTable.item(selected)
        row = content["values"]
        if row:
            self.var_pid.set(row[0])
            self.var_name.set(row[1])
            self.var_cat.set(row[2])
            self.var_sup.set(row[3])
            self.var_price.set(row[4])
            self.var_qty.set(row[5])
            self.var_status.set(row[6])

    def search(self):
        if self.var_searchby.get() == "" or self.var_searchtxt.get() == "":
            messagebox.showerror("Error", "Select search criteria and enter search text",
                                 parent=self.root)
            return
        col_map = {"Product ID": "pid", "Name": "name", "Category": "category",
                   "Supplier": "supplier"}
        col = col_map.get(self.var_searchby.get(), "name")
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM product WHERE {col} LIKE ?",
                           (f"%{self.var_searchtxt.get()}%",))
            rows = cursor.fetchall()
            conn.close()
            self.ProductTable.delete(*self.ProductTable.get_children())
            for row in rows:
                self.ProductTable.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

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
        self.root.title("Sales Records")
        self.root.geometry("1000x550")
        self.root.config(bg="#f0f0f0")

        self.var_invoice = tk.StringVar()
        self.blll_list = []
        self.bill_photo = None

        self._build_ui()
        self.show()

    def _build_ui(self):
        title = tk.Label(self.root, text="Sales Records", font=("Arial", 18, "bold"),
                         bg="#2c3e50", fg="white", pady=10)
        title.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left frame - sales list
        left_frame = tk.LabelFrame(main_frame, text="Sales List", bg="#f0f0f0",
                                   font=("Arial", 12, "bold"))
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)

        # Search
        search_frame = tk.Frame(left_frame, bg="#f0f0f0")
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(search_frame, text="Invoice:", bg="#f0f0f0", font=("Arial", 10)).pack(side=tk.LEFT)
        tk.Entry(search_frame, textvariable=self.var_invoice, font=("Arial", 10), width=15).pack(
            side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", command=self.search, bg="#8e44ad", fg="white",
                  font=("Arial", 10)).pack(side=tk.LEFT)
        tk.Button(search_frame, text="Clear", command=self.clear, bg="#3498db", fg="white",
                  font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        scroll_y = tk.Scrollbar(left_frame, orient=tk.VERTICAL)
        self.Sales_List = tk.Listbox(left_frame, font=("Arial", 11), width=30,
                                     yscrollcommand=scroll_y.set, selectbackground="#3498db")
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_y.config(command=self.Sales_List.yview)
        self.Sales_List.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.Sales_List.bind("<ButtonRelease-1>", self.get_data)

        # Right frame - bill area
        right_frame = tk.LabelFrame(main_frame, text="Bill Details", bg="#f0f0f0",
                                    font=("Arial", 12, "bold"))
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        scroll_y2 = tk.Scrollbar(right_frame, orient=tk.VERTICAL)
        self.bill_area = tk.Text(right_frame, font=("Courier", 10), width=50,
                                 yscrollcommand=scroll_y2.set, state=tk.DISABLED)
        scroll_y2.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_y2.config(command=self.bill_area.yview)
        self.bill_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def show(self):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT invoice FROM sales")
            rows = cursor.fetchall()
            conn.close()
            self.blll_list = [row[0] for row in rows]
            self.Sales_List.delete(0, tk.END)
            for inv in self.blll_list:
                self.Sales_List.insert(tk.END, inv)
        except Exception as e:
            pass

    def get_data(self, ev):
        selected = self.Sales_List.curselection()
        if not selected:
            return
        invoice = self.Sales_List.get(selected[0])
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sales WHERE invoice=?", (invoice,))
            row = cursor.fetchone()
            conn.close()
            if row:
                self.bill_area.config(state=tk.NORMAL)
                self.bill_area.delete("1.0", tk.END)
                self.bill_area.insert(tk.END, f"Invoice: {row[0]}\n")
                self.bill_area.insert(tk.END, f"Customer: {row[1]}\n")
                self.bill_area.insert(tk.END, f"Contact: {row[2]}\n")
                self.bill_area.insert(tk.END, f"Date: {row[5]}\n")
                self.bill_area.insert(tk.END, "-" * 40 + "\n")
                self.bill_area.insert(tk.END, row[3] if row[3] else "")
                self.bill_area.insert(tk.END, "-" * 40 + "\n")
                self.bill_area.insert(tk.END, f"Net Pay: {row[4]}\n")
                self.bill_area.config(state=tk.DISABLED)
        except Exception as e:
            pass

    def search(self):
        if self.var_invoice.get() == "":
            messagebox.showerror("Error", "Enter invoice number to search", parent=self.root)
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT invoice FROM sales WHERE invoice LIKE ?",
                           (f"%{self.var_invoice.get()}%",))
            rows = cursor.fetchall()
            conn.close()
            self.Sales_List.delete(0, tk.END)
            for row in rows:
                self.Sales_List.insert(tk.END, row[0])
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def clear(self):
        self.var_invoice.set("")
        self.bill_area.config(state=tk.NORMAL)
        self.bill_area.delete("1.0", tk.END)
        self.bill_area.config(state=tk.DISABLED)
        self.show()


# ─────────────────────────────────────────────
# billing.py
# ─────────────────────────────────────────────
class billClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Billing")
        self.root.geometry("1200x700")
        self.root.config(bg="#f0f0f0")

        self.var_search = tk.StringVar()
        self.var_pid = tk.StringVar()
        self.var_pname = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_stock = tk.StringVar()
        self.var_cname = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_cal_input = tk.StringVar()

        self.cart_list = []
        self.bill_amnt = 0
        self.discount = 0.0
        self.net_pay = 0
        self.siscount = 0
        self.chk_print = 0
        self.invoice = None

        self.icon_title = None

        self._build_ui()
        self.show()
        self.update_date_time()

    def _build_ui(self):
        # Title bar
        title_frame = tk.Frame(self.root, bg="#2c3e50", pady=5)
        title_frame.pack(fill=tk.X)
        tk.Label(title_frame, text="Billing System", font=("Arial", 18, "bold"),
                 bg="#2c3e50", fg="white").pack(side=tk.LEFT, padx=20)
        self.lbl_clock = tk.Label(title_frame, text="", font=("Arial", 12),
                                  bg="#2c3e50", fg="white")
        self.lbl_clock.pack(side=tk.RIGHT, padx=20)

        main_frame = tk.Frame(self.root, bg="#f0f0f0")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left - product search
        left_frame = tk.LabelFrame(main_frame, text="Product Details", bg="#f0f0f0",
                                   font=("Arial", 11, "bold"))
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)

        # Search
        search_frame = tk.Frame(left_frame, bg="#f0f0f0")
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(search_frame, text="Search:", bg="#f0f0f0", font=("Arial", 10)).pack(side=tk.LEFT)
        tk.Entry(search_frame, textvariable=self.var_search, font=("Arial", 10), width=15).pack(
            side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", command=self.search, bg="#8e44ad", fg="white",
                  font=("Arial", 10)).pack(side=tk.LEFT)

        # Product table
        scroll_x = tk.Scrollbar(left_frame, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(left_frame, orient=tk.VERTICAL)
        cols = ("pid", "name", "price", "qty", "status")
        self.product_Table = ttk.Treeview(left_frame, columns=cols,
                                          xscrollcommand=scroll_x.set,
                                          yscrollcommand=scroll_y.set, height=8)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.product_Table.xview)
        scroll_y.config(command=self.product_Table.yview)
        headers = ["PID", "Name", "Price", "Qty", "Status"]
        for col, header in zip(cols, headers):
            self.product_Table.heading(col, text=header)
            self.product_Table.column(col, width=80)
        self.product_Table["show"] = "headings"
        self.product_Table.pack(fill=tk.BOTH, expand=True, padx=5)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)

        # Product input fields
        fields_frame = tk.Frame(left_frame, bg="#f0f0f0")
        fields_frame.pack(fill=tk.X, padx=5, pady=5)

        for i, (label, var) in enumerate([("PID:", self.var_pid), ("Name:", self.var_pname),
                                           ("Price:", self.var_price), ("Qty:", self.var_qty)]):
            tk.Label(fields_frame, text=label, bg="#f0f0f0", font=("Arial", 10)).grid(
                row=i // 2, column=(i % 2) * 2, padx=5, pady=3, sticky=tk.W)
            tk.Entry(fields_frame, textvariable=var, font=("Arial", 10), width=12).grid(
                row=i // 2, column=(i % 2) * 2 + 1, padx=5, pady=3)

        tk.Label(fields_frame, text="In Stock:", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=2, column=0, padx=5, pady=3, sticky=tk.W)
        self.lbl_inStock = tk.Label(fields_frame, textvariable=self.var_stock,
                                    bg="#f0f0f0", font=("Arial", 10), fg="#27ae60")
        self.lbl_inStock.grid(row=2, column=1, padx=5, pady=3, sticky=tk.W)

        tk.Button(left_frame, text="Add to Cart", command=self.add_update_cart,
                  bg="#27ae60", fg="white", font=("Arial", 11), width=20).pack(pady=5)

        # Customer info
        cust_frame = tk.LabelFrame(left_frame, text="Customer Details", bg="#f0f0f0",
                                   font=("Arial", 11, "bold"))
        cust_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(cust_frame, text="Name:", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=0, column=0, padx=5, pady=3, sticky=tk.W)
        tk.Entry(cust_frame, textvariable=self.var_cname, font=("Arial", 10), width=18).grid(
            row=0, column=1, padx=5, pady=3)

        tk.Label(cust_frame, text="Contact:", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=1, column=0, padx=5, pady=3, sticky=tk.W)
        tk.Entry(cust_frame, textvariable=self.var_contact, font=("Arial", 10), width=18).grid(
            row=1, column=1, padx=5, pady=3)

        # Middle - cart
        mid_frame = tk.LabelFrame(main_frame, text="Cart", bg="#f0f0f0",
                                  font=("Arial", 11, "bold"))
        mid_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.cartTitle = tk.Label(mid_frame, text="Cart Items", font=("Arial", 12, "bold"),
                                  bg="#3498db", fg="white", pady=5)
        self.cartTitle.pack(fill=tk.X)

        scroll_x2 = tk.Scrollbar(mid_frame, orient=tk.HORIZONTAL)
        scroll_y2 = tk.Scrollbar(mid_frame, orient=tk.VERTICAL)
        cart_cols = ("pid", "name", "price", "qty", "total")
        self.CartTable = ttk.Treeview(mid_frame, columns=cart_cols,
                                      xscrollcommand=scroll_x2.set,
                                      yscrollcommand=scroll_y2.set, height=10)
        scroll_x2.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y2.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x2.config(command=self.CartTable.xview)
        scroll_y2.config(command=self.CartTable.yview)
        cart_headers = ["PID", "Name", "Price", "Qty", "Total"]
        for col, header in zip(cart_cols, cart_headers):
            self.CartTable.heading(col, text=header)
            self.CartTable.column(col, width=80)
        self.CartTable["show"] = "headings"
        self.CartTable.pack(fill=tk.BOTH, expand=True, padx=5)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        # Amount info
        amt_frame = tk.Frame(mid_frame, bg="#f0f0f0")
        amt_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(amt_frame, text="Bill Amount:", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=0, column=0, padx=5, pady=3, sticky=tk.W)
        self.lbl_amnt = tk.Label(amt_frame, text="0", bg="#f0f0f0", font=("Arial", 10, "bold"),
                                 fg="#e74c3c")
        self.lbl_amnt.grid(row=0, column=1, padx=5, pady=3, sticky=tk.W)

        tk.Label(amt_frame, text="Discount (%):", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=1, column=0, padx=5, pady=3, sticky=tk.W)
        self.lbl_discount = tk.Label(amt_frame, text="0", bg="#f0f0f0", font=("Arial", 10, "bold"),
                                     fg="#f39c12")
        self.lbl_discount.grid(row=1, column=1, padx=5, pady=3, sticky=tk.W)

        tk.Label(amt_frame, text="Net Pay:", bg="#f0f0f0", font=("Arial", 10)).grid(
            row=2, column=0, padx=5, pady=3, sticky=tk.W)
        self.lbl_net_pay = tk.Label(amt_frame, text="0", bg="#f0f0f0", font=("Arial", 11, "bold"),
                                    fg="#27ae60")
        self.lbl_net_pay.grid(row=2, column=1, padx=5, pady=3, sticky=tk.W)

        # Discount entry
        disc_frame = tk.Frame(mid_frame, bg="#f0f0f0")
        disc_frame.pack(fill=tk.X, padx=5, pady=3)
        tk.Label(disc_frame, text="Set Discount %:", bg="#f0f0f0", font=("Arial", 10)).pack(
            side=tk.LEFT)
        self.disc_entry = tk.Entry(disc_frame, font=("Arial", 10), width=8)
        self.disc_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(disc_frame, text="Apply", command=self._apply_discount,
                  bg="#f39c12", fg="white", font=("Arial", 10)).pack(side=tk.LEFT)

        # Buttons
        btn_frame2 = tk.Frame(mid_frame, bg="#f0f0f0")
        btn_frame2.pack(fill=tk.X, padx=5, pady=5)

        for text, cmd, color in [("Generate Bill", self.generate_bill, "#27ae60"),
                                  ("Clear Cart", self.clear_cart, "#e74c3c"),
                                  ("Clear All", self.clear_all, "#95a5a6"),
                                  ("Print Bill", self.print_bill, "#3498db")]:
            tk.Button(btn_frame2, text=text, command=cmd, bg=color, fg="white",
                      font=("Arial", 10), width=10).pack(side=tk.LEFT, padx=3)

        # Right - bill area
        right_frame = tk.LabelFrame(main_frame, text="Bill", bg="#f0f0f0",
                                    font=("Arial", 11, "bold"))
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)

        self.bill_top()
        self.bill_middle()
        self.bill_bottom()

        scroll_y3 = tk.Scrollbar(right_frame, orient=tk.VERTICAL)
        self.txt_bill_area = tk.Text(right_frame, font=("Courier", 9), width=40,
                                     yscrollcommand=scroll_y3.set, state=tk.DISABLED)
        scroll_y3.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_y3.config(command=self.txt_bill_area.yview)
        self.txt_bill_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Calculator
        cal_frame = tk.LabelFrame(right_frame, text="Calculator", bg="#f0f0f0",
                                  font=("Arial", 10, "bold"))
        cal_frame.pack(fill=tk.X, padx=5, pady=5)

        self.txt_cal_input = tk.Entry(cal_frame, textvariable=self.var_cal_input,
                                      font=("Arial", 12), width=20, justify=tk.RIGHT)
        self.txt_cal_input.pack(fill=tk.X, padx=5, pady=3)

        cal_buttons = [
            ["7", "8", "9", "/"],
            ["4", "5", "6", "*"],
            ["1", "2", "3", "-"],
            ["0", ".", "=", "+"],
        ]
        for row_btns in cal_buttons:
            row_frame = tk.Frame(cal_frame, bg="#f0f0f0")
            row_frame.pack(fill=tk.X)
            for btn_text in row_btns:
                if btn_text == "=":
                    tk.Button(row_frame, text=btn_text, command=self.perform_cal,
                              bg="#27ae60", fg="white", font=("Arial", 10), width=4).pack(
                        side=tk.LEFT, padx=2, pady=2)
                else:
                    tk.Button(row_frame, text=btn_text,
                              command=lambda t=btn_text: self.get_input(t),
                              bg="#ecf0f1", font=("Arial", 10), width=4).pack(
                        side=tk.LEFT, padx=2, pady=2)

        tk.Button(cal_frame, text="Clear", command=self.clear_cal,
                  bg="#e74c3c", fg="white", font=("Arial", 10)).pack(pady=3)

    def _apply_discount(self):
        try:
            self.discount = float(self.disc_entry.get())
            self.bill_update()
        except ValueError:
            messagebox.showerror("Error", "Enter a valid discount percentage", parent=self.root)

    def bill_top(self):
        pass

    def bill_middle(self):
        pass

    def bill_bottom(self):
        pass

    def bill_update(self):
        self.bill_amnt = sum(item[4] for item in self.cart_list)
        discount_amt = (self.bill_amnt * self.discount) / 100
        self.net_pay = self.bill_amnt - discount_amt
        self.lbl_amnt.config(text=f"${self.bill_amnt:.2f}")
        self.lbl_discount.config(text=f"{self.discount}% (${discount_amt:.2f})")
        self.lbl_net_pay.config(text=f"${self.net_pay:.2f}")

    def show(self):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT pid, name, price, qty, status FROM product WHERE status='Active'")
        rows = cursor.fetchall()
        conn.close()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", tk.END, values=row)

    def show_cart(self):
        self.CartTable.delete(*self.CartTable.get_children())
        for item in self.cart_list:
            self.CartTable.insert("", tk.END, values=item)
        self.bill_update()

    def get_data(self, ev):
        selected = self.product_Table.focus()
        content = self.product_Table.item(selected)
        row = content["values"]
        if row:
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_stock.set(row[3])
            self.var_qty.set("1")

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

            if qty > stock:
                messagebox.showerror("Error", f"Only {stock} items in stock", parent=self.root)
                return

            total = qty * price
            pid = self.var_pid.get()

            # Check if already in cart
            for i, item in enumerate(self.cart_list):
                if item[0] == pid:
                    self.cart_list[i] = (pid, self.var_pname.get(), price, qty, total)
                    self.show_cart()
                    return

            self.cart_list.append((pid, self.var_pname.get(), price, qty, total))
            self.show_cart()
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity or price", parent=self.root)

    def clear_cart(self):
        self.cart_list = []
        self.show_cart()

    def clear_all(self):
        self.cart_list = []
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")
        self.var_cname.set("")
        self.var_contact.set("")
        self.discount = 0.0
        self.show_cart()
        self.txt_bill_area.config(state=tk.NORMAL)
        self.txt_bill_area.delete("1.0", tk.END)
        self.txt_bill_area.config(state=tk.DISABLED)

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty", parent=self.root)
            return
        if self.var_cname.get() == "":
            messagebox.showerror("Error", "Enter customer name", parent=self.root)
            return

        self.invoice = f"INV{random.randint(10000, 99999)}"
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d %H:%M:%S")

        bill_text = "=" * 40 + "\n"
        bill_text += "       INVENTORY MANAGEMENT SYSTEM\n"
        bill_text += "=" * 40 + "\n"
        bill_text += f"Invoice: {self.invoice}\n"
        bill_text += f"Date: {date_str}\n"
        bill_text += f"Customer: {self.var_cname.get()}\n"
        bill_text += f"Contact: {self.var_contact.get()}\n"
        bill_text += "-" * 40 + "\n"
        bill_text += f"{'Item':<15}{'Qty':>5}{'Price':>8}{'Total':>10}\n"
        bill_text += "-" * 40 + "\n"

        for item in self.cart_list:
            bill_text += f"{str(item[1])[:14]:<15}{item[3]:>5}{item[2]:>8.2f}{item[4]:>10.2f}\n"

        bill_text += "-" * 40 + "\n"
        bill_text += f"{'Bill Amount:':<20}${self.bill_amnt:>18.2f}\n"
        bill_text += f"{'Discount:':<20}{self.discount:>17.1f}%\n"
        bill_text += f"{'Net Pay:':<20}${self.net_pay:>18.2f}\n"
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
            cursor = conn.cursor()
            cursor.execute("INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?)",
                           (self.invoice, self.var_cname.get(), self.var_contact.get(),
                            bill_text, str(self.net_pay), date_str))
            # Update product quantities
            for item in self.cart_list:
                cursor.execute("UPDATE product SET qty=qty-? WHERE pid=?", (item[3], item[0]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Bill generated! Invoice: {self.invoice}",
                                parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Error saving bill: {str(e)}", parent=self.root)

    def print_bill(self):
        if self.txt_bill_area.get("1.0", tk.END).strip() == "":
            messagebox.showerror("Error", "Generate a bill first", parent=self.root)
            return
        messagebox.showinfo("Print", "Bill sent to printer (simulated)", parent=self.root)

    def search(self):
        if self.var_search.get() == "":
            self.show()
            return
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT pid, name, price, qty, status FROM product WHERE name LIKE ? OR pid LIKE ?",
                           (f"%{self.var_search.get()}%", f"%{self.var_search.get()}%"))
            rows = cursor.fetchall()
            conn.close()
            self.product_Table.delete(*self.product_Table.get_children())
            for row in rows:
                self.product_Table.insert("", tk.END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

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
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self.update_date_time)


# ─────────────────────────────────────────────
# dashboard.py (IMS)
# ─────────────────────────────────────────────
class IMS:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("1100x650")
        self.root.config(bg="#1a1a2e")
        self.root.resizable(True, True)

        self.MenuLogo = None
        self.icon_side = None
        self.icon_title = None
        self.new_obj = None
        self.new_win = None

        self._build_ui()
        self.update_content()

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg="#16213e", pady=10)
        header.pack(fill=tk.X)

        tk.Label(header, text="📦 Inventory Management System",
                 font=("Arial", 22, "bold"), bg="#16213e", fg="#e94560").pack(side=tk.LEFT, padx=20)

        self.lbl_clock = tk.Label(header, text="", font=("Arial", 12),
                                  bg="#16213e", fg="white")
        self.lbl_clock.pack(side=tk.RIGHT, padx=20)

        # Sidebar
        sidebar = tk.Frame(self.root, bg="#0f3460", width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="MENU", font=("Arial", 14, "bold"),
                 bg="#0f3460", fg="#e94560", pady=15).pack(fill=tk.X)

        menu_items = [
            ("🏠 Dashboard", self.update_content),
            ("📂 Category", self.category),
            ("🏭 Supplier", self.supplier),
            ("👤 Employee", self.employee),
            ("📦 Product", self.product),
            ("💰 Sales", self.sales),
            ("🧾 Billing", self._open_billing),
        ]

        for text, cmd in menu_items:
            btn = tk.Button(sidebar, text=text, command=cmd,
                            bg="#0f3460", fg="white", font=("Arial", 11),
                            relief=tk.FLAT, anchor=tk.W, padx=20, pady=8,
                            activebackground="#e94560", activeforeground="white",
                            cursor="hand2")
            btn.pack(fill=tk.X)

        # Main content area
        self.content_frame = tk.Frame(self.root, bg="#1a1a2e")
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_dashboard()

    def _build_dashboard(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        tk.Label(self.content_frame, text="Dashboard", font=("Arial", 18, "bold"),
                 bg="#1a1a2e", fg="white").pack(pady=20)

        cards_frame = tk.Frame(self.content_frame, bg="#1a1a2e")
        cards_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Stats cards
        stats = self._get_stats()
        card_data = [
            ("📂 Categories", stats["categories"], "#e74c3c", "lbl_category"),
            ("🏭 Suppliers", stats["suppliers"], "#3498db", "lbl_supplier"),
            ("👤 Employees", stats["employees"], "#27ae60", "lbl_employee"),
            ("📦 Products", stats["products"], "#f39c12", "lbl_product"),
            ("💰 Sales", stats["sales"], "#9b59b6", "lbl_sales"),
        ]

        for i, (title, count, color, attr) in enumerate(card_data):
            card = tk.Frame(cards_frame, bg=color, width=180, height=120, relief=tk.RAISED, bd=2)
            card.grid(row=i // 3, column=i % 3, padx=15, pady=15, sticky="nsew")
            card.pack_propagate(False)

            tk.Label(card, text=title, font=("Arial", 12, "bold"),
                     bg=color, fg="white").pack(pady=10)
            lbl = tk.Label(card, text=str(count), font=("Arial", 24, "bold"),
                           bg=color, fg="white")
            lbl.pack()
            setattr(self, attr, lbl)

        for i in range(3):
            cards_frame.columnconfigure(i, weight=1)

    def _get_stats(self):
        stats = {}
        try:
            conn = get_connection()
            cursor = conn.cursor()
            for table, key in [("category", "categories"), ("supplier", "suppliers"),
                                ("employee", "employees"), ("product", "products"),
                                ("sales", "sales")]:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[key] = cursor.fetchone()[0]
            conn.close()
        except Exception:
            for key in ["categories", "suppliers", "employees", "products", "sales"]:
                stats[key] = 0
        return stats

    def update_content(self):
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))
        self._build_dashboard()
        self.root.after(1000, self._update_clock)

    def _update_clock(self):
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self._update_clock)

    def _open_window(self, cls):
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = cls(self.new_win)

    def category(self):
        self._open_window(categoryClass)

    def supplier(self):
        self._open_window(supplierClass)

    def employee(self):
        self._open_window(employeeClass)

    def product(self):
        self._open_window(productClass)

    def sales(self):
        self._open_window(salesClass)

    def _open_billing(self):
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = billClass(self.new_win)


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    initialize_db()
    root = tk.Tk()
    app = IMS(root)
    root.mainloop()