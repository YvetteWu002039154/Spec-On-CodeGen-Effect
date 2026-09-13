import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import datetime
from PIL import Image, ImageTk

def create_db() -> None:
    with sqlite3.connect(database="ims.db") as con:
        cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS employee(eid INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, contact TEXT, utype TEXT, salary TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS supplier(invoice INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, contact TEXT, desc TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS category(cid INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS product(pid INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, supplier TEXT, name TEXT, price TEXT, qty TEXT, status TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS bills(invoice INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, total TEXT)")
        con.commit()

class EmployeeClass:
    def __init__(self, root: tk.Toplevel) -> None:
        self.root = root
        self.root.geometry("800x500+220+130")
        self.root.title("Employee Management")
        self.root.focus_force()

        self.var_emp_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_utype = tk.StringVar()
        self.var_salary = tk.StringVar()

        tk.Label(self.root, text="Emp ID").place(x=50, y=50)
        tk.Entry(self.root, textvariable=self.var_emp_id).place(x=150, y=50)
        
        tk.Label(self.root, text="Name").place(x=50, y=90)
        tk.Entry(self.root, textvariable=self.var_name).place(x=150, y=90)
        
        tk.Label(self.root, text="Email").place(x=50, y=130)
        tk.Entry(self.root, textvariable=self.var_email).place(x=150, y=130)
        
        tk.Label(self.root, text="Contact").place(x=50, y=170)
        tk.Entry(self.root, textvariable=self.var_contact).place(x=150, y=170)
        
        tk.Label(self.root, text="User Type").place(x=50, y=210)
        ttk.Combobox(self.root, textvariable=self.var_utype, values=("Admin", "Employee"), state='readonly').place(x=150, y=210)
        
        tk.Label(self.root, text="Salary").place(x=50, y=250)
        tk.Entry(self.root, textvariable=self.var_salary).place(x=150, y=250)

        tk.Button(self.root, text="Save", command=self.add).place(x=50, y=300, width=80)
        tk.Button(self.root, text="Update", command=self.update).place(x=140, y=300, width=80)
        tk.Button(self.root, text="Delete", command=self.delete).place(x=230, y=300, width=80)
        tk.Button(self.root, text="Clear", command=self.clear).place(x=320, y=300, width=80)

        emp_frame = tk.Frame(self.root, bd=3, relief=tk.RIDGE)
        emp_frame.place(x=450, y=50, width=330, height=350)

        scrolly = tk.Scrollbar(emp_frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(emp_frame, orient=tk.HORIZONTAL)

        self.EmployeeTable = ttk.Treeview(emp_frame, columns=("eid", "name", "email", "contact", "utype", "salary"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.EmployeeTable.xview)
        scrolly.config(command=self.EmployeeTable.yview)

        self.EmployeeTable.heading("eid", text="EMP ID")
        self.EmployeeTable.heading("name", text="Name")
        self.EmployeeTable.heading("email", text="Email")
        self.EmployeeTable.heading("contact", text="Contact")
        self.EmployeeTable.heading("utype", text="User Type")
        self.EmployeeTable.heading("salary", text="Salary")
        self.EmployeeTable["show"] = "headings"
        self.EmployeeTable.pack(fill=tk.BOTH, expand=1)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def add(self) -> None:
        try:
            if self.var_name.get() == "":
                messagebox.showerror("Error", "Employee Name must be required", parent=self.root)
            else:
                with sqlite3.connect(database="ims.db") as con:
                    cur = con.cursor()
                    cur.execute("INSERT INTO employee (name, email, contact, utype, salary) VALUES(?,?,?,?,?)", (
                        self.var_name.get(),
                        self.var_email.get(),
                        self.var_contact.get(),
                        self.var_utype.get(),
                        self.var_salary.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Employee Added Successfully", parent=self.root)
                    self.show()
                    self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def show(self) -> None:
        try:
            with sqlite3.connect(database="ims.db") as con:
                cur = con.cursor()
                cur.execute("SELECT * FROM employee")
                rows = cur.fetchall()
                self.EmployeeTable.delete(*self.EmployeeTable.get_children())
                for row in rows:
                    self.EmployeeTable.insert('', tk.END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def get_data(self, ev: tk.Event) -> None:
        f = self.EmployeeTable.focus()
        content = (self.EmployeeTable.item(f))
        row = content['values']
        if row:
            self.var_emp_id.set(row[0])
            self.var_name.set(row[1])
            self.var_email.set(row[2])
            self.var_contact.set(row[3])
            self.var_utype.set(row[4])
            self.var_salary.set(row[5])

    def update(self) -> None:
        try:
            if self.var_emp_id.get() == "":
                messagebox.showerror("Error", "Employee ID must be required", parent=self.root)
            else:
                with sqlite3.connect(database="ims.db") as con:
                    cur = con.cursor()
                    cur.execute("UPDATE employee SET name=?, email=?, contact=?, utype=?, salary=? WHERE eid=?", (
                        self.var_name.get(),
                        self.var_email.get(),
                        self.var_contact.get(),
                        self.var_utype.get(),
                        self.var_salary.get(),
                        self.var_emp_id.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Employee Updated Successfully", parent=self.root)
                    self.show()
                    self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def delete(self) -> None:
        try:
            if self.var_emp_id.get() == "":
                messagebox.showerror("Error", "Employee ID must be required", parent=self.root)
            else:
                with sqlite3.connect(database="ims.db") as con:
                    cur = con.cursor()
                    cur.execute("DELETE FROM employee WHERE eid=?", (self.var_emp_id.get(),))
                    con.commit()
                    messagebox.showinfo("Success", "Employee Deleted Successfully", parent=self.root)
                    self.show()
                    self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def clear(self) -> None:
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_email.set("")
        self.var_contact.set("")
        self.var_utype.set("")
        self.var_salary.set("")

class SupplierClass:
    def __init__(self, root: tk.Toplevel) -> None:
        self.root = root
        self.root.geometry("800x500+220+130")
        self.root.title("Supplier Management")
        self.root.focus_force()

        self.var_sup_invoice = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_contact = tk.StringVar()

        tk.Label(self.root, text="Invoice No.").place(x=50, y=50)
        tk.Entry(self.root, textvariable=self.var_sup_invoice).place(x=150, y=50)
        
        tk.Label(self.root, text="Name").place(x=50, y=90)
        tk.Entry(self.root, textvariable=self.var_name).place(x=150, y=90)
        
        tk.Label(self.root, text="Contact").place(x=50, y=130)
        tk.Entry(self.root, textvariable=self.var_contact).place(x=150, y=130)
        
        tk.Label(self.root, text="Description").place(x=50, y=170)
        self.txt_desc = tk.Text(self.root, width=25, height=4)
        self.txt_desc.place(x=150, y=170)

        tk.Button(self.root, text="Save", command=self.add).place(x=50, y=300, width=80)
        tk.Button(self.root, text="Update", command=self.update).place(x=140, y=300, width=80)
        tk.Button(self.root, text="Delete", command=self.delete).place(x=230, y=300, width=80)
        tk.Button(self.root, text="Clear", command=self.clear).place(x=320, y=300, width=80)

        sup_frame = tk.Frame(self.root, bd=3, relief=tk.RIDGE)
        sup_frame.place(x=450, y=50, width=330, height=350)

        scrolly = tk.Scrollbar(sup_frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(sup_frame, orient=tk.HORIZONTAL)

        self.SupplierTable = ttk.Treeview(sup_frame, columns=("invoice", "name", "contact", "desc"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.SupplierTable.xview)
        scrolly.config(command=self.SupplierTable.yview)

        self.SupplierTable.heading("invoice", text="Invoice")
        self.SupplierTable.heading("name", text="Name")
        self.SupplierTable.heading("contact", text="Contact")
        self.SupplierTable.heading("desc", text="Description")
        self.SupplierTable["show"] = "headings"
        self.SupplierTable.pack(fill=tk.BOTH, expand=1)
        self.SupplierTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def add(self) -> None:
        try:
            if self.var_name.get() == "":
                messagebox.showerror("Error", "Supplier Name must be required", parent=self.root)
            else:
                with sqlite3.connect(database="ims.db") as con:
                    cur = con.cursor()
                    cur.execute("INSERT INTO supplier (name, contact, desc) VALUES(?,?,?)", (
                        self.var_name.get(),
                        self.var_contact.get(),
                        self.txt_desc.get('1.0', tk.END).strip()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Supplier Added Successfully", parent=self.root)
                    self.show()
                    self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def show(self) -> None:
        try:
            with sqlite3.connect(database="ims.db") as con:
                cur = con.cursor()
                cur.execute("SELECT * FROM supplier")
                rows = cur.fetchall()
                self.SupplierTable.delete(*self.SupplierTable.get_children())
                for row in rows:
                    self.SupplierTable.insert('', tk.END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def get_data(self, ev: tk.Event) -> None:
        f = self.SupplierTable.focus()
        content = (self.SupplierTable.item(f))
        row = content['values']
        if row:
            self.var_sup_invoice.set(row[0])
            self.var_name.set(row[1])
            self.var_contact.set(row[2])
            self.txt_desc.delete('1.0', tk.END)
            self.txt_desc.insert(tk.END, row[3])

    def update(self) -> None:
        try:
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice No. must be required", parent=self.root)
            else:
                with sqlite3.connect(database="ims.db") as con:
                    cur = con.cursor()
                    cur.execute("UPDATE supplier SET name=?, contact=?, desc=? WHERE invoice=?", (
                        self.var_name.get(),
                        self.var_contact.get(),
                        self.txt_desc.get('1.0', tk.END).strip(),
                        self.var_sup_invoice.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Supplier Updated Successfully", parent=self.root)
                    self.show()
                    self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def delete(self) -> None:
        try:
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice No. must be required", parent=self.root)
            else:
                with sqlite3.connect(database="ims.db") as con:
                    cur = con.cursor()
                    cur.execute("DELETE FROM supplier WHERE invoice=?", (self.var_sup_invoice.get(),))
                    con.commit()
                    messagebox.showinfo("Success", "Supplier Deleted Successfully", parent=self.root)
                    self.show()
                    self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def clear(self) -> None:
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete('1.0', tk.END)

class CategoryClass:
    def __init__(self, root: tk.Toplevel) -> None:
        self.root = root
        self.root.geometry("800x500+220+130")
        self.root.title("Category Management")
        self.root.focus_force()

        self.var_cat_id = tk.StringVar()
        self.var_name = tk.StringVar()

        tk.Label(self.root, text="Category Name").place(x=50, y=50)
        tk.Entry(self.root, textvariable=self.var_name).place(x=180, y=50)

        tk.Button(self.root, text="Add", command=self.add).place(x=50, y=100, width=80)
        tk.Button(self.root, text="Delete", command=self.delete).place(x=140, y=100, width=80)

        cat_frame = tk.Frame(self.root, bd=3, relief=tk.RIDGE)
        cat_frame.place(x=350, y=50, width=400, height=350)

        scrolly = tk.Scrollbar(cat_frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(cat_frame, orient=tk.HORIZONTAL)

        self.CategoryTable = ttk.Treeview(cat_frame, columns=("cid", "name"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.CategoryTable.xview)
        scrolly.config(command=self.CategoryTable.yview)

        self.CategoryTable.heading("cid", text="C_ID")
        self.CategoryTable.heading("name", text="Name")
        self.CategoryTable["show"] = "headings"
        self.CategoryTable.pack(fill=tk.BOTH, expand=1)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def add(self) -> None:
        try:
            if self.var_name.get() == "":
                messagebox.showerror("Error", "Category Name must be required", parent=self.root)
            else:
                with sqlite3.connect(database="ims.db") as con:
                    cur = con.cursor()
                    cur.execute("INSERT INTO category (name) VALUES(?)", (self.var_name.get(),))
                    con.commit()
                    messagebox.showinfo("Success", "Category Added Successfully", parent=self.root)
                    self.show()
                    self.var_name.set("")
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def show(self) -> None:
        try:
            with sqlite3.connect(database="ims.db") as con:
                cur = con.cursor()
                cur.execute("SELECT * FROM category")
                rows = cur.fetchall()
                self.CategoryTable.delete(*self.CategoryTable.get_children())
                for row in rows:
                    self.CategoryTable.insert('', tk.END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def get_data(self, ev: tk.Event) -> None:
        f = self.CategoryTable.focus()
        content = (self.CategoryTable.item(f))
        row = content['values']
        if row:
            self.var_cat_id.set(row[0])
            self.var_name.set(row[1])

    def delete(self) -> None:
        try:
            if self.var_cat_id.get() == "":
                messagebox.showerror("Error", "Select category from list", parent=self.root)
            else:
                with sqlite3.connect(database="ims.db") as con:
                    cur = con.cursor()
                    cur.execute("DELETE FROM category WHERE cid=?", (self.var_cat_id.get(),))
                    con.commit()
                    messagebox.showinfo("Success", "Category Deleted Successfully", parent=self.root)
                    self.show()
                    self.var_cat_id.set("")
                    self.var_name.set("")
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

class ProductClass:
    def __init__(self, root: tk.Toplevel) -> None:
        self.root = root
        self.root.geometry("800x500+220+130")
        self.root.title("Product Management")
        self.root.focus_force()

        self.var_pid = tk.StringVar()
        self.var_cat = tk.StringVar()
        self.var_sup = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_status = tk.StringVar()

        self.cat_list = []
        self.sup_list = []
        self.fetch_cat_sup()

        tk.Label(self.root, text="Category").place(x=50, y=50)
        ttk.Combobox(self.root, textvariable=self.var_cat, values=self.cat_list, state='readonly').place(x=150, y=50)
        
        tk.Label(self.root, text="Supplier").place(x=50, y=90)
        ttk.Combobox(self.root, textvariable=self.var_sup, values=self.sup_list, state='readonly').place(x=150, y=90)
        
        tk.Label(self.root, text="Name").place(x=50, y=130)
        tk.Entry(self.root, textvariable=self.var_name).place(x=150, y=130)
        
        tk.Label(self.root, text="Price").place(x=50, y=170)
        tk.Entry(self.root, textvariable=self.var_price).place(x=150, y=170)
        
        tk.Label(self.root, text="Quantity").place(x=50, y=210)
        tk.Entry(self.root, textvariable=self.var_qty).place(x=150, y=210)
        
        tk.Label(self.root, text="Status").place(x=50, y=250)
        ttk.Combobox(self.root, textvariable=self.var_status, values=("Active", "Inactive"), state='readonly').place(x=150, y=250)

        tk.Button(self.root, text="Save", command=self.add).place(x=50, y=300, width=80)
        tk.Button(self.root, text="Update", command=self.update).place(x=140, y=300, width=80)
        tk.Button(self.root, text="Delete", command=self.delete).place(x=230, y=300, width=80)
        tk.Button(self.root, text="Clear", command=self.clear).place(x=320, y=300, width=80)

        prod_frame = tk.Frame(self.root, bd=3, relief=tk.RIDGE)
        prod_frame.place(x=450, y=50, width=330, height=350)

        scrolly = tk.Scrollbar(prod_frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(prod_frame, orient=tk.HORIZONTAL)

        self.ProductTable = ttk.Treeview(prod_frame, columns=("pid", "category", "supplier", "name", "price", "qty", "status"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.ProductTable.xview)
        scrolly.config(command=self.ProductTable.yview)

        self.ProductTable.heading("pid", text="P_ID")
        self.ProductTable.heading("category", text="Category")
        self.ProductTable.heading("supplier", text="Supplier")
        self.ProductTable.heading("name", text="Name")
        self.ProductTable.heading("price", text="Price")
        self.ProductTable.heading("qty", text="Qty")
        self.ProductTable.heading("status", text="Status")
        self.ProductTable["show"] = "headings"
        self.ProductTable.pack(fill=tk.BOTH, expand=1)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def fetch_cat_sup(self) -> None:
        try:
            with sqlite3.connect(database="ims.db") as con:
                cur = con.cursor()
                cur.execute("SELECT name FROM category")
                cat = cur.fetchall()
                self.cat_list = [row[0] for row in cat]
                
                cur.execute("SELECT name FROM supplier")
                sup = cur.fetchall()
                self.sup_list = [row[0] for row in sup]
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def add(self) -> None:
        try:
            if self.var_name.get() == "":
                messagebox.showerror("Error", "Product Name must be required", parent=self.root)
            else:
                with sqlite3.connect(database="ims.db") as con:
                    cur = con.cursor()
                    cur.execute("INSERT INTO product (category, supplier, name, price, qty, status) VALUES(?,?,?,?,?,?)", (
                        self.var_cat.get(),
                        self.var_sup.get(),
                        self.var_name.get(),
                        self.var_price.get(),
                        self.var_qty.get(),
                        self.var_status.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Product Added Successfully", parent=self.root)
                    self.show()
                    self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def show(self) -> None:
        try:
            with sqlite3.connect(database="ims.db") as con:
                cur = con.cursor()
                cur.execute("SELECT * FROM product")
                rows = cur.fetchall()
                self.ProductTable.delete(*self.ProductTable.get_children())
                for row in rows:
                    self.ProductTable.insert('', tk.END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def get_data(self, ev: tk.Event) -> None:
        f = self.ProductTable.focus()
        content = (self.ProductTable.item(f))
        row = content['values']
        if row:
            self.var_pid.set(row[0])
            self.var_cat.set(row[1])
            self.var_sup.set(row[2])
            self.var_name.set(row[3])
            self.var_price.set(row[4])
            self.var_qty.set(row[5])
            self.var_status.set(row[6])

    def update(self) -> None:
        try:
            if self.var_pid.get() == "":
                messagebox.showerror("Error", "Product ID must be required", parent=self.root)
            else:
                with sqlite3.connect(database="ims.db") as con:
                    cur = con.cursor()
                    cur.execute("UPDATE product SET category=?, supplier=?, name=?, price=?, qty=?, status=? WHERE pid=?", (
                        self.var_cat.get(),
                        self.var_sup.get(),
                        self.var_name.get(),
                        self.var_price.get(),
                        self.var_qty.get(),
                        self.var_status.get(),
                        self.var_pid.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Product Updated Successfully", parent=self.root)
                    self.show()
                    self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def delete(self) -> None:
        try:
            if self.var_pid.get() == "":
                messagebox.showerror("Error", "Product ID must be required", parent=self.root)
            else:
                with sqlite3.connect(database="ims.db") as con:
                    cur = con.cursor()
                    cur.execute("DELETE FROM product WHERE pid=?", (self.var_pid.get(),))
                    con.commit()
                    messagebox.showinfo("Success", "Product Deleted Successfully", parent=self.root)
                    self.show()
                    self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def clear(self) -> None:
        self.var_pid.set("")
        self.var_cat.set("")
        self.var_sup.set("")
        self.var_name.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("")

class BillingClass:
    def __init__(self, root: tk.Toplevel) -> None:
        self.root = root
        self.root.geometry("1000x600+100+50")
        self.root.title("Billing Management")
        self.root.focus_force()

        self.cart_list = []
        self.var_search = tk.StringVar()
        self.var_cname = tk.StringVar()
        self.var_contact = tk.StringVar()
        
        self.var_pid = tk.StringVar()
        self.var_pname = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_stock = tk.StringVar()

        os.makedirs('bills', exist_ok=True)

        left_frame = tk.Frame(self.root, bd=2, relief=tk.RIDGE)
        left_frame.place(x=10, y=10, width=400, height=580)

        tk.Label(left_frame, text="Search Product").pack(pady=5)
        tk.Entry(left_frame, textvariable=self.var_search).pack(pady=5)
        tk.Button(left_frame, text="Search", command=self.search).pack(pady=5)

        prod_frame = tk.Frame(left_frame, bd=3, relief=tk.RIDGE)
        prod_frame.pack(fill=tk.BOTH, expand=1, pady=5)

        scrolly = tk.Scrollbar(prod_frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(prod_frame, orient=tk.HORIZONTAL)

        self.ProductTable = ttk.Treeview(prod_frame, columns=("pid", "name", "price", "qty", "status"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.ProductTable.xview)
        scrolly.config(command=self.ProductTable.yview)

        self.ProductTable.heading("pid", text="PID")
        self.ProductTable.heading("name", text="Name")
        self.ProductTable.heading("price", text="Price")
        self.ProductTable.heading("qty", text="Qty")
        self.ProductTable.heading("status", text="Status")
        self.ProductTable["show"] = "headings"
        self.ProductTable.pack(fill=tk.BOTH, expand=1)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)

        mid_frame = tk.Frame(self.root, bd=2, relief=tk.RIDGE)
        mid_frame.place(x=420, y=10, width=300, height=580)

        tk.Label(mid_frame, text="Customer Name").pack(pady=2)
        tk.Entry(mid_frame, textvariable=self.var_cname).pack(pady=2)
        tk.Label(mid_frame, text="Customer Contact").pack(pady=2)
        tk.Entry(mid_frame, textvariable=self.var_contact).pack(pady=2)

        cart_frame = tk.Frame(mid_frame, bd=3, relief=tk.RIDGE)
        cart_frame.pack(fill=tk.BOTH, expand=1, pady=5)

        scrolly2 = tk.Scrollbar(cart_frame, orient=tk.VERTICAL)
        scrollx2 = tk.Scrollbar(cart_frame, orient=tk.HORIZONTAL)

        self.CartTable = ttk.Treeview(cart_frame, columns=("pid", "name", "price", "qty"), yscrollcommand=scrolly2.set, xscrollcommand=scrollx2.set)
        scrollx2.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly2.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx2.config(command=self.CartTable.xview)
        scrolly2.config(command=self.CartTable.yview)

        self.CartTable.heading("pid", text="PID")
        self.CartTable.heading("name", text="Name")
        self.CartTable.heading("price", text="Price")
        self.CartTable.heading("qty", text="Qty")
        self.CartTable["show"] = "headings"
        self.CartTable.pack(fill=tk.BOTH, expand=1)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        tk.Label(mid_frame, text="Product Name").pack()
        tk.Entry(mid_frame, textvariable=self.var_pname, state='readonly').pack()
        tk.Label(mid_frame, text="Price").pack()
        tk.Entry(mid_frame, textvariable=self.var_price, state='readonly').pack()
        tk.Label(mid_frame, text="Quantity").pack()
        tk.Entry(mid_frame, textvariable=self.var_qty).pack()

        tk.Button(mid_frame, text="Add / Update Cart", command=self.add_update_cart).pack(pady=5)
        tk.Button(mid_frame, text="Clear Cart", command=self.clear_cart).pack(pady=5)

        right_frame = tk.Frame(self.root, bd=2, relief=tk.RIDGE)
        right_frame.place(x=730, y=10, width=260, height=580)

        tk.Label(right_frame, text="Bill Area").pack()
        scrolly3 = tk.Scrollbar(right_frame, orient=tk.VERTICAL)
        self.txt_bill_area = tk.Text(right_frame, yscrollcommand=scrolly3.set)
        scrolly3.pack(side=tk.RIGHT, fill=tk.Y)
        scrolly3.config(command=self.txt_bill_area.yview)
        self.txt_bill_area.pack(fill=tk.BOTH, expand=1)

        tk.Button(right_frame, text="Generate Bill", command=self.generate_bill).pack(pady=5, fill=tk.X)
        
        self.var_invoice_search = tk.StringVar()
        tk.Label(right_frame, text="Search Invoice No").pack()
        tk.Entry(right_frame, textvariable=self.var_invoice_search).pack()
        tk.Button(right_frame, text="Show Bill", command=self.show_bill).pack(pady=5, fill=tk.X)

        self.show()

    def show(self) -> None:
        try:
            with sqlite3.connect(database="ims.db") as con:
                cur = con.cursor()
                cur.execute("SELECT pid, name, price, qty, status FROM product WHERE status='Active'")
                rows = cur.fetchall()
                self.ProductTable.delete(*self.ProductTable.get_children())
                for row in rows:
                    self.ProductTable.insert('', tk.END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def search(self) -> None:
        try:
            with sqlite3.connect(database="ims.db") as con:
                cur = con.cursor()
                cur.execute("SELECT pid, name, price, qty, status FROM product WHERE name LIKE ? AND status='Active'", ('%'+self.var_search.get()+'%',))
                rows = cur.fetchall()
                self.ProductTable.delete(*self.ProductTable.get_children())
                for row in rows:
                    self.ProductTable.insert('', tk.END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def get_data(self, ev: tk.Event) -> None:
        f = self.ProductTable.focus()
        content = (self.ProductTable.item(f))
        row = content['values']
        if row:
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_stock.set(row[3])
            self.var_qty.set('1')

    def get_data_cart(self, ev: tk.Event) -> None:
        f = self.CartTable.focus()
        content = (self.CartTable.item(f))
        row = content['values']
        if row:
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_qty.set(row[3])

    def add_update_cart(self) -> None:
        if self.var_pid.get() == '':
            messagebox.showerror('Error', "Please select product from the list", parent=self.root)
            return
        elif self.var_qty.get() == '':
            messagebox.showerror('Error', "Quantity is required", parent=self.root)
            return
        
        try:
            qty = int(self.var_qty.get())
            stock = int(self.var_stock.get())
        except ValueError:
            messagebox.showerror('Error', "Invalid Quantity", parent=self.root)
            return

        if qty > stock:
            messagebox.showerror('Error', "Invalid Quantity, Not enough stock", parent=self.root)
            return

        price_calc = float(self.var_price.get())
        cart_data = [self.var_pid.get(), self.var_pname.get(), price_calc, qty]

        present = 'no'
        index_ = 0
        for row in self.cart_list:
            if self.var_pid.get() == str(row[0]):
                present = 'yes'
                break
            index_ += 1

        if present == 'yes':
            op = messagebox.askyesno('Confirm', "Product already present, Do you want to update | remove from the cart list?", parent=self.root)
            if op:
                if qty == 0:
                    self.cart_list.pop(index_)
                else:
                    self.cart_list[index_][3] = qty
        else:
            if qty > 0:
                self.cart_list.append(cart_data)

        self.show_cart()

    def show_cart(self) -> None:
        self.CartTable.delete(*self.CartTable.get_children())
        for row in self.cart_list:
            self.CartTable.insert('', tk.END, values=row)

    def clear_cart(self) -> None:
        self.cart_list.clear()
        self.show_cart()

    def generate_bill(self) -> None:
        if len(self.cart_list) == 0:
            messagebox.showerror("Error", "Please Add Product to Cart", parent=self.root)
            return
        
        bill_total = sum(float(row[2]) * int(row[3]) for row in self.cart_list)
        date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with sqlite3.connect(database="ims.db") as con:
                cur = con.cursor()
                cur.execute("INSERT INTO bills (date, total) VALUES(?,?)", (date_str, str(bill_total)))
                invoice_no = cur.lastrowid
                
                for row in self.cart_list:
                    pid = row[0]
                    qty = row[3]
                    cur.execute("SELECT qty FROM product WHERE pid=?", (pid,))
                    stock = int(cur.fetchone()[0])
                    new_stock = stock - qty
                    cur.execute("UPDATE product SET qty=? WHERE pid=?", (str(new_stock), pid))
                
                con.commit()

            bill_content = f"Invoice No: {invoice_no}\nDate: {date_str}\nCustomer: {self.var_cname.get()}\nContact: {self.var_contact.get()}\n"
            bill_content += "="*30 + "\n"
            bill_content += "Product\t\tQTY\tPrice\n"
            bill_content += "="*30 + "\n"
            for row in self.cart_list:
                bill_content += f"{row[1]}\t\t{row[3]}\t{row[2]}\n"
            bill_content += "="*30 + "\n"
            bill_content += f"Total Amount: {bill_total}\n"

            with open(f"bills/{invoice_no}.txt", "w") as f:
                f.write(bill_content)

            self.txt_bill_area.delete('1.0', tk.END)
            self.txt_bill_area.insert(tk.END, bill_content)
            
            messagebox.showinfo("Success", f"Bill Generated Successfully. Invoice No: {invoice_no}", parent=self.root)
            self.clear_cart()
            self.show()

        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def show_bill(self) -> None:
        invoice = self.var_invoice_search.get()
        if invoice == "":
            messagebox.showerror("Error", "Please enter invoice number", parent=self.root)
            return
        
        file_path = f"bills/{invoice}.txt"
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                content = f.read()
                self.txt_bill_area.delete('1.0', tk.END)
                self.txt_bill_area.insert(tk.END, content)
        else:
            messagebox.showerror("Error", "Invalid Invoice Number", parent=self.root)

class IMS:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.geometry("1350x700+0+0")
        self.root.title("Inventory Management System")

        create_db()

        img = Image.new('RGB', (50, 50), color = (73, 109, 137))
        self.icon_title = ImageTk.PhotoImage(img)
        title = tk.Label(self.root, text="Inventory Management System", image=self.icon_title, compound=tk.LEFT, font=("times new roman", 40, "bold"), bg="#010c48", fg="white", anchor="w", padx=20)
        title.place(x=0, y=0, relwidth=1, height=70)

        self.lbl_clock = tk.Label(self.root, text="Welcome to Inventory Management System\t\t Date: DD-MM-YYYY\t\t Time: HH:MM:SS", font=("times new roman", 15), bg="#4d636d", fg="white")
        self.lbl_clock.place(x=0, y=70, relwidth=1, height=30)

        LeftMenu = tk.Frame(self.root, bd=2, relief=tk.RIDGE, bg="white")
        LeftMenu.place(x=0, y=102, width=200, height=565)

        tk.Label(LeftMenu, text="Menu", font=("times new roman", 20), bg="#009688").pack(side=tk.TOP, fill=tk.X)
        tk.Button(LeftMenu, text="Employee", command=self.employee, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side=tk.TOP, fill=tk.X)
        tk.Button(LeftMenu, text="Supplier", command=self.supplier, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side=tk.TOP, fill=tk.X)
        tk.Button(LeftMenu, text="Category", command=self.category, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side=tk.TOP, fill=tk.X)
        tk.Button(LeftMenu, text="Product", command=self.product, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side=tk.TOP, fill=tk.X)
        tk.Button(LeftMenu, text="Billing", command=self.billing, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side=tk.TOP, fill=tk.X)
        tk.Button(LeftMenu, text="Exit", command=self.root.quit, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side=tk.TOP, fill=tk.X)

        self.lbl_employee = tk.Label(self.root, text="Total Employee\n[ 0 ]", bd=5, relief=tk.RIDGE, bg="#33bbf9", fg="white", font=("goudy old style", 20, "bold"))
        self.lbl_employee.place(x=300, y=120, height=150, width=300)

        self.lbl_supplier = tk.Label(self.root, text="Total Supplier\n[ 0 ]", bd=5, relief=tk.RIDGE, bg="#ff5722", fg="white", font=("goudy old style", 20, "bold"))
        self.lbl_supplier.place(x=650, y=120, height=150, width=300)

        self.lbl_category = tk.Label(self.root, text="Total Category\n[ 0 ]", bd=5, relief=tk.RIDGE, bg="#009688", fg="white", font=("goudy old style", 20, "bold"))
        self.lbl_category.place(x=1000, y=120, height=150, width=300)

        self.lbl_product = tk.Label(self.root, text="Total Product\n[ 0 ]", bd=5, relief=tk.RIDGE, bg="#607d8b", fg="white", font=("goudy old style", 20, "bold"))
        self.lbl_product.place(x=300, y=300, height=150, width=300)

        self.lbl_sales = tk.Label(self.root, text="Total Sales\n[ 0 ]", bd=5, relief=tk.RIDGE, bg="#ffc107", fg="white", font=("goudy old style", 20, "bold"))
        self.lbl_sales.place(x=650, y=300, height=150, width=300)

        self.update_time()
        self.update_dashboard()

    def update_time(self) -> None:
        time_ = datetime.datetime.now().strftime("%I:%M:%S %p")
        date_ = datetime.datetime.now().strftime("%d-%m-%Y")
        self.lbl_clock.config(text=f"Welcome to Inventory Management System\t\t Date: {date_}\t\t Time: {time_}")
        self.lbl_clock.after(1000, self.update_time)

    def update_dashboard(self) -> None:
        try:
            with sqlite3.connect(database="ims.db") as con:
                cur = con.cursor()
                cur.execute("SELECT * FROM employee")
                emp = cur.fetchall()
                self.lbl_employee.config(text=f"Total Employee\n[ {str(len(emp))} ]")

                cur.execute("SELECT * FROM supplier")
                sup = cur.fetchall()
                self.lbl_supplier.config(text=f"Total Supplier\n[ {str(len(sup))} ]")

                cur.execute("SELECT * FROM category")
                cat = cur.fetchall()
                self.lbl_category.config(text=f"Total Category\n[ {str(len(cat))} ]")

                cur.execute("SELECT * FROM product")
                prod = cur.fetchall()
                self.lbl_product.config(text=f"Total Product\n[ {str(len(prod))} ]")

                cur.execute("SELECT * FROM bills")
                bills = cur.fetchall()
                self.lbl_sales.config(text=f"Total Sales\n[ {str(len(bills))} ]")
        except Exception as ex:
            pass
        self.root.after(5000, self.update_dashboard)

    def employee(self) -> None:
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = EmployeeClass(self.new_win)

    def supplier(self) -> None:
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = SupplierClass(self.new_win)

    def category(self) -> None:
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = CategoryClass(self.new_win)

    def product(self) -> None:
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = ProductClass(self.new_win)

    def billing(self) -> None:
        self.new_win = tk.Toplevel(self.root)
        self.new_obj = BillingClass(self.new_win)

if __name__ == "__main__":
    root = tk.Tk()
    app = IMS(root)
    root.mainloop()