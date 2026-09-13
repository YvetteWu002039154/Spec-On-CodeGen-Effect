from tkinter import *
from tkinter import ttk, messagebox
from datetime import datetime
import sqlite3
import os
from typing import Optional, Any, Union

DB_FILE = "ims.db"

class IMS:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("1100x600+100+50")
        self.root.config(bg="white")
        self.new_win: Optional[Toplevel] = None
        self.new_obj: Any = None
        self.MenuLogo: Optional[PhotoImage] = None
        self.icon_side: Optional[PhotoImage] = None
        self.icon_title: Optional[PhotoImage] = None
        
        # Title bar area
        title_frame = Frame(self.root, bg="#0b5fa5", bd=2, relief=RIDGE)
        title_frame.pack(side=TOP, fill=X)
        self.icon_title = PhotoImage()  # placeholder
        self.lbl_title = Label(title_frame, image=self.icon_title, text="IMS", font=("times new roman", 20, "bold"), bg="#0b5fa5", fg="white", compound=LEFT)
        self.lbl_title.pack(side=LEFT, padx=10, pady=5)
        
        # Clock label
        self.lbl_clock = Label(title_frame, font=("times new roman", 14), bg="#0b5fa5", fg="white")
        self.lbl_clock.pack(side=RIGHT, padx=20, pady=5)
        
        # Menu side bar
        menu_frame = Frame(self.root, bg="#f0f0f0", bd=2, relief=RIDGE)
        menu_frame.place(x=0, y=50, width=160, height=550)
        
        # Use labels as buttons
        self.lbl_category = Label(menu_frame, text="Category", font=("times new roman", 16, "bold"), bg="#f0f0f0", cursor="hand2")
        self.lbl_category.pack(pady=10, fill=X)
        self.lbl_category.bind("<Button-1>", lambda e: self.category())
        self.lbl_employee = Label(menu_frame, text="Employee", font=("times new roman", 16, "bold"), bg="#f0f0f0", cursor="hand2")
        self.lbl_employee.pack(pady=10, fill=X)
        self.lbl_employee.bind("<Button-1>", lambda e: self.employee())
        self.lbl_product = Label(menu_frame, text="Product", font=("times new roman", 16, "bold"), bg="#f0f0f0", cursor="hand2")
        self.lbl_product.pack(pady=10, fill=X)
        self.lbl_product.bind("<Button-1>", lambda e: self.product())
        self.lbl_sales = Label(menu_frame, text="Sales", font=("times new roman", 16, "bold"), bg="#f0f0f0", cursor="hand2")
        self.lbl_sales.pack(pady=10, fill=X)
        self.lbl_sales.bind("<Button-1>", lambda e: self.sales())
        self.lbl_supplier = Label(menu_frame, text="Supplier", font=("times new roman", 16, "bold"), bg="#f0f0f0", cursor="hand2")
        self.lbl_supplier.pack(pady=10, fill=X)
        self.lbl_supplier.bind("<Button-1>", lambda e: self.supplier())
        
        self.update_content()
    
    def update_content(self) -> None:
        self.lbl_clock.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self.update_content)
    
    def category(self) -> None:
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_win = Toplevel(self.root)
        self.new_obj = categoryClass(self.new_win)
    
    def employee(self) -> None:
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_win = Toplevel(self.root)
        self.new_obj = employeeClass(self.new_win)
    
    def product(self) -> None:
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_win = Toplevel(self.root)
        self.new_obj = productClass(self.new_win)
    
    def sales(self) -> None:
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_win = Toplevel(self.root)
        self.new_obj = salesClass(self.new_win)
    
    def supplier(self) -> None:
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_win = Toplevel(self.root)
        self.new_obj = supplierClass(self.new_win)

class categoryClass:
    def __init__(self, root: Toplevel) -> None:
        self.root = root
        self.root.title("Category Management")
        self.root.geometry("800x450+200+200")
        self.root.resizable(False, False)
        
        self.im1: Optional[PhotoImage] = None
        self.im2: Optional[PhotoImage] = None
        self.var_cat_id = StringVar()
        self.var_name = StringVar()
        
        # Labels for images (not used)
        self.lbl_im1 = Label()
        self.lbl_im2 = Label()
        
        # Entry frame
        entry_frame = Frame(self.root, bg="white")
        entry_frame.pack(side=TOP, fill=X, padx=10, pady=10)
        
        Label(entry_frame, text="Category ID", font=("times new roman", 12), bg="white").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        Entry(entry_frame, textvariable=self.var_cat_id, font=("times new roman", 12)).grid(row=0, column=1, padx=5, pady=5)
        Label(entry_frame, text="Name", font=("times new roman", 12), bg="white").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        Entry(entry_frame, textvariable=self.var_name, font=("times new roman", 12)).grid(row=1, column=1, padx=5, pady=5)
        
        btn_frame = Frame(self.root, bg="white")
        btn_frame.pack(side=TOP, fill=X, padx=10)
        Button(btn_frame, text="Add", command=self.add, bg="#4CAF50", fg="white", width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, bg="#607D8B", fg="white", width=10).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, bg="#F44336", fg="white", width=10).pack(side=LEFT, padx=5)
        
        # Treeview
        tree_frame = Frame(self.root, bd=2, relief=RIDGE)
        tree_frame.pack(fill=BOTH, expand=1, padx=10, pady=10)
        scroll_y = Scrollbar(tree_frame, orient=VERTICAL)
        scroll_x = Scrollbar(tree_frame, orient=HORIZONTAL)
        self.CategoryTable = ttk.Treeview(tree_frame, columns=("id", "name"), yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.config(command=self.CategoryTable.yview)
        scroll_x.config(command=self.CategoryTable.xview)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_x.pack(side=BOTTOM, fill=X)
        self.CategoryTable.heading("id", text="ID")
        self.CategoryTable.heading("name", text="Name")
        self.CategoryTable["show"] = "headings"
        self.CategoryTable.pack(fill=BOTH, expand=1)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)
        
        self.show()
    
    def add(self) -> None:
        cat_id = self.var_cat_id.get()
        name = self.var_name.get()
        if not cat_id or not name:
            messagebox.showerror("Error", "All fields are required")
            return
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO category (cat_id, name) VALUES (?,?)", (cat_id, name))
            conn.commit()
            conn.close()
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def clear(self) -> None:
        self.var_cat_id.set("")
        self.var_name.set("")
    
    def delete(self) -> None:
        selected = self.CategoryTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select a record to delete")
            return
        cat_id = self.CategoryTable.item(selected, "values")[0]
        if messagebox.askyesno("Confirm Delete", "Are you sure?"):
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM category WHERE cat_id=?", (cat_id,))
                conn.commit()
                conn.close()
                self.show()
            except Exception as e:
                messagebox.showerror("Error", str(e))
    
    def get_data(self, ev: Any) -> None:
        selected = self.CategoryTable.focus()
        if selected:
            row = self.CategoryTable.item(selected, "values")
            self.var_cat_id.set(row[0])
            self.var_name.set(row[1])
    
    def show(self) -> None:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS category (cat_id TEXT PRIMARY KEY, name TEXT)")
        cursor.execute("SELECT * FROM category")
        rows = cursor.fetchall()
        self.CategoryTable.delete(*self.CategoryTable.get_children())
        for row in rows:
            self.CategoryTable.insert("", END, values=row)
        conn.close()

