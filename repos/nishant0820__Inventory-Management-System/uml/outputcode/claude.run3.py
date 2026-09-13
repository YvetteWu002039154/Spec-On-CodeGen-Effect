import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
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
                         font=("Arial", 20, "bold"), bg="#0f4d7d", fg="white",
                         pady=10)
        title.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left frame – form
        left = tk.LabelFrame(main_frame, text="Category Details",
                              font=("Arial", 12, "bold"), bg="white", padx=10, pady=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        tk.Label(left, text="Category ID", font=("Arial", 11), bg="white").grid(
            row=0, column=0, sticky=tk.W, pady=5)
        tk.Entry(left, textvariable=self.var_cat_id, font=("Arial", 11),
                 state="readonly").grid(row=0, column=1, pady=5, padx=5)

        tk.Label(left, text="Category Name", font=("Arial", 11), bg="white").grid(
            row=1, column=0, sticky=tk.W, pady=5)
        tk.Entry(left, textvariable=self.var_name, font=("Arial", 11)).grid(
            row=1, column=1, pady=5, padx=5)

        btn_frame = tk.Frame(left, bg="white")
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="Add", font=("Arial", 11), bg="#0f4d7d", fg="white",
                  width=8, command=self.add).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="Delete", font=("Arial", 11), bg="red", fg="white",
                  width=8, command=self.delete).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="Clear", font=("Arial", 11), bg="gray", fg="white",
                  width=8, command=self.clear).grid(row=0, column=2, padx=5)

        self.lbl_im1 = tk.Label(left, bg="white")
        self.lbl_im1.grid(row=3, column=0, pady=5)
        self.lbl_im2 = tk.Label(left, bg="white")
        self.lbl_im2.grid(row=3, column=1, pady=5)

        # Right frame – table
        right = tk.Frame(main_frame, bg="white")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_x = tk.Scrollbar(right, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(right, orient=tk.VERTICAL)
        self.CategoryTable = ttk.Treeview(
            right,
            columns=("cat_id", "name"),
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set
        )
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.CategoryTable.xview)
        scroll_y.config(command=self.CategoryTable.yview)

        self.CategoryTable.heading("cat_id", text="Category ID")
        self.CategoryTable.heading("name", text="Name")
        self.CategoryTable["show"] = "headings"
        self.CategoryTable.column("cat_id", width=150)
        self.CategoryTable.column("name", width=250)
        self.CategoryTable.pack(fill=tk.BOTH, expand=True)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)

    def _gen_id(self):
        return "CAT" + str(random.randint(1000, 9999))

    def add(self):
        if not self.var_name.get():
            messagebox.showerror("Error", "Category name is required", parent=self.root)
            return
        cat_id = self._gen_id()
        self.var_cat_id.set(cat_id)
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO category VALUES (?, ?)",
                      (cat_id, self.var_name.get()))
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
        content = self.CategoryTable.item(selected)
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
                         font=("Arial", 20, "bold"), bg="#0f4d7d", fg="white", pady=10)
        title.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.LabelFrame(main_frame, text="Supplier Details",
                              font=("Arial", 12, "bold"), bg="white", padx=10, pady=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        fields = [
            ("Invoice No", self.var_sup_invoice, True),
            ("Name", self.var_name, False),
            ("Contact", self.var_contact, False),
        ]
        for i, (label, var, ro) in enumerate(fields):
            tk.Label(left, text=label, font=("Arial", 11), bg="white").grid(
                row=i, column=0, sticky=tk.W, pady=5)
            state = "readonly" if ro else "normal"
            tk.Entry(left, textvariable=var, font=("Arial", 11), state=state).grid(
                row=i, column=1, pady=5, padx=5)

        tk.Label(left, text="Description", font=("Arial", 11), bg="white").grid(
            row=3, column=0, sticky=tk.NW, pady=5)
        self.txt_desc = tk.Text(left, font=("Arial", 11), width=25, height=5)
        self.txt_desc.grid(row=3, column=1, pady=5, padx=5)

        btn_frame = tk.Frame(left, bg="white")
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        for text, cmd, color in [
            ("Add", self.add, "#0f4d7d"),
            ("Update", self.update, "green"),
            ("Delete", self.delete, "red"),
            ("Clear", self.clear, "gray"),
        ]:
            tk.Button(btn_frame, text=text, font=("Arial", 11), bg=color, fg="white",
                      width=7, command=cmd).pack(side=tk.LEFT, padx=3)

        # Search
        search_frame = tk.Frame(left, bg="white")
        search_frame.grid(row=5, column=0, columnspan=2, pady=5)
        tk.Label(search_frame, text="Search By", font=("Arial", 11), bg="white").pack(side=tk.LEFT)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Invoice No", "Name", "Contact"],
                     font=("Arial", 11), width=10).pack(side=tk.LEFT, padx=3)
        tk.Entry(search_frame, textvariable=self.var_searchtxt,
                 font=("Arial", 11), width=12).pack(side=tk.LEFT, padx=3)
        tk.Button(search_frame, text="Search", font=("Arial", 11), bg="#0f4d7d", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=3)
        tk.Button(search_frame, text="Show All", font=("Arial", 11), bg="gray", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=3)

        right = tk.Frame(main_frame, bg="white")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_x = tk.Scrollbar(right, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(right, orient=tk.VERTICAL)
        self.SupplierTable = ttk.Treeview(
            right,
            columns=("invoice", "name", "contact", "desc"),
            xscrollcommand=scroll_x.set,
            yscrollcommand=scroll_y.set
        )
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.SupplierTable.xview)
        scroll_y.config(command=self.SupplierTable.yview)

        for col, text, w in [
            ("invoice", "Invoice No", 120),
            ("name", "Name", 150),
            ("contact", "Contact", 120),
            ("desc", "Description", 200),
        ]:
            self.SupplierTable.heading(col, text=text)
            self.SupplierTable.column(col, width=w)
        self.SupplierTable["show"] = "headings"
        self.SupplierTable.pack(fill=tk.BOTH, expand=True)
        self.SupplierTable.bind("<ButtonRelease-1>", self.get_data)

    def _gen_id(self):
        return "SUP" + str(random.randint(1000, 9999))

    def add(self):
        if not self.var_name.get():
            messagebox.showerror("Error", "Name is required", parent=self.root)
            return
        inv = self._gen_id()
        self.var_sup_invoice.set(inv)
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO supplier VALUES (?, ?, ?, ?)",
                      (inv, self.var_name.get(), self.var_contact.get(),
                       self.txt_desc.get("1.0", tk.END).strip()))
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
                       self.txt_desc.get("1.0", tk.END).strip(),
                       self.var_sup_invoice.get()))
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
                c.execute("DELETE FROM supplier WHERE sup_invoice=?",
                          (self.var_sup_invoice.get(),))
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
        content = self.SupplierTable.item(selected)
        row = content["values"]
        if row:
            self.var_sup_invoice.set(row[0])
            self.var_name.set(row[1])
            self.var_contact.set(row[2])
            self.txt_desc.delete("1.0", tk.END)
            self.txt_desc.insert(tk.END, row[3] if row[3] else "")

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get()
        col_map = {"Invoice No": "sup_invoice", "Name": "name", "Contact": "contact"}
        col = col_map.get(by, "name")
        conn = get_connection()
        c = conn.cursor()
        c.execute(f"SELECT * FROM supplier WHERE {col} LIKE ?", (f"%{txt}%",))
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
        self.root.geometry("1200x650")
        self.root.resizable(False, False)

        title = tk.Label(self.root, text="Employee Management",
                         font=("Arial", 20, "bold"), bg="#0f4d7d", fg="white", pady=10)
        title.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.LabelFrame(main_frame, text="Employee Details",
                              font=("Arial", 12, "bold"), bg="white", padx=10, pady=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        fields = [
            ("Employee ID", self.var_emp_id, True, None),
            ("Name", self.var_name, False, None),
            ("DOB (YYYY-MM-DD)", self.var_dob, False, None),
            ("DOJ (YYYY-MM-DD)", self.var_doj, False, None),
            ("Gender", self.var_gender, False, ["Male", "Female", "Other"]),
            ("Contact", self.var_contact, False, None),
            ("Email", self.var_email, False, None),
            ("Salary", self.var_salary, False, None),
            ("User Type", self.var_utype, False, ["Admin", "Employee"]),
            ("Password", self.var_pass, False, None),
        ]
        for i, (label, var, ro, opts) in enumerate(fields):
            tk.Label(left, text=label, font=("Arial", 10), bg="white").grid(
                row=i, column=0, sticky=tk.W, pady=3)
            if opts:
                ttk.Combobox(left, textvariable=var, values=opts,
                             font=("Arial", 10), width=18).grid(row=i, column=1, pady=3, padx=5)
            else:
                state = "readonly" if ro else "normal"
                show = "*" if label == "Password" else ""
                tk.Entry(left, textvariable=var, font=("Arial", 10),
                         state=state, show=show, width=20).grid(row=i, column=1, pady=3, padx=5)

        tk.Label(left, text="Address", font=("Arial", 10), bg="white").grid(
            row=len(fields), column=0, sticky=tk.NW, pady=3)
        self.txt_address = tk.Text(left, font=("Arial", 10), width=20, height=4)
        self.txt_address.grid(row=len(fields), column=1, pady=3, padx=5)

        btn_frame = tk.Frame(left, bg="white")
        btn_frame.grid(row=len(fields) + 1, column=0, columnspan=2, pady=8)
        for text, cmd, color in [
            ("Add", self.add, "#0f4d7d"),
            ("Update", self.update, "green"),
            ("Delete", self.delete, "red"),
            ("Clear", self.clear, "gray"),
        ]:
            tk.Button(btn_frame, text=text, font=("Arial", 10), bg=color, fg="white",
                      width=7, command=cmd).pack(side=tk.LEFT, padx=2)

        search_frame = tk.Frame(left, bg="white")
        search_frame.grid(row=len(fields) + 2, column=0, columnspan=2, pady=5)
        tk.Label(search_frame, text="Search By", font=("Arial", 10), bg="white").pack(side=tk.LEFT)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Employee ID", "Name", "Contact"],
                     font=("Arial", 10), width=10).pack(side=tk.LEFT, padx=2)
        tk.Entry(search_frame, textvariable=self.var_searchtxt,
                 font=("Arial", 10), width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(search_frame, text="Search", font=("Arial", 10), bg="#0f4d7d", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=2)
        tk.Button(search_frame, text="All", font=("Arial", 10), bg="gray", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=2)

        right = tk.Frame(main_frame, bg="white")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_x = tk.Scrollbar(right, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(right, orient=tk.VERTICAL)
        cols = ("emp_id", "name", "dob", "doj", "gender", "contact", "email",
                "salary", "utype", "password", "address")
        self.EmployeeTable = ttk.Treeview(
            right, columns=cols,
            xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set
        )
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.EmployeeTable.xview)
        scroll_y.config(command=self.EmployeeTable.yview)

        headers = ["Emp ID", "Name", "DOB", "DOJ", "Gender", "Contact",
                   "Email", "Salary", "User Type", "Password", "Address"]
        for col, hdr in zip(cols, headers):
            self.EmployeeTable.heading(col, text=hdr)
            self.EmployeeTable.column(col, width=100)
        self.EmployeeTable["show"] = "headings"
        self.EmployeeTable.pack(fill=tk.BOTH, expand=True)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)

    def _gen_id(self):
        return "EMP" + str(random.randint(1000, 9999))

    def add(self):
        if not self.var_name.get():
            messagebox.showerror("Error", "Name is required", parent=self.root)
            return
        emp_id = self._gen_id()
        self.var_emp_id.set(emp_id)
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO employee VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (emp_id, self.var_name.get(), self.var_dob.get(),
                       self.var_doj.get(), self.var_gender.get(),
                       self.var_contact.get(), self.var_email.get(),
                       self.var_salary.get(), self.var_utype.get(),
                       self.var_pass.get(),
                       self.txt_address.get("1.0", tk.END).strip()))
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
                       self.var_gender.get(), self.var_contact.get(),
                       self.var_email.get(), self.var_salary.get(),
                       self.var_utype.get(), self.var_pass.get(),
                       self.txt_address.get("1.0", tk.END).strip(),
                       self.var_emp_id.get()))
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
                    self.var_gender, self.var_contact, self.var_email,
                    self.var_salary, self.var_utype, self.var_pass]:
            var.set("")
        self.txt_address.delete("1.0", tk.END)

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
            self.txt_address.delete("1.0", tk.END)
            self.txt_address.insert(tk.END, row[10] if row[10] else "")

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get()
        col_map = {"Employee ID": "emp_id", "Name": "name", "Contact": "contact"}
        col = col_map.get(by, "name")
        conn = get_connection()
        c = conn.cursor()
        c.execute(f"SELECT * FROM employee WHERE {col} LIKE ?", (f"%{txt}%",))
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
        self.root.geometry("1200x600")
        self.root.resizable(False, False)

        title = tk.Label(self.root, text="Product Management",
                         font=("Arial", 20, "bold"), bg="#0f4d7d", fg="white", pady=10)
        title.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.LabelFrame(main_frame, text="Product Details",
                              font=("Arial", 12, "bold"), bg="white", padx=10, pady=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        tk.Label(left, text="Product ID", font=("Arial", 11), bg="white").grid(
            row=0, column=0, sticky=tk.W, pady=4)
        tk.Entry(left, textvariable=self.var_pid, font=("Arial", 11),
                 state="readonly").grid(row=0, column=1, pady=4, padx=5)

        tk.Label(left, text="Name", font=("Arial", 11), bg="white").grid(
            row=1, column=0, sticky=tk.W, pady=4)
        tk.Entry(left, textvariable=self.var_name, font=("Arial", 11)).grid(
            row=1, column=1, pady=4, padx=5)

        tk.Label(left, text="Price", font=("Arial", 11), bg="white").grid(
            row=2, column=0, sticky=tk.W, pady=4)
        tk.Entry(left, textvariable=self.var_price, font=("Arial", 11)).grid(
            row=2, column=1, pady=4, padx=5)

        tk.Label(left, text="Quantity", font=("Arial", 11), bg="white").grid(
            row=3, column=0, sticky=tk.W, pady=4)
        tk.Entry(left, textvariable=self.var_qty, font=("Arial", 11)).grid(
            row=3, column=1, pady=4, padx=5)

        tk.Label(left, text="Status", font=("Arial", 11), bg="white").grid(
            row=4, column=0, sticky=tk.W, pady=4)
        self.cmb_status = ttk.Combobox(left, textvariable=self.var_status,
                                        values=["Active", "Inactive"],
                                        font=("Arial", 11), width=17)
        self.cmb_status.grid(row=4, column=1, pady=4, padx=5)

        tk.Label(left, text="Category", font=("Arial", 11), bg="white").grid(
            row=5, column=0, sticky=tk.W, pady=4)
        self.cmb_cat = ttk.Combobox(left, textvariable=self.var_cat,
                                     font=("Arial", 11), width=17)
        self.cmb_cat.grid(row=5, column=1, pady=4, padx=5)

        tk.Label(left, text="Supplier", font=("Arial", 11), bg="white").grid(
            row=6, column=0, sticky=tk.W, pady=4)
        self.cmb_sup = ttk.Combobox(left, textvariable=self.var_sup,
                                     font=("Arial", 11), width=17)
        self.cmb_sup.grid(row=6, column=1, pady=4, padx=5)

        btn_frame = tk.Frame(left, bg="white")
        btn_frame.grid(row=7, column=0, columnspan=2, pady=8)
        for text, cmd, color in [
            ("Add", self.add, "#0f4d7d"),
            ("Update", self.update, "green"),
            ("Delete", self.delete, "red"),
            ("Clear", self.clear, "gray"),
        ]:
            tk.Button(btn_frame, text=text, font=("Arial", 11), bg=color, fg="white",
                      width=7, command=cmd).pack(side=tk.LEFT, padx=3)

        search_frame = tk.Frame(left, bg="white")
        search_frame.grid(row=8, column=0, columnspan=2, pady=5)
        tk.Label(search_frame, text="Search By", font=("Arial", 10), bg="white").pack(side=tk.LEFT)
        ttk.Combobox(search_frame, textvariable=self.var_searchby,
                     values=["Product ID", "Name", "Status"],
                     font=("Arial", 10), width=10).pack(side=tk.LEFT, padx=2)
        tk.Entry(search_frame, textvariable=self.var_searchtxt,
                 font=("Arial", 10), width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(search_frame, text="Search", font=("Arial", 10), bg="#0f4d7d", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=2)
        tk.Button(search_frame, text="All", font=("Arial", 10), bg="gray", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=2)

        right = tk.Frame(main_frame, bg="white")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_x = tk.Scrollbar(right, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(right, orient=tk.VERTICAL)
        cols = ("pid", "name", "price", "qty", "status", "cat", "sup")
        self.ProductTable = ttk.Treeview(
            right, columns=cols,
            xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set
        )
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.ProductTable.xview)
        scroll_y.config(command=self.ProductTable.yview)

        headers = ["Product ID", "Name", "Price", "Qty", "Status", "Category", "Supplier"]
        for col, hdr in zip(cols, headers):
            self.ProductTable.heading(col, text=hdr)
            self.ProductTable.column(col, width=110)
        self.ProductTable["show"] = "headings"
        self.ProductTable.pack(fill=tk.BOTH, expand=True)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)

    def fetch_cat_sup(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT name FROM category")
        self.cat_list = [r[0] for r in c.fetchall()]
        c.execute("SELECT name FROM supplier")
        self.sup_list = [r[0] for r in c.fetchall()]
        conn.close()
        self.cmb_cat["values"] = self.cat_list
        self.cmb_sup["values"] = self.sup_list

    def _gen_id(self):
        return "PRD" + str(random.randint(1000, 9999))

    def add(self):
        if not self.var_name.get():
            messagebox.showerror("Error", "Name is required", parent=self.root)
            return
        pid = self._gen_id()
        self.var_pid.set(pid)
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO product VALUES (?,?,?,?,?,?,?)",
                      (pid, self.var_name.get(), self.var_price.get(),
                       self.var_qty.get(), self.var_status.get(),
                       self.var_cat.get(), self.var_sup.get()))
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
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get()
        col_map = {"Product ID": "pid", "Name": "name", "Status": "status"}
        col = col_map.get(by, "name")
        conn = get_connection()
        c = conn.cursor()
        c.execute(f"SELECT * FROM product WHERE {col} LIKE ?", (f"%{txt}%",))
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
        self.Sales_List = None
        self.bill_area = None
        self.bill_photo = None
        self.blll_list = []
        self._build_ui()
        self.show()

    def _build_ui(self):
        self.root.title("Sales Records")
        self.root.geometry("1000x600")
        self.root.resizable(False, False)

        title = tk.Label(self.root, text="Sales Records",
                         font=("Arial", 20, "bold"), bg="#0f4d7d", fg="white", pady=10)
        title.pack(fill=tk.X)

        main_frame = tk.Frame(self.root, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.LabelFrame(main_frame, text="Invoice List",
                              font=("Arial", 12, "bold"), bg="white", padx=5, pady=5)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        search_frame = tk.Frame(left, bg="white")
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search Invoice", font=("Arial", 10), bg="white").pack(side=tk.LEFT)
        tk.Entry(search_frame, textvariable=self.var_invoice,
                 font=("Arial", 10), width=15).pack(side=tk.LEFT, padx=3)
        tk.Button(search_frame, text="Search", font=("Arial", 10), bg="#0f4d7d", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=2)
        tk.Button(search_frame, text="Clear", font=("Arial", 10), bg="gray", fg="white",
                  command=self.clear).pack(side=tk.LEFT, padx=2)

        scroll_y = tk.Scrollbar(left, orient=tk.VERTICAL)
        self.Sales_List = tk.Listbox(left, font=("Arial", 11), width=30,
                                      yscrollcommand=scroll_y.set)
        scroll_y.config(command=self.Sales_List.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.Sales_List.pack(fill=tk.BOTH, expand=True)
        self.Sales_List.bind("<ButtonRelease-1>", self.get_data)

        right = tk.LabelFrame(main_frame, text="Bill Details",
                               font=("Arial", 12, "bold"), bg="white", padx=5, pady=5)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll_y2 = tk.Scrollbar(right, orient=tk.VERTICAL)
        self.bill_area = tk.Text(right, font=("Courier", 11), yscrollcommand=scroll_y2.set)
        scroll_y2.config(command=self.bill_area.yview)
        scroll_y2.pack(side=tk.RIGHT, fill=tk.Y)
        self.bill_area.pack(fill=tk.BOTH, expand=True)

    def show(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT invoice FROM sales")
        rows = c.fetchall()
        conn.close()
        self.blll_list = [r[0] for r in rows]
        self.Sales_List.delete(0, tk.END)
        for inv in self.blll_list:
            self.Sales_List.insert(tk.END, inv)

    def get_data(self, ev):
        try:
            idx = self.Sales_List.curselection()[0]
            invoice = self.Sales_List.get(idx)
        except IndexError:
            return
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

    def search(self):
        txt = self.var_invoice.get()
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT invoice FROM sales WHERE invoice LIKE ?", (f"%{txt}%",))
        rows = c.fetchall()
        conn.close()
        self.Sales_List.delete(0, tk.END)
        for r in rows:
            self.Sales_List.insert(tk.END, r[0])

    def clear(self):
        self.var_invoice.set("")
        self.show()
        self.bill_area.config(state=tk.NORMAL)
        self.bill_area.delete("1.0", tk.END)
        self.bill_area.config(state=tk.DISABLED)


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
        self.var_cname = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_search = tk.StringVar()
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
        self.root.geometry("1400x750")
        self.root.resizable(False, False)

        # Top bar
        top = tk.Frame(self.root, bg="#0f4d7d", pady=5)
        top.pack(fill=tk.X)
        tk.Label(top, text="Billing / Point of Sale",
                 font=("Arial", 20, "bold"), bg="#0f4d7d", fg="white").pack(side=tk.LEFT, padx=10)
        self.lbl_clock = tk.Label(top, text="", font=("Arial", 12), bg="#0f4d7d", fg="white")
        self.lbl_clock.pack(side=tk.RIGHT, padx=10)

        main = tk.Frame(self.root, bg="white")
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ── Left: product search + table
        left = tk.Frame(main, bg="white")
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        search_f = tk.LabelFrame(left, text="Search Product",
                                  font=("Arial", 11, "bold"), bg="white", padx=5, pady=5)
        search_f.pack(fill=tk.X)
        tk.Entry(search_f, textvariable=self.var_search,
                 font=("Arial", 11), width=20).pack(side=tk.LEFT, padx=3)
        tk.Button(search_f, text="Search", font=("Arial", 11), bg="#0f4d7d", fg="white",
                  command=self.search).pack(side=tk.LEFT, padx=3)
        tk.Button(search_f, text="Show All", font=("Arial", 11), bg="gray", fg="white",
                  command=self.show).pack(side=tk.LEFT, padx=3)

        prod_f = tk.Frame(left, bg="white")
        prod_f.pack(fill=tk.BOTH, expand=True, pady=5)
        scroll_x = tk.Scrollbar(prod_f, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(prod_f, orient=tk.VERTICAL)
        cols = ("pid", "name", "price", "qty", "status")
        self.product_Table = ttk.Treeview(
            prod_f, columns=cols, height=12,
            xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set
        )
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.product_Table.xview)
        scroll_y.config(command=self.product_Table.yview)
        for col, hdr, w in zip(cols, ["PID", "Name", "Price", "Qty", "Status"],
                                [80, 150, 80, 60, 80]):
            self.product_Table.heading(col, text=hdr)
            self.product_Table.column(col, width=w)
        self.product_Table["show"] = "headings"
        self.product_Table.pack(fill=tk.BOTH, expand=True)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)

        # Product detail + add to cart
        detail_f = tk.LabelFrame(left, text="Product Detail",
                                  font=("Arial", 11, "bold"), bg="white", padx=5, pady=5)
        detail_f.pack(fill=tk.X)
        for i, (lbl, var) in enumerate([
            ("PID", self.var_pid), ("Name", self.var_pname),
            ("Price", self.var_price), ("Qty", self.var_qty)
        ]):
            tk.Label(detail_f, text=lbl, font=("Arial", 10), bg="white").grid(
                row=i // 2, column=(i % 2) * 2, sticky=tk.W, padx=3, pady=3)
            tk.Entry(detail_f, textvariable=var, font=("Arial", 10), width=14).grid(
                row=i // 2, column=(i % 2) * 2 + 1, padx=3, pady=3)

        self.lbl_inStock = tk.Label(detail_f, text="In Stock: 0",
                                     font=("Arial", 10, "bold"), bg="white", fg="green")
        self.lbl_inStock.grid(row=2, column=0, columnspan=2, pady=3)

        tk.Button(detail_f, text="Add to Cart", font=("Arial", 11), bg="#0f4d7d", fg="white",
                  command=self.add_update_cart).grid(row=2, column=2, columnspan=2, padx=5)

        # ── Middle: cart
        mid = tk.Frame(main, bg="white")
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        cust_f = tk.LabelFrame(mid, text="Customer Info",
                                font=("Arial", 11, "bold"), bg="white", padx=5, pady=5)
        cust_f.pack(fill=tk.X)
        tk.Label(cust_f, text="Name", font=("Arial", 10), bg="white").grid(
            row=0, column=0, sticky=tk.W, padx=3)
        tk.Entry(cust_f, textvariable=self.var_cname, font=("Arial", 10), width=18).grid(
            row=0, column=1, padx=3)
        tk.Label(cust_f, text="Contact", font=("Arial", 10), bg="white").grid(
            row=0, column=2, sticky=tk.W, padx=3)
        tk.Entry(cust_f, textvariable=self.var_contact, font=("Arial", 10), width=18).grid(
            row=0, column=3, padx=3)

        self.cartTitle = tk.Label(mid, text="Cart Items",
                                   font=("Arial", 12, "bold"), bg="#0f4d7d", fg="white")
        self.cartTitle.pack(fill=tk.X)

        cart_f = tk.Frame(mid, bg="white")
        cart_f.pack(fill=tk.BOTH, expand=True, pady=5)
        scroll_x2 = tk.Scrollbar(cart_f, orient=tk.HORIZONTAL)
        scroll_y2 = tk.Scrollbar(cart_f, orient=tk.VERTICAL)
        cart_cols = ("pid", "name", "price", "qty", "total")
        self.CartTable = ttk.Treeview(
            cart_f, columns=cart_cols, height=12,
            xscrollcommand=scroll_x2.set, yscrollcommand=scroll_y2.set
        )
        scroll_x2.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y2.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x2.config(command=self.CartTable.xview)
        scroll_y2.config(command=self.CartTable.yview)
        for col, hdr, w in zip(cart_cols, ["PID", "Name", "Price", "Qty", "Total"],
                                [80, 150, 80, 60, 90]):
            self.CartTable.heading(col, text=hdr)
            self.CartTable.column(col, width=w)
        self.CartTable["show"] = "headings"
        self.CartTable.pack(fill=tk.BOTH, expand=True)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        btn_cart_f = tk.Frame(mid, bg="white")
        btn_cart_f.pack(fill=tk.X)
        tk.Button(btn_cart_f, text="Remove Item", font=("Arial", 10), bg="red", fg="white",
                  command=self.clear_cart).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_cart_f, text="Clear All", font=("Arial", 10), bg="gray", fg="white",
                  command=self.clear_all).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_cart_f, text="Generate Bill", font=("Arial", 10), bg="green", fg="white",
                  command=self.generate_bill).pack(side=tk.LEFT, padx=5)

        amnt_f = tk.Frame(mid, bg="white")
        amnt_f.pack(fill=tk.X, pady=5)
        self.lbl_amnt = tk.Label(amnt_f, text="Total: $0.00",
                                  font=("Arial", 12, "bold"), bg="white")
        self.lbl_amnt.pack(side=tk.LEFT, padx=10)
        self.lbl_discount = tk.Label(amnt_f, text=f"Discount: {self.discount}%",
                                      font=("Arial", 12, "bold"), bg="white", fg="orange")
        self.lbl_discount.pack(side=tk.LEFT, padx=10)
        self.lbl_net_pay = tk.Label(amnt_f, text="Net Pay: $0.00",
                                     font=("Arial", 12, "bold"), bg="white", fg="green")
        self.lbl_net_pay.pack(side=tk.LEFT, padx=10)

        # ── Right: bill area + calculator
        right = tk.Frame(main, bg="white")
        right.pack(side=tk.LEFT, fill=tk.BOTH, padx=5)

        bill_lbl = tk.Label(right, text="Bill Area",
                             font=("Arial", 12, "bold"), bg="#0f4d7d", fg="white")
        bill_lbl.pack(fill=tk.X)

        scroll_y3 = tk.Scrollbar(right, orient=tk.VERTICAL)
        self.txt_bill_area = tk.Text(right, font=("Courier", 10), width=40, height=22,
                                      yscrollcommand=scroll_y3.set)
        scroll_y3.config(command=self.txt_bill_area.yview)
        scroll_y3.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_bill_area.pack(fill=tk.BOTH, expand=True)

        tk.Button(right, text="Print Bill", font=("Arial", 11), bg="#0f4d7d", fg="white",
                  command=self.print_bill).pack(fill=tk.X, pady=3)

        # Calculator
        cal_f = tk.LabelFrame(right, text="Calculator",
                               font=("Arial", 11, "bold"), bg="white", padx=5, pady=5)
        cal_f.pack(fill=tk.X, pady=5)
        self.txt_cal_input = tk.Entry(cal_f, textvariable=self.var_cal_input,
                                       font=("Arial", 12), justify=tk.RIGHT)
        self.txt_cal_input.pack(fill=tk.X, pady=3)

        cal_btns = [
            ["7", "8", "9", "/"],
            ["4", "5", "6", "*"],
            ["1", "2", "3", "-"],
            ["0", ".", "=", "+"],
        ]
        for row in cal_btns:
            row_f = tk.Frame(cal_f, bg="white")
            row_f.pack(fill=tk.X)
            for btn in row:
                tk.Button(row_f, text=btn, font=("Arial", 11), width=4,
                          command=lambda b=btn: self.get_input(b)).pack(side=tk.LEFT, padx=2, pady=2)
        tk.Button(cal_f, text="Clear", font=("Arial", 11), bg="red", fg="white",
                  command=self.clear_cal).pack(fill=tk.X, pady=2)

    def update_date_time(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.config(text=now)
        self.root.after(1000, self.update_date_time)

    def show(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT pid, name, price, qty, status FROM product WHERE status='Active'")
        rows = c.fetchall()
        conn.close()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", tk.END, values=row)

    def search(self):
        txt = self.var_search.get()
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT pid, name, price, qty, status FROM product WHERE name LIKE ? OR pid LIKE ?",
                  (f"%{txt}%", f"%{txt}%"))
        rows = c.fetchall()
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
            self.var_stock.set(str(row[3])) if hasattr(self, 'var_stock') else None

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
        if not self.var_pid.get() or not self.var_qty.get():
            messagebox.showerror("Error", "Select a product and enter quantity",
                                 parent=self.root)
            return
        try:
            qty = int(self.var_qty.get())
            price = float(self.var_price.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid quantity or price", parent=self.root)
            return

        # Check stock
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT qty FROM product WHERE pid=?", (self.var_pid.get(),))
        row = c.fetchone()
        conn.close()
        if not row or int(row[0]) < qty:
            messagebox.showerror("Error", "Insufficient stock", parent=self.root)
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
            self.CartTable.insert("", tk.END, values=item)

    def bill_update(self):
        self.bill_amnt = sum(item[4] for item in self.cart_list)
        self.siscount = self.bill_amnt * self.discount / 100
        self.net_pay = self.bill_amnt - self.siscount
        self.lbl_amnt.config(text=f"Total: ${self.bill_amnt:.2f}")
        self.lbl_discount.config(text=f"Discount ({self.discount}%): ${self.siscount:.2f}")
        self.lbl_net_pay.config(text=f"Net Pay: ${self.net_pay:.2f}")

    def clear_cart(self):
        selected = self.CartTable.focus()
        content = self.CartTable.item(selected)
        row = content["values"]
        if row:
            self.cart_list = [item for item in self.cart_list if item[0] != row[0]]
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
        self.var_cname.set("")
        self.var_contact.set("")
        self.txt_bill_area.delete("1.0", tk.END)

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty", parent=self.root)
            return
        self.invoice = "INV" + str(random.randint(10000, 99999))
        bill_text = self.bill_top() + self.bill_middle() + self.bill_bottom()
        self.txt_bill_area.delete("1.0", tk.END)
        self.txt_bill_area.insert(tk.END, bill_text)

        # Save to DB
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO sales VALUES (?,?,?,?,?,?)",
                      (self.invoice, self.var_cname.get(), self.var_contact.get(),
                       bill_text, str(self.net_pay),
                       datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            # Update stock
            for item in self.cart_list:
                c.execute("UPDATE product SET qty=qty-? WHERE pid=?", (item[3], item[0]))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", f"Bill generated! Invoice: {self.invoice}",
                                parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)

    def bill_top(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        top = "=" * 40 + "\n"
        top += "       INVENTORY MANAGEMENT SYSTEM\n"
        top += "=" * 40 + "\n"
        top += f"Invoice No : {self.invoice}\n"
        top += f"Date/Time  : {now}\n"
        top += f"Customer   : {self.var_cname.get()}\n"
        top += f"Contact    : {self.var_contact.get()}\n"
        top += "-" * 40 + "\n"
        return top

    def bill_middle(self):
        mid = f"{'Name':<18}{'Qty':>5}{'Price':>8}{'Total':>9}\n"
        mid += "-" * 40 + "\n"
        for item in self.cart_list:
            mid += f"{str(item[1]):<18}{str(item[3]):>5}{str(item[2]):>8}{str(item[4]):>9}\n"
        mid += "-" * 40 + "\n"
        return mid

    def bill_bottom(self):
        bot = f"{'Sub Total':<25}${self.bill_amnt:>10.2f}\n"
        bot += f"{'Discount (' + str(self.discount) + '%)':<25}${self.siscount:>10.2f}\n"
        bot += f"{'Net Pay':<25}${self.net_pay:>10.2f}\n"
        bot += "=" * 40 + "\n"
        bot += "      Thank you for shopping!\n"
        bot += "=" * 40 + "\n"
        return bot

    def print_bill(self):
        bill_content = self.txt_bill_area.get("1.0", tk.END)
        if not bill_content.strip():
            messagebox.showerror("Error", "No bill to print", parent=self.root)
            return
        filename = f"bill_{self.invoice if self.invoice else 'draft'}.txt"
        with open(filename, "w") as f:
            f.write(bill_content)
        messagebox.showinfo("Print", f"Bill saved to {filename}", parent=self.root)

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

    # Aliases kept for spec compatibility
    var_stock = None  # will be set dynamically


# ─────────────────────────────────────────────
# dashboard module
# ─────────────────────────────────────────────
class IMS:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("1200x700")
        self.root.resizable(False, False)

        self.MenuLogo = None
        self.icon_side = None
        self.icon_title = None
        self.new_obj = None
        self.new_win = None

        self.lbl_clock = None
        self.lbl_employee = None
        self.lbl_product = None
        self.lbl_category = None
        self.lbl_supplier = None
        self.lbl_sales = None

        self._build_ui()
        self.update_content()

    def _build_ui(self):
        # Title bar
        title_bar = tk.Frame(self.root, bg="#0f4d7d", pady=10)
        title_bar.pack(fill=tk.X)
        tk.Label(title_bar, text="INVENTORY MANAGEMENT SYSTEM",
                 font=("Arial", 24, "bold"), bg="#0f4d7d", fg="white").pack(side=tk.LEFT, padx=20)
        self.lbl_clock = tk.Label(title_bar, text="",
                                   font=("Arial", 12), bg="#0f4d7d", fg="white")
        self.lbl_clock.pack(side=tk.RIGHT, padx=20)

        # Side menu
        side = tk.Frame(self.root, bg="#1a1a2e", width=200)
        side.pack(side=tk.LEFT, fill=tk.Y)
        side.pack_propagate(False)

        tk.Label(side, text="MENU", font=("Arial", 14, "bold"),
                 bg="#1a1a2e", fg="white", pady=15).pack(fill=tk.X)

        menu_items = [
            ("Employee", self.employee),
            ("Category", self.category),
            ("Supplier", self.supplier),
            ("Product", self.product),
            ("Sales", self.sales),
            ("Billing", self._open_billing),
        ]
        for text, cmd in menu_items:
            btn = tk.Button(side, text=text, font=("Arial", 12), bg="#16213e", fg="white",
                            activebackground="#0f4d7d", activeforeground="white",
                            bd=0, pady=10, command=cmd)
            btn.pack(fill=tk.X, padx=5, pady=2)

        # Main content area
        content = tk.Frame(self.root, bg="#f0f0f0")
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Dashboard cards
        cards_frame = tk.Frame(content, bg="#f0f0f0")
        cards_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        card_data = [
            ("Employees", "#e74c3c", "lbl_employee"),
            ("Products", "#3498db", "lbl_product"),
            ("Categories", "#2ecc71", "lbl_category"),
            ("Suppliers", "#f39c12", "lbl_supplier"),
            ("Sales", "#9b59b6", "lbl_sales"),
        ]

        for i, (title, color, attr) in enumerate(card_data):
            card = tk.Frame(cards_frame, bg=color, width=180, height=120,
                            relief=tk.RAISED, bd=2)
            card.grid(row=i // 3, column=i % 3, padx=15, pady=15)
            card.pack_propagate(False)
            tk.Label(card, text=title, font=("Arial", 13, "bold"),
                     bg=color, fg="white").pack(pady=(20, 5))
            lbl = tk.Label(card, text="0", font=("Arial", 20, "bold"),
                           bg=color, fg="white")
            lbl.pack()
            setattr(self, attr, lbl)

    def _open_billing(self):
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = billClass(self.new_win)

    def update_content(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.config(text=now)

        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM employee")
            self.lbl_employee.config(text=str(c.fetchone()[0]))
            c.execute("SELECT COUNT(*) FROM product")
            self.lbl_product.config(text=str(c.fetchone()[0]))
            c.execute("SELECT COUNT(*) FROM category")
            self.lbl_category.config(text=str(c.fetchone()[0]))
            c.execute("SELECT COUNT(*) FROM supplier")
            self.lbl_supplier.config(text=str(c.fetchone()[0]))
            c.execute("SELECT COUNT(*) FROM sales")
            self.lbl_sales.config(text=str(c.fetchone()[0]))
            conn.close()
        except Exception:
            pass

        self.root.after(5000, self.update_content)

    def _open_window(self, cls):
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = cls(self.new_win)

    def category(self):
        self._open_window(categoryClass)

    def employee(self):
        self._open_window(employeeClass)

    def product(self):
        self._open_window(productClass)

    def sales(self):
        self._open_window(salesClass)

    def supplier(self):
        self._open_window(supplierClass)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = IMS(root)
    root.mainloop()