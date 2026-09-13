import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import datetime
from PIL import Image, ImageTk
from typing import Tuple, List, Any, Optional

class DatabaseManager:
    def __init__(self, db_name: str = "ims.db") -> None:
        self.db_name = db_name
        self.setup_database()

    def get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_name)

    def setup_database(self) -> None:
        con = self.get_connection()
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS employee (
                emp_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, email TEXT, gender TEXT, contact TEXT,
                dob TEXT, doj TEXT, pass TEXT, utype TEXT, address TEXT, salary TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS supplier (
                invoice_no INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, contact TEXT, desc TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS category (
                cid INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS product (
                pid INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT, supplier TEXT, name TEXT,
                price REAL, qty INTEGER, status TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bill (
                invoice_no TEXT PRIMARY KEY,
                date TEXT, total REAL, discount REAL, net_pay REAL
            )
        """)
        con.commit()
        con.close()

        if not os.path.exists("bills"):
            os.makedirs("bills")

class EmployeeManager(tk.Toplevel):
    def __init__(self, parent: tk.Tk, db: DatabaseManager) -> None:
        super().__init__(parent)
        self.title("Employee Management")
        self.geometry("1100x500+220+130")
        self.config(bg="white")
        self.focus_force()
        self.db = db

        self.var_emp_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_gender = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_dob = tk.StringVar()
        self.var_doj = tk.StringVar()
        self.var_pass = tk.StringVar()
        self.var_utype = tk.StringVar()
        self.var_salary = tk.StringVar()

        self.setup_ui()
        self.fetch_data()

    def setup_ui(self) -> None:
        title = tk.Label(self, text="Manage Employee Details", font=("goudy old style", 15), bg="#0f4d7d", fg="white")
        title.pack(side=tk.TOP, fill=tk.X)

        tk.Label(self, text="Emp ID", font=("goudy old style", 15), bg="white").place(x=50, y=50)
        tk.Entry(self, textvariable=self.var_emp_id, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=50, width=180)

        tk.Label(self, text="Gender", font=("goudy old style", 15), bg="white").place(x=350, y=50)
        cmb_gender = ttk.Combobox(self, textvariable=self.var_gender, values=("Select", "Male", "Female", "Other"), state="readonly", justify=tk.CENTER, font=("goudy old style", 15))
        cmb_gender.place(x=500, y=50, width=180)
        cmb_gender.current(0)

        tk.Label(self, text="Contact", font=("goudy old style", 15), bg="white").place(x=750, y=50)
        tk.Entry(self, textvariable=self.var_contact, font=("goudy old style", 15), bg="lightyellow").place(x=850, y=50, width=180)

        tk.Label(self, text="Name", font=("goudy old style", 15), bg="white").place(x=50, y=90)
        tk.Entry(self, textvariable=self.var_name, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=90, width=180)

        tk.Label(self, text="DOB", font=("goudy old style", 15), bg="white").place(x=350, y=90)
        tk.Entry(self, textvariable=self.var_dob, font=("goudy old style", 15), bg="lightyellow").place(x=500, y=90, width=180)

        tk.Label(self, text="DOJ", font=("goudy old style", 15), bg="white").place(x=750, y=90)
        tk.Entry(self, textvariable=self.var_doj, font=("goudy old style", 15), bg="lightyellow").place(x=850, y=90, width=180)

        tk.Label(self, text="Email", font=("goudy old style", 15), bg="white").place(x=50, y=130)
        tk.Entry(self, textvariable=self.var_email, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=130, width=180)

        tk.Label(self, text="Password", font=("goudy old style", 15), bg="white").place(x=350, y=130)
        tk.Entry(self, textvariable=self.var_pass, font=("goudy old style", 15), bg="lightyellow").place(x=500, y=130, width=180)

        tk.Label(self, text="User Type", font=("goudy old style", 15), bg="white").place(x=750, y=130)
        cmb_utype = ttk.Combobox(self, textvariable=self.var_utype, values=("Admin", "Employee"), state="readonly", justify=tk.CENTER, font=("goudy old style", 15))
        cmb_utype.place(x=850, y=130, width=180)
        cmb_utype.current(0)

        tk.Label(self, text="Address", font=("goudy old style", 15), bg="white").place(x=50, y=170)
        self.txt_address = tk.Text(self, font=("goudy old style", 15), bg="lightyellow")
        self.txt_address.place(x=150, y=170, width=300, height=60)

        tk.Label(self, text="Salary", font=("goudy old style", 15), bg="white").place(x=500, y=170)
        tk.Entry(self, textvariable=self.var_salary, font=("goudy old style", 15), bg="lightyellow").place(x=600, y=170, width=180)

        tk.Button(self, text="Save", command=self.add, font=("goudy old style", 15), bg="#2196f3", fg="white", cursor="hand2").place(x=500, y=205, width=110, height=28)
        tk.Button(self, text="Update", command=self.update, font=("goudy old style", 15), bg="#4caf50", fg="white", cursor="hand2").place(x=620, y=205, width=110, height=28)
        tk.Button(self, text="Delete", command=self.delete, font=("goudy old style", 15), bg="#f44336", fg="white", cursor="hand2").place(x=740, y=205, width=110, height=28)
        tk.Button(self, text="Clear", command=self.clear, font=("goudy old style", 15), bg="#607d8b", fg="white", cursor="hand2").place(x=860, y=205, width=110, height=28)

        emp_frame = tk.Frame(self, bd=3, relief=tk.RIDGE)
        emp_frame.place(x=0, y=250, relwidth=1, height=250)

        scrolly = tk.Scrollbar(emp_frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(emp_frame, orient=tk.HORIZONTAL)

        self.employee_table = ttk.Treeview(emp_frame, columns=("emp_id", "name", "email", "gender", "contact", "dob", "doj", "pass", "utype", "address", "salary"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.employee_table.xview)
        scrolly.config(command=self.employee_table.yview)

        for col in self.employee_table["columns"]:
            self.employee_table.heading(col, text=col.capitalize())
            self.employee_table.column(col, width=100)
        
        self.employee_table["show"] = "headings"
        self.employee_table.pack(fill=tk.BOTH, expand=1)
        self.employee_table.bind("<ButtonRelease-1>", self.get_data)

    def add(self) -> None:
        try:
            if self.var_emp_id.get() == "":
                messagebox.showerror("Error", "Employee ID Must be required", parent=self)
                return
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM employee WHERE emp_id=?", (self.var_emp_id.get(),))
            if cur.fetchone() is not None:
                messagebox.showerror("Error", "This Employee ID already assigned", parent=self)
            else:
                cur.execute("INSERT INTO employee (emp_id, name, email, gender, contact, dob, doj, pass, utype, address, salary) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                    self.var_emp_id.get(), self.var_name.get(), self.var_email.get(), self.var_gender.get(),
                    self.var_contact.get(), self.var_dob.get(), self.var_doj.get(), self.var_pass.get(),
                    self.var_utype.get(), self.txt_address.get('1.0', tk.END).strip(), self.var_salary.get()
                ))
                con.commit()
                messagebox.showinfo("Success", "Employee Added Successfully", parent=self)
                self.fetch_data()
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def fetch_data(self) -> None:
        try:
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM employee")
            rows = cur.fetchall()
            self.employee_table.delete(*self.employee_table.get_children())
            for row in rows:
                self.employee_table.insert('', tk.END, values=row)
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def get_data(self, ev: Any) -> None:
        f = self.employee_table.focus()
        content = self.employee_table.item(f)
        row = content['values']
        if not row: return
        self.var_emp_id.set(row[0])
        self.var_name.set(row[1])
        self.var_email.set(row[2])
        self.var_gender.set(row[3])
        self.var_contact.set(row[4])
        self.var_dob.set(row[5])
        self.var_doj.set(row[6])
        self.var_pass.set(row[7])
        self.var_utype.set(row[8])
        self.txt_address.delete('1.0', tk.END)
        self.txt_address.insert(tk.END, row[9])
        self.var_salary.set(row[10])

    def update(self) -> None:
        try:
            if self.var_emp_id.get() == "":
                messagebox.showerror("Error", "Employee ID Must be required", parent=self)
                return
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM employee WHERE emp_id=?", (self.var_emp_id.get(),))
            if cur.fetchone() is None:
                messagebox.showerror("Error", "Invalid Employee ID", parent=self)
            else:
                cur.execute("UPDATE employee SET name=?, email=?, gender=?, contact=?, dob=?, doj=?, pass=?, utype=?, address=?, salary=? WHERE emp_id=?", (
                    self.var_name.get(), self.var_email.get(), self.var_gender.get(),
                    self.var_contact.get(), self.var_dob.get(), self.var_doj.get(), self.var_pass.get(),
                    self.var_utype.get(), self.txt_address.get('1.0', tk.END).strip(), self.var_salary.get(),
                    self.var_emp_id.get()
                ))
                con.commit()
                messagebox.showinfo("Success", "Employee Updated Successfully", parent=self)
                self.fetch_data()
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def delete(self) -> None:
        try:
            if self.var_emp_id.get() == "":
                messagebox.showerror("Error", "Employee ID Must be required", parent=self)
                return
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM employee WHERE emp_id=?", (self.var_emp_id.get(),))
            if cur.fetchone() is None:
                messagebox.showerror("Error", "Invalid Employee ID", parent=self)
            else:
                op = messagebox.askyesno("Confirm", "Do you really want to delete?", parent=self)
                if op:
                    cur.execute("DELETE FROM employee WHERE emp_id=?", (self.var_emp_id.get(),))
                    con.commit()
                    messagebox.showinfo("Delete", "Employee Deleted Successfully", parent=self)
                    self.clear()
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def clear(self) -> None:
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_email.set("")
        self.var_gender.set("Select")
        self.var_contact.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_pass.set("")
        self.var_utype.set("Admin")
        self.txt_address.delete('1.0', tk.END)
        self.var_salary.set("")
        self.fetch_data()

class SupplierManager(tk.Toplevel):
    def __init__(self, parent: tk.Tk, db: DatabaseManager) -> None:
        super().__init__(parent)
        self.title("Supplier Management")
        self.geometry("1100x500+220+130")
        self.config(bg="white")
        self.focus_force()
        self.db = db

        self.var_sup_invoice = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_contact = tk.StringVar()

        self.setup_ui()
        self.fetch_data()

    def setup_ui(self) -> None:
        tk.Label(self, text="Manage Supplier Details", font=("goudy old style", 20, "bold"), bg="#0f4d7d", fg="white").pack(side=tk.TOP, fill=tk.X)

        tk.Label(self, text="Invoice No.", font=("goudy old style", 15), bg="white").place(x=50, y=80)
        tk.Entry(self, textvariable=self.var_sup_invoice, font=("goudy old style", 15), bg="lightyellow").place(x=180, y=80, width=180)

        tk.Label(self, text="Name", font=("goudy old style", 15), bg="white").place(x=50, y=120)
        tk.Entry(self, textvariable=self.var_name, font=("goudy old style", 15), bg="lightyellow").place(x=180, y=120, width=180)

        tk.Label(self, text="Contact", font=("goudy old style", 15), bg="white").place(x=50, y=160)
        tk.Entry(self, textvariable=self.var_contact, font=("goudy old style", 15), bg="lightyellow").place(x=180, y=160, width=180)

        tk.Label(self, text="Description", font=("goudy old style", 15), bg="white").place(x=50, y=200)
        self.txt_desc = tk.Text(self, font=("goudy old style", 15), bg="lightyellow")
        self.txt_desc.place(x=180, y=200, width=470, height=120)

        tk.Button(self, text="Save", command=self.add, font=("goudy old style", 15), bg="#2196f3", fg="white", cursor="hand2").place(x=180, y=370, width=110, height=35)
        tk.Button(self, text="Update", command=self.update, font=("goudy old style", 15), bg="#4caf50", fg="white", cursor="hand2").place(x=300, y=370, width=110, height=35)
        tk.Button(self, text="Delete", command=self.delete, font=("goudy old style", 15), bg="#f44336", fg="white", cursor="hand2").place(x=420, y=370, width=110, height=35)
        tk.Button(self, text="Clear", command=self.clear, font=("goudy old style", 15), bg="#607d8b", fg="white", cursor="hand2").place(x=540, y=370, width=110, height=35)

        sup_frame = tk.Frame(self, bd=3, relief=tk.RIDGE)
        sup_frame.place(x=700, y=80, width=380, height=350)

        scrolly = tk.Scrollbar(sup_frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(sup_frame, orient=tk.HORIZONTAL)

        self.supplier_table = ttk.Treeview(sup_frame, columns=("invoice_no", "name", "contact", "desc"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.supplier_table.xview)
        scrolly.config(command=self.supplier_table.yview)

        self.supplier_table.heading("invoice_no", text="Invoice No.")
        self.supplier_table.heading("name", text="Name")
        self.supplier_table.heading("contact", text="Contact")
        self.supplier_table.heading("desc", text="Description")
        self.supplier_table["show"] = "headings"
        self.supplier_table.pack(fill=tk.BOTH, expand=1)
        self.supplier_table.bind("<ButtonRelease-1>", self.get_data)

    def add(self) -> None:
        try:
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice No. Must be required", parent=self)
                return
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM supplier WHERE invoice_no=?", (self.var_sup_invoice.get(),))
            if cur.fetchone() is not None:
                messagebox.showerror("Error", "Invoice No. already assigned", parent=self)
            else:
                cur.execute("INSERT INTO supplier (invoice_no, name, contact, desc) VALUES(?,?,?,?)", (
                    self.var_sup_invoice.get(), self.var_name.get(), self.var_contact.get(),
                    self.txt_desc.get('1.0', tk.END).strip()
                ))
                con.commit()
                messagebox.showinfo("Success", "Supplier Added Successfully", parent=self)
                self.fetch_data()
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def fetch_data(self) -> None:
        try:
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM supplier")
            rows = cur.fetchall()
            self.supplier_table.delete(*self.supplier_table.get_children())
            for row in rows:
                self.supplier_table.insert('', tk.END, values=row)
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def get_data(self, ev: Any) -> None:
        f = self.supplier_table.focus()
        content = self.supplier_table.item(f)
        row = content['values']
        if not row: return
        self.var_sup_invoice.set(row[0])
        self.var_name.set(row[1])
        self.var_contact.set(row[2])
        self.txt_desc.delete('1.0', tk.END)
        self.txt_desc.insert(tk.END, row[3])

    def update(self) -> None:
        try:
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice No. Must be required", parent=self)
                return
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM supplier WHERE invoice_no=?", (self.var_sup_invoice.get(),))
            if cur.fetchone() is None:
                messagebox.showerror("Error", "Invalid Invoice No.", parent=self)
            else:
                cur.execute("UPDATE supplier SET name=?, contact=?, desc=? WHERE invoice_no=?", (
                    self.var_name.get(), self.var_contact.get(),
                    self.txt_desc.get('1.0', tk.END).strip(), self.var_sup_invoice.get()
                ))
                con.commit()
                messagebox.showinfo("Success", "Supplier Updated Successfully", parent=self)
                self.fetch_data()
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def delete(self) -> None:
        try:
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice No. Must be required", parent=self)
                return
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM supplier WHERE invoice_no=?", (self.var_sup_invoice.get(),))
            if cur.fetchone() is None:
                messagebox.showerror("Error", "Invalid Invoice No.", parent=self)
            else:
                op = messagebox.askyesno("Confirm", "Do you really want to delete?", parent=self)
                if op:
                    cur.execute("DELETE FROM supplier WHERE invoice_no=?", (self.var_sup_invoice.get(),))
                    con.commit()
                    messagebox.showinfo("Delete", "Supplier Deleted Successfully", parent=self)
                    self.clear()
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def clear(self) -> None:
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete('1.0', tk.END)
        self.fetch_data()

class CategoryManager(tk.Toplevel):
    def __init__(self, parent: tk.Tk, db: DatabaseManager) -> None:
        super().__init__(parent)
        self.title("Category Management")
        self.geometry("500x400+400+150")
        self.config(bg="white")
        self.focus_force()
        self.db = db

        self.var_cat_id = tk.StringVar()
        self.var_name = tk.StringVar()

        self.setup_ui()
        self.fetch_data()

    def setup_ui(self) -> None:
        tk.Label(self, text="Manage Product Category", font=("goudy old style", 20), bg="#184a45", fg="white").pack(side=tk.TOP, fill=tk.X)

        tk.Label(self, text="Enter Category Name", font=("goudy old style", 15), bg="white").place(x=50, y=60)
        tk.Entry(self, textvariable=self.var_name, font=("goudy old style", 15), bg="lightyellow").place(x=50, y=100, width=250)

        tk.Button(self, text="Add", command=self.add, font=("goudy old style", 15), bg="#4caf50", fg="white", cursor="hand2").place(x=320, y=100, width=100, height=30)
        tk.Button(self, text="Delete", command=self.delete, font=("goudy old style", 15), bg="#f44336", fg="white", cursor="hand2").place(x=320, y=140, width=100, height=30)

        cat_frame = tk.Frame(self, bd=3, relief=tk.RIDGE)
        cat_frame.place(x=50, y=190, width=400, height=180)

        scrolly = tk.Scrollbar(cat_frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(cat_frame, orient=tk.HORIZONTAL)

        self.category_table = ttk.Treeview(cat_frame, columns=("cid", "name"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.category_table.xview)
        scrolly.config(command=self.category_table.yview)

        self.category_table.heading("cid", text="C ID")
        self.category_table.heading("name", text="Name")
        self.category_table["show"] = "headings"
        self.category_table.pack(fill=tk.BOTH, expand=1)
        self.category_table.bind("<ButtonRelease-1>", self.get_data)

    def add(self) -> None:
        try:
            if self.var_name.get() == "":
                messagebox.showerror("Error", "Category Name Must be required", parent=self)
                return
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM category WHERE name=?", (self.var_name.get(),))
            if cur.fetchone() is not None:
                messagebox.showerror("Error", "Category already present", parent=self)
            else:
                cur.execute("INSERT INTO category (name) VALUES(?)", (self.var_name.get(),))
                con.commit()
                messagebox.showinfo("Success", "Category Added Successfully", parent=self)
                self.fetch_data()
                self.var_name.set("")
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def fetch_data(self) -> None:
        try:
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM category")
            rows = cur.fetchall()
            self.category_table.delete(*self.category_table.get_children())
            for row in rows:
                self.category_table.insert('', tk.END, values=row)
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def get_data(self, ev: Any) -> None:
        f = self.category_table.focus()
        content = self.category_table.item(f)
        row = content['values']
        if not row: return
        self.var_cat_id.set(row[0])
        self.var_name.set(row[1])

    def delete(self) -> None:
        try:
            if self.var_cat_id.get() == "":
                messagebox.showerror("Error", "Please select category from list", parent=self)
                return
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM category WHERE cid=?", (self.var_cat_id.get(),))
            if cur.fetchone() is None:
                messagebox.showerror("Error", "Invalid Category", parent=self)
            else:
                op = messagebox.askyesno("Confirm", "Do you really want to delete?", parent=self)
                if op:
                    cur.execute("DELETE FROM category WHERE cid=?", (self.var_cat_id.get(),))
                    con.commit()
                    messagebox.showinfo("Delete", "Category Deleted Successfully", parent=self)
                    self.fetch_data()
                    self.var_cat_id.set("")
                    self.var_name.set("")
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

class ProductManager(tk.Toplevel):
    def __init__(self, parent: tk.Tk, db: DatabaseManager) -> None:
        super().__init__(parent)
        self.title("Product Management")
        self.geometry("1100x500+220+130")
        self.config(bg="white")
        self.focus_force()
        self.db = db

        self.var_pid = tk.StringVar()
        self.var_cat = tk.StringVar()
        self.var_sup = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_status = tk.StringVar()

        self.cat_list: List[str] = []
        self.sup_list: List[str] = []
        self.fetch_cat_sup()

        self.setup_ui()
        self.fetch_data()

    def fetch_cat_sup(self) -> None:
        try:
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT name FROM category")
            cat = cur.fetchall()
            self.cat_list.append("Empty")
            if len(cat) > 0:
                self.cat_list = ["Select"] + [row[0] for row in cat]
            
            cur.execute("SELECT name FROM supplier")
            sup = cur.fetchall()
            self.sup_list.append("Empty")
            if len(sup) > 0:
                self.sup_list = ["Select"] + [row[0] for row in sup]
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def setup_ui(self) -> None:
        product_frame = tk.Frame(self, bd=2, relief=tk.RIDGE, bg="white")
        product_frame.place(x=10, y=10, width=450, height=480)

        tk.Label(product_frame, text="Manage Product Details", font=("goudy old style", 18), bg="#0f4d7d", fg="white").pack(side=tk.TOP, fill=tk.X)

        tk.Label(product_frame, text="Category", font=("goudy old style", 15), bg="white").place(x=30, y=60)
        cmb_cat = ttk.Combobox(product_frame, textvariable=self.var_cat, values=self.cat_list, state="readonly", justify=tk.CENTER, font=("goudy old style", 15))
        cmb_cat.place(x=150, y=60, width=200)
        cmb_cat.current(0)

        tk.Label(product_frame, text="Supplier", font=("goudy old style", 15), bg="white").place(x=30, y=110)
        cmb_sup = ttk.Combobox(product_frame, textvariable=self.var_sup, values=self.sup_list, state="readonly", justify=tk.CENTER, font=("goudy old style", 15))
        cmb_sup.place(x=150, y=110, width=200)
        cmb_sup.current(0)

        tk.Label(product_frame, text="Name", font=("goudy old style", 15), bg="white").place(x=30, y=160)
        tk.Entry(product_frame, textvariable=self.var_name, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=160, width=200)

        tk.Label(product_frame, text="Price", font=("goudy old style", 15), bg="white").place(x=30, y=210)
        tk.Entry(product_frame, textvariable=self.var_price, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=210, width=200)

        tk.Label(product_frame, text="Quantity", font=("goudy old style", 15), bg="white").place(x=30, y=260)
        tk.Entry(product_frame, textvariable=self.var_qty, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=260, width=200)

        tk.Label(product_frame, text="Status", font=("goudy old style", 15), bg="white").place(x=30, y=310)
        cmb_status = ttk.Combobox(product_frame, textvariable=self.var_status, values=("Active", "Inactive"), state="readonly", justify=tk.CENTER, font=("goudy old style", 15))
        cmb_status.place(x=150, y=310, width=200)
        cmb_status.current(0)

        tk.Button(product_frame, text="Save", command=self.add, font=("goudy old style", 15), bg="#2196f3", fg="white", cursor="hand2").place(x=10, y=400, width=100, height=40)
        tk.Button(product_frame, text="Update", command=self.update, font=("goudy old style", 15), bg="#4caf50", fg="white", cursor="hand2").place(x=120, y=400, width=100, height=40)
        tk.Button(product_frame, text="Delete", command=self.delete, font=("goudy old style", 15), bg="#f44336", fg="white", cursor="hand2").place(x=230, y=400, width=100, height=40)
        tk.Button(product_frame, text="Clear", command=self.clear, font=("goudy old style", 15), bg="#607d8b", fg="white", cursor="hand2").place(x=340, y=400, width=100, height=40)

        p_frame = tk.Frame(self, bd=3, relief=tk.RIDGE)
        p_frame.place(x=480, y=10, width=600, height=480)

        scrolly = tk.Scrollbar(p_frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(p_frame, orient=tk.HORIZONTAL)

        self.product_table = ttk.Treeview(p_frame, columns=("pid", "Category", "Supplier", "name", "price", "qty", "status"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.product_table.xview)
        scrolly.config(command=self.product_table.yview)

        self.product_table.heading("pid", text="P ID")
        self.product_table.heading("Category", text="Category")
        self.product_table.heading("Supplier", text="Supplier")
        self.product_table.heading("name", text="Name")
        self.product_table.heading("price", text="Price")
        self.product_table.heading("qty", text="Qty")
        self.product_table.heading("status", text="Status")
        self.product_table["show"] = "headings"
        self.product_table.pack(fill=tk.BOTH, expand=1)
        self.product_table.bind("<ButtonRelease-1>", self.get_data)

    def add(self) -> None:
        try:
            if self.var_cat.get() == "Select" or self.var_cat.get() == "Empty" or self.var_sup.get() == "Select" or self.var_name.get() == "":
                messagebox.showerror("Error", "All fields are required", parent=self)
                return
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM product WHERE name=?", (self.var_name.get(),))
            if cur.fetchone() is not None:
                messagebox.showerror("Error", "Product already present", parent=self)
            else:
                cur.execute("INSERT INTO product (category, supplier, name, price, qty, status) VALUES(?,?,?,?,?,?)", (
                    self.var_cat.get(), self.var_sup.get(), self.var_name.get(),
                    self.var_price.get(), self.var_qty.get(), self.var_status.get()
                ))
                con.commit()
                messagebox.showinfo("Success", "Product Added Successfully", parent=self)
                self.fetch_data()
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def fetch_data(self) -> None:
        try:
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM product")
            rows = cur.fetchall()
            self.product_table.delete(*self.product_table.get_children())
            for row in rows:
                self.product_table.insert('', tk.END, values=row)
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def get_data(self, ev: Any) -> None:
        f = self.product_table.focus()
        content = self.product_table.item(f)
        row = content['values']
        if not row: return
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
                messagebox.showerror("Error", "Please select product from list", parent=self)
                return
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM product WHERE pid=?", (self.var_pid.get(),))
            if cur.fetchone() is None:
                messagebox.showerror("Error", "Invalid Product", parent=self)
            else:
                cur.execute("UPDATE product SET category=?, supplier=?, name=?, price=?, qty=?, status=? WHERE pid=?", (
                    self.var_cat.get(), self.var_sup.get(), self.var_name.get(),
                    self.var_price.get(), self.var_qty.get(), self.var_status.get(), self.var_pid.get()
                ))
                con.commit()
                messagebox.showinfo("Success", "Product Updated Successfully", parent=self)
                self.fetch_data()
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def delete(self) -> None:
        try:
            if self.var_pid.get() == "":
                messagebox.showerror("Error", "Select Product from list", parent=self)
                return
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT * FROM product WHERE pid=?", (self.var_pid.get(),))
            if cur.fetchone() is None:
                messagebox.showerror("Error", "Invalid Product", parent=self)
            else:
                op = messagebox.askyesno("Confirm", "Do you really want to delete?", parent=self)
                if op:
                    cur.execute("DELETE FROM product WHERE pid=?", (self.var_pid.get(),))
                    con.commit()
                    messagebox.showinfo("Delete", "Product Deleted Successfully", parent=self)
                    self.clear()
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def clear(self) -> None:
        self.var_pid.set("")
        self.var_cat.set("Select")
        self.var_sup.set("Select")
        self.var_name.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("Active")
        self.fetch_data()

class ViewBillsManager(tk.Toplevel):
    def __init__(self, parent: tk.Tk, db: DatabaseManager) -> None:
        super().__init__(parent)
        self.title("View Bills")
        self.geometry("800x500+300+130")
        self.config(bg="white")
        self.focus_force()
        self.db = db

        self.setup_ui()
        self.fetch_bills()

    def setup_ui(self) -> None:
        tk.Label(self, text="Saved Bills", font=("goudy old style", 20, "bold"), bg="#0f4d7d", fg="white").pack(side=tk.TOP, fill=tk.X)

        list_frame = tk.Frame(self, bd=3, relief=tk.RIDGE)
        list_frame.place(x=10, y=50, width=250, height=430)

        scrolly = tk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.bill_list = tk.Listbox(list_frame, font=("goudy old style", 15), yscrollcommand=scrolly.set)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrolly.config(command=self.bill_list.yview)
        self.bill_list.pack(fill=tk.BOTH, expand=1)
        self.bill_list.bind("<ButtonRelease-1>", self.get_bill_data)

        bill_frame = tk.Frame(self, bd=3, relief=tk.RIDGE)
        bill_frame.place(x=270, y=50, width=510, height=430)

        scrolly2 = tk.Scrollbar(bill_frame, orient=tk.VERTICAL)
        self.txt_bill_area = tk.Text(bill_frame, font=("goudy old style", 12), yscrollcommand=scrolly2.set)
        scrolly2.pack(side=tk.RIGHT, fill=tk.Y)
        scrolly2.config(command=self.txt_bill_area.yview)
        self.txt_bill_area.pack(fill=tk.BOTH, expand=1)

    def fetch_bills(self) -> None:
        self.bill_list.delete(0, tk.END)
        for file in os.listdir("bills"):
            if file.endswith(".txt"):
                self.bill_list.insert(tk.END, file)

    def get_bill_data(self, ev: Any) -> None:
        index_ = self.bill_list.curselection()
        if not index_: return
        file_name = self.bill_list.get(index_)
        self.txt_bill_area.delete('1.0', tk.END)
        try:
            with open(f"bills/{file_name}", "r") as f:
                for line in f:
                    self.txt_bill_area.insert(tk.END, line)
        except Exception as ex:
            messagebox.showerror("Error", f"Error reading bill: {str(ex)}", parent=self)

class BillingManager(tk.Toplevel):
    def __init__(self, parent: tk.Tk, db: DatabaseManager) -> None:
        super().__init__(parent)
        self.title("Billing Area")
        self.geometry("1350x700+0+0")
        self.config(bg="white")
        self.focus_force()
        self.db = db

        self.cart_list: List[Tuple[str, str, str, str, str]] = []
        self.var_search = tk.StringVar()
        self.var_cname = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.chk_print = tk.IntVar()

        self.setup_ui()
        self.fetch_all_products()

    def setup_ui(self) -> None:
        title = tk.Label(self, text="Inventory Management System - Billing", font=("times new roman", 30, "bold"), bg="#010c48", fg="white")
        title.pack(side=tk.TOP, fill=tk.X)

        ProductFrame1 = tk.Frame(self, bd=4, relief=tk.RIDGE, bg="white")
        ProductFrame1.place(x=10, y=60, width=410, height=550)

        pTitle = tk.Label(ProductFrame1, text="All Products", font=("goudy old style", 20, "bold"), bg="#262626", fg="white")
        pTitle.pack(side=tk.TOP, fill=tk.X)

        ProductFrame2 = tk.Frame(ProductFrame1, bd=2, relief=tk.RIDGE, bg="white")
        ProductFrame2.place(x=2, y=42, width=398, height=90)

        tk.Label(ProductFrame2, text="Search Product | By Name", font=("times new roman", 15, "bold"), bg="white", fg="green").place(x=2, y=5)
        tk.Label(ProductFrame2, text="Product Name", font=("times new roman", 15, "bold"), bg="white").place(x=2, y=45)
        tk.Entry(ProductFrame2, textvariable=self.var_search, font=("times new roman", 15), bg="lightyellow").place(x=128, y=47, width=150, height=22)
        tk.Button(ProductFrame2, text="Search", command=self.search, font=("goudy old style", 15), bg="#2196f3", fg="white", cursor="hand2").place(x=285, y=45, width=100, height=25)
        tk.Button(ProductFrame2, text="Show All", command=self.fetch_all_products, font=("goudy old style", 15), bg="#083531", fg="white", cursor="hand2").place(x=285, y=10, width=100, height=25)

        ProductFrame3 = tk.Frame(ProductFrame1, bd=3, relief=tk.RIDGE)
        ProductFrame3.place(x=2, y=140, width=398, height=375)

        scrolly = tk.Scrollbar(ProductFrame3, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(ProductFrame3, orient=tk.HORIZONTAL)

        self.product_table = ttk.Treeview(ProductFrame3, columns=("pid", "name", "price", "qty", "status"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.product_table.xview)
        scrolly.config(command=self.product_table.yview)

        self.product_table.heading("pid", text="PID")
        self.product_table.heading("name", text="Name")
        self.product_table.heading("price", text="Price")
        self.product_table.heading("qty", text="QTY")
        self.product_table.heading("status", text="Status")
        self.product_table["show"] = "headings"
        self.product_table.column("pid", width=40)
        self.product_table.column("name", width=100)
        self.product_table.column("price", width=70)
        self.product_table.column("qty", width=40)
        self.product_table.column("status", width=70)
        self.product_table.pack(fill=tk.BOTH, expand=1)
        self.product_table.bind("<ButtonRelease-1>", self.get_product_data)

        tk.Label(ProductFrame1, text="Note: 'Enter 0 Quantity to remove product from Cart'", font=("goudy old style", 12), bg="white", fg="red").pack(side=tk.BOTTOM, fill=tk.X)

        CustomerFrame = tk.Frame(self, bd=4, relief=tk.RIDGE, bg="white")
        CustomerFrame.place(x=430, y=60, width=530, height=70)

        tk.Label(CustomerFrame, text="Customer Details", font=("goudy old style", 15), bg="white").place(x=5, y=5)
        tk.Label(CustomerFrame, text="Name", font=("times new roman", 15), bg="white").place(x=5, y=35)
        tk.Entry(CustomerFrame, textvariable=self.var_cname, font=("times new roman", 13), bg="lightyellow").place(x=60, y=35, width=180)
        tk.Label(CustomerFrame, text="Contact No.", font=("times new roman", 15), bg="white").place(x=250, y=35)
        tk.Entry(CustomerFrame, textvariable=self.var_contact, font=("times new roman", 13), bg="lightyellow").place(x=350, y=35, width=160)

        Cal_Cart_Frame = tk.Frame(self, bd=2, relief=tk.RIDGE, bg="white")
        Cal_Cart_Frame.place(x=430, y=135, width=530, height=360)

        self.var_cal_input = tk.StringVar()
        Cal_Frame = tk.Frame(Cal_Cart_Frame, bd=9, relief=tk.RIDGE, bg="white")
        Cal_Frame.place(x=5, y=10, width=268, height=340)

        txt_cal_input = tk.Entry(Cal_Frame, textvariable=self.var_cal_input, font=('arial', 15, 'bold'), width=21, bd=10, relief=tk.GROOVE, state='readonly', justify=tk.RIGHT)
        txt_cal_input.grid(row=0, columnspan=4)

        btn_7 = tk.Button(Cal_Frame, text='7', font=('arial', 15, 'bold'), command=lambda: self.get_input(7), bd=5, width=4, pady=10, cursor="hand2").grid(row=1, column=0)
        btn_8 = tk.Button(Cal_Frame, text='8', font=('arial', 15, 'bold'), command=lambda: self.get_input(8), bd=5, width=4, pady=10, cursor="hand2").grid(row=1, column=1)
        btn_9 = tk.Button(Cal_Frame, text='9', font=('arial', 15, 'bold'), command=lambda: self.get_input(9), bd=5, width=4, pady=10, cursor="hand2").grid(row=1, column=2)
        btn_sum = tk.Button(Cal_Frame, text='+', font=('arial', 15, 'bold'), command=lambda: self.get_input('+'), bd=5, width=4, pady=10, cursor="hand2").grid(row=1, column=3)

        btn_4 = tk.Button(Cal_Frame, text='4', font=('arial', 15, 'bold'), command=lambda: self.get_input(4), bd=5, width=4, pady=10, cursor="hand2").grid(row=2, column=0)
        btn_5 = tk.Button(Cal_Frame, text='5', font=('arial', 15, 'bold'), command=lambda: self.get_input(5), bd=5, width=4, pady=10, cursor="hand2").grid(row=2, column=1)
        btn_6 = tk.Button(Cal_Frame, text='6', font=('arial', 15, 'bold'), command=lambda: self.get_input(6), bd=5, width=4, pady=10, cursor="hand2").grid(row=2, column=2)
        btn_sub = tk.Button(Cal_Frame, text='-', font=('arial', 15, 'bold'), command=lambda: self.get_input('-'), bd=5, width=4, pady=10, cursor="hand2").grid(row=2, column=3)

        btn_1 = tk.Button(Cal_Frame, text='1', font=('arial', 15, 'bold'), command=lambda: self.get_input(1), bd=5, width=4, pady=10, cursor="hand2").grid(row=3, column=0)
        btn_2 = tk.Button(Cal_Frame, text='2', font=('arial', 15, 'bold'), command=lambda: self.get_input(2), bd=5, width=4, pady=10, cursor="hand2").grid(row=3, column=1)
        btn_3 = tk.Button(Cal_Frame, text='3', font=('arial', 15, 'bold'), command=lambda: self.get_input(3), bd=5, width=4, pady=10, cursor="hand2").grid(row=3, column=2)
        btn_mul = tk.Button(Cal_Frame, text='*', font=('arial', 15, 'bold'), command=lambda: self.get_input('*'), bd=5, width=4, pady=10, cursor="hand2").grid(row=3, column=3)

        btn_0 = tk.Button(Cal_Frame, text='0', font=('arial', 15, 'bold'), command=lambda: self.get_input(0), bd=5, width=4, pady=15, cursor="hand2").grid(row=4, column=0)
        btn_c = tk.Button(Cal_Frame, text='c', font=('arial', 15, 'bold'), command=self.clear_cal, bd=5, width=4, pady=15, cursor="hand2").grid(row=4, column=1)
        btn_eq = tk.Button(Cal_Frame, text='=', font=('arial', 15, 'bold'), command=self.perform_cal, bd=5, width=4, pady=15, cursor="hand2").grid(row=4, column=2)
        btn_div = tk.Button(Cal_Frame, text='/', font=('arial', 15, 'bold'), command=lambda: self.get_input('/'), bd=5, width=4, pady=15, cursor="hand2").grid(row=4, column=3)

        cart_Frame = tk.Frame(Cal_Cart_Frame, bd=3, relief=tk.RIDGE)
        cart_Frame.place(x=280, y=8, width=245, height=342)
        self.cartTitle = tk.Label(cart_Frame, text="Cart \t Total Product: [0]", font=("goudy old style", 15), bg="lightgray")
        self.cartTitle.pack(side=tk.TOP, fill=tk.X)

        scrolly_cart = tk.Scrollbar(cart_Frame, orient=tk.VERTICAL)
        scrollx_cart = tk.Scrollbar(cart_Frame, orient=tk.HORIZONTAL)

        self.CartTable = ttk.Treeview(cart_Frame, columns=("pid", "name", "price", "qty"), yscrollcommand=scrolly_cart.set, xscrollcommand=scrollx_cart.set)
        scrollx_cart.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly_cart.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx_cart.config(command=self.CartTable.xview)
        scrolly_cart.config(command=self.CartTable.yview)

        self.CartTable.heading("pid", text="PID")
        self.CartTable.heading("name", text="Name")
        self.CartTable.heading("price", text="Price")
        self.CartTable.heading("qty", text="QTY")
        self.CartTable["show"] = "headings"
        self.CartTable.column("pid", width=40)
        self.CartTable.column("name", width=90)
        self.CartTable.column("price", width=90)
        self.CartTable.column("qty", width=40)
        self.CartTable.pack(fill=tk.BOTH, expand=1)
        self.CartTable.bind("<ButtonRelease-1>", self.get_cart_data)

        Add_CartWidgetsFrame = tk.Frame(self, bd=2, relief=tk.RIDGE, bg="white")
        Add_CartWidgetsFrame.place(x=430, y=500, width=530, height=110)

        self.var_pid = tk.StringVar()
        self.var_pname = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_stock = tk.StringVar()

        tk.Label(Add_CartWidgetsFrame, text="Product Name", font=("times new roman", 15), bg="white").place(x=5, y=5)
        tk.Entry(Add_CartWidgetsFrame, textvariable=self.var_pname, font=("times new roman", 15), bg="lightyellow", state='readonly').place(x=5, y=35, width=190, height=22)

        tk.Label(Add_CartWidgetsFrame, text="Price Per Qty", font=("times new roman", 15), bg="white").place(x=210, y=5)
        tk.Entry(Add_CartWidgetsFrame, textvariable=self.var_price, font=("times new roman", 15), bg="lightyellow", state='readonly').place(x=210, y=35, width=150, height=22)

        tk.Label(Add_CartWidgetsFrame, text="Quantity", font=("times new roman", 15), bg="white").place(x=380, y=5)
        tk.Entry(Add_CartWidgetsFrame, textvariable=self.var_qty, font=("times new roman", 15), bg="lightyellow").place(x=380, y=35, width=120, height=22)

        self.lbl_inStock = tk.Label(Add_CartWidgetsFrame, text="In Stock", font=("times new roman", 15), bg="white")
        self.lbl_inStock.place(x=5, y=70)

        tk.Button(Add_CartWidgetsFrame, text="Clear", command=self.clear_cart_widgets, font=("times new roman", 15, "bold"), bg="lightgray", cursor="hand2").place(x=180, y=70, width=150, height=30)
        tk.Button(Add_CartWidgetsFrame, text="Add | Update Cart", command=self.add_update_cart, font=("times new roman", 15, "bold"), bg="orange", cursor="hand2").place(x=340, y=70, width=180, height=30)

        billFrame = tk.Frame(self, bd=2, relief=tk.RIDGE, bg="white")
        billFrame.place(x=970, y=60, width=370, height=410)

        tk.Label(billFrame, text="Customer Bill Area", font=("goudy old style", 20, "bold"), bg="#f44336", fg="white").pack(side=tk.TOP, fill=tk.X)
        scrolly_bill = tk.Scrollbar(billFrame, orient=tk.VERTICAL)
        self.txt_bill_area = tk.Text(billFrame, yscrollcommand=scrolly_bill.set)
        scrolly_bill.pack(side=tk.RIGHT, fill=tk.Y)
        scrolly_bill.config(command=self.txt_bill_area.yview)
        self.txt_bill_area.pack(fill=tk.BOTH, expand=1)

        billMenuFrame = tk.Frame(self, bd=2, relief=tk.RIDGE, bg="white")
        billMenuFrame.place(x=970, y=480, width=370, height=130)

        self.lbl_amnt = tk.Label(billMenuFrame, text="Bill Amount\n[0]", font=("goudy old style", 15, "bold"), bg="#3f51b5", fg="white")
        self.lbl_amnt.place(x=2, y=5, width=120, height=50)

        self.lbl_discount = tk.Label(billMenuFrame, text="Discount\n[5%]", font=("goudy old style", 15, "bold"), bg="#8bc34a", fg="white")
        self.lbl_discount.place(x=124, y=5, width=120, height=50)

        self.lbl_net_pay = tk.Label(billMenuFrame, text="Net Pay\n[0]", font=("goudy old style", 15, "bold"), bg="#607d8b", fg="white")
        self.lbl_net_pay.place(x=246, y=5, width=120, height=50)

        tk.Button(billMenuFrame, text="Print", cursor="hand2", font=("goudy old style", 15, "bold"), bg="lightgreen", fg="white").place(x=2, y=60, width=120, height=50)
        tk.Button(billMenuFrame, text="Clear All", command=self.clear_all, cursor="hand2", font=("goudy old style", 15, "bold"), bg="gray", fg="white").place(x=124, y=60, width=120, height=50)
        tk.Button(billMenuFrame, text="Generate Bill", command=self.generate_bill, cursor="hand2", font=("goudy old style", 15, "bold"), bg="#009688", fg="white").place(x=246, y=60, width=120, height=50)

    def get_input(self, num: Any) -> None:
        xnum = self.var_cal_input.get() + str(num)
        self.var_cal_input.set(xnum)

    def clear_cal(self) -> None:
        self.var_cal_input.set('')

    def perform_cal(self) -> None:
        result = self.var_cal_input.get()
        try:
            self.var_cal_input.set(str(eval(result)))
        except:
            self.var_cal_input.set("Error")

    def fetch_all_products(self) -> None:
        try:
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT pid, name, price, qty, status FROM product WHERE status='Active'")
            rows = cur.fetchall()
            self.product_table.delete(*self.product_table.get_children())
            for row in rows:
                self.product_table.insert('', tk.END, values=row)
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def search(self) -> None:
        try:
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("SELECT pid, name, price, qty, status FROM product WHERE name LIKE ? AND status='Active'", ('%'+self.var_search.get()+'%',))
            rows = cur.fetchall()
            self.product_table.delete(*self.product_table.get_children())
            for row in rows:
                self.product_table.insert('', tk.END, values=row)
            con.close()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def get_product_data(self, ev: Any) -> None:
        f = self.product_table.focus()
        content = self.product_table.item(f)
        row = content['values']
        if not row: return
        self.var_pid.set(row[0])
        self.var_pname.set(row[1])
        self.var_price.set(row[2])
        self.lbl_inStock.config(text=f"In Stock [{str(row[3])}]")
        self.var_stock.set(row[3])
        self.var_qty.set('1')

    def get_cart_data(self, ev: Any) -> None:
        f = self.CartTable.focus()
        content = self.CartTable.item(f)
        row = content['values']
        if not row: return
        self.var_pid.set(row[0])
        self.var_pname.set(row[1])
        self.var_price.set(row[2])
        self.var_qty.set(row[3])
        self.lbl_inStock.config(text=f"In Stock [{row[4]}]")
        self.var_stock.set(row[4])

    def add_update_cart(self) -> None:
        if self.var_pid.get() == '':
            messagebox.showerror('Error', "Please select product from the list", parent=self)
            return
        if self.var_qty.get() == '':
            messagebox.showerror('Error', "Quantity is Required", parent=self)
            return
        try:
            qty = int(self.var_qty.get())
            stock = int(self.var_stock.get())
        except ValueError:
            messagebox.showerror('Error', "Invalid Quantity", parent=self)
            return

        if qty > stock:
            messagebox.showerror('Error', "Invalid Quantity, Not enough stock", parent=self)
            return

        price_calc = float(self.var_price.get())
        cart_data = [self.var_pid.get(), self.var_pname.get(), price_calc, qty, stock]

        present = 'no'
        index_ = 0
        for row in self.cart_list:
            if self.var_pid.get() == row[0]:
                present = 'yes'
                break
            index_ += 1

        if present == 'yes':
            op = messagebox.askyesno('Confirm', "Product already present\nDo you want to Update | Remove from the Cart List", parent=self)
            if op:
                if qty == 0:
                    self.cart_list.pop(index_)
                else:
                    self.cart_list[index_][3] = qty
        else:
            if qty > 0:
                self.cart_list.append(cart_data)

        self.show_cart()
        self.bill_updates()

    def bill_updates(self) -> None:
        self.bill_amnt = 0.0
        self.net_pay = 0.0
        self.discount = 0.0
        for row in self.cart_list:
            self.bill_amnt += float(row[2]) * int(row[3])

        self.discount = (self.bill_amnt * 5) / 100
        self.net_pay = self.bill_amnt - self.discount
        self.lbl_amnt.config(text=f'Bill Amount\n[{str(self.bill_amnt)}]')
        self.lbl_net_pay.config(text=f'Net Pay\n[{str(self.net_pay)}]')
        self.cartTitle.config(text=f"Cart \t Total Product: [{str(len(self.cart_list))}]")

    def show_cart(self) -> None:
        try:
            self.CartTable.delete(*self.CartTable.get_children())
            for row in self.cart_list:
                self.CartTable.insert('', tk.END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def generate_bill(self) -> None:
        if self.var_cname.get() == '' or self.var_contact.get() == '':
            messagebox.showerror("Error", "Customer Details are required", parent=self)
            return
        if len(self.cart_list) == 0:
            messagebox.showerror("Error", "Please Add Product to the Cart", parent=self)
            return

        self.bill_top()
        self.bill_middle()
        self.bill_bottom()

        invoice = str(datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        
        try:
            with open(f'bills/{invoice}.txt', 'w') as f:
                f.write(self.txt_bill_area.get('1.0', tk.END))
            
            con = self.db.get_connection()
            cur = con.cursor()
            cur.execute("INSERT INTO bill (invoice_no, date, total, discount, net_pay) VALUES(?,?,?,?,?)", (
                invoice, datetime.datetime.now().strftime("%Y-%m-%d"), self.bill_amnt, self.discount, self.net_pay
            ))
            
            for row in self.cart_list:
                pid = row[0]
                qty = int(row[3])
                stock = int(row[4])
                new_stock = stock - qty
                status = 'Active' if new_stock > 0 else 'Inactive'
                cur.execute("UPDATE product SET qty=?, status=? WHERE pid=?", (new_stock, status, pid))
            
            con.commit()
            con.close()
            messagebox.showinfo('Saved', "Bill has been generated and saved", parent=self)
            self.fetch_all_products()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self)

    def bill_top(self) -> None:
        self.txt_bill_area.delete('1.0', tk.END)
        bill_top_temp = f'''
\tInventory Management System
\tPhone No. 9876543210 , Delhi-1254
{str("="*47)}
 Customer Name: {self.var_cname.get()}
 Ph no. :{self.var_contact.get()}
 Date: {str(datetime.datetime.now().strftime("%d/%m/%Y"))}
{str("="*47)}
 Product Name\t\t\tQTY\tPrice
{str("="*47)}
        '''
        self.txt_bill_area.insert('1.0', bill_top_temp)

    def bill_middle(self) -> None:
        for row in self.cart_list:
            name = row[1]
            qty = row[3]
            price = float(row[2]) * int(row[3])
            self.txt_bill_area.insert(tk.END, f"\n {name}\t\t\t{qty}\tRs.{price}")

    def bill_bottom(self) -> None:
        bill_bottom_temp = f'''
\n{str("="*47)}
 Bill Amount\t\t\t\tRs.{self.bill_amnt}
 Discount\t\t\t\tRs.{self.discount}
 Net Pay\t\t\t\tRs.{self.net_pay}
{str("="*47)}\n
        '''
        self.txt_bill_area.insert(tk.END, bill_bottom_temp)

    def clear_cart_widgets(self) -> None:
        self.var_pid.set('')
        self.var_pname.set('')
        self.var_price.set('')
        self.var_qty.set('')
        self.lbl_inStock.config(text="In Stock")
        self.var_stock.set('')

    def clear_all(self) -> None:
        self.cart_list.clear()
        self.var_cname.set('')
        self.var_contact.set('')
        self.txt_bill_area.delete('1.0', tk.END)
        self.cartTitle.config(text="Cart \t Total Product: [0]")
        self.var_search.set('')
        self.clear_cart_widgets()
        self.show_cart()
        self.bill_updates()
        self.fetch_all_products()

class InventorySystem:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.geometry("1350x700+0+0")
        self.root.title("Inventory Management System")
        self.root.config(bg="white")
        self.db = DatabaseManager()

        self.setup_ui()
        self.update_clock()
        self.update_dashboard_stats()

    def get_placeholder_image(self, width: int, height: int, color: str) -> ImageTk.PhotoImage:
        img = Image.new('RGB', (width, height), color=color)
        return ImageTk.PhotoImage(img)

    def setup_ui(self) -> None:
        self.icon_title = self.get_placeholder_image(50, 50, "blue")
        title = tk.Label(self.root, text="Inventory Management System", image=self.icon_title, compound=tk.LEFT, font=("times new roman", 40, "bold"), bg="#010c48", fg="white", anchor="w", padx=20)
        title.place(x=0, y=0, relwidth=1, height=70)

        btn_logout = tk.Button(self.root, text="Logout", font=("times new roman", 15, "bold"), bg="yellow", cursor="hand2")
        btn_logout.place(x=1150, y=10, height=50, width=150)

        self.lbl_clock = tk.Label(self.root, text="Welcome to Inventory Management System\t\t Date: DD-MM-YYYY\t\t Time: HH:MM:SS", font=("times new roman", 15), bg="#4d636d", fg="white")
        self.lbl_clock.place(x=0, y=70, relwidth=1, height=30)

        self.MenuLogo = self.get_placeholder_image(200, 200, "gray")
        LeftMenu = tk.Frame(self.root, bd=2, relief=tk.RIDGE, bg="white")
        LeftMenu.place(x=0, y=102, width=200, height=565)

        lbl_menuLogo = tk.Label(LeftMenu, image=self.MenuLogo)
        lbl_menuLogo.pack(side=tk.TOP, fill=tk.X)

        lbl_menu = tk.Label(LeftMenu, text="Menu", font=("times new roman", 20), bg="#009688").pack(side=tk.TOP, fill=tk.X)

        btn_employee = tk.Button(LeftMenu, text="Employee", command=self.open_employee, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side=tk.TOP, fill=tk.X)
        btn_supplier = tk.Button(LeftMenu, text="Supplier", command=self.open_supplier, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side=tk.TOP, fill=tk.X)
        btn_category = tk.Button(LeftMenu, text="Category", command=self.open_category, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side=tk.TOP, fill=tk.X)
        btn_product = tk.Button(LeftMenu, text="Product", command=self.open_product, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side=tk.TOP, fill=tk.X)
        btn_billing = tk.Button(LeftMenu, text="Billing", command=self.open_billing, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side=tk.TOP, fill=tk.X)
        btn_view_bills = tk.Button(LeftMenu, text="View Bills", command=self.open_view_bills, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side=tk.TOP, fill=tk.X)
        btn_exit = tk.Button(LeftMenu, text="Exit", command=self.root.quit, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side=tk.TOP, fill=tk.X)

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

    def update_clock(self) -> None:
        now = datetime.datetime.now()
        date_str = now.strftime("%d-%m-%Y")
        time_str = now.strftime("%I:%M:%S %p")
        self.lbl_clock.config(text=f"Welcome to Inventory Management System\t\t Date: {date_str}\t\t Time: {time_str}")
        self.root.after(1000, self.update_clock)

    def update_dashboard_stats(self) -> None:
        try:
            con = self.db.get_connection()
            cur = con.cursor()
            
            cur.execute("SELECT COUNT(*) FROM employee")
            emp_count = cur.fetchone()[0]
            self.lbl_employee.config(text=f"Total Employee\n[ {emp_count} ]")

            cur.execute("SELECT COUNT(*) FROM supplier")
            sup_count = cur.fetchone()[0]
            self.lbl_supplier.config(text=f"Total Supplier\n[ {sup_count} ]")

            cur.execute("SELECT COUNT(*) FROM category")
            cat_count = cur.fetchone()[0]
            self.lbl_category.config(text=f"Total Category\n[ {cat_count} ]")

            cur.execute("SELECT COUNT(*) FROM product")
            prod_count = cur.fetchone()[0]
            self.lbl_product.config(text=f"Total Product\n[ {prod_count} ]")

            cur.execute("SELECT COUNT(*) FROM bill")
            bill_count = cur.fetchone()[0]
            self.lbl_sales.config(text=f"Total Sales\n[ {bill_count} ]")

            con.close()
        except Exception as ex:
            pass
        self.root.after(5000, self.update_dashboard_stats)

    def open_employee(self) -> None:
        EmployeeManager(self.root, self.db)

    def open_supplier(self) -> None:
        SupplierManager(self.root, self.db)

    def open_category(self) -> None:
        CategoryManager(self.root, self.db)

    def open_product(self) -> None:
        ProductManager(self.root, self.db)

    def open_billing(self) -> None:
        BillingManager(self.root, self.db)

    def open_view_bills(self) -> None:
        ViewBillsManager(self.root, self.db)

if __name__ == "__main__":
    root = tk.Tk()
    app = InventorySystem(root)
    root.mainloop()