class employeeClass:
    def __init__(self, root: Toplevel) -> None:
        self.root = root
        self.root.title("Employee Management")
        self.root.geometry("950x550+150+100")
        
        self.var_emp_id = StringVar()
        self.var_name = StringVar()
        self.var_email = StringVar()
        self.var_contact = StringVar()
        self.var_gender = StringVar()
        self.var_dob = StringVar()
        self.var_doj = StringVar()
        self.var_pass = StringVar()
        self.var_utype = StringVar()
        self.var_salary = StringVar()
        self.txt_address = Text()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()
        
        # Entry frame
        entry_frame = LabelFrame(self.root, text="Employee Details", font=("times new roman", 12), bd=2, relief=RIDGE, bg="white")
        entry_frame.pack(side=LEFT, fill=BOTH, padx=10, pady=10)
        
        labels = ["Employee ID", "Name", "Email", "Contact", "Gender", "D.O.B", "D.O.J", "Password", "User Type", "Salary", "Address"]
        i=0
        for lbl in labels[:-1]:
            Label(entry_frame, text=lbl, font=("times new roman", 12), bg="white").grid(row=i, column=0, sticky="w", padx=5, pady=2)
            if lbl == "Gender":
                ttk.Combobox(entry_frame, textvariable=self.var_gender, values=("Male","Female"), state="readonly", width=18).grid(row=i, column=1, padx=5)
            elif lbl == "D.O.B":
                Entry(entry_frame, textvariable=self.var_dob, font=("times new roman", 12)).grid(row=i, column=1, padx=5)
            elif lbl == "D.O.J":
                Entry(entry_frame, textvariable=self.var_doj, font=("times new roman", 12)).grid(row=i, column=1, padx=5)
            elif lbl == "User Type":
                ttk.Combobox(entry_frame, textvariable=self.var_utype, values=("Admin","Employee"), state="readonly", width=18).grid(row=i, column=1, padx=5)
            else:
                Entry(entry_frame, textvariable=getattr(self, f"var_{lbl.lower().replace(' ', '_') if lbl!='Employee ID' else 'var_emp_id'}"), font=("times new roman", 12)).grid(row=i, column=1, padx=5)
            i+=1
        Label(entry_frame, text="Address", font=("times new roman", 12), bg="white").grid(row=i, column=0, sticky="w", padx=5)
        self.txt_address = Text(entry_frame, font=("times new roman", 12), width=20, height=3)
        self.txt_address.grid(row=i, column=1, padx=5)
        
        # Buttons
        btn_frame = Frame(entry_frame, bg="white")
        btn_frame.grid(row=i+1, columnspan=2, pady=10)
        Button(btn_frame, text="Add", command=self.add, bg="#4CAF50", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update, bg="#2196F3", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, bg="#F44336", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, bg="#607D8B", fg="white", width=8).pack(side=LEFT, padx=5)
        
        # Search
        search_frame = LabelFrame(self.root, text="Search", font=("times new roman", 12), bd=2, relief=RIDGE, bg="white")
        search_frame.pack(side=TOP, fill=X, padx=10, pady=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=("id","name","email"), state="readonly", width=12).pack(side=LEFT, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt, font=("times new roman", 12), width=20).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search, bg="#FFC107").pack(side=LEFT, padx=5)
        Button(search_frame, text="Show All", command=self.show, bg="#9E9E9E").pack(side=LEFT, padx=5)
        
        # Treeview
        tree_frame = Frame(self.root, bd=2, relief=RIDGE)
        tree_frame.pack(fill=BOTH, expand=1, padx=10, pady=10)
        scroll_y = Scrollbar(tree_frame, orient=VERTICAL)
        self.EmployeeTable = ttk.Treeview(tree_frame, columns=("eid","name","email","contact","gender","dob","doj","pass","utype","salary","address"), yscrollcommand=scroll_y.set)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_y.config(command=self.EmployeeTable.yview)
        self.EmployeeTable.heading("eid", text="EID")
        self.EmployeeTable.heading("name", text="Name")
        self.EmployeeTable.heading("email", text="Email")
        self.EmployeeTable.heading("contact", text="Contact")
        self.EmployeeTable.heading("gender", text="Gender")
        self.EmployeeTable.heading("dob", text="DOB")
        self.EmployeeTable.heading("doj", text="DOJ")
        self.EmployeeTable.heading("pass", text="Password")
        self.EmployeeTable.heading("utype", text="User Type")
        self.EmployeeTable.heading("salary", text="Salary")
        self.EmployeeTable.heading("address", text="Address")
        self.EmployeeTable["show"] = "headings"
        self.EmployeeTable.pack(fill=BOTH, expand=1)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()
    
    def add(self) -> None:
        if not self.var_emp_id.get() or not self.var_name.get():
            messagebox.showerror("Error", "ID and Name are required")
            return
        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS employee (eid TEXT PRIMARY KEY, name TEXT, email TEXT, contact TEXT, gender TEXT, dob TEXT, doj TEXT, pass TEXT, utype TEXT, salary TEXT, address TEXT)")
            cur.execute("INSERT OR IGNORE INTO employee VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
                self.var_emp_id.get(), self.var_name.get(), self.var_email.get(), self.var_contact.get(),
                self.var_gender.get(), self.var_dob.get(), self.var_doj.get(), self.var_pass.get(),
                self.var_utype.get(), self.var_salary.get(), self.txt_address.get("1.0", END).strip()
            ))
            conn.commit()
            conn.close()
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def clear(self) -> None:
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_email.set("")
        self.var_contact.set("")
        self.var_gender.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_pass.set("")
        self.var_utype.set("")
        self.var_salary.set("")
        self.txt_address.delete("1.0", END)
    
    def delete(self) -> None:
        selected = self.EmployeeTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select record")
            return
        eid = self.EmployeeTable.item(selected, "values")[0]
        if messagebox.askyesno("Delete", "Delete?"):
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("DELETE FROM employee WHERE eid=?", (eid,))
            conn.commit()
            conn.close()
            self.show()
    
    def update(self) -> None:
        if not self.var_emp_id.get():
            messagebox.showerror("Error", "Select record first")
            return
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("UPDATE employee SET name=?, email=?, contact=?, gender=?, dob=?, doj=?, pass=?, utype=?, salary=?, address=? WHERE eid=?", (
            self.var_name.get(), self.var_email.get(), self.var_contact.get(),
            self.var_gender.get(), self.var_dob.get(), self.var_doj.get(),
            self.var_pass.get(), self.var_utype.get(), self.var_salary.get(),
            self.txt_address.get("1.0", END).strip(), self.var_emp_id.get()
        ))
        conn.commit()
        conn.close()
        self.show()
    
    def get_data(self, ev: Any) -> None:
        selected = self.EmployeeTable.focus()
        if selected:
            row = self.EmployeeTable.item(selected, "values")
            self.var_emp_id.set(row[0])
            self.var_name.set(row[1])
            self.var_email.set(row[2])
            self.var_contact.set(row[3])
            self.var_gender.set(row[4])
            self.var_dob.set(row[5])
            self.var_doj.set(row[6])
            self.var_pass.set(row[7])
            self.var_utype.set(row[8])
            self.var_salary.set(row[9])
            self.txt_address.delete("1.0", END)
            self.txt_address.insert("1.0", row[10] if len(row)>10 else "")
    
    def search(self) -> None:
        searchby = self.var_searchby.get()
        searchtxt = self.var_searchtxt.get()
        if not searchby or not searchtxt:
            messagebox.showerror("Error", "Select search by and enter text")
            return
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        query = "SELECT * FROM employee WHERE {} LIKE ?".format({"id":"eid","name":"name","email":"email"}.get(searchby,""))
        cur.execute(query, ('%'+searchtxt+'%',))
        rows = cur.fetchall()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for row in rows:
            self.EmployeeTable.insert("", END, values=row)
        conn.close()
    
    def show(self) -> None:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS employee (eid TEXT PRIMARY KEY, name TEXT, email TEXT, contact TEXT, gender TEXT, dob TEXT, doj TEXT, pass TEXT, utype TEXT, salary TEXT, address TEXT)")
        cur.execute("SELECT * FROM employee")
        rows = cur.fetchall()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for row in rows:
            self.EmployeeTable.insert("", END, values=row)
        conn.close()

