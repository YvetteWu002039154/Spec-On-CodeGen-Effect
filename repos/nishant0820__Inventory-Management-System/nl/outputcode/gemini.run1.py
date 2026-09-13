import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import sqlite3
import os
from datetime import datetime
from typing import List, Tuple, Any, Optional

def create_database() -> None:
    con = sqlite3.connect(database=r'ims.db')
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS employee(eid INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, gender TEXT, contact TEXT, dob TEXT, doj TEXT, pass TEXT, utype TEXT, address TEXT, salary TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS supplier(invoice INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, contact TEXT, desc TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS category(cid INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS product(pid INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, supplier TEXT, name TEXT, price TEXT, qty TEXT, status TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS bills(invoice TEXT PRIMARY KEY, date TEXT, name TEXT, contact TEXT, bill_data TEXT)")
    con.commit()
    con.close()

class EmployeeClass:
    def __init__(self, root: tk.Tk) -> None:
        self.root = tk.Toplevel(root)
        self.root.geometry("1100x500+220+130")
        self.root.title("Employee Management")
        self.root.focus_force()

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

        title = tk.Label(self.root, text="Employee Details", font=("goudy old style", 15), bg="#0f4d7d", fg="white")
        title.pack(side=tk.TOP, fill=tk.X)

        tk.Label(self.root, text="Emp ID", font=("goudy old style", 12)).place(x=50, y=50)
        tk.Entry(self.root, textvariable=self.var_emp_id, font=("goudy old style", 12), bg="lightyellow").place(x=150, y=50, width=180)

        tk.Label(self.root, text="Name", font=("goudy old style", 12)).place(x=350, y=50)
        tk.Entry(self.root, textvariable=self.var_name, font=("goudy old style", 12), bg="lightyellow").place(x=450, y=50, width=180)

        tk.Label(self.root, text="Email", font=("goudy old style", 12)).place(x=650, y=50)
        tk.Entry(self.root, textvariable=self.var_email, font=("goudy old style", 12), bg="lightyellow").place(x=750, y=50, width=180)

        tk.Label(self.root, text="Gender", font=("goudy old style", 12)).place(x=50, y=90)
        cmb_gender = ttk.Combobox(self.root, textvariable=self.var_gender, values=("Male", "Female", "Other"), state='readonly', justify=tk.CENTER, font=("goudy old style", 12))
        cmb_gender.place(x=150, y=90, width=180)
        cmb_gender.current(0)

        tk.Label(self.root, text="Contact", font=("goudy old style", 12)).place(x=350, y=90)
        tk.Entry(self.root, textvariable=self.var_contact, font=("goudy old style", 12), bg="lightyellow").place(x=450, y=90, width=180)

        tk.Label(self.root, text="DOB", font=("goudy old style", 12)).place(x=650, y=90)
        tk.Entry(self.root, textvariable=self.var_dob, font=("goudy old style", 12), bg="lightyellow").place(x=750, y=90, width=180)

        tk.Label(self.root, text="DOJ", font=("goudy old style", 12)).place(x=50, y=130)
        tk.Entry(self.root, textvariable=self.var_doj, font=("goudy old style", 12), bg="lightyellow").place(x=150, y=130, width=180)

        tk.Label(self.root, text="Password", font=("goudy old style", 12)).place(x=350, y=130)
        tk.Entry(self.root, textvariable=self.var_pass, font=("goudy old style", 12), bg="lightyellow").place(x=450, y=130, width=180)

        tk.Label(self.root, text="User Type", font=("goudy old style", 12)).place(x=650, y=130)
        cmb_utype = ttk.Combobox(self.root, textvariable=self.var_utype, values=("Admin", "Employee"), state='readonly', justify=tk.CENTER, font=("goudy old style", 12))
        cmb_utype.place(x=750, y=130, width=180)
        cmb_utype.current(0)

        tk.Label(self.root, text="Address", font=("goudy old style", 12)).place(x=50, y=170)
        self.txt_address = tk.Text(self.root, font=("goudy old style", 12), bg="lightyellow")
        self.txt_address.place(x=150, y=170, width=480, height=60)

        tk.Label(self.root, text="Salary", font=("goudy old style", 12)).place(x=650, y=170)
        tk.Entry(self.root, textvariable=self.var_salary, font=("goudy old style", 12), bg="lightyellow").place(x=750, y=170, width=180)

        tk.Button(self.root, text="Save", command=self.add, font=("goudy old style", 12), bg="#2196f3", fg="white", cursor="hand2").place(x=150, y=250, width=110, height=28)
        tk.Button(self.root, text="Update", command=self.update, font=("goudy old style", 12), bg="#4caf50", fg="white", cursor="hand2").place(x=270, y=250, width=110, height=28)
        tk.Button(self.root, text="Delete", command=self.delete, font=("goudy old style", 12), bg="#f44336", fg="white", cursor="hand2").place(x=390, y=250, width=110, height=28)
        tk.Button(self.root, text="Clear", command=self.clear, font=("goudy old style", 12), bg="#607d8b", fg="white", cursor="hand2").place(x=510, y=250, width=110, height=28)

        emp_frame = tk.Frame(self.root, bd=3, relief=tk.RIDGE)
        emp_frame.place(x=0, y=300, relwidth=1, height=200)

        scrolly = tk.Scrollbar(emp_frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(emp_frame, orient=tk.HORIZONTAL)

        self.EmployeeTable = ttk.Treeview(emp_frame, columns=("eid", "name", "email", "gender", "contact", "dob", "doj", "pass", "utype", "address", "salary"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.EmployeeTable.xview)
        scrolly.config(command=self.EmployeeTable.yview)

        self.EmployeeTable.heading("eid", text="EMP ID")
        self.EmployeeTable.heading("name", text="Name")
        self.EmployeeTable.heading("email", text="Email")
        self.EmployeeTable.heading("gender", text="Gender")
        self.EmployeeTable.heading("contact", text="Contact")
        self.EmployeeTable.heading("dob", text="DOB")
        self.EmployeeTable.heading("doj", text="DOJ")
        self.EmployeeTable.heading("pass", text="Password")
        self.EmployeeTable.heading("utype", text="User Type")
        self.EmployeeTable.heading("address", text="Address")
        self.EmployeeTable.heading("salary", text="Salary")
        self.EmployeeTable["show"] = "headings"
        self.EmployeeTable.pack(fill=tk.BOTH, expand=1)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def add(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_emp_id.get() == "":
                messagebox.showerror("Error", "Employee ID Must be required", parent=self.root)
            else:
                cur.execute("Select * from employee where eid=?", (self.var_emp_id.get(),))
                row = cur.fetchone()
                if row is not None:
                    messagebox.showerror("Error", "This Employee ID already assigned, try different", parent=self.root)
                else:
                    cur.execute("Insert into employee (eid, name, email, gender, contact, dob, doj, pass, utype, address, salary) values(?,?,?,?,?,?,?,?,?,?,?)", (
                        self.var_emp_id.get(), self.var_name.get(), self.var_email.get(), self.var_gender.get(), self.var_contact.get(),
                        self.var_dob.get(), self.var_doj.get(), self.var_pass.get(), self.var_utype.get(), self.txt_address.get('1.0', tk.END), self.var_salary.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Employee Added Successfully", parent=self.root)
                    self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def show(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            cur.execute("select * from employee")
            rows = cur.fetchall()
            self.EmployeeTable.delete(*self.EmployeeTable.get_children())
            for row in rows:
                self.EmployeeTable.insert('', tk.END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def get_data(self, ev: Any) -> None:
        f = self.EmployeeTable.focus()
        content = (self.EmployeeTable.item(f))
        row = content['values']
        if not row:
            return
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
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_emp_id.get() == "":
                messagebox.showerror("Error", "Employee ID Must be required", parent=self.root)
            else:
                cur.execute("Select * from employee where eid=?", (self.var_emp_id.get(),))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror("Error", "Invalid Employee ID", parent=self.root)
                else:
                    cur.execute("Update employee set name=?, email=?, gender=?, contact=?, dob=?, doj=?, pass=?, utype=?, address=?, salary=? where eid=?", (
                        self.var_name.get(), self.var_email.get(), self.var_gender.get(), self.var_contact.get(),
                        self.var_dob.get(), self.var_doj.get(), self.var_pass.get(), self.var_utype.get(), self.txt_address.get('1.0', tk.END), self.var_salary.get(), self.var_emp_id.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Employee Updated Successfully", parent=self.root)
                    self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def delete(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_emp_id.get() == "":
                messagebox.showerror("Error", "Employee ID Must be required", parent=self.root)
            else:
                cur.execute("Select * from employee where eid=?", (self.var_emp_id.get(),))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror("Error", "Invalid Employee ID", parent=self.root)
                else:
                    op = messagebox.askyesno("Confirm", "Do you really want to delete?", parent=self.root)
                    if op:
                        cur.execute("delete from employee where eid=?", (self.var_emp_id.get(),))
                        con.commit()
                        messagebox.showinfo("Delete", "Employee Deleted Successfully", parent=self.root)
                        self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def clear(self) -> None:
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_email.set("")
        self.var_gender.set("Male")
        self.var_contact.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_pass.set("")
        self.var_utype.set("Admin")
        self.txt_address.delete('1.0', tk.END)
        self.var_salary.set("")
        self.show()

class SupplierClass:
    def __init__(self, root: tk.Tk) -> None:
        self.root = tk.Toplevel(root)
        self.root.geometry("1100x500+220+130")
        self.root.title("Supplier Management")
        self.root.focus_force()

        self.var_sup_invoice = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_contact = tk.StringVar()

        title = tk.Label(self.root, text="Supplier Details", font=("goudy old style", 15), bg="#0f4d7d", fg="white")
        title.pack(side=tk.TOP, fill=tk.X)

        tk.Label(self.root, text="Invoice No.", font=("goudy old style", 12)).place(x=50, y=50)
        tk.Entry(self.root, textvariable=self.var_sup_invoice, font=("goudy old style", 12), bg="lightyellow").place(x=150, y=50, width=180)

        tk.Label(self.root, text="Name", font=("goudy old style", 12)).place(x=50, y=90)
        tk.Entry(self.root, textvariable=self.var_name, font=("goudy old style", 12), bg="lightyellow").place(x=150, y=90, width=180)

        tk.Label(self.root, text="Contact", font=("goudy old style", 12)).place(x=50, y=130)
        tk.Entry(self.root, textvariable=self.var_contact, font=("goudy old style", 12), bg="lightyellow").place(x=150, y=130, width=180)

        tk.Label(self.root, text="Description", font=("goudy old style", 12)).place(x=50, y=170)
        self.txt_desc = tk.Text(self.root, font=("goudy old style", 12), bg="lightyellow")
        self.txt_desc.place(x=150, y=170, width=480, height=60)

        tk.Button(self.root, text="Save", command=self.add, font=("goudy old style", 12), bg="#2196f3", fg="white", cursor="hand2").place(x=150, y=250, width=110, height=28)
        tk.Button(self.root, text="Update", command=self.update, font=("goudy old style", 12), bg="#4caf50", fg="white", cursor="hand2").place(x=270, y=250, width=110, height=28)
        tk.Button(self.root, text="Delete", command=self.delete, font=("goudy old style", 12), bg="#f44336", fg="white", cursor="hand2").place(x=390, y=250, width=110, height=28)
        tk.Button(self.root, text="Clear", command=self.clear, font=("goudy old style", 12), bg="#607d8b", fg="white", cursor="hand2").place(x=510, y=250, width=110, height=28)

        sup_frame = tk.Frame(self.root, bd=3, relief=tk.RIDGE)
        sup_frame.place(x=0, y=300, relwidth=1, height=200)

        scrolly = tk.Scrollbar(sup_frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(sup_frame, orient=tk.HORIZONTAL)

        self.SupplierTable = ttk.Treeview(sup_frame, columns=("invoice", "name", "contact", "desc"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.SupplierTable.xview)
        scrolly.config(command=self.SupplierTable.yview)

        self.SupplierTable.heading("invoice", text="Invoice No.")
        self.SupplierTable.heading("name", text="Name")
        self.SupplierTable.heading("contact", text="Contact")
        self.SupplierTable.heading("desc", text="Description")
        self.SupplierTable["show"] = "headings"
        self.SupplierTable.pack(fill=tk.BOTH, expand=1)
        self.SupplierTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def add(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice No. Must be required", parent=self.root)
            else:
                cur.execute("Select * from supplier where invoice=?", (self.var_sup_invoice.get(),))
                row = cur.fetchone()
                if row is not None:
                    messagebox.showerror("Error", "This Invoice No. already assigned, try different", parent=self.root)
                else:
                    cur.execute("Insert into supplier (invoice, name, contact, desc) values(?,?,?,?)", (
                        self.var_sup_invoice.get(), self.var_name.get(), self.var_contact.get(), self.txt_desc.get('1.0', tk.END)
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Supplier Added Successfully", parent=self.root)
                    self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def show(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            cur.execute("select * from supplier")
            rows = cur.fetchall()
            self.SupplierTable.delete(*self.SupplierTable.get_children())
            for row in rows:
                self.SupplierTable.insert('', tk.END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def get_data(self, ev: Any) -> None:
        f = self.SupplierTable.focus()
        content = (self.SupplierTable.item(f))
        row = content['values']
        if not row:
            return
        self.var_sup_invoice.set(row[0])
        self.var_name.set(row[1])
        self.var_contact.set(row[2])
        self.txt_desc.delete('1.0', tk.END)
        self.txt_desc.insert(tk.END, row[3])

    def update(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice No. Must be required", parent=self.root)
            else:
                cur.execute("Select * from supplier where invoice=?", (self.var_sup_invoice.get(),))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror("Error", "Invalid Invoice No.", parent=self.root)
                else:
                    cur.execute("Update supplier set name=?, contact=?, desc=? where invoice=?", (
                        self.var_name.get(), self.var_contact.get(), self.txt_desc.get('1.0', tk.END), self.var_sup_invoice.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Supplier Updated Successfully", parent=self.root)
                    self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def delete(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice No. Must be required", parent=self.root)
            else:
                cur.execute("Select * from supplier where invoice=?", (self.var_sup_invoice.get(),))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror("Error", "Invalid Invoice No.", parent=self.root)
                else:
                    op = messagebox.askyesno("Confirm", "Do you really want to delete?", parent=self.root)
                    if op:
                        cur.execute("delete from supplier where invoice=?", (self.var_sup_invoice.get(),))
                        con.commit()
                        messagebox.showinfo("Delete", "Supplier Deleted Successfully", parent=self.root)
                        self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def clear(self) -> None:
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete('1.0', tk.END)
        self.show()

class CategoryClass:
    def __init__(self, root: tk.Tk) -> None:
        self.root = tk.Toplevel(root)
        self.root.geometry("1100x500+220+130")
        self.root.title("Category Management")
        self.root.focus_force()

        self.var_cat_id = tk.StringVar()
        self.var_name = tk.StringVar()

        title = tk.Label(self.root, text="Category Details", font=("goudy old style", 15), bg="#0f4d7d", fg="white")
        title.pack(side=tk.TOP, fill=tk.X)

        tk.Label(self.root, text="Category Name", font=("goudy old style", 12)).place(x=50, y=50)
        tk.Entry(self.root, textvariable=self.var_name, font=("goudy old style", 12), bg="lightyellow").place(x=180, y=50, width=180)

        tk.Button(self.root, text="Add", command=self.add, font=("goudy old style", 12), bg="#2196f3", fg="white", cursor="hand2").place(x=380, y=50, width=110, height=28)
        tk.Button(self.root, text="Delete", command=self.delete, font=("goudy old style", 12), bg="#f44336", fg="white", cursor="hand2").place(x=500, y=50, width=110, height=28)

        cat_frame = tk.Frame(self.root, bd=3, relief=tk.RIDGE)
        cat_frame.place(x=0, y=100, relwidth=1, height=400)

        scrolly = tk.Scrollbar(cat_frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(cat_frame, orient=tk.HORIZONTAL)

        self.CategoryTable = ttk.Treeview(cat_frame, columns=("cid", "name"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.CategoryTable.xview)
        scrolly.config(command=self.CategoryTable.yview)

        self.CategoryTable.heading("cid", text="Category ID")
        self.CategoryTable.heading("name", text="Name")
        self.CategoryTable["show"] = "headings"
        self.CategoryTable.pack(fill=tk.BOTH, expand=1)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def add(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_name.get() == "":
                messagebox.showerror("Error", "Category Name Must be required", parent=self.root)
            else:
                cur.execute("Select * from category where name=?", (self.var_name.get(),))
                row = cur.fetchone()
                if row is not None:
                    messagebox.showerror("Error", "This Category already exists", parent=self.root)
                else:
                    cur.execute("Insert into category (name) values(?)", (self.var_name.get(),))
                    con.commit()
                    messagebox.showinfo("Success", "Category Added Successfully", parent=self.root)
                    self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def show(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            cur.execute("select * from category")
            rows = cur.fetchall()
            self.CategoryTable.delete(*self.CategoryTable.get_children())
            for row in rows:
                self.CategoryTable.insert('', tk.END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def get_data(self, ev: Any) -> None:
        f = self.CategoryTable.focus()
        content = (self.CategoryTable.item(f))
        row = content['values']
        if not row:
            return
        self.var_cat_id.set(row[0])
        self.var_name.set(row[1])

    def delete(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_cat_id.get() == "":
                messagebox.showerror("Error", "Please select category from list", parent=self.root)
            else:
                cur.execute("Select * from category where cid=?", (self.var_cat_id.get(),))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror("Error", "Invalid Category", parent=self.root)
                else:
                    op = messagebox.askyesno("Confirm", "Do you really want to delete?", parent=self.root)
                    if op:
                        cur.execute("delete from category where cid=?", (self.var_cat_id.get(),))
                        con.commit()
                        messagebox.showinfo("Delete", "Category Deleted Successfully", parent=self.root)
                        self.var_cat_id.set("")
                        self.var_name.set("")
                        self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

class ProductClass:
    def __init__(self, root: tk.Tk) -> None:
        self.root = tk.Toplevel(root)
        self.root.geometry("1100x500+220+130")
        self.root.title("Product Management")
        self.root.focus_force()

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

        title = tk.Label(self.root, text="Product Details", font=("goudy old style", 15), bg="#0f4d7d", fg="white")
        title.pack(side=tk.TOP, fill=tk.X)

        tk.Label(self.root, text="Category", font=("goudy old style", 12)).place(x=50, y=50)
        cmb_cat = ttk.Combobox(self.root, textvariable=self.var_cat, values=self.cat_list, state='readonly', justify=tk.CENTER, font=("goudy old style", 12))
        cmb_cat.place(x=150, y=50, width=180)
        if self.cat_list:
            cmb_cat.current(0)

        tk.Label(self.root, text="Supplier", font=("goudy old style", 12)).place(x=50, y=90)
        cmb_sup = ttk.Combobox(self.root, textvariable=self.var_sup, values=self.sup_list, state='readonly', justify=tk.CENTER, font=("goudy old style", 12))
        cmb_sup.place(x=150, y=90, width=180)
        if self.sup_list:
            cmb_sup.current(0)

        tk.Label(self.root, text="Name", font=("goudy old style", 12)).place(x=50, y=130)
        tk.Entry(self.root, textvariable=self.var_name, font=("goudy old style", 12), bg="lightyellow").place(x=150, y=130, width=180)

        tk.Label(self.root, text="Price", font=("goudy old style", 12)).place(x=50, y=170)
        tk.Entry(self.root, textvariable=self.var_price, font=("goudy old style", 12), bg="lightyellow").place(x=150, y=170, width=180)

        tk.Label(self.root, text="Quantity", font=("goudy old style", 12)).place(x=50, y=210)
        tk.Entry(self.root, textvariable=self.var_qty, font=("goudy old style", 12), bg="lightyellow").place(x=150, y=210, width=180)

        tk.Label(self.root, text="Status", font=("goudy old style", 12)).place(x=50, y=250)
        cmb_status = ttk.Combobox(self.root, textvariable=self.var_status, values=("Active", "Inactive"), state='readonly', justify=tk.CENTER, font=("goudy old style", 12))
        cmb_status.place(x=150, y=250, width=180)
        cmb_status.current(0)

        tk.Button(self.root, text="Save", command=self.add, font=("goudy old style", 12), bg="#2196f3", fg="white", cursor="hand2").place(x=50, y=300, width=100, height=28)
        tk.Button(self.root, text="Update", command=self.update, font=("goudy old style", 12), bg="#4caf50", fg="white", cursor="hand2").place(x=160, y=300, width=100, height=28)
        tk.Button(self.root, text="Delete", command=self.delete, font=("goudy old style", 12), bg="#f44336", fg="white", cursor="hand2").place(x=270, y=300, width=100, height=28)
        tk.Button(self.root, text="Clear", command=self.clear, font=("goudy old style", 12), bg="#607d8b", fg="white", cursor="hand2").place(x=380, y=300, width=100, height=28)

        prod_frame = tk.Frame(self.root, bd=3, relief=tk.RIDGE)
        prod_frame.place(x=500, y=50, width=580, height=430)

        scrolly = tk.Scrollbar(prod_frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(prod_frame, orient=tk.HORIZONTAL)

        self.ProductTable = ttk.Treeview(prod_frame, columns=("pid", "category", "supplier", "name", "price", "qty", "status"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.ProductTable.xview)
        scrolly.config(command=self.ProductTable.yview)

        self.ProductTable.heading("pid", text="P ID")
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
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            cur.execute("Select name from category")
            cat = cur.fetchall()
            self.cat_list.append("Empty")
            if len(cat) > 0:
                self.cat_list.clear()
                for i in cat:
                    self.cat_list.append(i[0])

            cur.execute("Select name from supplier")
            sup = cur.fetchall()
            self.sup_list.append("Empty")
            if len(sup) > 0:
                self.sup_list.clear()
                for i in sup:
                    self.sup_list.append(i[0])
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def add(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_cat.get() == "Empty" or self.var_sup.get() == "Empty" or self.var_name.get() == "":
                messagebox.showerror("Error", "All fields are required", parent=self.root)
            else:
                cur.execute("Select * from product where name=?", (self.var_name.get(),))
                row = cur.fetchone()
                if row is not None:
                    messagebox.showerror("Error", "Product already present, try different", parent=self.root)
                else:
                    cur.execute("Insert into product (category, supplier, name, price, qty, status) values(?,?,?,?,?,?)", (
                        self.var_cat.get(), self.var_sup.get(), self.var_name.get(), self.var_price.get(), self.var_qty.get(), self.var_status.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Product Added Successfully", parent=self.root)
                    self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def show(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            cur.execute("select * from product")
            rows = cur.fetchall()
            self.ProductTable.delete(*self.ProductTable.get_children())
            for row in rows:
                self.ProductTable.insert('', tk.END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def get_data(self, ev: Any) -> None:
        f = self.ProductTable.focus()
        content = (self.ProductTable.item(f))
        row = content['values']
        if not row:
            return
        self.var_pid.set(row[0])
        self.var_cat.set(row[1])
        self.var_sup.set(row[2])
        self.var_name.set(row[3])
        self.var_price.set(row[4])
        self.var_qty.set(row[5])
        self.var_status.set(row[6])

    def update(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_pid.get() == "":
                messagebox.showerror("Error", "Please select product from list", parent=self.root)
            else:
                cur.execute("Select * from product where pid=?", (self.var_pid.get(),))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror("Error", "Invalid Product", parent=self.root)
                else:
                    cur.execute("Update product set category=?, supplier=?, name=?, price=?, qty=?, status=? where pid=?", (
                        self.var_cat.get(), self.var_sup.get(), self.var_name.get(), self.var_price.get(), self.var_qty.get(), self.var_status.get(), self.var_pid.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Product Updated Successfully", parent=self.root)
                    self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def delete(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_pid.get() == "":
                messagebox.showerror("Error", "Select product from list", parent=self.root)
            else:
                cur.execute("Select * from product where pid=?", (self.var_pid.get(),))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror("Error", "Invalid Product", parent=self.root)
                else:
                    op = messagebox.askyesno("Confirm", "Do you really want to delete?", parent=self.root)
                    if op:
                        cur.execute("delete from product where pid=?", (self.var_pid.get(),))
                        con.commit()
                        messagebox.showinfo("Delete", "Product Deleted Successfully", parent=self.root)
                        self.clear()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def clear(self) -> None:
        self.var_pid.set("")
        if self.cat_list:
            self.var_cat.set(self.cat_list[0])
        if self.sup_list:
            self.var_sup.set(self.sup_list[0])
        self.var_name.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("Active")
        self.show()

class BillingClass:
    def __init__(self, root: tk.Tk) -> None:
        self.root = tk.Toplevel(root)
        self.root.geometry("1350x700+0+0")
        self.root.title("Billing System")
        self.root.focus_force()

        self.cart_list: List[Tuple[str, str, str, str, str]] = []
        self.var_search = tk.StringVar()
        self.var_cname = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_pid = tk.StringVar()
        self.var_pname = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_stock = tk.StringVar()
        self.var_invoice_search = tk.StringVar()

        title = tk.Label(self.root, text="Billing System", font=("goudy old style", 15), bg="#0f4d7d", fg="white")
        title.pack(side=tk.TOP, fill=tk.X)

        ProductFrame1 = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        ProductFrame1.place(x=10, y=40, width=410, height=550)

        pTitle = tk.Label(ProductFrame1, text="All Products", font=("goudy old style", 15, "bold"), bg="#262626", fg="white")
        pTitle.pack(side=tk.TOP, fill=tk.X)

        ProductFrame2 = tk.Frame(ProductFrame1, bd=2, relief=tk.RIDGE, bg="white")
        ProductFrame2.place(x=2, y=42, width=398, height=90)

        tk.Label(ProductFrame2, text="Search Product | By Name", font=("times new roman", 12, "bold"), bg="white", fg="green").place(x=2, y=5)
        tk.Entry(ProductFrame2, textvariable=self.var_search, font=("times new roman", 12), bg="lightyellow").place(x=2, y=35, width=200, height=22)
        tk.Button(ProductFrame2, text="Search", command=self.search, font=("goudy old style", 11), bg="#2196f3", fg="white", cursor="hand2").place(x=210, y=35, width=80, height=22)
        tk.Button(ProductFrame2, text="Show All", command=self.show, font=("goudy old style", 11), bg="#083531", fg="white", cursor="hand2").place(x=295, y=35, width=80, height=22)

        ProductFrame3 = tk.Frame(ProductFrame1, bd=3, relief=tk.RIDGE)
        ProductFrame3.place(x=2, y=140, width=398, height=375)

        scrolly = tk.Scrollbar(ProductFrame3, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(ProductFrame3, orient=tk.HORIZONTAL)

        self.product_Table = ttk.Treeview(ProductFrame3, columns=("pid", "name", "price", "qty", "status"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.product_Table.xview)
        scrolly.config(command=self.product_Table.yview)

        self.product_Table.heading("pid", text="PID")
        self.product_Table.heading("name", text="Name")
        self.product_Table.heading("price", text="Price")
        self.product_Table.heading("qty", text="QTY")
        self.product_Table.heading("status", text="Status")
        self.product_Table["show"] = "headings"
        self.product_Table.pack(fill=tk.BOTH, expand=1)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)

        CustomerFrame = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        CustomerFrame.place(x=430, y=40, width=530, height=70)

        cTitle = tk.Label(CustomerFrame, text="Customer Details", font=("goudy old style", 12), bg="lightgray")
        cTitle.pack(side=tk.TOP, fill=tk.X)

        tk.Label(CustomerFrame, text="Name", font=("times new roman", 12), bg="white").place(x=5, y=35)
        tk.Entry(CustomerFrame, textvariable=self.var_cname, font=("times new roman", 12), bg="lightyellow").place(x=60, y=35, width=180)

        tk.Label(CustomerFrame, text="Contact No.", font=("times new roman", 12), bg="white").place(x=250, y=35)
        tk.Entry(CustomerFrame, textvariable=self.var_contact, font=("times new roman", 12), bg="lightyellow").place(x=340, y=35, width=160)

        Cal_Cart_Frame = tk.Frame(self.root, bd=2, relief=tk.RIDGE, bg="white")
        Cal_Cart_Frame.place(x=430, y=115, width=530, height=360)

        CartFrame = tk.Frame(Cal_Cart_Frame, bd=3, relief=tk.RIDGE)
        CartFrame.place(x=5, y=5, width=515, height=345)

        scrolly_cart = tk.Scrollbar(CartFrame, orient=tk.VERTICAL)
        scrollx_cart = tk.Scrollbar(CartFrame, orient=tk.HORIZONTAL)

        self.CartTable = ttk.Treeview(CartFrame, columns=("pid", "name", "price", "qty", "status"), yscrollcommand=scrolly_cart.set, xscrollcommand=scrollx_cart.set)
        scrollx_cart.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly_cart.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx_cart.config(command=self.CartTable.xview)
        scrolly_cart.config(command=self.CartTable.yview)

        self.CartTable.heading("pid", text="PID")
        self.CartTable.heading("name", text="Name")
        self.CartTable.heading("price", text="Price")
        self.CartTable.heading("qty", text="QTY")
        self.CartTable.heading("status", text="Status")
        self.CartTable["show"] = "headings"
        self.CartTable.pack(fill=tk.BOTH, expand=1)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        Add_CartWidgetsFrame = tk.Frame(self.root, bd=2, relief=tk.RIDGE, bg="white")
        Add_CartWidgetsFrame.place(x=430, y=480, width=530, height=110)

        tk.Label(Add_CartWidgetsFrame, text="Product Name", font=("times new roman", 12), bg="white").place(x=5, y=5)
        tk.Entry(Add_CartWidgetsFrame, textvariable=self.var_pname, font=("times new roman", 12), bg="lightyellow", state='readonly').place(x=5, y=30, width=190, height=22)

        tk.Label(Add_CartWidgetsFrame, text="Price", font=("times new roman", 12), bg="white").place(x=210, y=5)
        tk.Entry(Add_CartWidgetsFrame, textvariable=self.var_price, font=("times new roman", 12), bg="lightyellow", state='readonly').place(x=210, y=30, width=100, height=22)

        tk.Label(Add_CartWidgetsFrame, text="Quantity", font=("times new roman", 12), bg="white").place(x=320, y=5)
        tk.Entry(Add_CartWidgetsFrame, textvariable=self.var_qty, font=("times new roman", 12), bg="lightyellow").place(x=320, y=30, width=100, height=22)

        self.lbl_inStock = tk.Label(Add_CartWidgetsFrame, text="In Stock", font=("times new roman", 12), bg="white")
        self.lbl_inStock.place(x=5, y=70)

        tk.Button(Add_CartWidgetsFrame, text="Clear", command=self.clear_cart, font=("times new roman", 12, "bold"), bg="lightgray", cursor="hand2").place(x=180, y=70, width=100, height=30)
        tk.Button(Add_CartWidgetsFrame, text="Add | Update", command=self.add_update_cart, font=("times new roman", 12, "bold"), bg="orange", cursor="hand2").place(x=290, y=70, width=130, height=30)

        billFrame = tk.Frame(self.root, bd=2, relief=tk.RIDGE, bg="white")
        billFrame.place(x=970, y=40, width=370, height=550)

        bTitle = tk.Label(billFrame, text="Customer Bill Area", font=("goudy old style", 15, "bold"), bg="#f44336", fg="white")
        bTitle.pack(side=tk.TOP, fill=tk.X)

        scrolly_bill = tk.Scrollbar(billFrame, orient=tk.VERTICAL)
        self.txt_bill_area = tk.Text(billFrame, yscrollcommand=scrolly_bill.set)
        scrolly_bill.pack(side=tk.RIGHT, fill=tk.Y)
        scrolly_bill.config(command=self.txt_bill_area.yview)
        self.txt_bill_area.pack(fill=tk.BOTH, expand=1)

        billMenuFrame = tk.Frame(self.root, bd=2, relief=tk.RIDGE, bg="white")
        billMenuFrame.place(x=970, y=595, width=370, height=95)

        self.lbl_amnt = tk.Label(billMenuFrame, text="Bill Amount\n[0]", font=("goudy old style", 12, "bold"), bg="#3f51b5", fg="white")
        self.lbl_amnt.place(x=2, y=5, width=110, height=40)

        self.lbl_discount = tk.Label(billMenuFrame, text="Discount\n[5%]", font=("goudy old style", 12, "bold"), bg="#8bc34a", fg="white")
        self.lbl_discount.place(x=115, y=5, width=110, height=40)

        self.lbl_net_pay = tk.Label(billMenuFrame, text="Net Pay\n[0]", font=("goudy old style", 12, "bold"), bg="#607d8b", fg="white")
        self.lbl_net_pay.place(x=228, y=5, width=135, height=40)

        tk.Button(billMenuFrame, text="Print", command=self.print_bill, font=("goudy old style", 12, "bold"), bg="lightgreen", cursor="hand2").place(x=2, y=50, width=110, height=40)
        tk.Button(billMenuFrame, text="Clear All", command=self.clear_all, font=("goudy old style", 12, "bold"), bg="gray", fg="white", cursor="hand2").place(x=115, y=50, width=110, height=40)
        tk.Button(billMenuFrame, text="Generate Bill", command=self.generate_bill, font=("goudy old style", 12, "bold"), bg="#009688", fg="white", cursor="hand2").place(x=228, y=50, width=135, height=40)

        searchBillFrame = tk.Frame(self.root, bd=2, relief=tk.RIDGE, bg="white")
        searchBillFrame.place(x=10, y=600, width=410, height=60)
        tk.Label(searchBillFrame, text="Invoice No.", font=("times new roman", 12, "bold"), bg="white").place(x=5, y=15)
        tk.Entry(searchBillFrame, textvariable=self.var_invoice_search, font=("times new roman", 12), bg="lightyellow").place(x=100, y=15, width=150, height=25)
        tk.Button(searchBillFrame, text="Search Bill", command=self.search_bill, font=("goudy old style", 12, "bold"), bg="#2196f3", fg="white", cursor="hand2").place(x=260, y=15, width=120, height=25)

        self.show()
        self.update_date_time()

    def show(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            cur.execute("select pid, name, price, qty, status from product where status='Active'")
            rows = cur.fetchall()
            self.product_Table.delete(*self.product_Table.get_children())
            for row in rows:
                self.product_Table.insert('', tk.END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def search(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_search.get() == "":
                messagebox.showerror("Error", "Search input should be required", parent=self.root)
            else:
                cur.execute("select pid, name, price, qty, status from product where name LIKE '%" + self.var_search.get() + "%' and status='Active'")
                rows = cur.fetchall()
                if len(rows) != 0:
                    self.product_Table.delete(*self.product_Table.get_children())
                    for row in rows:
                        self.product_Table.insert('', tk.END, values=row)
                else:
                    messagebox.showerror("Error", "No record found!!!", parent=self.root)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def get_data(self, ev: Any) -> None:
        f = self.product_Table.focus()
        content = (self.product_Table.item(f))
        row = content['values']
        if not row:
            return
        self.var_pid.set(row[0])
        self.var_pname.set(row[1])
        self.var_price.set(row[2])
        self.lbl_inStock.config(text=f"In Stock [{str(row[3])}]")
        self.var_stock.set(row[3])
        self.var_qty.set('1')

    def get_data_cart(self, ev: Any) -> None:
        f = self.CartTable.focus()
        content = (self.CartTable.item(f))
        row = content['values']
        if not row:
            return
        self.var_pid.set(row[0])
        self.var_pname.set(row[1])
        self.var_price.set(row[2])
        self.var_qty.set(row[3])
        self.lbl_inStock.config(text=f"In Stock [{str(row[4])}]")
        self.var_stock.set(row[4])

    def add_update_cart(self) -> None:
        if self.var_pid.get() == '':
            messagebox.showerror('Error', "Please select product from the list", parent=self.root)
        elif self.var_qty.get() == '':
            messagebox.showerror('Error', "Quantity is Required", parent=self.root)
        elif int(self.var_qty.get()) > int(self.var_stock.get()):
            messagebox.showerror('Error', "Invalid Quantity", parent=self.root)
        else:
            price_cal = self.var_price.get()
            cart_data = [self.var_pid.get(), self.var_pname.get(), price_cal, self.var_qty.get(), self.var_stock.get()]
            present = 'no'
            index_ = 0
            for row in self.cart_list:
                if self.var_pid.get() == row[0]:
                    present = 'yes'
                    break
                index_ += 1
            if present == 'yes':
                op = messagebox.askyesno('Confirm', "Product already present\nDo you want to Update | Remove from the Cart List", parent=self.root)
                if op:
                    if self.var_qty.get() == "0":
                        self.cart_list.pop(index_)
                    else:
                        self.cart_list[index_][3] = self.var_qty.get()
            else:
                self.cart_list.append(cart_data)
            self.show_cart()
            self.bill_updates()

    def bill_updates(self) -> None:
        self.bill_amnt = 0.0
        self.net_pay = 0.0
        self.discount = 0.0
        for row in self.cart_list:
            self.bill_amnt = self.bill_amnt + (float(row[2]) * int(row[3]))
        self.discount = (self.bill_amnt * 5) / 100
        self.net_pay = self.bill_amnt - self.discount
        self.lbl_amnt.config(text=f'Bill Amount\n[{str(self.bill_amnt)}]')
        self.lbl_net_pay.config(text=f'Net Pay\n[{str(self.net_pay)}]')

    def show_cart(self) -> None:
        try:
            self.CartTable.delete(*self.CartTable.get_children())
            for row in self.cart_list:
                self.CartTable.insert('', tk.END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def generate_bill(self) -> None:
        if self.var_cname.get() == '' or self.var_contact.get() == '':
            messagebox.showerror("Error", f"Customer Details are required", parent=self.root)
        elif len(self.cart_list) == 0:
            messagebox.showerror("Error", f"Please Add Product to the Cart", parent=self.root)
        else:
            self.bill_top()
            self.bill_middle()
            self.bill_bottom()
            self.save_bill()

    def bill_top(self) -> None:
        self.invoice = int(datetime.now().strftime("%H%M%S")) + int(datetime.now().strftime("%d%m%Y"))
        bill_top_temp = f'''
\t\tInventory Management
\t Phone No. 9876543210 , Delhi-1254
{str("="*47)}
 Customer Name: {self.var_cname.get()}
 Ph no. :{self.var_contact.get()}
 Bill No. {str(self.invoice)}\t\t\tDate: {str(datetime.now().strftime("%d/%m/%Y"))}
{str("="*47)}
 Product Name\t\t\tQTY\tPrice
{str("="*47)}
        '''
        self.txt_bill_area.delete('1.0', tk.END)
        self.txt_bill_area.insert('1.0', bill_top_temp)

    def bill_middle(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            for row in self.cart_list:
                pid = row[0]
                name = row[1]
                qty = int(row[3])
                price = float(row[2]) * qty
                self.txt_bill_area.insert(tk.END, f"\n {name}\t\t\t{qty}\tRs.{price}")
                cur.execute('Update product set qty=qty-? where pid=?', (qty, pid))
            con.commit()
            self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def bill_bottom(self) -> None:
        bill_bottom_temp = f'''
{str("="*47)}
 Bill Amount\t\t\t\tRs.{self.bill_amnt}
 Discount\t\t\t\tRs.{self.discount}
 Net Pay\t\t\t\tRs.{self.net_pay}
{str("="*47)}\n
        '''
        self.txt_bill_area.insert(tk.END, bill_bottom_temp)

    def save_bill(self) -> None:
        op = messagebox.askyesno('Save Bill', "Do you want to save the Bill?", parent=self.root)
        if op:
            bill_data = self.txt_bill_area.get('1.0', tk.END)
            os.makedirs('bills', exist_ok=True)
            with open(f'bills/{self.invoice}.txt', 'w') as f:
                f.write(bill_data)
            
            con = sqlite3.connect(database=r'ims.db')
            cur = con.cursor()
            try:
                cur.execute("Insert into bills (invoice, date, name, contact, bill_data) values(?,?,?,?,?)", (
                    str(self.invoice), str(datetime.now().strftime("%d/%m/%Y")), self.var_cname.get(), self.var_contact.get(), bill_data
                ))
                con.commit()
                messagebox.showinfo('Saved', f'Bill No. {self.invoice} has been saved Successfully', parent=self.root)
            except Exception as ex:
                messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
            finally:
                con.close()

    def print_bill(self) -> None:
        if self.txt_bill_area.get('1.0', tk.END) == '\n':
            messagebox.showerror('Error', "Please generate bill, to print the receipt", parent=self.root)
        else:
            messagebox.showinfo('Print', "Please connect printer", parent=self.root)

    def search_bill(self) -> None:
        if self.var_invoice_search.get() == "":
            messagebox.showerror("Error", "Invoice No. should be required", parent=self.root)
        else:
            con = sqlite3.connect(database=r'ims.db')
            cur = con.cursor()
            try:
                cur.execute("select bill_data from bills where invoice=?", (self.var_invoice_search.get(),))
                row = cur.fetchone()
                if row is not None:
                    self.txt_bill_area.delete('1.0', tk.END)
                    self.txt_bill_area.insert('1.0', row[0])
                else:
                    messagebox.showerror("Error", "Invalid Invoice No.", parent=self.root)
            except Exception as ex:
                messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
            finally:
                con.close()

    def clear_cart(self) -> None:
        self.var_pid.set('')
        self.var_pname.set('')
        self.var_price.set('')
        self.var_qty.set('')
        self.lbl_inStock.config(text=f"In Stock")
        self.var_stock.set('')

    def clear_all(self) -> None:
        self.cart_list.clear()
        self.var_cname.set('')
        self.var_contact.set('')
        self.txt_bill_area.delete('1.0', tk.END)
        self.var_search.set('')
        self.clear_cart()
        self.show()
        self.show_cart()
        self.bill_updates()

    def update_date_time(self) -> None:
        time_ = datetime.now().strftime("%I:%M:%S %p")
        date_ = datetime.now().strftime("%d-%m-%Y")
        self.root.after(200, self.update_date_time)

class IMS:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.geometry("1350x700+0+0")
        self.root.title("Inventory Management System")

        self.icon_img = Image.new('RGB', (50, 50), color=(73, 109, 137))
        self.icon_photo = ImageTk.PhotoImage(self.icon_img)

        title = tk.Label(self.root, text="Inventory Management System", image=self.icon_photo, compound=tk.LEFT, font=("times new roman", 40, "bold"), bg="#010c48", fg="white", anchor="w", padx=20)
        title.place(x=0, y=0, relwidth=1, height=70)

        btn_logout = tk.Button(self.root, text="Logout", font=("times new roman", 15, "bold"), bg="yellow", cursor="hand2")
        btn_logout.place(x=1150, y=10, height=50, width=150)

        self.lbl_clock = tk.Label(self.root, text="Welcome to Inventory Management System\t\t Date: DD-MM-YYYY\t\t Time: HH:MM:SS", font=("times new roman", 15), bg="#4d636d", fg="white")
        self.lbl_clock.place(x=0, y=70, relwidth=1, height=30)

        LeftMenu = tk.Frame(self.root, bd=2, relief=tk.RIDGE, bg="white")
        LeftMenu.place(x=0, y=102, width=200, height=565)

        self.menu_logo = Image.new('RGB', (200, 200), color=(200, 200, 200))
        self.menu_logo_photo = ImageTk.PhotoImage(self.menu_logo)
        lbl_menu_logo = tk.Label(LeftMenu, image=self.menu_logo_photo)
        lbl_menu_logo.pack(side=tk.TOP, fill=tk.X)

        lbl_menu = tk.Label(LeftMenu, text="Menu", font=("times new roman", 20), bg="#009688")
        lbl_menu.pack(side=tk.TOP, fill=tk.X)

        btn_employee = tk.Button(LeftMenu, text="Employee", command=self.employee, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2")
        btn_employee.pack(side=tk.TOP, fill=tk.X)
        btn_supplier = tk.Button(LeftMenu, text="Supplier", command=self.supplier, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2")
        btn_supplier.pack(side=tk.TOP, fill=tk.X)
        btn_category = tk.Button(LeftMenu, text="Category", command=self.category, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2")
        btn_category.pack(side=tk.TOP, fill=tk.X)
        btn_product = tk.Button(LeftMenu, text="Product", command=self.product, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2")
        btn_product.pack(side=tk.TOP, fill=tk.X)
        btn_billing = tk.Button(LeftMenu, text="Billing", command=self.billing, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2")
        btn_billing.pack(side=tk.TOP, fill=tk.X)
        btn_exit = tk.Button(LeftMenu, text="Exit", command=self.root.destroy, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2")
        btn_exit.pack(side=tk.TOP, fill=tk.X)

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

        self.update_content()

    def employee(self) -> None:
        EmployeeClass(self.root)

    def supplier(self) -> None:
        SupplierClass(self.root)

    def category(self) -> None:
        CategoryClass(self.root)

    def product(self) -> None:
        ProductClass(self.root)

    def billing(self) -> None:
        BillingClass(self.root)

    def update_content(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            cur.execute("select * from employee")
            emp = cur.fetchall()
            self.lbl_employee.config(text=f'Total Employee\n[ {str(len(emp))} ]')

            cur.execute("select * from supplier")
            sup = cur.fetchall()
            self.lbl_supplier.config(text=f'Total Supplier\n[ {str(len(sup))} ]')

            cur.execute("select * from category")
            cat = cur.fetchall()
            self.lbl_category.config(text=f'Total Category\n[ {str(len(cat))} ]')

            cur.execute("select * from product")
            prod = cur.fetchall()
            self.lbl_product.config(text=f'Total Product\n[ {str(len(prod))} ]')

            cur.execute("select * from bills")
            bill = cur.fetchall()
            self.lbl_sales.config(text=f'Total Sales\n[ {str(len(bill))} ]')

            time_ = datetime.now().strftime("%I:%M:%S %p")
            date_ = datetime.now().strftime("%d-%m-%Y")
            self.lbl_clock.config(text=f"Welcome to Inventory Management System\t\t Date: {str(date_)}\t\t Time: {str(time_)}")
            self.lbl_clock.after(200, self.update_content)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

if __name__ == "__main__":
    create_database()
    root = tk.Tk()
    obj = IMS(root)
    root.mainloop()