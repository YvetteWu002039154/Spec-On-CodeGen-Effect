from tkinter import *
from tkinter import ttk
from tkinter import messagebox
from datetime import datetime
import sqlite3
import random
import time
import os

conn = sqlite3.connect("ims.db")
c = conn.cursor()

def create_tables():
    c.execute('''CREATE TABLE IF NOT EXISTS category
                 (cat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS supplier
                 (sup_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sup_invoice TEXT,
                  name TEXT,
                  contact TEXT,
                  description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS employee
                 (emp_id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  email TEXT,
                  contact TEXT,
                  dob TEXT,
                  doj TEXT,
                  gender TEXT,
                  password TEXT,
                  utype TEXT,
                  address TEXT,
                  salary REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS product
                 (pid INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  category_id INTEGER,
                  supplier_id INTEGER,
                  price REAL,
                  quantity INTEGER,
                  status TEXT,
                  FOREIGN KEY(category_id) REFERENCES category(cat_id),
                  FOREIGN KEY(supplier_id) REFERENCES supplier(sup_id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  invoice_no TEXT,
                  date TEXT,
                  total_amount REAL)''')
    conn.commit()

create_tables()

class categoryClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Category Management")
        self.root.geometry("1100x500+220+130")
        self.root.resizable(False, False)
        self.var_cat_id = StringVar()
        self.var_name = StringVar()
        self.im1 = None
        self.im2 = None
        try:
            self.im1 = PhotoImage(file="images/im1.png")
            self.im2 = PhotoImage(file="images/im2.png")
        except:
            pass
        self.lbl_im1 = Label(self.root, image=self.im1)
        self.lbl_im1.place(x=50, y=10, width=45, height=45)
        self.lbl_im2 = Label(self.root, image=self.im2)
        self.lbl_im2.place(x=500, y=10, width=45, height=45)
        lbl_title = Label(self.root, text="Manage Category", font=("times new roman", 30, "bold"), bg="#0f4d6c", fg="white")
        lbl_title.pack(side=TOP, fill=X)
        frame1 = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        frame1.place(x=20, y=70, width=450, height=250)
        Label(frame1, text="Category Id", font=("times new roman", 15, "bold"), bg="white").place(x=30, y=20)
        Label(frame1, text="Name", font=("times new roman", 15, "bold"), bg="white").place(x=30, y=70)
        txt_cat_id = Entry(frame1, textvariable=self.var_cat_id, font=("times new roman", 15), state='readonly', bg="lightgray")
        txt_cat_id.place(x=30, y=50, width=200)
        txt_name = Entry(frame1, textvariable=self.var_name, font=("times new roman", 15), bg="lightgray")
        txt_name.place(x=30, y=100, width=200)
        btn_frame = Frame(frame1, bd=2, relief=RIDGE, bg="white")
        btn_frame.place(x=30, y=170, width=390)
        Button(btn_frame, text="Add", command=self.add, font=("times new roman", 15), bg="#2196f3", fg="white", cursor="hand2").pack(side=LEFT, padx=5, pady=5)
        Button(btn_frame, text="Delete", command=self.delete, font=("times new roman", 15), bg="#f44336", fg="white", cursor="hand2").pack(side=LEFT, padx=5, pady=5)
        Button(btn_frame, text="Clear", command=self.clear, font=("times new roman", 15), bg="#607d8b", fg="white", cursor="hand2").pack(side=LEFT, padx=5, pady=5)
        frame2 = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        frame2.place(x=500, y=70, width=550, height=400)
        scroll_y = Scrollbar(frame2, orient=VERTICAL)
        scroll_x = Scrollbar(frame2, orient=HORIZONTAL)
        self.CategoryTable = ttk.Treeview(frame2, columns=("cid", "name"), yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.config(command=self.CategoryTable.yview)
        scroll_x.config(command=self.CategoryTable.xview)
        self.CategoryTable.heading("cid", text="Category ID")
        self.CategoryTable.heading("name", text="Name")
        self.CategoryTable["show"] = "headings"
        self.CategoryTable.column("cid", width=100)
        self.CategoryTable.column("name", width=100)
        self.CategoryTable.pack(fill=BOTH, expand=1)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def add(self):
        if self.var_name.get() == "":
            messagebox.showerror("Error", "Category name required", parent=self.root)
            return
        try:
            c.execute("INSERT INTO category (name) VALUES (?)", (self.var_name.get(),))
            conn.commit()
            self.show()
            self.clear()
            messagebox.showinfo("Success", "Category added", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Error due to: {str(e)}", parent=self.root)

    def delete(self):
        if self.var_cat_id.get() == "":
            messagebox.showerror("Error", "Select category from list", parent=self.root)
            return
        confirm = messagebox.askyesno("Confirm", "Delete this category?", parent=self.root)
        if confirm:
            try:
                c.execute("DELETE FROM category WHERE cat_id=?", (self.var_cat_id.get(),))
                conn.commit()
                self.show()
                self.clear()
                messagebox.showinfo("Success", "Category deleted", parent=self.root)
            except Exception as e:
                messagebox.showerror("Error", f"Error due to: {str(e)}", parent=self.root)

    def clear(self):
        self.var_cat_id.set("")
        self.var_name.set("")

    def get_data(self, ev):
        f = self.CategoryTable.focus()
        content = self.CategoryTable.item(f)
        row = content['values']
        if row:
            self.var_cat_id.set(row[0])
            self.var_name.set(row[1])

    def show(self):
        self.CategoryTable.delete(*self.CategoryTable.get_children())
        c.execute("SELECT * FROM category")
        rows = c.fetchall()
        for row in rows:
            self.CategoryTable.insert("", END, values=row)

class supplierClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Supplier Management")
        self.root.geometry("1100x500+220+130")
        self.root.resizable(False, False)
        self.var_sup_invoice = StringVar()
        self.var_name = StringVar()
        self.var_contact = StringVar()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()
        self.txt_desc = Text(self.root, font=("times new roman", 15), bg="lightgray")
        lbl_title = Label(self.root, text="Manage Supplier", font=("times new roman", 30, "bold"), bg="#0f4d6c", fg="white")
        lbl_title.pack(side=TOP, fill=X)
        frame1 = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        frame1.place(x=20, y=70, width=450, height=300)
        Label(frame1, text="Invoice No.", font=("times new roman", 15, "bold"), bg="white").place(x=30, y=20)
        Label(frame1, text="Name", font=("times new roman", 15, "bold"), bg="white").place(x=30, y=70)
        Label(frame1, text="Contact", font=("times new roman", 15, "bold"), bg="white").place(x=30, y=120)
        Label(frame1, text="Description", font=("times new roman", 15, "bold"), bg="white").place(x=30, y=170)
        txt_inv = Entry(frame1, textvariable=self.var_sup_invoice, font=("times new roman", 15), bg="lightgray")
        txt_inv.place(x=30, y=50, width=200)
        txt_name = Entry(frame1, textvariable=self.var_name, font=("times new roman", 15), bg="lightgray")
        txt_name.place(x=30, y=100, width=200)
        txt_contact = Entry(frame1, textvariable=self.var_contact, font=("times new roman", 15), bg="lightgray")
        txt_contact.place(x=30, y=150, width=200)
        self.txt_desc.place(x=30, y=200, width=200, height=50)
        btn_frame = Frame(frame1, bd=2, relief=RIDGE, bg="white")
        btn_frame.place(x=30, y=270, width=390)
        Button(btn_frame, text="Add", command=self.add, font=("times new roman", 15), bg="#2196f3", fg="white", cursor="hand2").pack(side=LEFT, padx=5, pady=5)
        Button(btn_frame, text="Update", command=self.update, font=("times new roman", 15), bg="#4caf50", fg="white", cursor="hand2").pack(side=LEFT, padx=5, pady=5)
        Button(btn_frame, text="Delete", command=self.delete, font=("times new roman", 15), bg="#f44336", fg="white", cursor="hand2").pack(side=LEFT, padx=5, pady=5)
        Button(btn_frame, text="Clear", command=self.clear, font=("times new roman", 15), bg="#607d8b", fg="white", cursor="hand2").pack(side=LEFT, padx=5, pady=5)
        search_frame = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        search_frame.place(x=500, y=70, width=550, height=50)
        cmb_search = ttk.Combobox(search_frame, textvariable=self.var_searchby, font=("times new roman", 13), state='readonly', values=("invoice", "name", "contact"))
        cmb_search.place(x=10, y=10, width=150)
        cmb_search.current(0)
        txt_search = Entry(search_frame, textvariable=self.var_searchtxt, font=("times new roman", 15), bg="lightgray")
        txt_search.place(x=170, y=10, width=150)
        Button(search_frame, text="Search", command=self.search, font=("times new roman", 15), bg="#2196f3", fg="white", cursor="hand2").place(x=330, y=10, width=100)
        Button(search_frame, text="Show All", command=self.show, font=("times new roman", 15), bg="#4caf50", fg="white", cursor="hand2").place(x=440, y=10, width=100)
        frame2 = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        frame2.place(x=500, y=130, width=550, height=340)
        scroll_y = Scrollbar(frame2, orient=VERTICAL)
        scroll_x = Scrollbar(frame2, orient=HORIZONTAL)
        self.SupplierTable = ttk.Treeview(frame2, columns=("sup_id", "invoice", "name", "contact", "description"), yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.config(command=self.SupplierTable.yview)
        scroll_x.config(command=self.SupplierTable.xview)
        self.SupplierTable.heading("sup_id", text="Sup ID")
        self.SupplierTable.heading("invoice", text="Invoice")
        self.SupplierTable.heading("name", text="Name")
        self.SupplierTable.heading("contact", text="Contact")
        self.SupplierTable.heading("description", text="Description")
        self.SupplierTable["show"] = "headings"
        self.SupplierTable.column("sup_id", width=60)
        self.SupplierTable.column("invoice", width=100)
        self.SupplierTable.column("name", width=100)
        self.SupplierTable.column("contact", width=100)
        self.SupplierTable.column("description", width=150)
        self.SupplierTable.pack(fill=BOTH, expand=1)
        self.SupplierTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def add(self):
        if self.var_name.get() == "" or self.var_contact.get() == "":
            messagebox.showerror("Error", "All fields required", parent=self.root)
            return
        try:
            c.execute("INSERT INTO supplier (sup_invoice, name, contact, description) VALUES (?,?,?,?)",
                      (self.var_sup_invoice.get(), self.var_name.get(), self.var_contact.get(), self.txt_desc.get("1.0", END)))
            conn.commit()
            self.show()
            self.clear()
            messagebox.showinfo("Success", "Supplier added", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Error due to: {str(e)}", parent=self.root)

    def update(self):
        if not self.var_sup_invoice.get():
            messagebox.showerror("Error", "Select supplier from list", parent=self.root)
            return
        try:
            c.execute("UPDATE supplier SET name=?, contact=?, description=? WHERE sup_invoice=?",
                      (self.var_name.get(), self.var_contact.get(), self.txt_desc.get("1.0", END), self.var_sup_invoice.get()))
            conn.commit()
            self.show()
            self.clear()
            messagebox.showinfo("Success", "Supplier updated", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Error due to: {str(e)}", parent=self.root)

    def delete(self):
        if not self.var_sup_invoice.get():
            messagebox.showerror("Error", "Select supplier from list", parent=self.root)
            return
        confirm = messagebox.askyesno("Confirm", "Delete this supplier?", parent=self.root)
        if confirm:
            try:
                c.execute("DELETE FROM supplier WHERE sup_invoice=?", (self.var_sup_invoice.get(),))
                conn.commit()
                self.show()
                self.clear()
                messagebox.showinfo("Success", "Supplier deleted", parent=self.root)
            except Exception as e:
                messagebox.showerror("Error", f"Error due to: {str(e)}", parent=self.root)

    def clear(self):
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete("1.0", END)

    def get_data(self, ev):
        f = self.SupplierTable.focus()
        content = self.SupplierTable.item(f)
        row = content['values']
        if row:
            self.var_sup_invoice.set(row[1])
            self.var_name.set(row[2])
            self.var_contact.set(row[3])
            self.txt_desc.delete("1.0", END)
            self.txt_desc.insert(END, row[4])

    def search(self):
        criteria = self.var_searchby.get()
        txt = self.var_searchtxt.get()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        try:
            if criteria == "invoice":
                c.execute("SELECT * FROM supplier WHERE sup_invoice LIKE ?", ('%'+txt+'%',))
            elif criteria == "name":
                c.execute("SELECT * FROM supplier WHERE name LIKE ?", ('%'+txt+'%',))
            elif criteria == "contact":
                c.execute("SELECT * FROM supplier WHERE contact LIKE ?", ('%'+txt+'%',))
            rows = c.fetchall()
            for row in rows:
                self.SupplierTable.insert("", END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def show(self):
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        try:
            c.execute("SELECT * FROM supplier")
            rows = c.fetchall()
            for row in rows:
                self.SupplierTable.insert("", END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

class employeeClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Employee Management")
        self.root.geometry("1350x700+0+0")
        self.var_emp_id = StringVar()
        self.var_name = StringVar()
        self.var_email = StringVar()
        self.var_contact = StringVar()
        self.var_dob = StringVar()
        self.var_doj = StringVar()
        self.var_gender = StringVar()
        self.var_pass = StringVar()
        self.var_utype = StringVar()
        self.var_salary = StringVar()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()
        self.txt_address = Text(self.root, font=("times new roman", 15), bg="lightgray")
        lbl_title = Label(self.root, text="Manage Employees", font=("times new roman", 30, "bold"), bg="#0f4d6c", fg="white")
        lbl_title.pack(side=TOP, fill=X)
        frame1 = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        frame1.place(x=10, y=70, width=400, height=550)
        fields = [("Emp ID", self.var_emp_id), ("Name", self.var_name), ("Email", self.var_email), ("Contact", self.var_contact),
                  ("DOB", self.var_dob), ("DOJ", self.var_doj), ("Gender", self.var_gender), ("User Type", self.var_utype),
                  ("Password", self.var_pass), ("Salary", self.var_salary)]
        y_pos = 20
        for text, var in fields:
            Label(frame1, text=text, font=("times new roman", 15, "bold"), bg="white").place(x=30, y=y_pos)
            ent = Entry(frame1, textvariable=var, font=("times new roman", 15), bg="lightgray")
            ent.place(x=150, y=y_pos, width=200)
            y_pos += 40
        Label(frame1, text="Address", font=("times new roman", 15, "bold"), bg="white").place(x=30, y=y_pos)
        self.txt_address.place(x=150, y=y_pos, width=200, height=50)
        y_pos += 70
        btn_frame = Frame(frame1, bd=2, relief=RIDGE, bg="white")
        btn_frame.place(x=30, y=y_pos, width=350)
        Button(btn_frame, text="Add", command=self.add, font=("times new roman", 15), bg="#2196f3", fg="white", cursor="hand2").pack(side=LEFT, padx=5, pady=5)
        Button(btn_frame, text="Update", command=self.update, font=("times new roman", 15), bg="#4caf50", fg="white", cursor="hand2").pack(side=LEFT, padx=5, pady=5)
        Button(btn_frame, text="Delete", command=self.delete, font=("times new roman", 15), bg="#f44336", fg="white", cursor="hand2").pack(side=LEFT, padx=5, pady=5)
        Button(btn_frame, text="Clear", command=self.clear, font=("times new roman", 15), bg="#607d8b", fg="white", cursor="hand2").pack(side=LEFT, padx=5, pady=5)
        search_frame = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        search_frame.place(x=430, y=70, width=900, height=50)
        cmb_search = ttk.Combobox(search_frame, textvariable=self.var_searchby, font=("times new roman", 13), state='readonly', values=("Emp ID", "Name", "Email", "Contact"))
        cmb_search.place(x=10, y=10, width=150)
        cmb_search.current(1)
        txt_search = Entry(search_frame, textvariable=self.var_searchtxt, font=("times new roman", 15), bg="lightgray")
        txt_search.place(x=170, y=10, width=200)
        Button(search_frame, text="Search", command=self.search, font=("times new roman", 15), bg="#2196f3", fg="white", cursor="hand2").place(x=380, y=10, width=100)
        Button(search_frame, text="Show All", command=self.show, font=("times new roman", 15), bg="#4caf50", fg="white", cursor="hand2").place(x=490, y=10, width=100)
        frame2 = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        frame2.place(x=430, y=130, width=900, height=490)
        scroll_y = Scrollbar(frame2, orient=VERTICAL)
        scroll_x = Scrollbar(frame2, orient=HORIZONTAL)
        self.EmployeeTable = ttk.Treeview(frame2, columns=("eid", "name", "email", "contact", "dob", "doj", "gender", "utype", "pass", "address", "salary"),
                                          yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.config(command=self.EmployeeTable.yview)
        scroll_x.config(command=self.EmployeeTable.xview)
        self.EmployeeTable.heading("eid", text="Emp ID")
        self.EmployeeTable.heading("name", text="Name")
        self.EmployeeTable.heading("email", text="Email")
        self.EmployeeTable.heading("contact", text="Contact")
        self.EmployeeTable.heading("dob", text="DOB")
        self.EmployeeTable.heading("doj", text="DOJ")
        self.EmployeeTable.heading("gender", text="Gender")
        self.EmployeeTable.heading("utype", text="User Type")
        self.EmployeeTable.heading("pass", text="Password")
        self.EmployeeTable.heading("address", text="Address")
        self.EmployeeTable.heading("salary", text="Salary")
        self.EmployeeTable["show"] = "headings"
        cols = [("eid", 70), ("name", 100), ("email", 120), ("contact", 100), ("dob", 80), ("doj", 80), ("gender", 60),
                ("utype", 80), ("pass", 80), ("address", 120), ("salary", 80)]
        for col, w in cols:
            self.EmployeeTable.column(col, width=w)
        self.EmployeeTable.pack(fill=BOTH, expand=1)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def add(self):
        if self.var_name.get() == "":
            messagebox.showerror("Error", "Name required", parent=self.root)
            return
        try:
            c.execute("INSERT INTO employee (name, email, contact, dob, doj, gender, password, utype, address, salary) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (self.var_name.get(), self.var_email.get(), self.var_contact.get(), self.var_dob.get(), self.var_doj.get(),
                       self.var_gender.get(), self.var_pass.get(), self.var_utype.get(), self.txt_address.get("1.0", END), self.var_salary.get()))
            conn.commit()
            self.show()
            self.clear()
            messagebox.showinfo("Success", "Employee added", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def update(self):
        if not self.var_emp_id.get():
            messagebox.showerror("Error", "Select employee from list", parent=self.root)
            return
        try:
            c.execute("UPDATE employee SET name=?, email=?, contact=?, dob=?, doj=?, gender=?, password=?, utype=?, address=?, salary=? WHERE emp_id=?",
                      (self.var_name.get(), self.var_email.get(), self.var_contact.get(), self.var_dob.get(), self.var_doj.get(),
                       self.var_gender.get(), self.var_pass.get(), self.var_utype.get(), self.txt_address.get("1.0", END),
                       self.var_salary.get(), self.var_emp_id.get()))
            conn.commit()
            self.show()
            self.clear()
            messagebox.showinfo("Success", "Employee updated", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def delete(self):
        if not self.var_emp_id.get():
            messagebox.showerror("Error", "Select employee from list", parent=self.root)
            return
        confirm = messagebox.askyesno("Confirm", "Delete this employee?", parent=self.root)
        if confirm:
            try:
                c.execute("DELETE FROM employee WHERE emp_id=?", (self.var_emp_id.get(),))
                conn.commit()
                self.show()
                self.clear()
                messagebox.showinfo("Success", "Employee deleted", parent=self.root)
            except Exception as e:
                messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def clear(self):
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_email.set("")
        self.var_contact.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_gender.set("")
        self.var_pass.set("")
        self.var_utype.set("")
        self.var_salary.set("")
        self.txt_address.delete("1.0", END)

    def get_data(self, ev):
        f = self.EmployeeTable.focus()
        content = self.EmployeeTable.item(f)
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
            self.var_pass.set(row[8])
            self.txt_address.delete("1.0", END)
            self.txt_address.insert(END, row[9])
            self.var_salary.set(row[10])

    def search(self):
        col_map = {"Emp ID": "emp_id", "Name": "name", "Email": "email", "Contact": "contact"}
        field = col_map.get(self.var_searchby.get(), "name")
        txt = self.var_searchtxt.get()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        try:
            c.execute(f"SELECT * FROM employee WHERE {field} LIKE ?", ('%'+txt+'%',))
            rows = c.fetchall()
            for row in rows:
                self.EmployeeTable.insert("", END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def show(self):
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        try:
            c.execute("SELECT * FROM employee")
            rows = c.fetchall()
            for row in rows:
                self.EmployeeTable.insert("", END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

class productClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Product Management")
        self.root.geometry("1350x700+0+0")
        self.var_pid = StringVar()
        self.var_name = StringVar()
        self.var_price = StringVar()
        self.var_qty = StringVar()
        self.var_status = StringVar()
        self.var_cat = StringVar()
        self.var_sup = StringVar()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()
        self.cat_list = []
        self.sup_list = []
        lbl_title = Label(self.root, text="Manage Products", font=("times new roman", 30, "bold"), bg="#0f4d6c", fg="white")
        lbl_title.pack(side=TOP, fill=X)
        frame1 = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        frame1.place(x=10, y=70, width=400, height=550)
        fields = [("PID", self.var_pid), ("Name", self.var_name), ("Price", self.var_price), ("Quantity", self.var_qty),
                  ("Status", self.var_status)]
        y_pos = 20
        for text, var in fields:
            Label(frame1, text=text, font=("times new roman", 15, "bold"), bg="white").place(x=30, y=y_pos)
            ent = Entry(frame1, textvariable=var, font=("times new roman", 15), bg="lightgray")
            ent.place(x=150, y=y_pos, width=200)
            y_pos += 40
        Label(frame1, text="Category", font=("times new roman", 15, "bold"), bg="white").place(x=30, y=y_pos)
        cmb_cat = ttk.Combobox(frame1, textvariable=self.var_cat, font=("times new roman", 15), state='readonly', values=self.cat_list)
        cmb_cat.place(x=150, y=y_pos, width=200)
        y_pos += 40
        Label(frame1, text="Supplier", font=("times new roman", 15, "bold"), bg="white").place(x=30, y=y_pos)
        cmb_sup = ttk.Combobox(frame1, textvariable=self.var_sup, font=("times new roman", 15), state='readonly', values=self.sup_list)
        cmb_sup.place(x=150, y=y_pos, width=200)
        y_pos += 50
        btn_frame = Frame(frame1, bd=2, relief=RIDGE, bg="white")
        btn_frame.place(x=30, y=y_pos, width=350)
        Button(btn_frame, text="Add", command=self.add, font=("times new roman", 15), bg="#2196f3", fg="white", cursor="hand2").pack(side=LEFT, padx=5, pady=5)
        Button(btn_frame, text="Update", command=self.update, font=("times new roman", 15), bg="#4caf50", fg="white", cursor="hand2").pack(side=LEFT, padx=5, pady=5)
        Button(btn_frame, text="Delete", command=self.delete, font=("times new roman", 15), bg="#f44336", fg="white", cursor="hand2").pack(side=LEFT, padx=5, pady=5)
        Button(btn_frame, text="Clear", command=self.clear, font=("times new roman", 15), bg="#607d8b", fg="white", cursor="hand2").pack(side=LEFT, padx=5, pady=5)
        search_frame = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        search_frame.place(x=430, y=70, width=900, height=50)
        cmb_search = ttk.Combobox(search_frame, textvariable=self.var_searchby, font=("times new roman", 13), state='readonly', values=("PID", "Name", "Category", "Supplier"))
        cmb_search.place(x=10, y=10, width=150)
        cmb_search.current(1)
        txt_search = Entry(search_frame, textvariable=self.var_searchtxt, font=("times new roman", 15), bg="lightgray")
        txt_search.place(x=170, y=10, width=200)
        Button(search_frame, text="Search", command=self.search, font=("times new roman", 15), bg="#2196f3", fg="white", cursor="hand2").place(x=380, y=10, width=100)
        Button(search_frame, text="Show All", command=self.show, font=("times new roman", 15), bg="#4caf50", fg="white", cursor="hand2").place(x=490, y=10, width=100)
        frame2 = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        frame2.place(x=430, y=130, width=900, height=490)
        scroll_y = Scrollbar(frame2, orient=VERTICAL)
        scroll_x = Scrollbar(frame2, orient=HORIZONTAL)
        self.ProductTable = ttk.Treeview(frame2, columns=("pid", "name", "category", "supplier", "price", "qty", "status"),
                                         yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.config(command=self.ProductTable.yview)
        scroll_x.config(command=self.ProductTable.xview)
        self.ProductTable.heading("pid", text="PID")
        self.ProductTable.heading("name", text="Name")
        self.ProductTable.heading("category", text="Category")
        self.ProductTable.heading("supplier", text="Supplier")
        self.ProductTable.heading("price", text="Price")
        self.ProductTable.heading("qty", text="Qty")
        self.ProductTable.heading("status", text="Status")
        self.ProductTable["show"] = "headings"
        cols = [("pid", 60), ("name", 120), ("category", 100), ("supplier", 100), ("price", 80), ("qty", 80), ("status", 80)]
        for col, w in cols:
            self.ProductTable.column(col, width=w)
        self.ProductTable.pack(fill=BOTH, expand=1)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)
        self.fetch_cat_sup()
        self.show()

    def fetch_cat_sup(self):
        try:
            c.execute("SELECT name FROM category")
            self.cat_list = [row[0] for row in c.fetchall()]
            c.execute("SELECT name FROM supplier")
            self.sup_list = [row[0] for row in c.fetchall()]
            # Update comboboxes if they exist (they are created after __init__, but we can't easily update. We'll assume they are created with proper lists.)
        except:
            pass

    def add(self):
        if self.var_name.get() == "" or self.var_price.get() == "":
            messagebox.showerror("Error", "Required fields missing", parent=self.root)
            return
        # Get category id and supplier id from names
        cat_id = None
        sup_id = None
        try:
            c.execute("SELECT cat_id FROM category WHERE name=?", (self.var_cat.get(),))
            row = c.fetchone()
            if row: cat_id = row[0]
            c.execute("SELECT sup_id FROM supplier WHERE name=?", (self.var_sup.get(),))
            row = c.fetchone()
            if row: sup_id = row[0]
        except:
            pass
        try:
            c.execute("INSERT INTO product (name, category_id, supplier_id, price, quantity, status) VALUES (?,?,?,?,?,?)",
                      (self.var_name.get(), cat_id, sup_id, float(self.var_price.get()), int(self.var_qty.get()), self.var_status.get()))
            conn.commit()
            self.show()
            self.clear()
            messagebox.showinfo("Success", "Product added", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def update(self):
        if not self.var_pid.get():
            messagebox.showerror("Error", "Select product from list", parent=self.root)
            return
        cat_id = None
        sup_id = None
        try:
            c.execute("SELECT cat_id FROM category WHERE name=?", (self.var_cat.get(),))
            row = c.fetchone()
            if row: cat_id = row[0]
            c.execute("SELECT sup_id FROM supplier WHERE name=?", (self.var_sup.get(),))
            row = c.fetchone()
            if row: sup_id = row[0]
        except:
            pass
        try:
            c.execute("UPDATE product SET name=?, category_id=?, supplier_id=?, price=?, quantity=?, status=? WHERE pid=?",
                      (self.var_name.get(), cat_id, sup_id, float(self.var_price.get()), int(self.var_qty.get()),
                       self.var_status.get(), self.var_pid.get()))
            conn.commit()
            self.show()
            self.clear()
            messagebox.showinfo("Success", "Product updated", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def delete(self):
        if not self.var_pid.get():
            messagebox.showerror("Error", "Select product from list", parent=self.root)
            return
        confirm = messagebox.askyesno("Confirm", "Delete this product?", parent=self.root)
        if confirm:
            try:
                c.execute("DELETE FROM product WHERE pid=?", (self.var_pid.get(),))
                conn.commit()
                self.show()
                self.clear()
                messagebox.showinfo("Success", "Product deleted", parent=self.root)
            except Exception as e:
                messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def clear(self):
        self.var_pid.set("")
        self.var_name.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("")
        self.var_cat.set("")
        self.var_sup.set("")

    def get_data(self, ev):
        f = self.ProductTable.focus()
        content = self.ProductTable.item(f)
        row = content['values']
        if row:
            self.var_pid.set(row[0])
            self.var_name.set(row[1])
            self.var_cat.set(row[2])
            self.var_sup.set(row[3])
            self.var_price.set(row[4])
            self.var_qty.set(row[5])
            self.var_status.set(row[6])

    def search(self):
        col_map = {"PID": "pid", "Name": "p.name", "Category": "c.name", "Supplier": "s.name"}
        field = col_map.get(self.var_searchby.get(), "p.name")
        txt = self.var_searchtxt.get()
        self.ProductTable.delete(*self.ProductTable.get_children())
        query = f"""SELECT p.pid, p.name, c.name, s.name, p.price, p.quantity, p.status
                    FROM product p
                    LEFT JOIN category c ON p.category_id = c.cat_id
                    LEFT JOIN supplier s ON p.supplier_id = s.sup_id
                    WHERE {field} LIKE ?"""
        try:
            c.execute(query, ('%'+txt+'%',))
            rows = c.fetchall()
            for row in rows:
                self.ProductTable.insert("", END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def show(self):
        self.ProductTable.delete(*self.ProductTable.get_children())
        try:
            c.execute("""SELECT p.pid, p.name, c.name, s.name, p.price, p.quantity, p.status
                         FROM product p
                         LEFT JOIN category c ON p.category_id = c.cat_id
                         LEFT JOIN supplier s ON p.supplier_id = s.sup_id""")
            rows = c.fetchall()
            for row in rows:
                self.ProductTable.insert("", END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

class salesClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Sales Records")
        self.root.geometry("1000x600+250+80")
        self.var_invoice = StringVar()
        self.bill_photo = None
        self.blll_list = []  # blll_list
        lbl_title = Label(self.root, text="Sales Records", font=("times new roman", 30, "bold"), bg="#0f4d6c", fg="white")
        lbl_title.pack(side=TOP, fill=X)
        search_frame = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        search_frame.place(x=20, y=70, width=960, height=50)
        Label(search_frame, text="Invoice No", font=("times new roman", 15, "bold"), bg="white").pack(side=LEFT, padx=10)
        txt_inv = Entry(search_frame, textvariable=self.var_invoice, font=("times new roman", 15), bg="lightgray")
        txt_inv.pack(side=LEFT, padx=10)
        Button(search_frame, text="Search", command=self.search, font=("times new roman", 15), bg="#2196f3", fg="white", cursor="hand2").pack(side=LEFT, padx=10)
        Button(search_frame, text="Show All", command=self.show, font=("times new roman", 15), bg="#4caf50", fg="white", cursor="hand2").pack(side=LEFT, padx=10)
        self.bill_area = Text(self.root, font=("times new roman", 12), bg="white")
        self.bill_area.place(x=20, y=130, width=450, height=400)
        frame_list = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        frame_list.place(x=500, y=130, width=480, height=400)
        scroll_y = Scrollbar(frame_list, orient=VERTICAL)
        self.Sales_List = Listbox(frame_list, yscrollcommand=scroll_y.set, font=("times new roman", 12))
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_y.config(command=self.Sales_List.yview)
        self.Sales_List.pack(fill=BOTH, expand=1)
        self.Sales_List.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def clear(self):
        self.bill_area.delete("1.0", END)
        self.var_invoice.set("")

    def get_data(self, ev):
        index = self.Sales_List.curselection()
        if index:
            inv = self.Sales_List.get(index[0])
            self.var_invoice.set(inv)
            # Load bill details from sales table? We don't have bill details stored individually; for simplicity show invoice number.
            self.bill_area.delete("1.0", END)
            self.bill_area.insert(END, f"Invoice: {inv}")

    def search(self):
        inv = self.var_invoice.get()
        self.Sales_List.delete(0, END)
        try:
            c.execute("SELECT invoice_no FROM sales WHERE invoice_no LIKE ?", ('%'+inv+'%',))
            rows = c.fetchall()
            for r in rows:
                self.Sales_List.insert(END, r[0])
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def show(self):
        self.Sales_List.delete(0, END)
        try:
            c.execute("SELECT invoice_no FROM sales ORDER BY id DESC")
            rows = c.fetchall()
            for r in rows:
                self.Sales_List.insert(END, r[0])
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

class billClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Billing Module")
        self.root.geometry("1350x750+0+0")
        self.var_pid = StringVar()
        self.var_pname = StringVar()
        self.var_price = StringVar()
        self.var_qty = StringVar()
        self.var_stock = StringVar()
        self.var_search = StringVar()
        self.var_cname = StringVar()
        self.var_contact = StringVar()
        self.var_cal_input = StringVar()
        self.cart_list = []
        self.chk_print = IntVar()
        self.discount = 0.0
        self.net_pay = 0.0
        self.siscount = 0  # integer discount percent?
        self.invoice = ""
        self.icon_title = None
        try:
            self.icon_title = PhotoImage(file="images/logo.png")
        except:
            pass
        self.lbl_clock = Label(self.root, font=("times new roman", 15, "bold"), bg="#0f4d6c", fg="white")
        self.lbl_clock.pack(side=TOP, fill=X, pady=5)
        self.update_date_time()
        # Layout frames
        self.bill_top()
        self.bill_middle()
        self.bill_bottom()
        self.show()  # load product table initially

    def update_date_time(self):
        now = datetime.now()
        dt = now.strftime("%d/%m/%Y %H:%M:%S")
        self.lbl_clock.config(text=f"Date: {dt}")
        self.root.after(1000, self.update_date_time)

    def bill_top(self):
        top_frame = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        top_frame.place(x=10, y=30, width=1320, height=250)
        # Customer info
        Label(top_frame, text="Customer Name", font=("times new roman", 12, "bold"), bg="white").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        Entry(top_frame, textvariable=self.var_cname, font=("times new roman", 12), bg="lightgray").grid(row=0, column=1, padx=5, pady=5)
        Label(top_frame, text="Contact No", font=("times new roman", 12, "bold"), bg="white").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        Entry(top_frame, textvariable=self.var_contact, font=("times new roman", 12), bg="lightgray").grid(row=0, column=3, padx=5, pady=5)
        # Search product
        Label(top_frame, text="Search Product", font=("times new roman", 12, "bold"), bg="white").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        Entry(top_frame, textvariable=self.var_search, font=("times new roman", 12), bg="lightgray").grid(row=1, column=1, padx=5, pady=5)
        Button(top_frame, text="Search", command=self.search, font=("times new roman", 12), bg="#2196f3", fg="white").grid(row=1, column=2, padx=5, pady=5)
        Button(top_frame, text="Show All", command=self.show, font=("times new roman", 12), bg="#4caf50", fg="white").grid(row=1, column=3, padx=5, pady=5)
        # Product table
        frame_prod = Frame(top_frame, bd=2, relief=RIDGE, bg="white")
        frame_prod.grid(row=2, column=0, columnspan=4, padx=10, pady=10, sticky='nsew')
        scroll_y = Scrollbar(frame_prod, orient=VERTICAL)
        scroll_x = Scrollbar(frame_prod, orient=HORIZONTAL)
        self.product_Table = ttk.Treeview(frame_prod, columns=("pid", "name", "price", "stock", "category", "supplier"),
                                          yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.config(command=self.product_Table.yview)
        scroll_x.config(command=self.product_Table.xview)
        self.product_Table.heading("pid", text="PID")
        self.product_Table.heading("name", text="Name")
        self.product_Table.heading("price", text="Price")
        self.product_Table.heading("stock", text="Stock")
        self.product_Table.heading("category", text="Category")
        self.product_Table.heading("supplier", text="Supplier")
        self.product_Table["show"] = "headings"
        self.product_Table.column("pid", width=60)
        self.product_Table.column("name", width=150)
        self.product_Table.column("price", width=80)
        self.product_Table.column("stock", width=80)
        self.product_Table.column("category", width=100)
        self.product_Table.column("supplier", width=100)
        self.product_Table.pack(fill=BOTH, expand=1)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)

    def bill_middle(self):
        mid_frame = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        mid_frame.place(x=10, y=290, width=950, height=250)
        # Cart table
        scroll_y = Scrollbar(mid_frame, orient=VERTICAL)
        scroll_x = Scrollbar(mid_frame, orient=HORIZONTAL)
        self.CartTable = ttk.Treeview(mid_frame, columns=("pid", "name", "price", "qty", "amount"),
                                      yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.pack(side=BOTTOM, fill=X)
        scroll_y.config(command=self.CartTable.yview)
        scroll_x.config(command=self.CartTable.xview)
        self.CartTable.heading("pid", text="PID")
        self.CartTable.heading("name", text="Name")
        self.CartTable.heading("price", text="Price")
        self.CartTable.heading("qty", text="Qty")
        self.CartTable.heading("amount", text="Amount")
        self.CartTable["show"] = "headings"
        self.CartTable.pack(fill=BOTH, expand=1)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)
        self.cartTitle = Label(mid_frame, text="Cart Items", font=("times new roman", 15, "bold"), bg="white")
        self.cartTitle.pack(side=TOP, fill=X)

    def bill_bottom(self):
        bottom_frame = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        bottom_frame.place(x=10, y=550, width=1320, height=180)
        # Customer input area for cart
        Label(bottom_frame, text="PID", font=("times new roman", 12, "bold"), bg="white").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        Entry(bottom_frame, textvariable=self.var_pid, font=("times new roman", 12), state='readonly', bg="lightgray").grid(row=0, column=1, padx=5, pady=5)
        Label(bottom_frame, text="Name", font=("times new roman", 12, "bold"), bg="white").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        Entry(bottom_frame, textvariable=self.var_pname, font=("times new roman", 12), state='readonly', bg="lightgray").grid(row=0, column=3, padx=5, pady=5)
        Label(bottom_frame, text="Price", font=("times new roman", 12, "bold"), bg="white").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        Entry(bottom_frame, textvariable=self.var_price, font=("times new roman", 12), state='readonly', bg="lightgray").grid(row=1, column=1, padx=5, pady=5)
        Label(bottom_frame, text="Stock", font=("times new roman", 12, "bold"), bg="white").grid(row=1, column=2, padx=5, pady=5, sticky='w')
        self.lbl_inStock = Label(bottom_frame, textvariable=self.var_stock, font=("times new roman", 12), bg="white")
        self.lbl_inStock.grid(row=1, column=3, padx=5, pady=5, sticky='w')
        Label(bottom_frame, text="Qty", font=("times new roman", 12, "bold"), bg="white").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        Entry(bottom_frame, textvariable=self.var_qty, font=("times new roman", 12)).grid(row=2, column=1, padx=5, pady=5)
        # Buttons
        btn_frame = Frame(bottom_frame, bd=2, relief=RIDGE, bg="white")
        btn_frame.grid(row=3, column=0, columnspan=4, pady=10)
        Button(btn_frame, text="Add to Cart", command=self.add_update_cart, font=("times new roman", 12), bg="#2196f3", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update Cart", command=self.add_update_cart, font=("times new roman", 12), bg="#4caf50", fg="white").pack(side=LEFT, padx=5)  # same function for simplicity
        Button(btn_frame, text="Clear Cart", command=self.clear_cart, font=("times new roman", 12), bg="#f44336", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear All", command=self.clear_all, font=("times new roman", 12), bg="#607d8b", fg="white").pack(side=LEFT, padx=5)
        # Billing details
        bill_frame = Frame(bottom_frame, bd=2, relief=RIDGE, bg="white")
        bill_frame.place(x=500, y=5, width=400, height=150)
        self.lbl_amnt = Label(bill_frame, text="Total Amount", font=("times new roman", 12), bg="white")
        self.lbl_amnt.grid(row=0, column=0)
        self.lbl_discount = Label(bill_frame, text="Discount %", font=("times new roman", 12), bg="white")
        self.lbl_discount.grid(row=1, column=0)
        self.lbl_net_pay = Label(bill_frame, text="Net Pay", font=("times new roman", 15, "bold"), bg="white")
        self.lbl_net_pay.grid(row=2, column=0)
        self.txt_bill_area = Text(bill_frame, font=("times new roman", 10), height=4)
        self.txt_bill_area.grid(row=3, column=0, columnspan=2, pady=5)
        # Discount entry
        Entry(bill_frame, textvariable=self.var_disc, font=("times new roman", 12)).grid(row=1, column=1)
        self.var_disc = StringVar()  # Correct variable name
        Button(bill_frame, text="Calculate", command=self.bill_update, font=("times new roman", 12)).grid(row=1, column=2, padx=5)
        Button(bill_frame, text="Generate Bill", command=self.generate_bill, font=("times new roman", 12), bg="#ff9800", fg="white").grid(row=2, column=1, pady=5)
        Button(bill_frame, text="Print Bill", command=self.print_bill, font=("times new roman", 12), bg="#9c27b0", fg="white").grid(row=2, column=2, padx=5)
        # Calculator
        calc_frame = Frame(bottom_frame, bd=2, relief=RIDGE, bg="white")
        calc_frame.place(x=920, y=5, width=380, height=150)
        self.txt_cal_input = Entry(calc_frame, textvariable=self.var_cal_input, font=("times new roman", 12), justify=RIGHT)
        self.txt_cal_input.grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky='ew')
        buttons = ['7','8','9','+','4','5','6','-','1','2','3','*','C','0','=','/']
        row_val = 1
        col_val = 0
        for b in buttons:
            if b == 'C':
                cmd = self.clear_cal
            elif b == '=':
                cmd = self.perform_cal
            else:
                cmd = lambda x=b: self.get_input(x)
            Button(calc_frame, text=b, command=cmd, font=("times new roman", 12, "bold"), bg="lightblue").grid(row=row_val, column=col_val, padx=2, pady=2, sticky='ew')
            col_val += 1
            if col_val > 3:
                col_val = 0
                row_val += 1

    def get_data(self, ev):
        f = self.product_Table.focus()
        content = self.product_Table.item(f)
        row = content['values']
        if row:
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_stock.set(row[3])

    def get_data_cart(self, ev):
        f = self.CartTable.focus()
        content = self.CartTable.item(f)
        row = content['values']
        if row:
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_qty.set(row[3])
            # stock not in cart; maybe set from product? For update we just use those.
            self.var_stock.set("")  # unknown

    def add_update_cart(self):
        pid = self.var_pid.get()
        if not pid:
            messagebox.showerror("Error", "Select product first", parent=self.root)
            return
        try:
            qty = int(self.var_qty.get())
            if qty <= 0:
                messagebox.showerror("Error", "Quantity must be > 0", parent=self.root)
                return
        except:
            messagebox.showerror("Error", "Invalid quantity", parent=self.root)
            return
        # Check stock
        stock = int(self.var_stock.get()) if self.var_stock.get() else 0
        if qty > stock:
            messagebox.showerror("Error", "Insufficient stock", parent=self.root)
            return
        # Update or add to cart
        price = float(self.var_price.get())
        amount = price * qty
        # Check if already in cart
        found = False
        for child in self.CartTable.get_children():
            vals = self.CartTable.item(child, 'values')
            if vals[0] == pid:
                # update
                new_qty = int(vals[3]) + qty if not found else qty  # replace if second call? We'll treat as only update if found
                # Actually if found, we'll update the qty to current entry qty if user wants to replace
                if new_qty > stock:
                    messagebox.showerror("Error", "Insufficient stock", parent=self.root)
                    return
                new_amount = price * new_qty
                self.CartTable.item(child, values=(pid, self.var_pname.get(), price, new_qty, new_amount))
                found = True
                break
        if not found:
            self.CartTable.insert("", END, values=(pid, self.var_pname.get(), price, qty, amount))
        self.bill_update()
        self.var_qty.set("")
        self.var_stock.set("")

    def bill_update(self):
        total = 0.0
        for child in self.CartTable.get_children():
            total += float(self.CartTable.item(child, 'values')[4])
        self.lbl_amnt.config(text=f"Total Amount: {total:.2f}")
        try:
            disc = float(self.var_disc.get())
            if disc < 0 or disc > 100:
                disc = 0
        except:
            disc = 0
        discount_amount = total * disc / 100
        self.net_pay = total - discount_amount
        self.lbl_net_pay.config(text=f"Net Pay: {self.net_pay:.2f}")
        self.discount = disc

    def clear_cart(self):
        self.CartTable.delete(*self.CartTable.get_children())
        self.lbl_amnt.config(text="Total Amount:")
        self.lbl_net_pay.config(text="Net Pay:")
        self.var_disc.set("")

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
        self.txt_bill_area.delete("1.0", END)

    def search(self):
        txt = self.var_search.get()
        self.product_Table.delete(*self.product_Table.get_children())
        query = """SELECT p.pid, p.name, p.price, p.quantity, c.name, s.name
                   FROM product p
                   LEFT JOIN category c ON p.category_id = c.cat_id
                   LEFT JOIN supplier s ON p.supplier_id = s.sup_id
                   WHERE p.name LIKE ? OR c.name LIKE ? OR s.name LIKE ?"""
        try:
            c.execute(query, ('%'+txt+'%', '%'+txt+'%', '%'+txt+'%'))
            rows = c.fetchall()
            for row in rows:
                self.product_Table.insert("", END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def show(self):
        self.product_Table.delete(*self.product_Table.get_children())
        try:
            c.execute("""SELECT p.pid, p.name, p.price, p.quantity, c.name, s.name
                         FROM product p
                         LEFT JOIN category c ON p.category_id = c.cat_id
                         LEFT JOIN supplier s ON p.supplier_id = s.sup_id""")
            rows = c.fetchall()
            for row in rows:
                self.product_Table.insert("", END, values=row)
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)

    def generate_bill(self):
        if not self.CartTable.get_children():
            messagebox.showerror("Error", "Cart is empty", parent=self.root)
            return
        # Generate invoice number
        self.invoice = "INV-" + str(random.randint(1000, 9999)) + "-" + datetime.now().strftime("%d%m%Y")
        total_amount = sum(float(self.CartTable.item(child, 'values')[4]) for child in self.CartTable.get_children())
        try:
            c.execute("INSERT INTO sales (invoice_no, date, total_amount) VALUES (?, ?, ?)",
                      (self.invoice, datetime.now().strftime("%d/%m/%Y %H:%M:%S"), total_amount))
            conn.commit()
            # Reduce stock
            for child in self.CartTable.get_children():
                vals = self.CartTable.item(child, 'values')
                pid = vals[0]
                qty_sold = int(vals[3])
                c.execute("UPDATE product SET quantity = quantity - ? WHERE pid = ?", (qty_sold, pid))
            conn.commit()
        except Exception as e:
            messagebox.showerror("Error", f"Error: {str(e)}", parent=self.root)
            return
        # Show bill in text area
        self.txt_bill_area.delete("1.0", END)
        self.txt_bill_area.insert(END, f"Invoice: {self.invoice}\n")
        self.txt_bill_area.insert(END, f"Customer: {self.var_cname.get()}\n")
        self.txt_bill_area.insert(END, "Items:\n")
        for child in self.CartTable.get_children():
            vals = self.CartTable.item(child, 'values')
            self.txt_bill_area.insert(END, f"{vals[1]} x{vals[3]} @ {vals[2]} = {vals[4]}\n")
        self.txt_bill_area.insert(END, f"Discount: {self.discount}%\n")
        self.txt_bill_area.insert(END, f"Net Pay: {self.net_pay:.2f}\n")
        messagebox.showinfo("Success", "Bill generated", parent=self.root)

    def print_bill(self):
        if not self.txt_bill_area.get("1.0", END).strip():
            messagebox.showinfo("Print", "No bill to print", parent=self.root)
            return
        # Simulate printing: just show message
        messagebox.showinfo("Print", "Bill sent to printer", parent=self.root)

    def clear_cal(self):
        self.var_cal_input.set("")

    def get_input(self, num):
        current = self.var_cal_input.get()
        self.var_cal_input.set(current + str(num))

    def perform_cal(self):
        try:
            result = eval(self.var_cal_input.get())
            self.var_cal_input.set(str(result))
        except:
            messagebox.showerror("Error", "Invalid expression", parent=self.root)

    def show_cart(self):
        pass  # already visible

class IMS:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1350x700+0+0")
        self.root.title("Inventory Management System")
        self.root.config(bg="white")
        self.new_win = None
        self.new_obj = None
        self.MenuLogo = None
        self.icon_side = None
        self.icon_title = None
        try:
            self.MenuLogo = PhotoImage(file="images/logo.png")
        except:
            pass
        # Title frame
        title_frame = Frame(self.root, bd=2, relief=RIDGE, bg="#0f4d6c")
        title_frame.place(x=0, y=0, width=1350, height=50)
        self.lbl_clock = Label(title_frame, text="", font=("times new roman", 15, "bold"), bg="#0f4d6c", fg="white")
        self.lbl_clock.pack(side=RIGHT, padx=20)
        self.update_content()
        # Sidebar
        side_frame = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        side_frame.place(x=0, y=50, width=200, height=650)
        if self.MenuLogo:
            Label(side_frame, image=self.MenuLogo, bg="white").place(x=50, y=20)
        btn_category = Button(side_frame, text="Category", command=self.category, font=("times new roman", 14, "bold"), bg="#2196f3", fg="white", cursor="hand2")
        btn_category.place(x=20, y=100, width=160)
        btn_employee = Button(side_frame, text="Employee", command=self.employee, font=("times new roman", 14, "bold"), bg="#2196f3", fg="white", cursor="hand2")
        btn_employee.place(x=20, y=160, width=160)
        btn_product = Button(side_frame, text="Product", command=self.product, font=("times new roman", 14, "bold"), bg="#2196f3", fg="white", cursor="hand2")
        btn_product.place(x=20, y=220, width=160)
        btn_supplier = Button(side_frame, text="Supplier", command=self.supplier, font=("times new roman", 14, "bold"), bg="#2196f3", fg="white", cursor="hand2")
        btn_supplier.place(x=20, y=280, width=160)
        btn_sales = Button(side_frame, text="Sales", command=self.sales, font=("times new roman", 14, "bold"), bg="#2196f3", fg="white", cursor="hand2")
        btn_sales.place(x=20, y=340, width=160)
        btn_billing = Button(side_frame, text="Billing", command=self.billing, font=("times new roman", 14, "bold"), bg="#ff9800", fg="white", cursor="hand2")
        btn_billing.place(x=20, y=400, width=160)
        # Main content area (empty)
        self.main_frame = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        self.main_frame.place(x=200, y=50, width=1150, height=650)

    def update_content(self):
        now = datetime.now()
        dt = now.strftime("%d/%m/%Y %H:%M:%S")
        self.lbl_clock.config(text=dt)
        self.root.after(1000, self.update_content)

    def category(self):
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_win = Toplevel(self.root)
        self.new_obj = categoryClass(self.new_win)

    def employee(self):
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_win = Toplevel(self.root)
        self.new_obj = employeeClass(self.new_win)

    def product(self):
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_win = Toplevel(self.root)
        self.new_obj = productClass(self.new_win)

    def supplier(self):
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_win = Toplevel(self.root)
        self.new_obj = supplierClass(self.new_win)

    def sales(self):
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_win = Toplevel(self.root)
        self.new_obj = salesClass(self.new_win)

    def billing(self):
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_win = Toplevel(self.root)
        self.new_obj = billClass(self.new_win)

if __name__ == "__main__":
    root = Tk()
    app = IMS(root)
    root.mainloop()