class productClass:
    def __init__(self, root: Toplevel) -> None:
        self.root = root
        self.root.title("Product Management")
        self.root.geometry("950x600+150+80")
        
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
        
        self.fetch_cat_sup()
        
        # Entry frame
        entry_frame = LabelFrame(self.root, text="Product Details", font=("times new roman", 12), bd=2, relief=RIDGE, bg="white")
        entry_frame.pack(side=LEFT, fill=BOTH, padx=10, pady=10)
        labels = ["PID","Name","Price","Quantity","Status","Category","Supplier"]
        for i, lbl in enumerate(labels):
            Label(entry_frame, text=lbl, font=("times new roman", 12), bg="white").grid(row=i, column=0, sticky="w", padx=5, pady=2)
            if lbl == "Category":
                ttk.Combobox(entry_frame, textvariable=self.var_cat, values=self.cat_list, state="readonly", width=18).grid(row=i, column=1, padx=5)
            elif lbl == "Supplier":
                ttk.Combobox(entry_frame, textvariable=self.var_sup, values=self.sup_list, state="readonly", width=18).grid(row=i, column=1, padx=5)
            elif lbl == "Status":
                ttk.Combobox(entry_frame, textvariable=self.var_status, values=("Active","Inactive"), state="readonly", width=18).grid(row=i, column=1, padx=5)
            else:
                Entry(entry_frame, textvariable=getattr(self, f"var_{lbl.lower()}") , font=("times new roman", 12)).grid(row=i, column=1, padx=5)
        
        btn_frame = Frame(entry_frame, bg="white")
        btn_frame.grid(row=len(labels), columnspan=2, pady=10)
        Button(btn_frame, text="Add", command=self.add, bg="#4CAF50", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update, bg="#2196F3", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, bg="#F44336", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, bg="#607D8B", fg="white", width=8).pack(side=LEFT, padx=5)
        
        search_frame = LabelFrame(self.root, text="Search", font=("times new roman", 12), bd=2, relief=RIDGE, bg="white")
        search_frame.pack(side=TOP, fill=X, padx=10, pady=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=("pid","name","category","supplier"), state="readonly", width=12).pack(side=LEFT, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt, font=("times new roman", 12)).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search, bg="#FFC107").pack(side=LEFT, padx=5)
        Button(search_frame, text="Show All", command=self.show, bg="#9E9E9E").pack(side=LEFT, padx=5)
        
        tree_frame = Frame(self.root, bd=2, relief=RIDGE)
        tree_frame.pack(fill=BOTH, expand=1, padx=10, pady=10)
        scroll_y = Scrollbar(tree_frame, orient=VERTICAL)
        self.ProductTable = ttk.Treeview(tree_frame, columns=("pid","name","price","qty","status","category","supplier"), yscrollcommand=scroll_y.set)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_y.config(command=self.ProductTable.yview)
        self.ProductTable.heading("pid", text="PID")
        self.ProductTable.heading("name", text="Name")
        self.ProductTable.heading("price", text="Price")
        self.ProductTable.heading("qty", text="Qty")
        self.ProductTable.heading("status", text="Status")
        self.ProductTable.heading("category", text="Category")
        self.ProductTable.heading("supplier", text="Supplier")
        self.ProductTable["show"] = "headings"
        self.ProductTable.pack(fill=BOTH, expand=1)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()
    
    def fetch_cat_sup(self) -> None:
        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("SELECT name FROM category")
            self.cat_list = [row[0] for row in cur.fetchall()]
            cur.execute("SELECT name FROM supplier")
            self.sup_list = [row[0] for row in cur.fetchall()]
            conn.close()
        except:
            pass
    
    def add(self) -> None:
        if not self.var_pid.get() or not self.var_name.get():
            messagebox.showerror("Error", "PID and Name required")
            return
        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS product (pid TEXT PRIMARY KEY, name TEXT, price REAL, qty INTEGER, status TEXT, category TEXT, supplier TEXT)")
            cur.execute("INSERT OR IGNORE INTO product VALUES (?,?,?,?,?,?,?)", (
                self.var_pid.get(), self.var_name.get(), float(self.var_price.get() or 0),
                int(self.var_qty.get() or 0), self.var_status.get(), self.var_cat.get(), self.var_sup.get()
            ))
            conn.commit()
            conn.close()
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def clear(self) -> None:
        self.var_pid.set("")
        self.var_name.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("")
        self.var_cat.set("")
        self.var_sup.set("")
    
    def delete(self) -> None:
        selected = self.ProductTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select record")
            return
        pid = self.ProductTable.item(selected, "values")[0]
        if messagebox.askyesno("Delete", "Delete?"):
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("DELETE FROM product WHERE pid=?", (pid,))
            conn.commit()
            conn.close()
            self.show()
    
    def update(self) -> None:
        if not self.var_pid.get():
            messagebox.showerror("Error", "Select record first")
            return
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("UPDATE product SET name=?, price=?, qty=?, status=?, category=?, supplier=? WHERE pid=?", (
            self.var_name.get(), float(self.var_price.get() or 0),
            int(self.var_qty.get() or 0), self.var_status.get(),
            self.var_cat.get(), self.var_sup.get(), self.var_pid.get()
        ))
        conn.commit()
        conn.close()
        self.show()
    
    def get_data(self, ev: Any) -> None:
        selected = self.ProductTable.focus()
        if selected:
            row = self.ProductTable.item(selected, "values")
            self.var_pid.set(row[0])
            self.var_name.set(row[1])
            self.var_price.set(row[2])
            self.var_qty.set(row[3])
            self.var_status.set(row[4])
            self.var_cat.set(row[5])
            self.var_sup.set(row[6])
    
    def search(self) -> None:
        searchby = self.var_searchby.get()
        searchtxt = self.var_searchtxt.get()
        col = {"pid":"pid","name":"name","category":"category","supplier":"supplier"}.get(searchby,"")
        if not col or not searchtxt:
            messagebox.showerror("Error", "Select criteria and enter text")
            return
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM product WHERE {col} LIKE ?", ('%'+searchtxt+'%',))
        rows = cur.fetchall()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for row in rows:
            self.ProductTable.insert("", END, values=row)
        conn.close()
    
    def show(self) -> None:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS product (pid TEXT PRIMARY KEY, name TEXT, price REAL, qty INTEGER, status TEXT, category TEXT, supplier TEXT)")
        cur.execute("SELECT * FROM product")
        rows = cur.fetchall()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for row in rows:
            self.ProductTable.insert("", END, values=row)
        conn.close()

