import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import sqlite3
import os
from datetime import datetime
from typing import List, Tuple, Optional, Any

def setup_database() -> None:
    con = sqlite3.connect(database='ims.db')
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS employee(eid INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, gender TEXT, contact TEXT, dob TEXT, doj TEXT, pass TEXT, utype TEXT, address TEXT, salary TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS supplier(invoice INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, contact TEXT, desc TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS category(cid INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS product(pid INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, supplier TEXT, name TEXT, price TEXT, qty TEXT, status TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS bills(invoice INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, name TEXT, contact TEXT, total TEXT)")
    con.commit()
    con.close()
    
    if not os.path.exists('bills'):
        os.makedirs('bills')

def get_placeholder_image(width: int, height: int, color: str) -> ImageTk.PhotoImage:
    img = Image.new("RGB", (width, height), color)
    return ImageTk.PhotoImage(img)

class EmployeeClass:
    def __init__(self, root: tk.Toplevel) -> None:
        self.root = root
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
        
        search_frame = tk.LabelFrame(self.root, text="Search Employee", font=("goudy old style", 12, "bold"), bd=2, relief=tk.RIDGE, bg="white")
        search_frame.place(x=250, y=20, width=600, height=70)
        
        self.var_search_by = tk.StringVar()
        cmb_search = ttk.Combobox(search_frame, textvariable=self.var_search_by, values=("Select", "Email", "Name", "Contact"), state='readonly', justify=tk.CENTER, font=("goudy old style", 15))
        cmb_search.place(x=10, y=10, width=180)
        cmb_search.current(0)
        
        self.var_search_txt = tk.StringVar()
        txt_search = tk.Entry(search_frame, textvariable=self.var_search_txt, font=("goudy old style", 15), bg="lightyellow")
        txt_search.place(x=200, y=10)
        
        btn_search = tk.Button(search_frame, text="Search", command=self.search, font=("goudy old style", 15), bg="#4caf50", fg="white", cursor="hand2")
        btn_search.place(x=410, y=9, width=150, height=30)
        
        title = tk.Label(self.root, text="Employee Details", font=("goudy old style", 15), bg="#0f4d7d", fg="white")
        title.place(x=50, y=100, width=1000)
        
        tk.Label(self.root, text="Emp ID", font=("goudy old style", 15), bg="white").place(x=50, y=150)
        tk.Label(self.root, text="Gender", font=("goudy old style", 15), bg="white").place(x=350, y=150)
        tk.Label(self.root, text="Contact", font=("goudy old style", 15), bg="white").place(x=750, y=150)
        
        tk.Entry(self.root, textvariable=self.var_emp_id, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=150, width=180)
        ttk.Combobox(self.root, textvariable=self.var_gender, values=("Select", "Male", "Female", "Other"), state='readonly', justify=tk.CENTER, font=("goudy old style", 15)).place(x=500, y=150, width=180)
        tk.Entry(self.root, textvariable=self.var_contact, font=("goudy old style", 15), bg="lightyellow").place(x=850, y=150, width=180)
        
        tk.Label(self.root, text="Name", font=("goudy old style", 15), bg="white").place(x=50, y=190)
        tk.Label(self.root, text="DOB", font=("goudy old style", 15), bg="white").place(x=350, y=190)
        tk.Label(self.root, text="DOJ", font=("goudy old style", 15), bg="white").place(x=750, y=190)
        
        tk.Entry(self.root, textvariable=self.var_name, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=190, width=180)
        tk.Entry(self.root, textvariable=self.var_dob, font=("goudy old style", 15), bg="lightyellow").place(x=500, y=190, width=180)
        tk.Entry(self.root, textvariable=self.var_doj, font=("goudy old style", 15), bg="lightyellow").place(x=850, y=190, width=180)
        
        tk.Label(self.root, text="Email", font=("goudy old style", 15), bg="white").place(x=50, y=230)
        tk.Label(self.root, text="Password", font=("goudy old style", 15), bg="white").place(x=350, y=230)
        tk.Label(self.root, text="User Type", font=("goudy old style", 15), bg="white").place(x=750, y=230)
        
        tk.Entry(self.root, textvariable=self.var_email, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=230, width=180)
        tk.Entry(self.root, textvariable=self.var_pass, font=("goudy old style", 15), bg="lightyellow").place(x=500, y=230, width=180)
        ttk.Combobox(self.root, textvariable=self.var_utype, values=("Admin", "Employee"), state='readonly', justify=tk.CENTER, font=("goudy old style", 15)).place(x=850, y=230, width=180)
        
        tk.Label(self.root, text="Address", font=("goudy old style", 15), bg="white").place(x=50, y=270)
        tk.Label(self.root, text="Salary", font=("goudy old style", 15), bg="white").place(x=500, y=270)
        
        self.txt_address = tk.Text(self.root, font=("goudy old style", 15), bg="lightyellow")
        self.txt_address.place(x=150, y=270, width=300, height=60)
        tk.Entry(self.root, textvariable=self.var_salary, font=("goudy old style", 15), bg="lightyellow").place(x=600, y=270, width=180)
        
        tk.Button(self.root, text="Save", command=self.add, font=("goudy old style", 15), bg="#2196f3", fg="white", cursor="hand2").place(x=500, y=305, width=110, height=28)
        tk.Button(self.root, text="Update", command=self.update, font=("goudy old style", 15), bg="#4caf50", fg="white", cursor="hand2").place(x=620, y=305, width=110, height=28)
        tk.Button(self.root, text="Delete", command=self.delete, font=("goudy old style", 15), bg="#f44336", fg="white", cursor="hand2").place(x=740, y=305, width=110, height=28)
        tk.Button(self.root, text="Clear", command=self.clear, font=("goudy old style", 15), bg="#607d8b", fg="white", cursor="hand2").place(x=860, y=305, width=110, height=28)
        
        emp_frame = tk.Frame(self.root, bd=3, relief=tk.RIDGE)
        emp_frame.place(x=0, y=350, relwidth=1, height=150)
        
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
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            if self.var_emp_id.get() == "":
                messagebox.showerror("Error", "Employee ID Must be required", parent=self.root)
            else:
                cur.execute("SELECT * FROM employee WHERE eid=?", (self.var_emp_id.get(),))
                row = cur.fetchone()
                if row is not None:
                    messagebox.showerror("Error", "This Employee ID already assigned, try different", parent=self.root)
                else:
                    cur.execute("INSERT INTO employee (eid, name, email, gender, contact, dob, doj, pass, utype, address, salary) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                        self.var_emp_id.get(), self.var_name.get(), self.var_email.get(), self.var_gender.get(),
                        self.var_contact.get(), self.var_dob.get(), self.var_doj.get(), self.var_pass.get(),
                        self.var_utype.get(), self.txt_address.get('1.0', tk.END).strip(), self.var_salary.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Employee Added Successfully", parent=self.root)
                    self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def show(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            cur.execute("SELECT * FROM employee")
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
            self.txt_address.delete('1.0', tk.END)
            self.txt_address.insert(tk.END, row[9])
            self.var_salary.set(row[10])

    def update(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            if self.var_emp_id.get() == "":
                messagebox.showerror("Error", "Employee ID Must be required", parent=self.root)
            else:
                cur.execute("SELECT * FROM employee WHERE eid=?", (self.var_emp_id.get(),))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror("Error", "Invalid Employee ID", parent=self.root)
                else:
                    cur.execute("UPDATE employee SET name=?, email=?, gender=?, contact=?, dob=?, doj=?, pass=?, utype=?, address=?, salary=? WHERE eid=?", (
                        self.var_name.get(), self.var_email.get(), self.var_gender.get(), self.var_contact.get(),
                        self.var_dob.get(), self.var_doj.get(), self.var_pass.get(), self.var_utype.get(),
                        self.txt_address.get('1.0', tk.END).strip(), self.var_salary.get(), self.var_emp_id.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Employee Updated Successfully", parent=self.root)
                    self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def delete(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            if self.var_emp_id.get() == "":
                messagebox.showerror("Error", "Employee ID Must be required", parent=self.root)
            else:
                cur.execute("SELECT * FROM employee WHERE eid=?", (self.var_emp_id.get(),))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror("Error", "Invalid Employee ID", parent=self.root)
                else:
                    op = messagebox.askyesno("Confirm", "Do you really want to delete?", parent=self.root)
                    if op:
                        cur.execute("DELETE FROM employee WHERE eid=?", (self.var_emp_id.get(),))
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
        self.var_gender.set("Select")
        self.var_contact.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_pass.set("")
        self.var_utype.set("Admin")
        self.txt_address.delete('1.0', tk.END)
        self.var_salary.set("")
        self.var_search_txt.set("")
        self.var_search_by.set("Select")
        self.show()

    def search(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            if self.var_search_by.get() == "Select":
                messagebox.showerror("Error", "Select Search By option", parent=self.root)
            elif self.var_search_txt.get() == "":
                messagebox.showerror("Error", "Search input should be required", parent=self.root)
            else:
                cur.execute(f"SELECT * FROM employee WHERE {self.var_search_by.get()} LIKE '%{self.var_search_txt.get()}%'")
                rows = cur.fetchall()
                if len(rows) != 0:
                    self.EmployeeTable.delete(*self.EmployeeTable.get_children())
                    for row in rows:
                        self.EmployeeTable.insert('', tk.END, values=row)
                else:
                    messagebox.showerror("Error", "No record found", parent=self.root)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

class SupplierClass:
    def __init__(self, root: tk.Toplevel) -> None:
        self.root = root
        self.root.geometry("1100x500+220+130")
        self.root.title("Supplier Management")
        self.root.focus_force()
        
        self.var_sup_invoice = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_contact = tk.StringVar()
        
        search_frame = tk.LabelFrame(self.root, text="Search Supplier", font=("goudy old style", 12, "bold"), bd=2, relief=tk.RIDGE, bg="white")
        search_frame.place(x=250, y=20, width=600, height=70)
        
        self.var_search_txt = tk.StringVar()
        tk.Label(search_frame, text="Invoice No.", font=("goudy old style", 15), bg="white").place(x=10, y=10)
        tk.Entry(search_frame, textvariable=self.var_search_txt, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=10, width=200)
        tk.Button(search_frame, text="Search", command=self.search, font=("goudy old style", 15), bg="#4caf50", fg="white", cursor="hand2").place(x=380, y=9, width=150, height=30)
        
        title = tk.Label(self.root, text="Supplier Details", font=("goudy old style", 15), bg="#0f4d7d", fg="white")
        title.place(x=50, y=100, width=1000)
        
        tk.Label(self.root, text="Invoice No.", font=("goudy old style", 15), bg="white").place(x=50, y=150)
        tk.Entry(self.root, textvariable=self.var_sup_invoice, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=150, width=180)
        
        tk.Label(self.root, text="Name", font=("goudy old style", 15), bg="white").place(x=50, y=190)
        tk.Entry(self.root, textvariable=self.var_name, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=190, width=180)
        
        tk.Label(self.root, text="Contact", font=("goudy old style", 15), bg="white").place(x=50, y=230)
        tk.Entry(self.root, textvariable=self.var_contact, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=230, width=180)
        
        tk.Label(self.root, text="Description", font=("goudy old style", 15), bg="white").place(x=50, y=270)
        self.txt_desc = tk.Text(self.root, font=("goudy old style", 15), bg="lightyellow")
        self.txt_desc.place(x=150, y=270, width=300, height=90)
        
        tk.Button(self.root, text="Save", command=self.add, font=("goudy old style", 15), bg="#2196f3", fg="white", cursor="hand2").place(x=150, y=380, width=110, height=28)
        tk.Button(self.root, text="Update", command=self.update, font=("goudy old style", 15), bg="#4caf50", fg="white", cursor="hand2").place(x=270, y=380, width=110, height=28)
        tk.Button(self.root, text="Delete", command=self.delete, font=("goudy old style", 15), bg="#f44336", fg="white", cursor="hand2").place(x=390, y=380, width=110, height=28)
        tk.Button(self.root, text="Clear", command=self.clear, font=("goudy old style", 15), bg="#607d8b", fg="white", cursor="hand2").place(x=510, y=380, width=110, height=28)
        
        sup_frame = tk.Frame(self.root, bd=3, relief=tk.RIDGE)
        sup_frame.place(x=650, y=150, width=400, height=300)
        
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
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice No. Must be required", parent=self.root)
            else:
                cur.execute("SELECT * FROM supplier WHERE invoice=?", (self.var_sup_invoice.get(),))
                row = cur.fetchone()
                if row is not None:
                    messagebox.showerror("Error", "Invoice No. already assigned, try different", parent=self.root)
                else:
                    cur.execute("INSERT INTO supplier (invoice, name, contact, desc) VALUES(?,?,?,?)", (
                        self.var_sup_invoice.get(), self.var_name.get(), self.var_contact.get(),
                        self.txt_desc.get('1.0', tk.END).strip()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Supplier Added Successfully", parent=self.root)
                    self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def show(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            cur.execute("SELECT * FROM supplier")
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
        if row:
            self.var_sup_invoice.set(row[0])
            self.var_name.set(row[1])
            self.var_contact.set(row[2])
            self.txt_desc.delete('1.0', tk.END)
            self.txt_desc.insert(tk.END, row[3])

    def update(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice No. Must be required", parent=self.root)
            else:
                cur.execute("SELECT * FROM supplier WHERE invoice=?", (self.var_sup_invoice.get(),))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror("Error", "Invalid Invoice No.", parent=self.root)
                else:
                    cur.execute("UPDATE supplier SET name=?, contact=?, desc=? WHERE invoice=?", (
                        self.var_name.get(), self.var_contact.get(),
                        self.txt_desc.get('1.0', tk.END).strip(), self.var_sup_invoice.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Supplier Updated Successfully", parent=self.root)
                    self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def delete(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            if self.var_sup_invoice.get() == "":
                messagebox.showerror("Error", "Invoice No. Must be required", parent=self.root)
            else:
                cur.execute("SELECT * FROM supplier WHERE invoice=?", (self.var_sup_invoice.get(),))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror("Error", "Invalid Invoice No.", parent=self.root)
                else:
                    op = messagebox.askyesno("Confirm", "Do you really want to delete?", parent=self.root)
                    if op:
                        cur.execute("DELETE FROM supplier WHERE invoice=?", (self.var_sup_invoice.get(),))
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
        self.var_search_txt.set("")
        self.show()

    def search(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            if self.var_search_txt.get() == "":
                messagebox.showerror("Error", "Invoice No. should be required", parent=self.root)
            else:
                cur.execute("SELECT * FROM supplier WHERE invoice=?", (self.var_search_txt.get(),))
                row = cur.fetchone()
                if row is not None:
                    self.SupplierTable.delete(*self.SupplierTable.get_children())
                    self.SupplierTable.insert('', tk.END, values=row)
                else:
                    messagebox.showerror("Error", "No record found", parent=self.root)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

class CategoryClass:
    def __init__(self, root: tk.Toplevel) -> None:
        self.root = root
        self.root.geometry("1100x500+220+130")
        self.root.title("Category Management")
        self.root.focus_force()
        
        self.var_cat_id = tk.StringVar()
        self.var_name = tk.StringVar()
        
        title = tk.Label(self.root, text="Manage Product Category", font=("goudy old style", 30), bg="#184a45", fg="white", bd=3, relief=tk.RIDGE)
        title.pack(side=tk.TOP, fill=tk.X, padx=20, pady=20)
        
        tk.Label(self.root, text="Enter Category Name", font=("goudy old style", 30), bg="white").place(x=50, y=100)
        tk.Entry(self.root, textvariable=self.var_name, font=("goudy old style", 18), bg="lightyellow").place(x=50, y=170, width=300)
        
        tk.Button(self.root, text="Add", command=self.add, font=("goudy old style", 15), bg="#4caf50", fg="white", cursor="hand2").place(x=360, y=170, width=150, height=30)
        tk.Button(self.root, text="Delete", command=self.delete, font=("goudy old style", 15), bg="#f44336", fg="white", cursor="hand2").place(x=520, y=170, width=150, height=30)
        
        cat_frame = tk.Frame(self.root, bd=3, relief=tk.RIDGE)
        cat_frame.place(x=700, y=100, width=380, height=350)
        
        scrolly = tk.Scrollbar(cat_frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(cat_frame, orient=tk.HORIZONTAL)
        
        self.CategoryTable = ttk.Treeview(cat_frame, columns=("cid", "name"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.CategoryTable.xview)
        scrolly.config(command=self.CategoryTable.yview)
        
        self.CategoryTable.heading("cid", text="C ID")
        self.CategoryTable.heading("name", text="Name")
        self.CategoryTable["show"] = "headings"
        self.CategoryTable.pack(fill=tk.BOTH, expand=1)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)
        
        self.show()

    def add(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            if self.var_name.get() == "":
                messagebox.showerror("Error", "Category Name Must be required", parent=self.root)
            else:
                cur.execute("SELECT * FROM category WHERE name=?", (self.var_name.get(),))
                row = cur.fetchone()
                if row is not None:
                    messagebox.showerror("Error", "Category already present, try different", parent=self.root)
                else:
                    cur.execute("INSERT INTO category (name) VALUES(?)", (self.var_name.get(),))
                    con.commit()
                    messagebox.showinfo("Success", "Category Added Successfully", parent=self.root)
                    self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def show(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            cur.execute("SELECT * FROM category")
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
        if row:
            self.var_cat_id.set(row[0])
            self.var_name.set(row[1])

    def delete(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            if self.var_cat_id.get() == "":
                messagebox.showerror("Error", "Please select category from the list", parent=self.root)
            else:
                cur.execute("SELECT * FROM category WHERE cid=?", (self.var_cat_id.get(),))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror("Error", "Invalid Category", parent=self.root)
                else:
                    op = messagebox.askyesno("Confirm", "Do you really want to delete?", parent=self.root)
                    if op:
                        cur.execute("DELETE FROM category WHERE cid=?", (self.var_cat_id.get(),))
                        con.commit()
                        messagebox.showinfo("Delete", "Category Deleted Successfully", parent=self.root)
                        self.show()
                        self.var_cat_id.set("")
                        self.var_name.set("")
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

class ProductClass:
    def __init__(self, root: tk.Toplevel) -> None:
        self.root = root
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
        
        product_frame = tk.Frame(self.root, bd=2, relief=tk.RIDGE, bg="white")
        product_frame.place(x=10, y=10, width=450, height=480)
        
        tk.Label(product_frame, text="Manage Product Details", font=("goudy old style", 18), bg="#0f4d7d", fg="white").pack(side=tk.TOP, fill=tk.X)
        
        tk.Label(product_frame, text="Category", font=("goudy old style", 15), bg="white").place(x=30, y=60)
        tk.Label(product_frame, text="Supplier", font=("goudy old style", 15), bg="white").place(x=30, y=110)
        tk.Label(product_frame, text="Name", font=("goudy old style", 15), bg="white").place(x=30, y=160)
        tk.Label(product_frame, text="Price", font=("goudy old style", 15), bg="white").place(x=30, y=210)
        tk.Label(product_frame, text="Quantity", font=("goudy old style", 15), bg="white").place(x=30, y=260)
        tk.Label(product_frame, text="Status", font=("goudy old style", 15), bg="white").place(x=30, y=310)
        
        ttk.Combobox(product_frame, textvariable=self.var_cat, values=self.cat_list, state='readonly', justify=tk.CENTER, font=("goudy old style", 15)).place(x=150, y=60, width=200)
        ttk.Combobox(product_frame, textvariable=self.var_sup, values=self.sup_list, state='readonly', justify=tk.CENTER, font=("goudy old style", 15)).place(x=150, y=110, width=200)
        tk.Entry(product_frame, textvariable=self.var_name, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=160, width=200)
        tk.Entry(product_frame, textvariable=self.var_price, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=210, width=200)
        tk.Entry(product_frame, textvariable=self.var_qty, font=("goudy old style", 15), bg="lightyellow").place(x=150, y=260, width=200)
        ttk.Combobox(product_frame, textvariable=self.var_status, values=("Active", "Inactive"), state='readonly', justify=tk.CENTER, font=("goudy old style", 15)).place(x=150, y=310, width=200)
        
        tk.Button(product_frame, text="Save", command=self.add, font=("goudy old style", 15), bg="#2196f3", fg="white", cursor="hand2").place(x=10, y=400, width=100, height=40)
        tk.Button(product_frame, text="Update", command=self.update, font=("goudy old style", 15), bg="#4caf50", fg="white", cursor="hand2").place(x=120, y=400, width=100, height=40)
        tk.Button(product_frame, text="Delete", command=self.delete, font=("goudy old style", 15), bg="#f44336", fg="white", cursor="hand2").place(x=230, y=400, width=100, height=40)
        tk.Button(product_frame, text="Clear", command=self.clear, font=("goudy old style", 15), bg="#607d8b", fg="white", cursor="hand2").place(x=340, y=400, width=100, height=40)
        
        search_frame = tk.LabelFrame(self.root, text="Search Product", font=("goudy old style", 12, "bold"), bd=2, relief=tk.RIDGE, bg="white")
        search_frame.place(x=480, y=10, width=600, height=80)
        
        self.var_search_by = tk.StringVar()
        ttk.Combobox(search_frame, textvariable=self.var_search_by, values=("Select", "Category", "Supplier", "Name"), state='readonly', justify=tk.CENTER, font=("goudy old style", 15)).place(x=10, y=10, width=150)
        
        self.var_search_txt = tk.StringVar()
        tk.Entry(search_frame, textvariable=self.var_search_txt, font=("goudy old style", 15), bg="lightyellow").place(x=180, y=10, width=200)
        tk.Button(search_frame, text="Search", command=self.search, font=("goudy old style", 15), bg="#4caf50", fg="white", cursor="hand2").place(x=410, y=9, width=150, height=30)
        
        p_frame = tk.Frame(self.root, bd=3, relief=tk.RIDGE)
        p_frame.place(x=480, y=100, width=600, height=390)
        
        scrolly = tk.Scrollbar(p_frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(p_frame, orient=tk.HORIZONTAL)
        
        self.ProductTable = ttk.Treeview(p_frame, columns=("pid", "Category", "Supplier", "name", "price", "qty", "status"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.ProductTable.xview)
        scrolly.config(command=self.ProductTable.yview)
        
        self.ProductTable.heading("pid", text="P ID")
        self.ProductTable.heading("Category", text="Category")
        self.ProductTable.heading("Supplier", text="Supplier")
        self.ProductTable.heading("name", text="Name")
        self.ProductTable.heading("price", text="Price")
        self.ProductTable.heading("qty", text="Qty")
        self.ProductTable.heading("status", text="Status")
        self.ProductTable["show"] = "headings"
        self.ProductTable.pack(fill=tk.BOTH, expand=1)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)
        
        self.show()

    def fetch_cat_sup(self) -> None:
        self.cat_list.append("Empty")
        self.sup_list.append("Empty")
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            cur.execute("SELECT name FROM category")
            cat = cur.fetchall()
            if len(cat) > 0:
                self.cat_list.clear()
                for i in cat:
                    self.cat_list.append(i[0])
            cur.execute("SELECT name FROM supplier")
            sup = cur.fetchall()
            if len(sup) > 0:
                self.sup_list.clear()
                for i in sup:
                    self.sup_list.append(i[0])
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def add(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            if self.var_cat.get() == "Select" or self.var_cat.get() == "Empty" or self.var_sup.get() == "Select" or self.var_name.get() == "":
                messagebox.showerror("Error", "All fields are required", parent=self.root)
            else:
                cur.execute("SELECT * FROM product WHERE name=?", (self.var_name.get(),))
                row = cur.fetchone()
                if row is not None:
                    messagebox.showerror("Error", "Product already present, try different", parent=self.root)
                else:
                    cur.execute("INSERT INTO product (Category, Supplier, name, price, qty, status) VALUES(?,?,?,?,?,?)", (
                        self.var_cat.get(), self.var_sup.get(), self.var_name.get(),
                        self.var_price.get(), self.var_qty.get(), self.var_status.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Product Added Successfully", parent=self.root)
                    self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def show(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            cur.execute("SELECT * FROM product")
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
        if row:
            self.var_pid.set(row[0])
            self.var_cat.set(row[1])
            self.var_sup.set(row[2])
            self.var_name.set(row[3])
            self.var_price.set(row[4])
            self.var_qty.set(row[5])
            self.var_status.set(row[6])

    def update(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            if self.var_pid.get() == "":
                messagebox.showerror("Error", "Please select product from list", parent=self.root)
            else:
                cur.execute("SELECT * FROM product WHERE pid=?", (self.var_pid.get(),))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror("Error", "Invalid Product", parent=self.root)
                else:
                    cur.execute("UPDATE product SET Category=?, Supplier=?, name=?, price=?, qty=?, status=? WHERE pid=?", (
                        self.var_cat.get(), self.var_sup.get(), self.var_name.get(),
                        self.var_price.get(), self.var_qty.get(), self.var_status.get(), self.var_pid.get()
                    ))
                    con.commit()
                    messagebox.showinfo("Success", "Product Updated Successfully", parent=self.root)
                    self.show()
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def delete(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            if self.var_pid.get() == "":
                messagebox.showerror("Error", "Select product from list", parent=self.root)
            else:
                cur.execute("SELECT * FROM product WHERE pid=?", (self.var_pid.get(),))
                row = cur.fetchone()
                if row is None:
                    messagebox.showerror("Error", "Invalid Product", parent=self.root)
                else:
                    op = messagebox.askyesno("Confirm", "Do you really want to delete?", parent=self.root)
                    if op:
                        cur.execute("DELETE FROM product WHERE pid=?", (self.var_pid.get(),))
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
        self.var_search_txt.set("")
        self.var_search_by.set("Select")
        self.show()

    def search(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            if self.var_search_by.get() == "Select":
                messagebox.showerror("Error", "Select Search By option", parent=self.root)
            elif self.var_search_txt.get() == "":
                messagebox.showerror("Error", "Search input should be required", parent=self.root)
            else:
                cur.execute(f"SELECT * FROM product WHERE {self.var_search_by.get()} LIKE '%{self.var_search_txt.get()}%'")
                rows = cur.fetchall()
                if len(rows) != 0:
                    self.ProductTable.delete(*self.ProductTable.get_children())
                    for row in rows:
                        self.ProductTable.insert('', tk.END, values=row)
                else:
                    messagebox.showerror("Error", "No record found", parent=self.root)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

class BillingClass:
    def __init__(self, root: tk.Toplevel) -> None:
        self.root = root
        self.root.geometry("1350x700+0+0")
        self.root.title("Billing System")
        self.root.focus_force()
        
        self.cart_list: List[Tuple[str, str, str, str, str]] = []
        self.chk_print = 0
        
        title = tk.Label(self.root, text="Inventory Management System - Billing", font=("times new roman", 30, "bold"), bg="#010c48", fg="white", anchor="w", padx=20)
        title.place(x=0, y=0, relwidth=1, height=70)
        
        self.lbl_clock = tk.Label(self.root, text="Welcome to Inventory Management System\t\t Date: DD-MM-YYYY\t\t Time: HH:MM:SS", font=("times new roman", 15), bg="#4d636d", fg="white")
        self.lbl_clock.place(x=0, y=70, relwidth=1, height=30)
        
        ProductFrame1 = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        ProductFrame1.place(x=6, y=110, width=410, height=550)
        
        pTitle = tk.Label(ProductFrame1, text="All Products", font=("goudy old style", 20, "bold"), bg="#262626", fg="white")
        pTitle.pack(side=tk.TOP, fill=tk.X)
        
        ProductFrame2 = tk.Frame(ProductFrame1, bd=2, relief=tk.RIDGE, bg="white")
        ProductFrame2.place(x=2, y=42, width=398, height=90)
        
        tk.Label(ProductFrame2, text="Search Product | By Name", font=("times new roman", 15, "bold"), bg="white", fg="green").place(x=2, y=5)
        
        self.var_search = tk.StringVar()
        tk.Entry(ProductFrame2, textvariable=self.var_search, font=("times new roman", 15), bg="lightyellow").place(x=2, y=45, width=240, height=22)
        tk.Button(ProductFrame2, text="Search", command=self.search, font=("goudy old style", 15), bg="#2196f3", fg="white", cursor="hand2").place(x=245, y=45, width=70, height=22)
        tk.Button(ProductFrame2, text="Show All", command=self.show, font=("goudy old style", 15), bg="#083531", fg="white", cursor="hand2").place(x=318, y=45, width=75, height=22)
        
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
        self.product_Table.column("pid", width=40, justify=tk.CENTER)
        self.product_Table.column("name", width=100)
        self.product_Table.column("price", width=70)
        self.product_Table.column("qty", width=40, justify=tk.CENTER)
        self.product_Table.column("status", width=70)
        self.product_Table.pack(fill=tk.BOTH, expand=1)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)
        
        CustomerFrame = tk.Frame(self.root, bd=4, relief=tk.RIDGE, bg="white")
        CustomerFrame.place(x=420, y=110, width=530, height=70)
        
        cTitle = tk.Label(CustomerFrame, text="Customer Details", font=("goudy old style", 15), bg="lightgray")
        cTitle.pack(side=tk.TOP, fill=tk.X)
        
        self.var_cname = tk.StringVar()
        self.var_contact = tk.StringVar()
        
        tk.Label(CustomerFrame, text="Name", font=("times new roman", 15), bg="white").place(x=5, y=35)
        tk.Entry(CustomerFrame, textvariable=self.var_cname, font=("times new roman", 13), bg="lightyellow").place(x=60, y=35, width=180)
        
        tk.Label(CustomerFrame, text="Contact No.", font=("times new roman", 15), bg="white").place(x=250, y=35)
        tk.Entry(CustomerFrame, textvariable=self.var_contact, font=("times new roman", 13), bg="lightyellow").place(x=350, y=35, width=160)
        
        Cal_Cart_Frame = tk.Frame(self.root, bd=2, relief=tk.RIDGE, bg="white")
        Cal_Cart_Frame.place(x=420, y=190, width=530, height=360)
        
        cart_Frame = tk.Frame(Cal_Cart_Frame, bd=3, relief=tk.RIDGE)
        cart_Frame.place(x=5, y=8, width=515, height=342)
        
        self.cartTitle = tk.Label(cart_Frame, text="Cart \t Total Product: [0]", font=("goudy old style", 15), bg="lightgray")
        self.cartTitle.pack(side=tk.TOP, fill=tk.X)
        
        scrolly = tk.Scrollbar(cart_Frame, orient=tk.VERTICAL)
        scrollx = tk.Scrollbar(cart_Frame, orient=tk.HORIZONTAL)
        
        self.CartTable = ttk.Treeview(cart_Frame, columns=("pid", "name", "price", "qty", "status"), yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrollx.pack(side=tk.BOTTOM, fill=tk.X)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        scrollx.config(command=self.CartTable.xview)
        scrolly.config(command=self.CartTable.yview)
        
        self.CartTable.heading("pid", text="PID")
        self.CartTable.heading("name", text="Name")
        self.CartTable.heading("price", text="Price")
        self.CartTable.heading("qty", text="QTY")
        self.CartTable.heading("status", text="Status")
        self.CartTable["show"] = "headings"
        self.CartTable.column("pid", width=40, justify=tk.CENTER)
        self.CartTable.column("name", width=90)
        self.CartTable.column("price", width=90)
        self.CartTable.column("qty", width=40, justify=tk.CENTER)
        self.CartTable.column("status", width=90)
        self.CartTable.pack(fill=tk.BOTH, expand=1)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)
        
        Add_CartWidgetsFrame = tk.Frame(self.root, bd=2, relief=tk.RIDGE, bg="white")
        Add_CartWidgetsFrame.place(x=420, y=550, width=530, height=110)
        
        self.var_pid = tk.StringVar()
        self.var_pname = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_stock = tk.StringVar()
        
        tk.Label(Add_CartWidgetsFrame, text="Product Name", font=("times new roman", 15), bg="white").place(x=5, y=5)
        tk.Entry(Add_CartWidgetsFrame, textvariable=self.var_pname, font=("times new roman", 15), bg="lightyellow", state='readonly').place(x=5, y=35, width=190, height=22)
        
        tk.Label(Add_CartWidgetsFrame, text="Price", font=("times new roman", 15), bg="white").place(x=210, y=5)
        tk.Entry(Add_CartWidgetsFrame, textvariable=self.var_price, font=("times new roman", 15), bg="lightyellow", state='readonly').place(x=210, y=35, width=110, height=22)
        
        tk.Label(Add_CartWidgetsFrame, text="Quantity", font=("times new roman", 15), bg="white").place(x=340, y=5)
        tk.Entry(Add_CartWidgetsFrame, textvariable=self.var_qty, font=("times new roman", 15), bg="lightyellow").place(x=340, y=35, width=100, height=22)
        
        self.lbl_inStock = tk.Label(Add_CartWidgetsFrame, text="In Stock", font=("times new roman", 15), bg="white")
        self.lbl_inStock.place(x=5, y=70)
        
        tk.Button(Add_CartWidgetsFrame, text="Clear", command=self.clear_cart_widgets, font=("times new roman", 15, "bold"), bg="lightgray", cursor="hand2").place(x=180, y=70, width=150, height=30)
        tk.Button(Add_CartWidgetsFrame, text="Add | Update", command=self.add_update_cart, font=("times new roman", 15, "bold"), bg="orange", cursor="hand2").place(x=340, y=70, width=180, height=30)
        
        billFrame = tk.Frame(self.root, bd=2, relief=tk.RIDGE, bg="white")
        billFrame.place(x=953, y=110, width=390, height=410)
        
        bTitle = tk.Label(billFrame, text="Customer Bill Area", font=("goudy old style", 20, "bold"), bg="#f44336", fg="white")
        bTitle.pack(side=tk.TOP, fill=tk.X)
        
        scrolly = tk.Scrollbar(billFrame, orient=tk.VERTICAL)
        scrolly.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.txt_bill_area = tk.Text(billFrame, yscrollcommand=scrolly.set)
        self.txt_bill_area.pack(fill=tk.BOTH, expand=1)
        scrolly.config(command=self.txt_bill_area.yview)
        
        billMenuFrame = tk.Frame(self.root, bd=2, relief=tk.RIDGE, bg="white")
        billMenuFrame.place(x=953, y=520, width=390, height=140)
        
        self.lbl_amnt = tk.Label(billMenuFrame, text="Bill Amount\n[0]", font=("goudy old style", 15, "bold"), bg="#3f51b5", fg="white")
        self.lbl_amnt.place(x=2, y=5, width=120, height=70)
        
        self.lbl_discount = tk.Label(billMenuFrame, text="Discount\n[5%]", font=("goudy old style", 15, "bold"), bg="#8bc34a", fg="white")
        self.lbl_discount.place(x=124, y=5, width=120, height=70)
        
        self.lbl_net_pay = tk.Label(billMenuFrame, text="Net Pay\n[0]", font=("goudy old style", 15, "bold"), bg="#607d8b", fg="white")
        self.lbl_net_pay.place(x=246, y=5, width=135, height=70)
        
        tk.Button(billMenuFrame, text="Print", command=self.print_bill, font=("goudy old style", 15, "bold"), bg="lightgreen", cursor="hand2").place(x=2, y=80, width=120, height=50)
        tk.Button(billMenuFrame, text="Clear All", command=self.clear_all, font=("goudy old style", 15, "bold"), bg="gray", fg="white", cursor="hand2").place(x=124, y=80, width=120, height=50)
        tk.Button(billMenuFrame, text="Generate", command=self.generate_bill, font=("goudy old style", 15, "bold"), bg="#009688", fg="white", cursor="hand2").place(x=246, y=80, width=135, height=50)
        
        searchBillFrame = tk.Frame(self.root, bd=2, relief=tk.RIDGE, bg="white")
        searchBillFrame.place(x=953, y=70, width=390, height=40)
        
        self.var_invoice_search = tk.StringVar()
        tk.Label(searchBillFrame, text="Invoice No.", font=("times new roman", 12, "bold"), bg="white").place(x=5, y=5)
        tk.Entry(searchBillFrame, textvariable=self.var_invoice_search, font=("times new roman", 12), bg="lightyellow").place(x=100, y=5, width=150, height=25)
        tk.Button(searchBillFrame, text="Search", command=self.search_bill, font=("times new roman", 12, "bold"), bg="#2196f3", fg="white", cursor="hand2").place(x=260, y=5, width=100, height=25)
        
        self.show()
        self.update_date_time()

    def show(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            cur.execute("SELECT pid, name, price, qty, status FROM product WHERE status='Active'")
            rows = cur.fetchall()
            self.product_Table.delete(*self.product_Table.get_children())
            for row in rows:
                self.product_Table.insert('', tk.END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def search(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
            if self.var_search.get() == "":
                messagebox.showerror("Error", "Search input should be required", parent=self.root)
            else:
                cur.execute("SELECT pid, name, price, qty, status FROM product WHERE name LIKE '%" + self.var_search.get() + "%' and status='Active'")
                rows = cur.fetchall()
                if len(rows) != 0:
                    self.product_Table.delete(*self.product_Table.get_children())
                    for row in rows:
                        self.product_Table.insert('', tk.END, values=row)
                else:
                    messagebox.showerror("Error", "No record found", parent=self.root)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
        finally:
            con.close()

    def get_data(self, ev: Any) -> None:
        f = self.product_Table.focus()
        content = (self.product_Table.item(f))
        row = content['values']
        if row:
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
        if row:
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_qty.set(row[3])
            self.lbl_inStock.config(text=f"In Stock [{str(row[4])}]")
            self.var_stock.set(row[4])

    def add_update_cart(self) -> None:
        if self.var_pid.get() == "":
            messagebox.showerror("Error", "Please select product from the list", parent=self.root)
        elif self.var_qty.get() == "":
            messagebox.showerror("Error", "Quantity is required", parent=self.root)
        elif int(self.var_qty.get()) > int(self.var_stock.get()):
            messagebox.showerror("Error", "Invalid Quantity", parent=self.root)
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
                op = messagebox.askyesno("Confirm", "Product already present\nDo you want to Update | Remove from the Cart List?", parent=self.root)
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
        self.bill_amnt = 0
        self.net_pay = 0
        self.discount = 0
        for row in self.cart_list:
            self.bill_amnt = self.bill_amnt + (float(row[2]) * int(row[3]))
        
        self.discount = (self.bill_amnt * 5) / 100
        self.net_pay = self.bill_amnt - self.discount
        self.lbl_amnt.config(text=f"Bill Amount\n[{str(self.bill_amnt)}]")
        self.lbl_net_pay.config(text=f"Net Pay\n[{str(self.net_pay)}]")
        self.cartTitle.config(text=f"Cart \t Total Product: [{str(len(self.cart_list))}]")

    def show_cart(self) -> None:
        try:
            self.CartTable.delete(*self.CartTable.get_children())
            for row in self.cart_list:
                self.CartTable.insert('', tk.END, values=row)
        except Exception as ex:
            messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)

    def generate_bill(self) -> None:
        if self.var_cname.get() == "" or self.var_contact.get() == "":
            messagebox.showerror("Error", "Customer Details are required", parent=self.root)
        elif len(self.cart_list) == 0:
            messagebox.showerror("Error", "Please Add Product to the Cart", parent=self.root)
        else:
            self.bill_top()
            self.bill_middle()
            self.bill_bottom()
            
            con = sqlite3.connect(database='ims.db')
            cur = con.cursor()
            try:
                cur.execute("INSERT INTO bills (date, name, contact, total) VALUES(?,?,?,?)", (
                    datetime.now().strftime("%d-%m-%Y"), self.var_cname.get(), self.var_contact.get(), str(self.net_pay)
                ))
                con.commit()
                
                cur.execute("SELECT last_insert_rowid()")
                invoice_no = cur.fetchone()[0]
                
                fp = open(f'bills/{invoice_no}.txt', 'w')
                fp.write(self.txt_bill_area.get('1.0', tk.END))
                fp.close()
                
                for row in self.cart_list:
                    pid = row[0]
                    qty = int(row[4]) - int(row[3])
                    status = 'Active'
                    if qty == 0:
                        status = 'Inactive'
                    cur.execute("UPDATE product SET qty=?, status=? WHERE pid=?", (qty, status, pid))
                con.commit()
                
                messagebox.showinfo("Saved", f"Bill has been generated and saved with Invoice No: {invoice_no}", parent=self.root)
                self.chk_print = 1
                self.show()
            except Exception as ex:
                messagebox.showerror("Error", f"Error due to : {str(ex)}", parent=self.root)
            finally:
                con.close()

    def bill_top(self) -> None:
        self.txt_bill_area.delete('1.0', tk.END)
        self.txt_bill_area.insert(tk.END, "\t\tInventory Management System\n")
        self.txt_bill_area.insert(tk.END, "\t\tPhone No. 9876543210\n")
        self.txt_bill_area.insert(tk.END, "="*47 + "\n")
        self.txt_bill_area.insert(tk.END, f" Customer Name: {self.var_cname.get()}\n")
        self.txt_bill_area.insert(tk.END, f" Phone No.    : {self.var_contact.get()}\n")
        self.txt_bill_area.insert(tk.END, f" Date         : {datetime.now().strftime('%d-%m-%Y')}\n")
        self.txt_bill_area.insert(tk.END, "="*47 + "\n")
        self.txt_bill_area.insert(tk.END, " Product Name\t\t\tQTY\tPrice\n")
        self.txt_bill_area.insert(tk.END, "="*47 + "\n")

    def bill_middle(self) -> None:
        for row in self.cart_list:
            name = row[1]
            qty = row[3]
            price = str(float(row[2]) * int(row[3]))
            self.txt_bill_area.insert(tk.END, f" {name}\t\t\t{qty}\tRs.{price}\n")

    def bill_bottom(self) -> None:
        self.txt_bill_area.insert(tk.END, "="*47 + "\n")
        self.txt_bill_area.insert(tk.END, f" Bill Amount \t\t\t\tRs.{self.bill_amnt}\n")
        self.txt_bill_area.insert(tk.END, f" Discount \t\t\t\tRs.{self.discount}\n")
        self.txt_bill_area.insert(tk.END, f" Net Pay \t\t\t\tRs.{self.net_pay}\n")
        self.txt_bill_area.insert(tk.END, "="*47 + "\n")

    def clear_cart_widgets(self) -> None:
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.lbl_inStock.config(text="In Stock")
        self.var_stock.set("")

    def clear_all(self) -> None:
        self.chk_print = 0
        self.cart_list.clear()
        self.var_cname.set("")
        self.var_contact.set("")
        self.txt_bill_area.delete('1.0', tk.END)
        self.var_search.set("")
        self.clear_cart_widgets()
        self.show()
        self.show_cart()
        self.bill_updates()

    def update_date_time(self) -> None:
        time_ = datetime.now().strftime("%I:%M:%S")
        date_ = datetime.now().strftime("%d-%m-%Y")
        self.lbl_clock.config(text=f"Welcome to Inventory Management System\t\t Date: {date_}\t\t Time: {time_}")
        self.lbl_clock.after(200, self.update_date_time)

    def print_bill(self) -> None:
        if self.chk_print == 1:
            messagebox.showinfo("Print", "Please wait while printing", parent=self.root)
            new_file = tempfile.mktemp('.txt')
            open(new_file, 'w').write(self.txt_bill_area.get('1.0', tk.END))
            os.startfile(new_file, 'print')
        else:
            messagebox.showerror("Error", "Please generate bill, to print the receipt", parent=self.root)

    def search_bill(self) -> None:
        if self.var_invoice_search.get() == "":
            messagebox.showerror("Error", "Invoice No. should be required", parent=self.root)
        else:
            try:
                fp = open(f'bills/{self.var_invoice_search.get()}.txt', 'r')
                self.txt_bill_area.delete('1.0', tk.END)
                for i in fp:
                    self.txt_bill_area.insert(tk.END, i)
                fp.close()
            except Exception:
                messagebox.showerror("Error", "Invalid Invoice No.", parent=self.root)

class IMS:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.geometry("1350x700+0+0")
        self.root.title("Inventory Management System")
        
        self.icon_title = get_placeholder_image(50, 50, "blue")
        title = tk.Label(self.root, text="Inventory Management System", image=self.icon_title, compound=tk.LEFT, font=("times new roman", 40, "bold"), bg="#010c48", fg="white", anchor="w", padx=20)
        title.place(x=0, y=0, relwidth=1, height=70)
        
        btn_logout = tk.Button(self.root, text="Logout", command=self.root.destroy, font=("times new roman", 15, "bold"), bg="yellow", cursor="hand2")
        btn_logout.place(x=1150, y=10, height=50, width=150)
        
        self.lbl_clock = tk.Label(self.root, text="Welcome to Inventory Management System\t\t Date: DD-MM-YYYY\t\t Time: HH:MM:SS", font=("times new roman", 15), bg="#4d636d", fg="white")
        self.lbl_clock.place(x=0, y=70, relwidth=1, height=30)
        
        self.MenuLogo = get_placeholder_image(200, 200, "gray")
        LeftMenu = tk.Frame(self.root, bd=2, relief=tk.RIDGE, bg="white")
        LeftMenu.place(x=0, y=102, width=200, height=565)
        
        lbl_menuLogo = tk.Label(LeftMenu, image=self.MenuLogo)
        lbl_menuLogo.pack(side=tk.TOP, fill=tk.X)
        
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
        self.update_date_time()

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

    def update_content(self) -> None:
        con = sqlite3.connect(database='ims.db')
        cur = con.cursor()
        try:
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
            bill = cur.fetchall()
            self.lbl_sales.config(text=f"Total Sales\n[ {str(len(bill))} ]")
        except Exception as ex:
            pass
        finally:
            con.close()
        self.lbl_employee.after(2000, self.update_content)

    def update_date_time(self) -> None:
        time_ = datetime.now().strftime("%I:%M:%S")
        date_ = datetime.now().strftime("%d-%m-%Y")
        self.lbl_clock.config(text=f"Welcome to Inventory Management System\t\t Date: {date_}\t\t Time: {time_}")
        self.lbl_clock.after(200, self.update_date_time)

if __name__ == "__main__":
    setup_database()
    root = tk.Tk()
    obj = IMS(root)
    root.mainloop()