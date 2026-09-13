import sqlite3
import os
import datetime
import time
from tkinter import Tk, Toplevel, Frame, Label, Button, Entry, Text, Scrollbar, StringVar, IntVar, ttk, messagebox, END, VERTICAL, HORIZONTAL, RIGHT, Y, X, BOTTOM, BOTH
from PIL import Image, ImageTk
from typing import Any, List, Tuple

def create_db() -> None:
    con = sqlite3.connect(database=r'ims.db')
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS employee(eid INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, gender TEXT, contact TEXT, dob TEXT, doj TEXT, pass TEXT, utype TEXT, address TEXT, salary TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS supplier(invoice INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, contact TEXT, desc TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS category(cid INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS product(pid INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, supplier TEXT, name TEXT, price TEXT, qty TEXT, status TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS billing(invoice TEXT PRIMARY KEY, date TEXT, cname TEXT, contact TEXT, amount TEXT)")
    con.commit()
    con.close()

class EmployeeClass:
    def __init__(self, root: Toplevel) -> None:
        self.root = root
        self.root.geometry("1100x500+220+130")
        self.root.title("Employee Management")
        self.root.focus_force()

        self.var_emp_id = StringVar()
        self.var_name = StringVar()
        self.var_email = StringVar()
        self.var_gender = StringVar()
        self.var_contact = StringVar()
        self.var_dob = StringVar()
        self.var_doj = StringVar()
        self.var_pass = StringVar()
        self.var_utype = StringVar()
        self.var_salary = StringVar()

        Label(self.root, text="Emp ID").place(x=50, y=50)
        Entry(self.root, textvariable=self.var_emp_id).place(x=150, y=50, width=180)
        Label(self.root, text="Gender").place(x=350, y=50)
        ttk.Combobox(self.root, textvariable=self.var_gender, values=("Male", "Female", "Other"), state='readonly').place(x=500, y=50, width=180)
        Label(self.root, text="Contact").place(x=750, y=50)
        Entry(self.root, textvariable=self.var_contact).place(x=850, y=50, width=180)

        Label(self.root, text="Name").place(x=50, y=90)
        Entry(self.root, textvariable=self.var_name).place(x=150, y=90, width=180)
        Label(self.root, text="DOB").place(x=350, y=90)
        Entry(self.root, textvariable=self.var_dob).place(x=500, y=90, width=180)
        Label(self.root, text="DOJ").place(x=750, y=90)
        Entry(self.root, textvariable=self.var_doj).place(x=850, y=90, width=180)

        Label(self.root, text="Email").place(x=50, y=130)
        Entry(self.root, textvariable=self.var_email).place(x=150, y=130, width=180)
        Label(self.root, text="Password").place(x=350, y=130)
        Entry(self.root, textvariable=self.var_pass).place(x=500, y=130, width=180)
        Label(self.root, text="User Type").place(x=750, y=130)
        ttk.Combobox(self.root, textvariable=self.var_utype, values=("Admin", "Employee"), state='readonly').place(x=850, y=130, width=180)

        Label(self.root, text="Address").place(x=50, y=170)
        self.txt_address = Text(self.root, width=30, height=3)
        self.txt_address.place(x=150, y=170, width=530, height=60)
        Label(self.root, text="Salary").place(x=750, y=170)
        Entry(self.root, textvariable=self.var_salary).place(x=850, y=170, width=180)

        Button(self.root, text="Save", command=self.add).place(x=500, y=250, width=110, height=28)
        Button(self.root, text="Update", command=self.update).place(x=620, y=250, width=110, height=28)
        Button(self.root, text="Delete", command=self.delete).place(x=740, y=250, width=110, height=28)
        Button(self.root, text="Clear", command=self.clear).place(x=860, y=250, width=110, height=28)

        emp_frame = Frame(self.root, bd=3, relief="ridge")
        emp_frame.place(x=0, y=300, relwidth=1, height=200)
        scrolly = Scrollbar(emp_frame, orient=VERTICAL)
        scrollx = Scrollbar(emp_frame, orient=HORIZONTAL)
        self.EmployeeTable = ttk.Treeview(emp_frame, columns=("eid", "name", "email", "gender", "contact", "dob", "doj", "pass", "utype", "address", "salary"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.pack(side=RIGHT, fill=Y)
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
        self.EmployeeTable.pack(fill=BOTH, expand=1)
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
                    messagebox.showerror("Error", "This Employee ID already assigned", parent=self.root)
                else:
                    cur.execute("Insert into employee (eid, name, email, gender, contact, dob, doj, pass, utype, address, salary) values(?,?,?,?,?,?,?,?,?,?,?)", (
                        self.var_emp_id.get(), self.var_name.get(), self.var_email.get(), self.var_gender.get(), self.var_contact.get(), self.var_dob.get(), self.var_doj.get(), self.var_pass.get(), self.var_utype.get(), self.txt_address.get('1.0', END), self.var_salary.get()
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
                self.EmployeeTable.insert('', END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def get_data(self, ev: Any) -> None:
        f = self.EmployeeTable.focus()
        content = (self.EmployeeTable.item(f))
        row = content['values']
        if row:
            self.var_emp_id.set(row[0])
            self.var_name.set(row[1])
            self.var_email.set(row[2])
            self.var_gender.set(row[3])
            self.var_contact.set(row[4])
            self.var_dob.set(row[5])
            self.var_doj.set(row[6])
            self.var_pass.set(row[7])
            self.var_utype.set(row[8])
            self.txt_address.delete('1.0', END)
            self.txt_address.insert(END, row[9])
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
                        self.var_name.get(), self.var_email.get(), self.var_gender.get(), self.var_contact.get(), self.var_dob.get(), self.var_doj.get(), self.var_pass.get(), self.var_utype.get(), self.txt_address.get('1.0', END), self.var_salary.get(), self.var_emp_id.get()
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
        self.var_gender.set("")
        self.var_contact.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_pass.set("")
        self.var_utype.set("")
        self.txt_address.delete('1.0', END)
        self.var_salary.set("")
        self.show()

class SupplierClass:
    def __init__(self, root: Toplevel) -> None:
        self.root = root
        self.root.geometry("1100x500+220+130")
        self.root.title("Supplier Management")
        self.root.focus_force()

        self.var_sup_invoice = StringVar()
        self.var_name = StringVar()
        self.var_contact = StringVar()

        Label(self.root, text="Invoice No.").place(x=50, y=50)
        Entry(self.root, textvariable=self.var_sup_invoice).place(x=150, y=50, width=180)
        Label(self.root, text="Name").place(x=50, y=90)
        Entry(self.root, textvariable=self.var_name).place(x=150, y=90, width=180)
        Label(self.root, text="Contact").place(x=50, y=130)
        Entry(self.root, textvariable=self.var_contact).place(x=150, y=130, width=180)
        Label(self.root, text="Description").place(x=50, y=170)
        self.txt_desc = Text(self.root, width=30, height=3)
        self.txt_desc.place(x=150, y=170, width=300, height=60)

        Button(self.root, text="Save", command=self.add).place(x=150, y=250, width=110, height=28)
        Button(self.root, text="Update", command=self.update).place(x=270, y=250, width=110, height=28)
        Button(self.root, text="Delete", command=self.delete).place(x=390, y=250, width=110, height=28)
        Button(self.root, text="Clear", command=self.clear).place(x=510, y=250, width=110, height=28)

        sup_frame = Frame(self.root, bd=3, relief="ridge")
        sup_frame.place(x=600, y=50, width=480, height=350)
        scrolly = Scrollbar(sup_frame, orient=VERTICAL)
        scrollx = Scrollbar(sup_frame, orient=HORIZONTAL)
        self.supplierTable = ttk.Treeview(sup_frame, columns=("invoice", "name", "contact", "desc"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.config(command=self.supplierTable.xview)
        scrolly.config(command=self.supplierTable.yview)
        self.supplierTable.heading("invoice", text="Invoice No.")
        self.supplierTable.heading("name", text="Name")
        self.supplierTable.heading("contact", text="Contact")
        self.supplierTable.heading("desc", text="Description")
        self.supplierTable["show"] = "headings"
        self.supplierTable.pack(fill=BOTH, expand=1)
        self.supplierTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def add(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice must be required", parent=self.root)
            else:
                cur.execute("Select * from supplier where invoice=?", (self.var_sup_invoice.get(),))
                row = cur.fetchone()
                if row is not None:
                    messagebox.showerror("Error", "Invoice No. already assigned", parent=self.root)
                else:
                    cur.execute("Insert into supplier (invoice, name, contact, desc) values(?,?,?,?)", (
                        self.var_sup_invoice.get(), self.var_name.get(), self.var_contact.get(), self.txt_desc.get('1.0', END)
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
            self.supplierTable.delete(*self.supplierTable.get_children())
            for row in rows:
                self.supplierTable.insert('', END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def get_data(self, ev: Any) -> None:
        f = self.supplierTable.focus()
        content = (self.supplierTable.item(f))
        row = content['values']
        if row:
            self.var_sup_invoice.set(row[0])
            self.var_name.set(row[1])
            self.var_contact.set(row[2])
            self.txt_desc.delete('1.0', END)
            self.txt_desc.insert(END, row[3])

    def update(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice No. must be required", parent=self.root)
            else:
                cur.execute("Select * from supplier where invoice=?", (self.var_sup_invoice.get(),))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror("Error", "Invalid Invoice No.", parent=self.root)
                else:
                    cur.execute("Update supplier set name=?, contact=?, desc=? where invoice=?", (
                        self.var_name.get(), self.var_contact.get(), self.txt_desc.get('1.0', END), self.var_sup_invoice.get()
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
                messagebox.showerror("Error", "Invoice No. must be required", parent=self.root)
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
        self.txt_desc.delete('1.0', END)
        self.show()

class CategoryClass:
    def __init__(self, root: Toplevel) -> None:
        self.root = root
        self.root.geometry("1100x500+220+130")
        self.root.title("Category Management")
        self.root.focus_force()

        self.var_cat_id = StringVar()
        self.var_name = StringVar()

        Label(self.root, text="Enter Category Name").place(x=50, y=50)
        Entry(self.root, textvariable=self.var_name).place(x=50, y=90, width=300)
        Button(self.root, text="Add", command=self.add).place(x=360, y=90, width=100, height=28)
        Button(self.root, text="Delete", command=self.delete).place(x=470, y=90, width=100, height=28)

        cat_frame = Frame(self.root, bd=3, relief="ridge")
        cat_frame.place(x=600, y=50, width=480, height=350)
        scrolly = Scrollbar(cat_frame, orient=VERTICAL)
        scrollx = Scrollbar(cat_frame, orient=HORIZONTAL)
        self.categoryTable = ttk.Treeview(cat_frame, columns=("cid", "name"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.config(command=self.categoryTable.xview)
        scrolly.config(command=self.categoryTable.yview)
        self.categoryTable.heading("cid", text="C ID")
        self.categoryTable.heading("name", text="Name")
        self.categoryTable["show"] = "headings"
        self.categoryTable.pack(fill=BOTH, expand=1)
        self.categoryTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def add(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_name.get() == "":
                messagebox.showerror("Error", "Category name must be required", parent=self.root)
            else:
                cur.execute("Select * from category where name=?", (self.var_name.get(),))
                row = cur.fetchone()
                if row is not None:
                    messagebox.showerror("Error", "Category already present", parent=self.root)
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
            self.categoryTable.delete(*self.categoryTable.get_children())
            for row in rows:
                self.categoryTable.insert('', END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def get_data(self, ev: Any) -> None:
        f = self.categoryTable.focus()
        content = (self.categoryTable.item(f))
        row = content['values']
        if row:
            self.var_cat_id.set(row[0])
            self.var_name.set(row[1])

    def delete(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            if self.var_cat_id.get() == "":
                messagebox.showerror("Error", "Please select category from the list", parent=self.root)
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
    def __init__(self, root: Toplevel) -> None:
        self.root = root
        self.root.geometry("1100x500+220+130")
        self.root.title("Product Management")
        self.root.focus_force()

        self.var_pid = StringVar()
        self.var_cat = StringVar()
        self.var_sup = StringVar()
        self.var_name = StringVar()
        self.var_price = StringVar()
        self.var_qty = StringVar()
        self.var_status = StringVar()

        self.cat_list: List[str] = []
        self.sup_list: List[str] = []
        self.fetch_cat_sup()

        Label(self.root, text="Category").place(x=50, y=50)
        ttk.Combobox(self.root, textvariable=self.var_cat, values=self.cat_list, state='readonly').place(x=150, y=50, width=180)
        Label(self.root, text="Supplier").place(x=50, y=90)
        ttk.Combobox(self.root, textvariable=self.var_sup, values=self.sup_list, state='readonly').place(x=150, y=90, width=180)
        Label(self.root, text="Name").place(x=50, y=130)
        Entry(self.root, textvariable=self.var_name).place(x=150, y=130, width=180)
        Label(self.root, text="Price").place(x=50, y=170)
        Entry(self.root, textvariable=self.var_price).place(x=150, y=170, width=180)
        Label(self.root, text="Quantity").place(x=50, y=210)
        Entry(self.root, textvariable=self.var_qty).place(x=150, y=210, width=180)
        Label(self.root, text="Status").place(x=50, y=250)
        ttk.Combobox(self.root, textvariable=self.var_status, values=("Active", "Inactive"), state='readonly').place(x=150, y=250, width=180)

        Button(self.root, text="Save", command=self.add).place(x=50, y=300, width=100, height=28)
        Button(self.root, text="Update", command=self.update).place(x=160, y=300, width=100, height=28)
        Button(self.root, text="Delete", command=self.delete).place(x=270, y=300, width=100, height=28)
        Button(self.root, text="Clear", command=self.clear).place(x=380, y=300, width=100, height=28)

        prod_frame = Frame(self.root, bd=3, relief="ridge")
        prod_frame.place(x=500, y=50, width=580, height=400)
        scrolly = Scrollbar(prod_frame, orient=VERTICAL)
        scrollx = Scrollbar(prod_frame, orient=HORIZONTAL)
        self.productTable = ttk.Treeview(prod_frame, columns=("pid", "Category", "Supplier", "name", "price", "qty", "status"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.config(command=self.productTable.xview)
        scrolly.config(command=self.productTable.yview)
        self.productTable.heading("pid", text="P ID")
        self.productTable.heading("Category", text="Category")
        self.productTable.heading("Supplier", text="Supplier")
        self.productTable.heading("name", text="Name")
        self.productTable.heading("price", text="Price")
        self.productTable.heading("qty", text="Qty")
        self.productTable.heading("status", text="Status")
        self.productTable["show"] = "headings"
        self.productTable.pack(fill=BOTH, expand=1)
        self.productTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def fetch_cat_sup(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            cur.execute("Select name from category")
            cat = cur.fetchall()
            self.cat_list.append("Empty")
            if len(cat) > 0:
                del self.cat_list[:]
                self.cat_list.append("Select")
                for i in cat:
                    self.cat_list.append(i[0])

            cur.execute("Select name from supplier")
            sup = cur.fetchall()
            self.sup_list.append("Empty")
            if len(sup) > 0:
                del self.sup_list[:]
                self.sup_list.append("Select")
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
            if self.var_cat.get() == "Select" or self.var_cat.get() == "Empty" or self.var_sup.get() == "Select" or self.var_name.get() == "":
                messagebox.showerror("Error", "All fields are required", parent=self.root)
            else:
                cur.execute("Select * from product where name=?", (self.var_name.get(),))
                row = cur.fetchone()
                if row is not None:
                    messagebox.showerror("Error", "Product already present", parent=self.root)
                else:
                    cur.execute("Insert into product (Category, Supplier, name, price, qty, status) values(?,?,?,?,?,?)", (
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
            self.productTable.delete(*self.productTable.get_children())
            for row in rows:
                self.productTable.insert('', END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def get_data(self, ev: Any) -> None:
        f = self.productTable.focus()
        content = (self.productTable.item(f))
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
                    cur.execute("Update product set Category=?, Supplier=?, name=?, price=?, qty=?, status=? where pid=?", (
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
        self.var_cat.set("Select")
        self.var_sup.set("Select")
        self.var_name.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("Active")
        self.show()

class BillingClass:
    def __init__(self, root: Toplevel) -> None:
        self.root = root
        self.root.geometry("1100x600+220+50")
        self.root.title("Billing Management")
        self.root.focus_force()

        self.cart_list: List[Tuple[str, str, str, str, str]] = []
        self.var_search = StringVar()
        self.var_cname = StringVar()
        self.var_contact = StringVar()
        self.var_pid = StringVar()
        self.var_pname = StringVar()
        self.var_price = StringVar()
        self.var_qty = StringVar()
        self.var_stock = StringVar()

        ProductFrame = Frame(self.root, bd=4, relief="ridge")
        ProductFrame.place(x=10, y=10, width=410, height=550)
        Label(ProductFrame, text="All Products").pack(side="top", fill="x")
        SearchFrame = Frame(ProductFrame, bd=2, relief="ridge")
        SearchFrame.place(x=2, y=30, width=398, height=50)
        Label(SearchFrame, text="Search Product").place(x=5, y=10)
        Entry(SearchFrame, textvariable=self.var_search).place(x=110, y=10, width=150)
        Button(SearchFrame, text="Search", command=self.search).place(x=270, y=8, width=100, height=25)
        Button(SearchFrame, text="Show All", command=self.show).place(x=270, y=35, width=100, height=25)

        pFrame = Frame(ProductFrame, bd=3, relief="ridge")
        pFrame.place(x=2, y=90, width=398, height=250)
        scrolly = Scrollbar(pFrame, orient=VERTICAL)
        scrollx = Scrollbar(pFrame, orient=HORIZONTAL)
        self.productTable = ttk.Treeview(pFrame, columns=("pid", "name", "price", "qty", "status"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.config(command=self.productTable.xview)
        scrolly.config(command=self.productTable.yview)
        self.productTable.heading("pid", text="PID")
        self.productTable.heading("name", text="Name")
        self.productTable.heading("price", text="Price")
        self.productTable.heading("qty", text="Qty")
        self.productTable.heading("status", text="Status")
        self.productTable["show"] = "headings"
        self.productTable.pack(fill=BOTH, expand=1)
        self.productTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

        AddCartFrame = Frame(ProductFrame, bd=3, relief="ridge")
        AddCartFrame.place(x=2, y=350, width=398, height=180)
        Label(AddCartFrame, text="Product Name").place(x=5, y=5)
        Entry(AddCartFrame, textvariable=self.var_pname, state='readonly').place(x=5, y=25, width=150)
        Label(AddCartFrame, text="Price").place(x=170, y=5)
        Entry(AddCartFrame, textvariable=self.var_price, state='readonly').place(x=170, y=25, width=100)
        Label(AddCartFrame, text="Quantity").place(x=280, y=5)
        Entry(AddCartFrame, textvariable=self.var_qty).place(x=280, y=25, width=100)
        Label(AddCartFrame, text="In Stock").place(x=5, y=60)
        Entry(AddCartFrame, textvariable=self.var_stock, state='readonly').place(x=5, y=80, width=150)
        Button(AddCartFrame, text="Clear", command=self.clear_cart_item).place(x=170, y=80, width=100, height=25)
        Button(AddCartFrame, text="Add | Update", command=self.add_update_cart).place(x=280, y=80, width=100, height=25)

        CustomerFrame = Frame(self.root, bd=4, relief="ridge")
        CustomerFrame.place(x=430, y=10, width=350, height=70)
        Label(CustomerFrame, text="Customer Details").pack(side="top", fill="x")
        Label(CustomerFrame, text="Name").place(x=5, y=30)
        Entry(CustomerFrame, textvariable=self.var_cname).place(x=50, y=30, width=120)
        Label(CustomerFrame, text="Contact").place(x=180, y=30)
        Entry(CustomerFrame, textvariable=self.var_contact).place(x=230, y=30, width=100)

        CalCartFrame = Frame(self.root, bd=2, relief="ridge")
        CalCartFrame.place(x=430, y=90, width=350, height=350)
        cartFrame = Frame(CalCartFrame, bd=3, relief="ridge")
        cartFrame.place(x=2, y=2, width=342, height=342)
        scrolly2 = Scrollbar(cartFrame, orient=VERTICAL)
        scrollx2 = Scrollbar(cartFrame, orient=HORIZONTAL)
        self.CartTable = ttk.Treeview(cartFrame, columns=("pid", "name", "price", "qty", "total"), yscrollcommand=scrolly2.set, xscrollcommand=scrollx2.set)
        scrollx2.pack(side=BOTTOM, fill=X)
        scrolly2.pack(side=RIGHT, fill=Y)
        scrollx2.config(command=self.CartTable.xview)
        scrolly2.config(command=self.CartTable.yview)
        self.CartTable.heading("pid", text="PID")
        self.CartTable.heading("name", text="Name")
        self.CartTable.heading("price", text="Price")
        self.CartTable.heading("qty", text="Qty")
        self.CartTable.heading("total", text="Total")
        self.CartTable["show"] = "headings"
        self.CartTable.pack(fill=BOTH, expand=1)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        BillMenuFrame = Frame(self.root, bd=2, relief="ridge")
        BillMenuFrame.place(x=430, y=450, width=350, height=110)
        self.lbl_amnt = Label(BillMenuFrame, text="Bill Amount\n[0]")
        self.lbl_amnt.place(x=2, y=5, width=110, height=40)
        self.lbl_net_pay = Label(BillMenuFrame, text="Net Pay\n[0]")
        self.lbl_net_pay.place(x=115, y=5, width=110, height=40)
        Button(BillMenuFrame, text="Clear All", command=self.clear_all).place(x=230, y=5, width=110, height=40)
        Button(BillMenuFrame, text="Generate Bill", command=self.generate_bill).place(x=2, y=50, width=340, height=50)

        BillFrame = Frame(self.root, bd=4, relief="ridge")
        BillFrame.place(x=790, y=10, width=300, height=550)
        Label(BillFrame, text="Customer Bill Area").pack(side="top", fill="x")
        scrolly3 = Scrollbar(BillFrame, orient=VERTICAL)
        self.txt_bill_area = Text(BillFrame, yscrollcommand=scrolly3.set)
        scrolly3.pack(side=RIGHT, fill=Y)
        scrolly3.config(command=self.txt_bill_area.yview)
        self.txt_bill_area.pack(fill=BOTH, expand=1)

    def show(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            cur.execute("select pid, name, price, qty, status from product where status='Active'")
            rows = cur.fetchall()
            self.productTable.delete(*self.productTable.get_children())
            for row in rows:
                self.productTable.insert('', END, values=row)
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
                    self.productTable.delete(*self.productTable.get_children())
                    for row in rows:
                        self.productTable.insert('', END, values=row)
                else:
                    messagebox.showerror("Error", "No record found", parent=self.root)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def get_data(self, ev: Any) -> None:
        f = self.productTable.focus()
        content = (self.productTable.item(f))
        row = content['values']
        if row:
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_stock.set(row[3])
            self.var_qty.set('1')

    def get_data_cart(self, ev: Any) -> None:
        f = self.CartTable.focus()
        content = (self.CartTable.item(f))
        row = content['values']
        if row:
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_qty.set(row[3])
            self.var_stock.set(row[4])

    def add_update_cart(self) -> None:
        if self.var_pid.get() == '':
            messagebox.showerror('Error', "Please select product from the list", parent=self.root)
        elif self.var_qty.get() == '':
            messagebox.showerror('Error', "Quantity is Required", parent=self.root)
        elif int(self.var_qty.get()) > int(self.var_stock.get()):
            messagebox.showerror('Error', "Invalid Quantity", parent=self.root)
        else:
            price_calc = float(int(self.var_qty.get()) * float(self.var_price.get()))
            cart_data = [self.var_pid.get(), self.var_pname.get(), self.var_price.get(), self.var_qty.get(), str(price_calc)]
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
                        self.cart_list[index_] = tuple(cart_data)
            else:
                self.cart_list.append(tuple(cart_data))
            self.show_cart()
            self.bill_updates()

    def bill_updates(self) -> None:
        self.bill_amnt = 0.0
        self.net_pay = 0.0
        for row in self.cart_list:
            self.bill_amnt += float(row[4])
        self.net_pay = self.bill_amnt
        self.lbl_amnt.config(text=f'Bill Amount\n[{str(self.bill_amnt)}]')
        self.lbl_net_pay.config(text=f'Net Pay\n[{str(self.net_pay)}]')

    def show_cart(self) -> None:
        try:
            self.CartTable.delete(*self.CartTable.get_children())
            for row in self.cart_list:
                self.CartTable.insert('', END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def generate_bill(self) -> None:
        if self.var_cname.get() == '' or self.var_contact.get() == '':
            messagebox.showerror("Error", "Customer Details are required", parent=self.root)
        elif len(self.cart_list) == 0:
            messagebox.showerror("Error", "Please Add Product to the Cart", parent=self.root)
        else:
            self.bill_top()
            self.bill_middle()
            self.bill_bottom()
            self.save_bill()

    def bill_top(self) -> None:
        self.invoice = int(time.time())
        bill_top_temp = f'''
\tInventory Management
\tPhone No. 9876543210
{str("="*35)}
 Customer Name: {self.var_cname.get()}
 Ph no. :{self.var_contact.get()}
 Bill No. {str(self.invoice)}\t\t\tDate: {str(time.strftime("%d/%m/%Y"))}
{str("="*35)}
 Product Name\t\t\tQTY\tPrice
{str("="*35)}
        '''
        self.txt_bill_area.delete('1.0', END)
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
                self.txt_bill_area.insert(END, f"\n {name}\t\t\t{qty}\tRs.{price}")
                cur.execute("select qty from product where pid=?", (pid,))
                p_qty = cur.fetchone()[0]
                new_qty = int(p_qty) - qty
                status = 'Active'
                if new_qty == 0:
                    status = 'Inactive'
                cur.execute("Update product set qty=?, status=? where pid=?", (new_qty, status, pid))
            con.commit()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()
            self.show()

    def bill_bottom(self) -> None:
        bill_bottom_temp = f'''
{str("="*35)}
 Bill Amount\t\t\t\tRs.{self.bill_amnt}
 Net Pay\t\t\t\tRs.{self.net_pay}
{str("="*35)}\n
        '''
        self.txt_bill_area.insert(END, bill_bottom_temp)

    def save_bill(self) -> None:
        op = messagebox.askyesno("Save Bill", "Do you want to save the Bill?", parent=self.root)
        if op:
            self.bill_data = self.txt_bill_area.get('1.0', END)
            if not os.path.exists('bills'):
                os.makedirs('bills')
            with open(f'bills/{str(self.invoice)}.txt', 'w') as f:
                f.write(self.bill_data)
            
            con = sqlite3.connect(database=r'ims.db')
            cur = con.cursor()
            try:
                cur.execute("Insert into billing (invoice, date, cname, contact, amount) values(?,?,?,?,?)", (
                    str(self.invoice), str(time.strftime("%d/%m/%Y")), self.var_cname.get(), self.var_contact.get(), str(self.net_pay)
                ))
                con.commit()
            except Exception as ex:
                messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
            finally:
                con.close()
            messagebox.showinfo("Saved", f"Bill No. {self.invoice} has been saved successfully", parent=self.root)

    def clear_cart_item(self) -> None:
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")

    def clear_all(self) -> None:
        self.cart_list.clear()
        self.var_cname.set("")
        self.var_contact.set("")
        self.txt_bill_area.delete('1.0', END)
        self.clear_cart_item()
        self.show_cart()
        self.bill_updates()

class IMS:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.geometry("1350x700+0+0")
        self.root.title("Inventory Management System")

        title = Label(self.root, text="Inventory Management System", font=("times new roman", 40, "bold"), bg="#010c48", fg="white", anchor="w", padx=20)
        title.place(x=0, y=0, relwidth=1, height=70)

        self.lbl_clock = Label(self.root, text="Welcome to Inventory Management System\t\t Date: DD-MM-YYYY\t\t Time: HH:MM:SS", font=("times new roman", 15), bg="#4d636d", fg="white")
        self.lbl_clock.place(x=0, y=70, relwidth=1, height=30)

        LeftMenu = Frame(self.root, bd=2, relief="ridge", bg="white")
        LeftMenu.place(x=0, y=102, width=200, height=565)

        Label(LeftMenu, text="Menu", font=("times new roman", 20), bg="#009688").pack(side="top", fill="x")
        Button(LeftMenu, text="Employee", command=self.employee, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side="top", fill="x")
        Button(LeftMenu, text="Supplier", command=self.supplier, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side="top", fill="x")
        Button(LeftMenu, text="Category", command=self.category, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side="top", fill="x")
        Button(LeftMenu, text="Product", command=self.product, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side="top", fill="x")
        Button(LeftMenu, text="Billing", command=self.billing, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side="top", fill="x")
        Button(LeftMenu, text="Exit", command=self.root.quit, font=("times new roman", 20, "bold"), bg="white", bd=3, cursor="hand2").pack(side="top", fill="x")

        self.lbl_employee = Label(self.root, text="Total Employee\n[ 0 ]", bd=5, relief="ridge", bg="#33bbf9", fg="white", font=("goudy old style", 20, "bold"))
        self.lbl_employee.place(x=300, y=120, height=150, width=300)

        self.lbl_supplier = Label(self.root, text="Total Supplier\n[ 0 ]", bd=5, relief="ridge", bg="#ff5722", fg="white", font=("goudy old style", 20, "bold"))
        self.lbl_supplier.place(x=650, y=120, height=150, width=300)

        self.lbl_category = Label(self.root, text="Total Category\n[ 0 ]", bd=5, relief="ridge", bg="#009688", fg="white", font=("goudy old style", 20, "bold"))
        self.lbl_category.place(x=1000, y=120, height=150, width=300)

        self.lbl_product = Label(self.root, text="Total Product\n[ 0 ]", bd=5, relief="ridge", bg="#607d8b", fg="white", font=("goudy old style", 20, "bold"))
        self.lbl_product.place(x=300, y=300, height=150, width=300)

        self.lbl_sales = Label(self.root, text="Total Sales\n[ 0 ]", bd=5, relief="ridge", bg="#ffc107", fg="white", font=("goudy old style", 20, "bold"))
        self.lbl_sales.place(x=650, y=300, height=150, width=300)

        self.im = Image.new('RGB', (300, 150), color=(73, 109, 137))
        self.im_tk = ImageTk.PhotoImage(self.im)
        Label(self.root, image=self.im_tk, bd=5, relief="ridge").place(x=1000, y=300, height=150, width=300)

        self.update_content()

    def update_content(self) -> None:
        con = sqlite3.connect(database=r'ims.db')
        cur = con.cursor()
        try:
            cur.execute("select * from employee")
            emp = cur.fetchall()
            self.lbl_employee.config(text=f"Total Employee\n[ {str(len(emp))} ]")

            cur.execute("select * from supplier")
            sup = cur.fetchall()
            self.lbl_supplier.config(text=f"Total Supplier\n[ {str(len(sup))} ]")

            cur.execute("select * from category")
            cat = cur.fetchall()
            self.lbl_category.config(text=f"Total Category\n[ {str(len(cat))} ]")

            cur.execute("select * from product")
            prod = cur.fetchall()
            self.lbl_product.config(text=f"Total Product\n[ {str(len(prod))} ]")

            cur.execute("select * from billing")
            bill = cur.fetchall()
            self.lbl_sales.config(text=f"Total Sales\n[ {str(len(bill))} ]")

            time_ = time.strftime("%I:%M:%S")
            date_ = time.strftime("%d-%m-%Y")
            self.lbl_clock.config(text=f"Welcome to Inventory Management System\t\t Date: {str(date_)}\t\t Time: {str(time_)}")
            self.lbl_clock.after(200, self.update_content)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def employee(self) -> None:
        self.new_win = Toplevel(self.root)
        self.new_obj = EmployeeClass(self.new_win)

    def supplier(self) -> None:
        self.new_win = Toplevel(self.root)
        self.new_obj = SupplierClass(self.new_win)

    def category(self) -> None:
        self.new_win = Toplevel(self.root)
        self.new_obj = CategoryClass(self.new_win)

    def product(self) -> None:
        self.new_win = Toplevel(self.root)
        self.new_obj = ProductClass(self.new_win)

    def billing(self) -> None:
        self.new_win = Toplevel(self.root)
        self.new_obj = BillingClass(self.new_win)

if __name__ == "__main__":
    create_db()
    root = Tk()
    obj = IMS(root)
    root.mainloop()