class salesClass:
    def __init__(self, root: Toplevel) -> None:
        self.root = root
        self.root.title("Sales Management")
        self.root.geometry("1000x600+100+100")
        self.var_invoice = StringVar()
        self.blll_list = []
        self.bill_photo: Optional[PhotoImage] = None
        
        top_frame = Frame(self.root, bg="white")
        top_frame.pack(side=TOP, fill=X, padx=10, pady=5)
        Button(top_frame, text="New Bill", command=self.open_bill, bg="#4CAF50", fg="white", font=("times new roman", 12)).pack(side=LEFT, padx=10)
        Label(top_frame, text="Invoice No.", font=("times new roman", 12), bg="white").pack(side=LEFT)
        Entry(top_frame, textvariable=self.var_invoice, font=("times new roman", 12), width=20).pack(side=LEFT, padx=5)
        Button(top_frame, text="Search", command=self.search, bg="#FFC107").pack(side=LEFT, padx=5)
        Button(top_frame, text="Clear", command=self.clear, bg="#607D8B", fg="white").pack(side=LEFT, padx=5)
        
        left_frame = Frame(self.root, bd=2, relief=RIDGE)
        left_frame.pack(side=LEFT, fill=BOTH, expand=1, padx=10, pady=5)
        scroll_y = Scrollbar(left_frame, orient=VERTICAL)
        self.Sales_List = Listbox(left_frame, font=("times new roman", 12), yscrollcommand=scroll_y.set)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_y.config(command=self.Sales_List.yview)
        self.Sales_List.pack(fill=BOTH, expand=1)
        self.Sales_List.bind("<ButtonRelease-1>", self.get_data)
        
        right_frame = Frame(self.root, bd=2, relief=RIDGE)
        right_frame.pack(side=RIGHT, fill=BOTH, padx=10, pady=5)
        Label(right_frame, text="Bill Details", font=("times new roman", 14)).pack()
        self.bill_area = Text(right_frame, font=("times new roman", 12), width=50)
        self.bill_area.pack(fill=BOTH, expand=1)
        
        self.show()
    
    def open_bill(self) -> None:
        bill_win = Toplevel(self.root)
        app = billClass(bill_win)  # not stored as attribute in diagram, but fine
    
    def clear(self) -> None:
        self.bill_area.delete("1.0", END)
        self.var_invoice.set("")
    
    def get_data(self, ev: Any) -> None:
        selected = self.Sales_List.curselection()
        if selected:
            index = selected[0]
            invoice = self.Sales_List.get(index)
            self.var_invoice.set(invoice)
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("SELECT bill_text FROM sales WHERE invoice=?", (invoice,))
            row = cur.fetchone()
            if row:
                self.bill_area.delete("1.0", END)
                self.bill_area.insert("1.0", row[0])
            conn.close()
    
    def search(self) -> None:
        inv = self.var_invoice.get()
        if not inv:
            messagebox.showerror("Error", "Enter invoice number")
            return
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT invoice FROM sales WHERE invoice LIKE ?", ('%'+inv+'%',))
        rows = cur.fetchall()
        self.Sales_List.delete(0, END)
        for r in rows:
            self.Sales_List.insert(END, r[0])
        conn.close()
    
    def show(self) -> None:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS sales (invoice TEXT PRIMARY KEY, bill_text TEXT)")
        cur.execute("SELECT invoice FROM sales")
        rows = cur.fetchall()
        self.Sales_List.delete(0, END)
        for r in rows:
            self.Sales_List.insert(END, r[0])
        conn.close()

