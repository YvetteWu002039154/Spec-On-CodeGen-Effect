import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import datetime
import random
import os

DB_NAME = "ims.db"

def create_tables():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS category (
                    cat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS employee (
                    emp_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT,
                    contact TEXT,
                    dob TEXT,
                    doj TEXT,
                    gender TEXT,
                    utype TEXT,
                    salary REAL,
                    address TEXT,
                    password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS supplier (
                    sup_invoice TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    contact TEXT,
                    description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS product (
                    pid INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price REAL NOT NULL,
                    qty INTEGER NOT NULL,
                    cat_id INTEGER,
                    sup_id TEXT,
                    status TEXT,
                    FOREIGN KEY (cat_id) REFERENCES category(cat_id),
                    FOREIGN KEY (sup_id) REFERENCES supplier(sup_invoice))''')
    c.execute('''CREATE TABLE IF NOT EXISTS invoice (
                    invoice_id TEXT PRIMARY KEY,
                    date TEXT,
                    total REAL,
                    discount REAL,
                    net_pay REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS invoice_item (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id TEXT,
                    pid INTEGER,
                    name TEXT,
                    price REAL,
                    qty INTEGER,
                    total REAL,
                    FOREIGN KEY (invoice_id) REFERENCES invoice(invoice_id),
                    FOREIGN KEY (pid) REFERENCES product(pid))''')
    conn.commit()
    conn.close()

create_tables()

class categoryClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Category Management")
        self.root.geometry("600x400")
        self.var_cat_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.im1 = None
        self.im2 = None
        # Top Frame
        top = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        top.pack(fill=tk.X)
        lbl = tk.Label(top, text="Manage Categories", font=("arial", 15, "bold"), bg="white", fg="darkblue")
        lbl.grid(row=0, column=0, padx=20, pady=5)

        # Entry Frame
        frame1 = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        frame1.place(x=20, y=60, width=560, height=130)
        tk.Label(frame1, text="Category ID", font=("arial", 12), bg="white").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        tk.Entry(frame1, textvariable=self.var_cat_id, state='readonly', font=("arial", 12)).grid(row=0, column=1, padx=10, pady=10, sticky="w")
        tk.Label(frame1, text="Name", font=("arial", 12), bg="white").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        tk.Entry(frame1, textvariable=self.var_name, font=("arial", 12)).grid(row=1, column=1, padx=10, pady=10, sticky="w")

        # Button Frame
        frame2 = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        frame2.place(x=20, y=200, width=560, height=50)
        tk.Button(frame2, text="Add", width=10, command=self.add).grid(row=0, column=0, padx=10)
        tk.Button(frame2, text="Clear", width=10, command=self.clear).grid(row=0, column=1, padx=10)
        tk.Button(frame2, text="Delete", width=10, command=self.delete).grid(row=0, column=2, padx=10)

        # Table Frame
        frame3 = tk.Frame(self.root, bd=4, relief=tk.RIDGE)
        frame3.place(x=20, y=260, width=560, height=180)
        scroll_x = tk.Scrollbar(frame3, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(frame3, orient=tk.VERTICAL)
        self.CategoryTable = ttk.Treeview(frame3, columns=("cat_id", "name"), xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.CategoryTable.xview)
        scroll_y.config(command=self.CategoryTable.yview)
        self.CategoryTable.heading("cat_id", text="ID")
        self.CategoryTable.heading("name", text="Name")
        self.CategoryTable['show'] = 'headings'
        self.CategoryTable.column("cat_id", width=100)
        self.CategoryTable.column("name", width=200)
        self.CategoryTable.pack(fill=tk.BOTH, expand=1)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def add(self):
        if self.var_name.get() == "":
            messagebox.showerror("Error", "Name is required")
            return
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO category (name) VALUES (?)", (self.var_name.get(),))
            conn.commit()
            conn.close()
            self.show()
            self.clear()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clear(self):
        self.var_cat_id.set("")
        self.var_name.set("")

    def delete(self):
        if self.var_cat_id.get() == "":
            messagebox.showerror("Error", "Select a category to delete")
            return
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("DELETE FROM category WHERE cat_id=?", (self.var_cat_id.get(),))
            conn.commit()
            conn.close()
            self.show()
            self.clear()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def get_data(self, ev):
        r = self.CategoryTable.focus()
        content = self.CategoryTable.item(r)
        row = content['values']
        if row:
            self.var_cat_id.set(row[0])
            self.var_name.set(row[1])

    def show(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM category")
        rows = c.fetchall()
        self.CategoryTable.delete(*self.CategoryTable.get_children())
        for row in rows:
            self.CategoryTable.insert('', tk.END, values=row)
        conn.close()


class employeeClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Employee Management")
        self.root.geometry("900x600")
        self.var_emp_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_dob = tk.StringVar()
        self.var_doj = tk.StringVar()
        self.var_gender = tk.StringVar()
        self.var_utype = tk.StringVar()
        self.var_salary = tk.StringVar()
        self.var_pass = tk.StringVar()
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()
        self.txt_address = None

        # Main frame
        main = tk.Frame(self.root, bd=4, relief=tk.RIDGE)
        main.pack(fill=tk.BOTH, expand=1)
        # Top
        top = tk.Label(main, text="Employee Management", font=("arial", 18, "bold"), bg="lightgray")
        top.pack(fill=tk.X)
        # Form
        form = tk.Frame(main, bd=4, relief=tk.RIDGE, bg="white")
        form.pack(pady=5, padx=5, fill=tk.X)
        labels = ["Emp ID", "Name", "Email", "Contact", "DOB", "DOJ", "Gender", "User Type", "Salary", "Password", "Address"]
        vars_ = [self.var_emp_id, self.var_name, self.var_email, self.var_contact, self.var_dob, self.var_doj, self.var_gender, self.var_utype, self.var_salary, self.var_pass]
        entries = []
        for i, (label, var) in enumerate(zip(labels, vars_)):
            tk.Label(form, text=label, font=("arial", 10, "bold"), bg="white").grid(row=i, column=0, padx=5, pady=5, sticky="w")
            if label == "Emp ID":
                ent = tk.Entry(form, textvariable=var, state='readonly')
            elif label == "Gender":
                ent = ttk.Combobox(form, textvariable=var, values=["Male", "Female", "Other"])
            else:
                ent = tk.Entry(form, textvariable=var)
            ent.grid(row=i, column=1, padx=5, pady=5)
            entries.append(ent)
        # Address is Text
        tk.Label(form, text="Address", font=("arial", 10, "bold"), bg="white").grid(row=len(vars_), column=0, padx=5, pady=5, sticky="w")
        self.txt_address = tk.Text(form, height=3, width=30)
        self.txt_address.grid(row=len(vars_), column=1, padx=5, pady=5)

        # Buttons
        btn_frame = tk.Frame(main, bd=4, relief=tk.RIDGE, bg="white")
        btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame, text="Add", width=10, command=self.add).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Update", width=10, command=self.update).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Delete", width=10, command=self.delete).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Clear", width=10, command=self.clear).pack(side=tk.LEFT, padx=10)

        # Search
        search_frame = tk.Frame(main, bd=4, relief=tk.RIDGE, bg="white")
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search By", font=("arial", 10, "bold"), bg="white").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=["emp_id", "name", "email", "contact"]).pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", command=self.search).pack(side=tk.LEFT, padx=5)

        # Table
        table_frame = tk.Frame(main, bd=4, relief=tk.RIDGE)
        table_frame.pack(fill=tk.BOTH, expand=1, padx=5, pady=5)
        scroll_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        self.EmployeeTable = ttk.Treeview(table_frame, columns=("emp_id", "name", "email", "contact", "dob", "doj", "gender", "utype", "salary", "address"), xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.EmployeeTable.xview)
        scroll_y.config(command=self.EmployeeTable.yview)
        self.EmployeeTable.heading("emp_id", text="ID")
        self.EmployeeTable.heading("name", text="Name")
        self.EmployeeTable.heading("email", text="Email")
        self.EmployeeTable.heading("contact", text="Contact")
        self.EmployeeTable.heading("dob", text="DOB")
        self.EmployeeTable.heading("doj", text="DOJ")
        self.EmployeeTable.heading("gender", text="Gender")
        self.EmployeeTable.heading("utype", text="User Type")
        self.EmployeeTable.heading("salary", text="Salary")
        self.EmployeeTable.heading("address", text="Address")
        self.EmployeeTable['show'] = 'headings'
        for col in ("emp_id", "name", "email", "contact", "dob", "doj", "gender", "utype", "salary", "address"):
            self.EmployeeTable.column(col, width=90)
        self.EmployeeTable.pack(fill=tk.BOTH, expand=1)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def add(self):
        if self.var_name.get() == "" or self.var_email.get() == "":
            messagebox.showerror("Error", "Name and Email are required")
            return
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO employee (name, email, contact, dob, doj, gender, utype, salary, address, password) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (self.var_name.get(), self.var_email.get(), self.var_contact.get(), self.var_dob.get(), self.var_doj.get(),
                       self.var_gender.get(), self.var_utype.get(), self.var_salary.get(), self.txt_address.get("1.0", tk.END).strip(),
                       self.var_pass.get()))
            conn.commit()
            conn.close()
            self.show()
            self.clear()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clear(self):
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_email.set("")
        self.var_contact.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_gender.set("")
        self.var_utype.set("")
        self.var_salary.set("")
        self.var_pass.set("")
        self.txt_address.delete("1.0", tk.END)

    def delete(self):
        if self.var_emp_id.get() == "":
            messagebox.showerror("Error", "Select an employee to delete")
            return
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("DELETE FROM employee WHERE emp_id=?", (self.var_emp_id.get(),))
            conn.commit()
            conn.close()
            self.show()
            self.clear()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def get_data(self, ev):
        r = self.EmployeeTable.focus()
        content = self.EmployeeTable.item(r)
        row = content['values']
        if row:
            self.var_emp_id.set(row[0])
            self.var_name.set(row[1])
            self.var_email.set(row[2])
            self.var_contact.set(row[3])
            self.var_dob.set(row[4])
            self.var_doj.set(row[5])
            self.var_gender.set(row[6])
            self.var_utype.set(row[7])
            self.var_salary.set(row[8])
            self.txt_address.delete("1.0", tk.END)
            self.txt_address.insert(tk.END, row[9])
            # password not displayed

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        if by and txt:
            c.execute(f"SELECT * FROM employee WHERE {by} LIKE ?", ('%' + txt + '%',))
        else:
            c.execute("SELECT * FROM employee")
        rows = c.fetchall()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for row in rows:
            self.EmployeeTable.insert('', tk.END, values=row[:10])
        conn.close()

    def show(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM employee")
        rows = c.fetchall()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for row in rows:
            self.EmployeeTable.insert('', tk.END, values=row[:10])
        conn.close()

    def update(self):
        if self.var_emp_id.get() == "":
            messagebox.showerror("Error", "Select an employee to update")
            return
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("UPDATE employee SET name=?, email=?, contact=?, dob=?, doj=?, gender=?, utype=?, salary=?, address=?, password=? WHERE emp_id=?",
                      (self.var_name.get(), self.var_email.get(), self.var_contact.get(), self.var_dob.get(), self.var_doj.get(),
                       self.var_gender.get(), self.var_utype.get(), self.var_salary.get(), self.txt_address.get("1.0", tk.END).strip(),
                       self.var_pass.get(), self.var_emp_id.get()))
            conn.commit()
            conn.close()
            self.show()
            self.clear()
        except Exception as e:
            messagebox.showerror("Error", str(e))


class supplierClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Supplier Management")
        self.root.geometry("700x500")
        self.var_sup_invoice = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()
        self.txt_desc = None
        # UI
        main = tk.Frame(self.root, bd=4, relief=tk.RIDGE)
        main.pack(fill=tk.BOTH, expand=1)
        tk.Label(main, text="Supplier Management", font=("arial", 15, "bold"), bg="lightgray").pack(fill=tk.X)
        form = tk.Frame(main, bd=4, relief=tk.RIDGE, bg="white")
        form.pack(pady=5, padx=5, fill=tk.X)
        tk.Label(form, text="Invoice No", font=("arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=5)
        tk.Entry(form, textvariable=self.var_sup_invoice).grid(row=0, column=1, padx=5, pady=5)
        tk.Label(form, text="Name").grid(row=1, column=0)
        tk.Entry(form, textvariable=self.var_name).grid(row=1, column=1)
        tk.Label(form, text="Contact").grid(row=2, column=0)
        tk.Entry(form, textvariable=self.var_contact).grid(row=2, column=1)
        tk.Label(form, text="Description").grid(row=3, column=0)
        self.txt_desc = tk.Text(form, height=3, width=30)
        self.txt_desc.grid(row=3, column=1)
        btn_frame = tk.Frame(main, bd=4, relief=tk.RIDGE, bg="white")
        btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame, text="Add", width=10, command=self.add).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Update", width=10, command=self.update).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Delete", width=10, command=self.delete).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Clear", width=10, command=self.clear).pack(side=tk.LEFT, padx=10)
        search_frame = tk.Frame(main, bd=4, relief=tk.RIDGE, bg="white")
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search By").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=["sup_invoice", "name", "contact"]).pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", command=self.search).pack(side=tk.LEFT, padx=5)
        table_frame = tk.Frame(main, bd=4, relief=tk.RIDGE)
        table_frame.pack(fill=tk.BOTH, expand=1)
        scroll_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        self.SupplierTable = ttk.Treeview(table_frame, columns=("sup_invoice", "name", "contact", "description"), xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.SupplierTable.xview)
        scroll_y.config(command=self.SupplierTable.yview)
        self.SupplierTable.heading("sup_invoice", text="Invoice")
        self.SupplierTable.heading("name", text="Name")
        self.SupplierTable.heading("contact", text="Contact")
        self.SupplierTable.heading("description", text="Desc")
        self.SupplierTable['show'] = 'headings'
        self.SupplierTable.column("sup_invoice", width=100)
        self.SupplierTable.column("name", width=150)
        self.SupplierTable.column("contact", width=150)
        self.SupplierTable.column("description", width=200)
        self.SupplierTable.pack(fill=tk.BOTH, expand=1)
        self.SupplierTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def add(self):
        if self.var_sup_invoice.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "Invoice No and Name required")
            return
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO supplier (sup_invoice, name, contact, description) VALUES (?,?,?,?)",
                      (self.var_sup_invoice.get(), self.var_name.get(), self.var_contact.get(), self.txt_desc.get("1.0", tk.END).strip()))
            conn.commit()
            conn.close()
            self.show()
            self.clear()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clear(self):
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete("1.0", tk.END)

    def delete(self):
        if self.var_sup_invoice.get() == "":
            messagebox.showerror("Error", "Select supplier to delete")
            return
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("DELETE FROM supplier WHERE sup_invoice=?", (self.var_sup_invoice.get(),))
            conn.commit()
            conn.close()
            self.show()
            self.clear()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def get_data(self, ev):
        r = self.SupplierTable.focus()
        content = self.SupplierTable.item(r)
        row = content['values']
        if row:
            self.var_sup_invoice.set(row[0])
            self.var_name.set(row[1])
            self.var_contact.set(row[2])
            self.txt_desc.delete("1.0", tk.END)
            self.txt_desc.insert(tk.END, row[3])

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        if by and txt:
            c.execute(f"SELECT * FROM supplier WHERE {by} LIKE ?", ('%' + txt + '%',))
        else:
            c.execute("SELECT * FROM supplier")
        rows = c.fetchall()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert('', tk.END, values=row)
        conn.close()

    def show(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM supplier")
        rows = c.fetchall()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert('', tk.END, values=row)
        conn.close()

    def update(self):
        if self.var_sup_invoice.get() == "":
            messagebox.showerror("Error", "Select supplier to update")
            return
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("UPDATE supplier SET name=?, contact=?, description=? WHERE sup_invoice=?",
                      (self.var_name.get(), self.var_contact.get(), self.txt_desc.get("1.0", tk.END).strip(), self.var_sup_invoice.get()))
            conn.commit()
            conn.close()
            self.show()
            self.clear()
        except Exception as e:
            messagebox.showerror("Error", str(e))


class productClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Product Management")
        self.root.geometry("900x600")
        self.var_pid = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_cat = tk.StringVar()
        self.var_sup = tk.StringVar()
        self.var_status = tk.StringVar()
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()
        self.cat_list = []
        self.sup_list = []
        self.fetch_cat_sup()
        # UI
        main = tk.Frame(self.root, bd=4, relief=tk.RIDGE)
        main.pack(fill=tk.BOTH, expand=1)
        tk.Label(main, text="Product Management", font=("arial", 15, "bold"), bg="lightgray").pack(fill=tk.X)
        form = tk.Frame(main, bd=4, relief=tk.RIDGE, bg="white")
        form.pack(pady=5, padx=5, fill=tk.X)
        labels = ["PID", "Name", "Price", "Quantity", "Category", "Supplier", "Status"]
        vars_ = [self.var_pid, self.var_name, self.var_price, self.var_qty, self.var_cat, self.var_sup, self.var_status]
        for i, (label, var) in enumerate(zip(labels, vars_)):
            tk.Label(form, text=label).grid(row=i, column=0, padx=5, pady=5, sticky="w")
            if label == "PID":
                tk.Entry(form, textvariable=var, state='readonly').grid(row=i, column=1)
            elif label == "Category":
                ttk.Combobox(form, textvariable=var, values=self.cat_list).grid(row=i, column=1)
            elif label == "Supplier":
                ttk.Combobox(form, textvariable=var, values=self.sup_list).grid(row=i, column=1)
            elif label == "Status":
                ttk.Combobox(form, textvariable=var, values=["Active", "Inactive"]).grid(row=i, column=1)
            else:
                tk.Entry(form, textvariable=var).grid(row=i, column=1)
        btn_frame = tk.Frame(main, bd=4, relief=tk.RIDGE, bg="white")
        btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame, text="Add", width=10, command=self.add).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Update", width=10, command=self.update).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Delete", width=10, command=self.delete).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Clear", width=10, command=self.clear).pack(side=tk.LEFT, padx=10)
        search_frame = tk.Frame(main, bd=4, relief=tk.RIDGE, bg="white")
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search By").pack(side=tk.LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=["pid", "name", "category", "supplier"]).pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_searchtxt).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", command=self.search).pack(side=tk.LEFT, padx=5)
        table_frame = tk.Frame(main, bd=4, relief=tk.RIDGE)
        table_frame.pack(fill=tk.BOTH, expand=1)
        scroll_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        self.ProductTable = ttk.Treeview(table_frame, columns=("pid", "name", "price", "qty", "cat", "sup", "status"), xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.ProductTable.xview)
        scroll_y.config(command=self.ProductTable.yview)
        self.ProductTable.heading("pid", text="PID")
        self.ProductTable.heading("name", text="Name")
        self.ProductTable.heading("price", text="Price")
        self.ProductTable.heading("qty", text="Qty")
        self.ProductTable.heading("cat", text="Category")
        self.ProductTable.heading("sup", text="Supplier")
        self.ProductTable.heading("status", text="Status")
        self.ProductTable['show'] = 'headings'
        self.ProductTable.column("pid", width=60)
        self.ProductTable.column("name", width=150)
        self.ProductTable.column("price", width=80)
        self.ProductTable.column("qty", width=60)
        self.ProductTable.column("cat", width=120)
        self.ProductTable.column("sup", width=120)
        self.ProductTable.column("status", width=80)
        self.ProductTable.pack(fill=tk.BOTH, expand=1)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def fetch_cat_sup(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT name FROM category")
        self.cat_list = [row[0] for row in c.fetchall()]
        c.execute("SELECT sup_invoice FROM supplier")
        self.sup_list = [row[0] for row in c.fetchall()]
        conn.close()

    def add(self):
        if self.var_name.get() == "" or self.var_price.get() == "":
            messagebox.showerror("Error", "Name and Price required")
            return
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO product (name, price, qty, cat_id, sup_id, status) VALUES (?,?,?, (SELECT cat_id FROM category WHERE name=?), ?, ?)",
                      (self.var_name.get(), self.var_price.get(), self.var_qty.get(), self.var_cat.get(), self.var_sup.get(), self.var_status.get()))
            conn.commit()
            conn.close()
            self.show()
            self.clear()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def clear(self):
        self.var_pid.set("")
        self.var_name.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_cat.set("")
        self.var_sup.set("")
        self.var_status.set("")

    def delete(self):
        if self.var_pid.get() == "":
            messagebox.showerror("Error", "Select product")
            return
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("DELETE FROM product WHERE pid=?", (self.var_pid.get(),))
            conn.commit()
            conn.close()
            self.show()
            self.clear()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def get_data(self, ev):
        r = self.ProductTable.focus()
        content = self.ProductTable.item(r)
        row = content['values']
        if row:
            self.var_pid.set(row[0])
            self.var_name.set(row[1])
            self.var_price.set(row[2])
            self.var_qty.set(row[3])
            self.var_cat.set(row[4])
            self.var_sup.set(row[5])
            self.var_status.set(row[6])

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        query = "SELECT product.pid, product.name, product.price, product.qty, category.name, supplier.sup_invoice, product.status FROM product LEFT JOIN category ON product.cat_id=category.cat_id LEFT JOIN supplier ON product.sup_id=supplier.sup_invoice"
        if by and txt:
            if by == 'category':
                query += " WHERE category.name LIKE ?"
            elif by == 'supplier':
                query += " WHERE supplier.sup_invoice LIKE ?"
            else:
                query += f" WHERE product.{by} LIKE ?"
            c.execute(query, ('%' + txt + '%',))
        else:
            c.execute(query)
        rows = c.fetchall()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for row in rows:
            self.ProductTable.insert('', tk.END, values=row)
        conn.close()

    def show(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT product.pid, product.name, product.price, product.qty, category.name, supplier.sup_invoice, product.status FROM product LEFT JOIN category ON product.cat_id=category.cat_id LEFT JOIN supplier ON product.sup_id=supplier.sup_invoice")
        rows = c.fetchall()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for row in rows:
            self.ProductTable.insert('', tk.END, values=row)
        conn.close()

    def update(self):
        if self.var_pid.get() == "":
            messagebox.showerror("Error", "Select product")
            return
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("UPDATE product SET name=?, price=?, qty=?, cat_id=(SELECT cat_id FROM category WHERE name=?), sup_id=?, status=? WHERE pid=?",
                      (self.var_name.get(), self.var_price.get(), self.var_qty.get(), self.var_cat.get(), self.var_sup.get(), self.var_status.get(), self.var_pid.get()))
            conn.commit()
            conn.close()
            self.show()
            self.clear()
        except Exception as e:
            messagebox.showerror("Error", str(e))


class salesClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Sales Management")
        self.root.geometry("900x600")
        self.var_invoice = tk.StringVar()
        self.blll_list = []
        self.bill_photo = None
        self.bill_area = None
        self.Sales_List = None
        # UI
        main = tk.Frame(self.root, bd=4, relief=tk.RIDGE)
        main.pack(fill=tk.BOTH, expand=1)
        tk.Label(main, text="Sales Management", font=("arial", 15, "bold"), bg="lightgray").pack(fill=tk.X)
        # Invoice search
        search_frame = tk.Frame(main, bd=4, relief=tk.RIDGE, bg="white")
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Invoice No").pack(side=tk.LEFT, padx=5)
        tk.Entry(search_frame, textvariable=self.var_invoice).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", command=self.search).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Show All", command=self.show).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Clear", command=self.clear).pack(side=tk.LEFT, padx=5)
        # Listbox of invoices
        list_frame = tk.Frame(main, bd=4, relief=tk.RIDGE)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=1, padx=5, pady=5)
        scroll = tk.Scrollbar(list_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.Sales_List = tk.Listbox(list_frame, yscrollcommand=scroll.set, font=("arial", 12), width=30)
        self.Sales_List.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        scroll.config(command=self.Sales_List.yview)
        self.Sales_List.bind("<ButtonRelease-1>", self.get_data)
        # Bill area
        bill_frame = tk.Frame(main, bd=4, relief=tk.RIDGE)
        bill_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1, padx=5, pady=5)
        self.bill_area = tk.Text(bill_frame, font=("arial", 12))
        self.bill_area.pack(fill=tk.BOTH, expand=1)
        self.show()

    def get_data(self, ev):
        selection = self.Sales_List.curselection()
        if selection:
            invoice = self.Sales_List.get(selection[0]).split()[0]  # assume first word is invoice id
            self.var_invoice.set(invoice)
            self.search()

    def search(self):
        inv = self.var_invoice.get()
        if not inv:
            return
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM invoice WHERE invoice_id=?", (inv,))
        inv_row = c.fetchone()
        if inv_row:
            self.bill_area.delete("1.0", tk.END)
            self.bill_area.insert(tk.END, f"Invoice: {inv_row[0]}\nDate: {inv_row[1]}\nTotal: {inv_row[2]}\nDiscount: {inv_row[3]}\nNet Pay: {inv_row[4]}\n\nItems:\n")
            c.execute("SELECT * FROM invoice_item WHERE invoice_id=?", (inv,))
            items = c.fetchall()
            self.blll_list = items
            for item in items:
                self.bill_area.insert(tk.END, f"PID:{item[2]}, {item[3]} x{item[5]} @{item[4]} = {item[6]}\n")
        else:
            self.bill_area.delete("1.0", tk.END)
            self.bill_area.insert(tk.END, "Invoice not found")
        conn.close()

    def clear(self):
        self.var_invoice.set("")
        self.bill_area.delete("1.0", tk.END)

    def show(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT invoice_id, date, total, discount, net_pay FROM invoice ORDER BY date DESC")
        rows = c.fetchall()
        self.Sales_List.delete(0, tk.END)
        for row in rows:
            self.Sales_List.insert(tk.END, f"{row[0]}  {row[1]}  Total:{row[2]}  Net:{row[4]}")
        conn.close()


class billClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Billing System")
        self.root.geometry("1200x700")
        self.var_pid = tk.StringVar()
        self.var_pname = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_stock = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_cname = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_search = tk.StringVar()
        self.var_cal_input = tk.StringVar()
        self.cart_list = []
        self.bill_amnt = 0
        self.net_pay = 0.0
        self.discount = 0.0
        self.chk_print = 0
        self.siscount = 0
        self.invoice = ""
        self.icon_title = None
        self.lbl_clock = None
        self.lbl_inStock = None
        self.lbl_amnt = None
        self.lbl_discount = None
        self.lbl_net_pay = None
        self.cartTitle = None
        self.product_Table = None
        self.CartTable = None
        self.txt_bill_area = None
        self.txt_cal_input = None
        self.bill_top()
        self.bill_middle()
        self.bill_bottom()
        self.update_date_time()
        self.show()

    def update_date_time(self):
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self.update_date_time)

    def bill_top(self):
        top = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        top.pack(fill=tk.X)
        self.lbl_clock = tk.Label(top, font=("arial", 12), bg="white")
        self.lbl_clock.pack(side=tk.LEFT, padx=10)
        tk.Label(top, text="Billing System", font=("arial", 20, "bold"), bg="white", fg="darkblue").pack(side=tk.LEFT, padx=50)
        # customer info
        tk.Label(top, text="Customer Name:", bg="white").pack(side=tk.LEFT, padx=5)
        tk.Entry(top, textvariable=self.var_cname).pack(side=tk.LEFT, padx=5)
        tk.Label(top, text="Contact:", bg="white").pack(side=tk.LEFT, padx=5)
        tk.Entry(top, textvariable=self.var_contact).pack(side=tk.LEFT, padx=5)

    def bill_middle(self):
        mid = tk.Frame(self.root, bd=4, relief=tk.RIDGE)
        mid.pack(fill=tk.BOTH, expand=1, padx=5, pady=5)
        # left: product list
        left = tk.Frame(mid, bd=4, relief=tk.RIDGE)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        tk.Label(left, text="Product List", font=("arial", 14, "bold")).pack()
        search_f = tk.Frame(left, bg="white")
        search_f.pack(fill=tk.X)
        tk.Label(search_f, text="Search").pack(side=tk.LEFT, padx=5)
        tk.Entry(search_f, textvariable=self.var_search).pack(side=tk.LEFT, padx=5)
        tk.Button(search_f, text="Search", command=self.search).pack(side=tk.LEFT, padx=5)
        table_frame = tk.Frame(left)
        table_frame.pack(fill=tk.BOTH, expand=1)
        scroll_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        scroll_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        self.product_Table = ttk.Treeview(table_frame, columns=("pid", "name", "price", "qty"), xscrollcommand=scroll_x.set, yscrollcommand=scroll_y.set)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.config(command=self.product_Table.xview)
        scroll_y.config(command=self.product_Table.yview)
        self.product_Table.heading("pid", text="PID")
        self.product_Table.heading("name", text="Name")
        self.product_Table.heading("price", text="Price")
        self.product_Table.heading("qty", text="Qty")
        self.product_Table['show'] = 'headings'
        self.product_Table.column("pid", width=60)
        self.product_Table.column("name", width=150)
        self.product_Table.column("price", width=80)
        self.product_Table.column("qty", width=60)
        self.product_Table.pack(fill=tk.BOTH, expand=1)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)
        # right: cart
        right = tk.Frame(mid, bd=4, relief=tk.RIDGE)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)
        self.cartTitle = tk.Label(right, text="Cart", font=("arial", 14, "bold"))
        self.cartTitle.pack()
        cart_table_frame = tk.Frame(right)
        cart_table_frame.pack(fill=tk.BOTH, expand=1)
        scroll_x2 = tk.Scrollbar(cart_table_frame, orient=tk.HORIZONTAL)
        scroll_y2 = tk.Scrollbar(cart_table_frame, orient=tk.VERTICAL)
        self.CartTable = ttk.Treeview(cart_table_frame, columns=("pid", "name", "price", "qty", "total"), xscrollcommand=scroll_x2.set, yscrollcommand=scroll_y2.set)
        scroll_x2.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y2.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x2.config(command=self.CartTable.xview)
        scroll_y2.config(command=self.CartTable.yview)
        self.CartTable.heading("pid", text="PID")
        self.CartTable.heading("name", text="Name")
        self.CartTable.heading("price", text="Price")
        self.CartTable.heading("qty", text="Qty")
        self.CartTable.heading("total", text="Total")
        self.CartTable['show'] = 'headings'
        self.CartTable.column("pid", width=60)
        self.CartTable.column("name", width=150)
        self.CartTable.column("price", width=80)
        self.CartTable.column("qty", width=60)
        self.CartTable.column("total", width=80)
        self.CartTable.pack(fill=tk.BOTH, expand=1)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)
        # input fields for cart
        cart_input = tk.Frame(right, bg="white")
        cart_input.pack(fill=tk.X, pady=5)
        tk.Label(cart_input, text="Prod ID").grid(row=0, column=0, padx=5)
        tk.Entry(cart_input, textvariable=self.var_pid, state='readonly').grid(row=0, column=1, padx=5)
        tk.Label(cart_input, text="Name").grid(row=0, column=2)
        tk.Entry(cart_input, textvariable=self.var_pname, state='readonly').grid(row=0, column=3)
        tk.Label(cart_input, text="Price").grid(row=1, column=0)
        tk.Entry(cart_input, textvariable=self.var_price, state='readonly').grid(row=1, column=1)
        tk.Label(cart_input, text="Stock").grid(row=1, column=2)
        self.lbl_inStock = tk.Label(cart_input, text="", fg="green")
        self.lbl_inStock.grid(row=1, column=3)
        tk.Label(cart_input, text="Qty").grid(row=2, column=0)
        tk.Entry(cart_input, textvariable=self.var_qty).grid(row=2, column=1)
        tk.Button(cart_input, text="ADD TO CART", command=self.add_update_cart).grid(row=2, column=2, columnspan=2)
        # calculator
        calc_frame = tk.Frame(right, bg="white")
        calc_frame.pack(fill=tk.X, pady=5)
        self.txt_cal_input = tk.Entry(calc_frame, textvariable=self.var_cal_input, width=20)
        self.txt_cal_input.grid(row=0, column=0, columnspan=3)
        buttons = [
            ('7',1,0), ('8',1,1), ('9',1,2), ('+',1,3),
            ('4',2,0), ('5',2,1), ('6',2,2), ('-',2,3),
            ('1',3,0), ('2',3,1), ('3',3,2), ('*',3,3),
            ('0',4,0), ('C',4,1), ('=',4,2), ('/',4,3)
        ]
        for (text, r, c) in buttons:
            tk.Button(calc_frame, text=text, width=4, command=lambda t=text: self.get_input(t)).grid(row=r, column=c)

    def bill_bottom(self):
        bottom = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        bottom.pack(fill=tk.X, pady=5)
        tk.Label(bottom, text="Total Amount").pack(side=tk.LEFT, padx=10)
        self.lbl_amnt = tk.Label(bottom, text="0", font=("arial", 12, "bold"))
        self.lbl_amnt.pack(side=tk.LEFT, padx=10)
        tk.Label(bottom, text="Discount %").pack(side=tk.LEFT, padx=10)
        self.lbl_discount = tk.Entry(bottom, width=5)
        self.lbl_discount.pack(side=tk.LEFT, padx=10)
        self.lbl_discount.insert(0, "0")
        tk.Label(bottom, text="Net Pay").pack(side=tk.LEFT, padx=10)
        self.lbl_net_pay = tk.Label(bottom, text="0", font=("arial", 12, "bold"))
        self.lbl_net_pay.pack(side=tk.LEFT, padx=10)
        tk.Button(bottom, text="Generate Bill", command=self.generate_bill).pack(side=tk.LEFT, padx=20)
        tk.Button(bottom, text="Clear Cart", command=self.clear_cart).pack(side=tk.LEFT, padx=10)
        tk.Button(bottom, text="Print", command=self.print_bill).pack(side=tk.LEFT, padx=10)
        # bill text area
        self.txt_bill_area = tk.Text(self.root, height=10)
        self.txt_bill_area.pack(fill=tk.X, padx=10, pady=5)

    def get_data(self, ev):
        r = self.product_Table.focus()
        content = self.product_Table.item(r)
        row = content['values']
        if row:
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.lbl_inStock.config(text=row[3])
            self.var_stock.set(row[3])
            self.var_qty.set("1")

    def get_data_cart(self, ev):
        r = self.CartTable.focus()
        content = self.CartTable.item(r)
        row = content['values']
        if row:
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_qty.set(row[3])

    def add_update_cart(self):
        pid = self.var_pid.get()
        name = self.var_pname.get()
        price = float(self.var_price.get() or 0)
        stock = int(self.var_stock.get() or 0)
        qty = int(self.var_qty.get() or 0)
        if pid == "" or qty <= 0:
            messagebox.showerror("Error", "Select product and quantity")
            return
        if qty > stock:
            messagebox.showerror("Error", "Insufficient stock")
            return
        total = price * qty
        # check if already in cart, then update
        updated = False
        for i, item in enumerate(self.cart_list):
            if item[0] == pid:
                self.cart_list[i] = (pid, name, price, qty, total)
                updated = True
                break
        if not updated:
            self.cart_list.append((pid, name, price, qty, total))
        self.show_cart()
        self.bill_update()

    def show_cart(self):
        self.CartTable.delete(*self.CartTable.get_children())
        for item in self.cart_list:
            self.CartTable.insert('', tk.END, values=item)
        total = sum(item[4] for item in self.cart_list)
        self.lbl_amnt.config(text=str(total))

    def bill_update(self):
        total = sum(item[4] for item in self.cart_list)
        discount_text = self.lbl_discount.get()
        try:
            discount = float(discount_text)
        except:
            discount = 0
        net = total - (total * discount / 100)
        self.net_pay = net
        self.discount = discount
        self.lbl_net_pay.config(text=str(net))

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty")
            return
        # generate invoice number
        now = datetime.datetime.now()
        inv = f"INV-{now.strftime('%Y%m%d%H%M%S')}-{random.randint(100,999)}"
        total = sum(item[4] for item in self.cart_list)
        discount = self.discount
        net = self.net_pay
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO invoice (invoice_id, date, total, discount, net_pay) VALUES (?,?,?,?,?)",
                      (inv, now.strftime("%Y-%m-%d %H:%M:%S"), total, discount, net))
            for item in self.cart_list:
                c.execute("INSERT INTO invoice_item (invoice_id, pid, name, price, qty, total) VALUES (?,?,?,?,?,?)",
                          (inv, item[0], item[1], item[2], item[3], item[4]))
                # reduce stock
                c.execute("UPDATE product SET qty = qty - ? WHERE pid=? AND qty >= ?", (item[3], item[0], item[3]))
            conn.commit()
            # display bill in text area
            bill_text = f"Invoice: {inv}\nDate: {now}\nCustomer: {self.var_cname.get()}\nContact: {self.var_contact.get()}\n\nItems:\n"
            for item in self.cart_list:
                bill_text += f"{item[1]} x{item[3]} @{item[2]} = {item[4]}\n"
            bill_text += f"\nTotal: {total}\nDiscount: {discount}%\nNet Pay: {net}"
            self.txt_bill_area.delete("1.0", tk.END)
            self.txt_bill_area.insert(tk.END, bill_text)
            self.invoice = inv
            self.chk_print = 1
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            conn.close()

    def print_bill(self):
        if self.chk_print == 0:
            messagebox.showerror("Error", "Generate bill first")
            return
        # Here we would print, but just show message
        messagebox.showinfo("Print", "Bill sent to printer (demo)")
        # or open a temporary file
        # pass

    def clear_cart(self):
        self.cart_list.clear()
        self.CartTable.delete(*self.CartTable.get_children())
        self.lbl_amnt.config(text="0")
        self.lbl_net_pay.config(text="0")
        self.net_pay = 0
        self.bill_amnt = 0

    def clear_all(self):
        self.clear_cart()
        self.txt_bill_area.delete("1.0", tk.END)

    def clear_cal(self):
        self.var_cal_input.set("")

    def get_input(self, num):
        if num == 'C':
            self.clear_cal()
        elif num == '=':
            self.perform_cal()
        else:
            self.var_cal_input.set(self.var_cal_input.get() + num)

    def perform_cal(self):
        try:
            result = eval(self.var_cal_input.get())
            self.var_cal_input.set(str(result))
        except:
            self.var_cal_input.set("Error")

    def search(self):
        txt = self.var_search.get()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        if txt:
            c.execute("SELECT pid, name, price, qty FROM product WHERE name LIKE ? OR pid LIKE ?", ('%'+txt+'%', '%'+txt+'%'))
        else:
            c.execute("SELECT pid, name, price, qty FROM product")
        rows = c.fetchall()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert('', tk.END, values=row)
        conn.close()

    def show(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT pid, name, price, qty FROM product")
        rows = c.fetchall()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert('', tk.END, values=row)
        conn.close()


class IMS:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("1350x700+0+0")
        self.MenuLogo = None
        self.icon_side = None
        self.icon_title = None
        self.new_obj = None
        self.new_win = None
        # Header
        header = tk.Frame(self.root, bg="darkblue")
        header.pack(fill=tk.X)
        self.lbl_clock = tk.Label(header, text="", font=("arial", 12), bg="darkblue", fg="white")
        self.lbl_clock.pack(side=tk.LEFT, padx=10)
        tk.Label(header, text="Inventory Management", font=("arial", 20, "bold"), bg="darkblue", fg="white").pack(side=tk.LEFT, padx=50)
        # Sidebar
        sidebar = tk.Frame(self.root, bg="lightgray", width=200)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        # Labels acting as buttons
        self.lbl_category = tk.Label(sidebar, text="Category", font=("arial", 12), bg="lightgray", cursor="hand2")
        self.lbl_category.pack(pady=10)
        self.lbl_category.bind("<Button-1>", lambda e: self.category())
        self.lbl_employee = tk.Label(sidebar, text="Employee", font=("arial", 12), bg="lightgray", cursor="hand2")
        self.lbl_employee.pack(pady=10)
        self.lbl_employee.bind("<Button-1>", lambda e: self.employee())
        self.lbl_product = tk.Label(sidebar, text="Product", font=("arial", 12), bg="lightgray", cursor="hand2")
        self.lbl_product.pack(pady=10)
        self.lbl_product.bind("<Button-1>", lambda e: self.product())
        self.lbl_supplier = tk.Label(sidebar, text="Supplier", font=("arial", 12), bg="lightgray", cursor="hand2")
        self.lbl_supplier.pack(pady=10)
        self.lbl_supplier.bind("<Button-1>", lambda e: self.supplier())
        self.lbl_sales = tk.Label(sidebar, text="Sales", font=("arial", 12), bg="lightgray", cursor="hand2")
        self.lbl_sales.pack(pady=10)
        self.lbl_sales.bind("<Button-1>", lambda e: self.sales())
        # Bill button separately maybe
        tk.Label(sidebar, text="Billing", font=("arial", 12), bg="lightgray", cursor="hand2").pack(pady=10)
        tk.Label(sidebar, text="Billing", font=("arial", 12), bg="lightgray", cursor="hand2").bind("<Button-1>", lambda e: self.open_billing())
        # Main content area
        self.content = tk.Frame(self.root, bg="white")
        self.content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1)
        self.update_content()
        self.update_clock()

    def update_clock(self):
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self.update_clock)

    def category(self):
        if self.new_win:
            self.new_win.destroy()
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = categoryClass(self.new_win)

    def employee(self):
        if self.new_win:
            self.new_win.destroy()
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = employeeClass(self.new_win)

    def product(self):
        if self.new_win:
            self.new_win.destroy()
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = productClass(self.new_win)

    def supplier(self):
        if self.new_win:
            self.new_win.destroy()
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = supplierClass(self.new_win)

    def sales(self):
        if self.new_win:
            self.new_win.destroy()
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = salesClass(self.new_win)

    def open_billing(self):
        if self.new_win:
            self.new_win.destroy()
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = billClass(self.new_win)

    def update_content(self):
        # Could show dashboard info
        for widget in self.content.winfo_children():
            widget.destroy()
        tk.Label(self.content, text="Welcome to Inventory Management System", font=("arial", 20)).pack(expand=1)


if __name__ == "__main__":
    root = tk.Tk()
    app = IMS(root)
    root.mainloop()