class supplierClass:
    def __init__(self, root: Toplevel) -> None:
        self.root = root
        self.root.title("Supplier Management")
        self.root.geometry("800x550+200+150")
        self.var_sup_invoice = StringVar()
        self.var_name = StringVar()
        self.var_contact = StringVar()
        self.txt_desc = Text()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()
        
        entry_frame = LabelFrame(self.root, text="Supplier Details", font=("times new roman", 12), bd=2, relief=RIDGE, bg="white")
        entry_frame.pack(side=TOP, fill=X, padx=10, pady=10)
        Label(entry_frame, text="Invoice No.", font=("times new roman", 12), bg="white").grid(row=0, column=0, sticky="w", padx=5)
        Entry(entry_frame, textvariable=self.var_sup_invoice, font=("times new roman", 12)).grid(row=0, column=1, padx=5)
        Label(entry_frame, text="Name", font=("times new roman", 12), bg="white").grid(row=1, column=0, sticky="w", padx=5)
        Entry(entry_frame, textvariable=self.var_name, font=("times new roman", 12)).grid(row=1, column=1, padx=5)
        Label(entry_frame, text="Contact", font=("times new roman", 12), bg="white").grid(row=2, column=0, sticky="w", padx=5)
        Entry(entry_frame, textvariable=self.var_contact, font=("times new roman", 12)).grid(row=2, column=1, padx=5)
        Label(entry_frame, text="Description", font=("times new roman", 12), bg="white").grid(row=3, column=0, sticky="w", padx=5)
        self.txt_desc = Text(entry_frame, font=("times new roman", 12), width=30, height=4)
        self.txt_desc.grid(row=3, column=1, padx=5)
        
        btn_frame = Frame(entry_frame, bg="white")
        btn_frame.grid(row=4, columnspan=2, pady=10)
        Button(btn_frame, text="Add", command=self.add, bg="#4CAF50", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update, bg="#2196F3", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, bg="#F44336", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, bg="#607D8B", fg="white", width=8).pack(side=LEFT, padx=5)
        
        search_frame = LabelFrame(self.root, text="Search", font=("times new roman", 12), bd=2, relief=RIDGE, bg="white")
        search_frame.pack(fill=X, padx=10, pady=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=("invoice","name"), state="readonly", width=12).pack(side=LEFT, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt, font=("times new roman", 12), width=20).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search, bg="#FFC107").pack(side=LEFT, padx=5)
        Button(search_frame, text="Show All", command=self.show, bg="#9E9E9E").pack(side=LEFT, padx=5)
        
        tree_frame = Frame(self.root, bd=2, relief=RIDGE)
        tree_frame.pack(fill=BOTH, expand=1, padx=10, pady=10)
        scroll_y = Scrollbar(tree_frame, orient=VERTICAL)
        self.SupplierTable = ttk.Treeview(tree_frame, columns=("invoice","name","contact","desc"), yscrollcommand=scroll_y.set)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_y.config(command=self.SupplierTable.yview)
        self.SupplierTable.heading("invoice", text="Invoice")
        self.SupplierTable.heading("name", text="Name")
        self.SupplierTable.heading("contact", text="Contact")
        self.SupplierTable.heading("desc", text="Description")
        self.SupplierTable["show"] = "headings"
        self.SupplierTable.pack(fill=BOTH, expand=1)
        self.SupplierTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()
    
    def add(self) -> None:
        if not self.var_sup_invoice.get() or not self.var_name.get():
            messagebox.showerror("Error", "Invoice and name required")
            return
        try:
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS supplier (invoice TEXT PRIMARY KEY, name TEXT, contact TEXT, desc TEXT)")
            cur.execute("INSERT OR IGNORE INTO supplier VALUES (?,?,?,?)", (
                self.var_sup_invoice.get(), self.var_name.get(), self.var_contact.get(),
                self.txt_desc.get("1.0", END).strip()
            ))
            conn.commit()
            conn.close()
            self.clear()
            self.show()
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def clear(self) -> None:
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete("1.0", END)
    
    def delete(self) -> None:
        selected = self.SupplierTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select record")
            return
        inv = self.SupplierTable.item(selected, "values")[0]
        if messagebox.askyesno("Delete", "Delete?"):
            conn = sqlite3.connect(DB_FILE)
            cur = conn.cursor()
            cur.execute("DELETE FROM supplier WHERE invoice=?", (inv,))
            conn.commit()
            conn.close()
            self.show()
    
    def update(self) -> None:
        if not self.var_sup_invoice.get():
            messagebox.showerror("Error", "Select record first")
            return
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("UPDATE supplier SET name=?, contact=?, desc=? WHERE invoice=?", (
            self.var_name.get(), self.var_contact.get(),
            self.txt_desc.get("1.0", END).strip(), self.var_sup_invoice.get()
        ))
        conn.commit()
        conn.close()
        self.show()
    
    def get_data(self, ev: Any) -> None:
        selected = self.SupplierTable.focus()
        if selected:
            row = self.SupplierTable.item(selected, "values")
            self.var_sup_invoice.set(row[0])
            self.var_name.set(row[1])
            self.var_contact.set(row[2])
            self.txt_desc.delete("1.0", END)
            self.txt_desc.insert("1.0", row[3] if len(row)>3 else "")
    
    def search(self) -> None:
        searchby = self.var_searchby.get()
        searchtxt = self.var_searchtxt.get()
        col = {"invoice":"invoice","name":"name"}.get(searchby,"")
        if not col or not searchtxt:
            messagebox.showerror("Error", "Select column and enter text")
            return
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM supplier WHERE {col} LIKE ?", ('%'+searchtxt+'%',))
        rows = cur.fetchall()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert("", END, values=row)
        conn.close()
    
    def show(self) -> None:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS supplier (invoice TEXT PRIMARY KEY, name TEXT, contact TEXT, desc TEXT)")
        cur.execute("SELECT * FROM supplier")
        rows = cur.fetchall()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert("", END, values=row)
        conn.close()

class billClass:
    def __init__(self, root: Toplevel) -> None:
        self.root = root
        self.root.title("Billing System")
        self.root.geometry("1100x600+100+50")
        self.invoice: Optional[str] = None
        self.chk_print = IntVar()
        self.siscount = 0
        self.discount = 0.0
        self.bill_amnt = 0
        self.net_pay: float = 0.0
        self.cart_list = []
        
        # Variables
        self.var_cname = StringVar()
        self.var_contact = StringVar()
        self.var_search = StringVar()
        self.var_pid = StringVar()
        self.var_pname = StringVar()
        self.var_price = StringVar()
        self.var_qty = StringVar()
        self.var_stock = StringVar()
        self.var_cal_input = StringVar()
        
        self.icon_title: Optional[PhotoImage] = None
        self.txt_bill_area = Text()
        self.txt_cal_input = Entry()
        
        self.bill_top()
        self.bill_middle()
        self.bill_bottom()
        self.update_date_time()
    
    def update_date_time(self) -> None:
        if hasattr(self, 'lbl_clock'):
            self.lbl_clock.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self.update_date_time)
    
    def bill_top(self) -> None:
        top = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        top.pack(side=TOP, fill=X)
        Label(top, text="Billing System", font=("times new roman", 24, "bold"), bg="white").pack()
        self.lbl_clock = Label(top, font=("times new roman", 14), bg="white")
        self.lbl_clock.pack()
    
    def bill_middle(self) -> None:
        mid = Frame(self.root, bd=2, relief=RIDGE)
        mid.pack(fill=BOTH, expand=1, padx=10, pady=10)
        
        # Left product search
        prod_frame = LabelFrame(mid, text="Product Search", font=("times new roman", 12), bd=2, relief=RIDGE, bg="white")
        prod_frame.pack(side=LEFT, fill=BOTH, expand=1, padx=5)
        Label(prod_frame, text="Search by Name", font=("times new roman", 12), bg="white").grid(row=0, column=0, padx=5, pady=5)
        Entry(prod_frame, textvariable=self.var_search, font=("times new roman", 12)).grid(row=0, column=1, padx=5)
        Button(prod_frame, text="Search", command=self.search, bg="#FFC107").grid(row=0, column=2, padx=5)
        
        # product table
        table_frame = Frame(prod_frame, bd=2, relief=RIDGE)
        table_frame.grid(row=1, columnspan=3, pady=10)
        scroll_y = Scrollbar(table_frame, orient=VERTICAL)
        self.product_Table = ttk.Treeview(table_frame, columns=("pid","name","price","qty"), yscrollcommand=scroll_y.set)
        scroll_y.pack(side=RIGHT, fill=Y)
        scroll_y.config(command=self.product_Table.yview)
        self.product_Table.heading("pid", text="PID")
        self.product_Table.heading("name", text="Name")
        self.product_Table.heading("price", text="Price")
        self.product_Table.heading("qty", text="Qty")
        self.product_Table["show"] = "headings"
        self.product_Table.pack(fill=BOTH, expand=1)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)
        
        # add to cart frame
        add_frame = Frame(prod_frame, bg="white")
        add_frame.grid(row=2, columnspan=3, pady=10)
        labels = ["PID","Name","Price","Qty","In Stock"]
        entries = [self.var_pid, self.var_pname, self.var_price, self.var_qty, self.var_stock]
        for i, (lbl, var) in enumerate(zip(labels, entries)):
            Label(add_frame, text=lbl, font=("times new roman", 10), bg="white").grid(row=0, column=i, padx=2)
            ent = Entry(add_frame, textvariable=var, font=("times new roman", 10), width=10, state="readonly" if lbl=="In Stock" or lbl=="PID" or lbl=="Name" or lbl=="Price" else "normal")
            ent.grid(row=1, column=i, padx=2)
        Button(add_frame, text="Add to Cart", command=self.add_update_cart, bg="#4CAF50", fg="white").grid(row=1, column=len(entries), padx=5)
        Button(add_frame, text="Clear", command=self.clear_cart, bg="#F44336", fg="white").grid(row=1, column=len(entries)+1, padx=5)
        
        # Right cart display
        cart_frame = LabelFrame(mid, text="Cart", font=("times new roman", 12), bd=2, relief=RIDGE, bg="white")
        cart_frame.pack(side=RIGHT, fill=BOTH, expand=1, padx=5)
        Label(cart_frame, text="Cart Items", font=("times new roman", 14, "bold"), bg="white").pack()
        self.cartTitle = Label(cart_frame, text="", font=("times new roman", 12), bg="white")
        self.cartTitle.pack()
        
        cart_table_frame = Frame(cart_frame, bd=2, relief=RIDGE)
        cart_table_frame.pack(fill=BOTH, expand=1, pady=10)
        scroll_y2 = Scrollbar(cart_table_frame, orient=VERTICAL)
        self.CartTable = ttk.Treeview(cart_table_frame, columns=("pid","name","price","qty","total"), yscrollcommand=scroll_y2.set)
        scroll_y2.pack(side=RIGHT, fill=Y)
        scroll_y2.config(command=self.CartTable.yview)
        self.CartTable.heading("pid", text="PID")
        self.CartTable.heading("name", text="Name")
        self.CartTable.heading("price", text="Price")
        self.CartTable.heading("qty", text="Qty")
        self.CartTable.heading("total", text="Total")
        self.CartTable["show"] = "headings"
        self.CartTable.pack(fill=BOTH, expand=1)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)
    
    def bill_bottom(self) -> None:
        bottom = Frame(self.root, bd=2, relief=RIDGE, bg="white")
        bottom.pack(side=BOTTOM, fill=X, padx=10, pady=10)
        
        cust_frame = LabelFrame(bottom, text="Customer Details", font=("times new roman", 12), bd=2, relief=RIDGE, bg="white")
        cust_frame.pack(side=LEFT, padx=5)
        Label(cust_frame, text="Name", font=("times new roman", 12), bg="white").grid(row=0, column=0, padx=5)
        Entry(cust_frame, textvariable=self.var_cname, font=("times new roman", 12)).grid(row=0, column=1, padx=5)
        Label(cust_frame, text="Contact", font=("times new roman", 12), bg="white").grid(row=1, column=0, padx=5)
        Entry(cust_frame, textvariable=self.var_contact, font=("times new roman", 12)).grid(row=1, column=1, padx=5)
        
        calc_frame = Frame(bottom, bg="white")
        calc_frame.pack(side=LEFT, padx=20)
        self.lbl_amnt = Label(calc_frame, text="Bill Amount: 0", font=("times new roman", 14), bg="white")
        self.lbl_amnt.pack()
        self.lbl_discount = Label(calc_frame, text="Discount: 0", font=("times new roman", 14), bg="white")
        self.lbl_discount.pack()
        self.lbl_net_pay = Label(calc_frame, text="Net Pay: 0", font=("times new roman", 14, "bold"), bg="white")
        self.lbl_net_pay.pack()
        self.lbl_inStock = Label(calc_frame, text="", fg="red", bg="white")
        self.lbl_inStock.pack()
        
        # simple calculator
        frame_cal = Frame(bottom, bg="white")
        frame_cal.pack(side=RIGHT, padx=10)
        self.txt_cal_input = Entry(frame_cal, textvariable=self.var_cal_input, font=("times new roman", 14), width=20)
        self.txt_cal_input.grid(row=0, columnspan=4)
        buttons = [('7','8','9','+'),('4','5','6','-'),('1','2','3','*'),('0','.','/','C')]
        for i, row in enumerate(buttons):
            for j, char in enumerate(row):
                if char == 'C':
                    Button(frame_cal, text=char, command=self.clear_cal, width=5, height=2).grid(row=i+1, column=j)
                else:
                    Button(frame_cal, text=char, command=lambda c=char: self.get_input(c), width=5, height=2).grid(row=i+1, column=j)
        Button(frame_cal, text="=", command=self.perform_cal, width=5, height=2, bg="#4CAF50", fg="white").grid(row=4, columnspan=4)
        
        # bottom buttons
        bottom_btn = Frame(bottom, bg="white")
        bottom_btn.pack(side=BOTTOM, fill=X, pady=5)
        Button(bottom_btn, text="Generate Bill", command=self.generate_bill, bg="#2196F3", fg="white", width=12).pack(side=LEFT, padx=5)
        Button(bottom_btn, text="Print", command=self.print_bill, bg="#4CAF50", fg="white", width=12).pack(side=LEFT, padx=5)
        Checkbutton(bottom_btn, text="Print", variable=self.chk_print, onvalue=1, offvalue=0, bg="white").pack(side=LEFT, padx=5)
        Button(bottom_btn, text="Clear All", command=self.clear_all, bg="#F44336", fg="white", width=12).pack(side=LEFT, padx=5)
    
    def search(self) -> None:
        term = self.var_search.get()
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT pid, name, price, qty FROM product WHERE name LIKE ?", ('%'+term+'%',))
        rows = cur.fetchall()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", END, values=row)
        conn.close()
    
    def get_data(self, ev: Any) -> None:
        selected = self.product_Table.focus()
        if selected:
            row = self.product_Table.item(selected, "values")
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_stock.set(row[3])
            self.var_qty.set("1")
    
    def get_data_cart(self, ev: Any) -> None:
        selected = self.CartTable.focus()
        if selected:
            row = self.CartTable.item(selected, "values")
            self.var_pid.set(row[0])
            self.var_pname.set(row[1])
            self.var_price.set(row[2])
            self.var_qty.set(row[3])
            # stock is not in cart, so ignore
    
    def add_update_cart(self) -> None:
        pid = self.var_pid.get()
        if not pid:
            messagebox.showerror("Error", "Select a product")
            return
        try:
            qty = int(self.var_qty.get()) if self.var_qty.get() else 1
        except:
            messagebox.showerror("Error", "Invalid quantity")
            return
        stock = int(self.var_stock.get()) if self.var_stock.get() else 0
        if qty > stock:
            messagebox.showerror("Error", "Not enough stock")
            return
        price = float(self.var_price.get()) if self.var_price.get() else 0
        total = qty * price
        # Check if already in cart
        found = False
        for i, item in enumerate(self.cart_list):
            if item[0] == pid:
                self.cart_list[i] = (pid, self.var_pname.get(), price, qty, total)
                found = True
                break
        if not found:
            self.cart_list.append((pid, self.var_pname.get(), price, qty, total))
        self.show_cart()
    
    def clear_cart(self) -> None:
        self.cart_list = []
        self.show_cart()
    
    def show_cart(self) -> None:
        self.CartTable.delete(*self.CartTable.get_children())
        total_amt = 0
        for item in self.cart_list:
            self.CartTable.insert("", END, values=item)
            total_amt += item[4]
        self.bill_amnt = total_amt
        self.net_pay = total_amt - self.discount
        self.lbl_amnt.config(text=f"Bill Amount: {total_amt:.2f}")
        self.lbl_discount.config(text=f"Discount: {self.discount:.2f}")
        self.lbl_net_pay.config(text=f"Net Pay: {self.net_pay:.2f}")
        # Clear entry fields for product selection
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")
    
    def get_input(self, num: str) -> None:
        self.var_cal_input.set(self.var_cal_input.get() + num)
    
    def perform_cal(self) -> None:
        expr = self.var_cal_input.get()
        try:
            result = eval(expr)
            self.var_cal_input.set(str(result))
            # treat result as discount percentage? Not specified, but we can apply as discount
            self.discount = float(result) if isinstance(result, (int, float)) else 0.0
        except:
            self.var_cal_input.set("Error")
    
    def clear_cal(self) -> None:
        self.var_cal_input.set("")
    
    def generate_bill(self) -> None:
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty")
            return
        # Create invoice number based on timestamp
        self.invoice = "INV-" + datetime.now().strftime("%Y%m%d%H%M%S")
        # prepare bill text
        bill_text = f"Invoice: {self.invoice}\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        bill_text += f"Customer: {self.var_cname.get()}\nContact: {self.var_contact.get()}\n"
        bill_text += "-"*40 + "\n"
        bill_text += f"{'PID':<10}{'Name':<15}{'Price':<8}{'Qty':<5}{'Total':<8}\n"
        total_amt = 0
        for item in self.cart_list:
            bill_text += f"{item[0]:<10}{item[1]:<15}{item[2]:<8.2f}{item[3]:<5}{item[4]:<8.2f}\n"
            total_amt += item[4]
        bill_text += "-"*40 + "\n"
        bill_text += f"Subtotal: {total_amt:.2f}\nDiscount: {self.discount:.2f}\nNet Pay: {(total_amt - self.discount):.2f}\n"
        
        # store in sales table
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS sales (invoice TEXT PRIMARY KEY, bill_text TEXT)")
        cur.execute("INSERT INTO sales VALUES (?,?)", (self.invoice, bill_text))
        conn.commit()
        
        # update product quantities
        for item in self.cart_list:
            cur.execute("UPDATE product SET qty = qty - ? WHERE pid=? AND qty >= ?", (item[3], item[0], item[3]))
        conn.commit()
        conn.close()
        
        # display bill
        self.txt_bill_area = Text(self.root, font=("times new roman", 12), width=50, height=15)
        self.txt_bill_area.place(x=200, y=150)
        self.txt_bill_area.insert(END, bill_text)
        self.txt_bill_area.config(state=DISABLED)
        
        messagebox.showinfo("Success", f"Bill {self.invoice} generated")
        if self.chk_print.get():
            self.print_bill()
    
    def print_bill(self) -> None:
        if hasattr(self, 'txt_bill_area'):
            import tempfile, webbrowser
            # simple print: save to temp file and open
            content = self.txt_bill_area.get("1.0", END)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                fname = f.name
            messagebox.showinfo("Print", f"Bill saved to {fname}. Open to print.")
    
    def clear_all(self) -> None:
        self.clear_cart()
        self.var_cname.set("")
        self.var_contact.set("")
        self.var_cal_input.set("")
        if hasattr(self, 'txt_bill_area'):
            self.txt_bill_area.destroy()
        self.bill_amnt = 0
        self.net_pay = 0.0
        self.discount = 0.0
    
    def bill_update(self) -> None:
        pass  # not specified

if __name__ == "__main__":
    # Initialize database tables
    root = Tk()
    app = IMS(root)
    root.mainloop()