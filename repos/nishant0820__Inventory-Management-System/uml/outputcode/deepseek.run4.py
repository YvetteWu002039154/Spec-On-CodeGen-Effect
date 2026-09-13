from tkinter import *
from tkinter import ttk
from tkinter import messagebox
import datetime
import random
import string


class IMS:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1350x700+0+0")
        self.root.title("Inventory Management System | Developed By: Python")
        self.root.config(bg="white")

        # icon images (placeholder for actual images)
        self.icon_title = PhotoImage(file="images/logo.png") if False else None
        self.icon_side = PhotoImage(file="images/side.png") if False else None

        # Title label
        title = Label(self.root, text="Inventory Management System", font=("times new roman", 40, "bold"), bg="#010c48", fg="white", bd=5, relief=GROOVE)
        title.pack(side=TOP, fill=X)

        # left menu labels (clickable buttons)
        menu_frame = Frame(self.root, bg="#020a33", bd=5, relief=RIDGE)
        menu_frame.place(x=0, y=80, width=280, height=620)

        self.lbl_employee = Label(menu_frame, text="Employee", font=("times new roman", 20, "bold"), bg="#020a33", fg="white", cursor="hand2")
        self.lbl_employee.grid(row=0, column=0, pady=20, padx=50, sticky="w")
        self.lbl_employee.bind("<Button-1>", lambda e: self.employee())

        self.lbl_supplier = Label(menu_frame, text="Supplier", font=("times new roman", 20, "bold"), bg="#020a33", fg="white", cursor="hand2")
        self.lbl_supplier.grid(row=1, column=0, pady=20, padx=50, sticky="w")
        self.lbl_supplier.bind("<Button-1>", lambda e: self.supplier())

        self.lbl_category = Label(menu_frame, text="Category", font=("times new roman", 20, "bold"), bg="#020a33", fg="white", cursor="hand2")
        self.lbl_category.grid(row=2, column=0, pady=20, padx=50, sticky="w")
        self.lbl_category.bind("<Button-1>", lambda e: self.category())

        self.lbl_product = Label(menu_frame, text="Product", font=("times new roman", 20, "bold"), bg="#020a33", fg="white", cursor="hand2")
        self.lbl_product.grid(row=3, column=0, pady=20, padx=50, sticky="w")
        self.lbl_product.bind("<Button-1>", lambda e: self.product())

        self.lbl_sales = Label(menu_frame, text="Sales", font=("times new roman", 20, "bold"), bg="#020a33", fg="white", cursor="hand2")
        self.lbl_sales.grid(row=4, column=0, pady=20, padx=50, sticky="w")
        self.lbl_sales.bind("<Button-1>", lambda e: self.sales())

        self.lbl_clock = Label(menu_frame, text="", font=("times new roman", 15, "bold"), bg="#020a33", fg="white")
        self.lbl_clock.grid(row=5, column=0, pady=20, padx=20)

        self.update_content()
        self.update_date_time()

        # content area
        self.content_frame = Frame(self.root, bg="white", bd=5, relief=GROOVE)
        self.content_frame.place(x=280, y=80, width=1050, height=620)

        self.new_obj = None

    def update_content(self):
        # could update dashboard stats, not required to be fully functional
        pass

    def update_date_time(self):
        now = datetime.datetime.now()
        dt = now.strftime("%d/%m/%Y %H:%M:%S")
        self.lbl_clock.config(text=dt)
        self.root.after(1000, self.update_date_time)

    def employee(self):
        self.new_win = Toplevel(self.root)
        self.new_obj = employeeClass(self.new_win)

    def supplier(self):
        self.new_win = Toplevel(self.root)
        self.new_obj = supplierClass(self.new_win)

    def category(self):
        self.new_win = Toplevel(self.root)
        self.new_obj = categoryClass(self.new_win)

    def product(self):
        self.new_win = Toplevel(self.root)
        self.new_obj = productClass(self.new_win)

    def sales(self):
        self.new_win = Toplevel(self.root)
        self.new_obj = salesClass(self.new_win)


class categoryClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Category")
        self.root.geometry("600x400")
        self.root.config(bg="white")

        self.var_cat_id = StringVar()
        self.var_name = StringVar()

        # load placeholder images (if needed)
        self.im1 = None
        self.im2 = None
        self.lbl_im1 = None
        self.lbl_im2 = None

        # Labels and Entries
        lbl_catId = Label(self.root, text="Category ID", font=("times new roman", 15), bg="white")
        lbl_catId.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        txt_catId = Entry(self.root, textvariable=self.var_cat_id, font=("times new roman", 15), bg="lightyellow")
        txt_catId.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        lbl_name = Label(self.root, text="Category Name", font=("times new roman", 15), bg="white")
        lbl_name.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        txt_name = Entry(self.root, textvariable=self.var_name, font=("times new roman", 15), bg="lightyellow")
        txt_name.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # Buttons
        btn_add = Button(self.root, text="Add", command=self.add, font=("times new roman", 15), bg="#4CAF50", fg="white", cursor="hand2")
        btn_add.grid(row=2, column=0, padx=10, pady=20)
        btn_clear = Button(self.root, text="Clear", command=self.clear, font=("times new roman", 15), bg="#f44336", fg="white", cursor="hand2")
        btn_clear.grid(row=2, column=1, padx=10, pady=20)
        btn_delete = Button(self.root, text="Delete", command=self.delete, font=("times new roman", 15), bg="#607d8b", fg="white", cursor="hand2")
        btn_delete.grid(row=2, column=2, padx=10, pady=20)

        # Treeview
        self.CategoryTable = ttk.Treeview(self.root, columns=("catid", "name"), show='headings')
        self.CategoryTable.heading("catid", text="Category ID")
        self.CategoryTable.heading("name", text="Category Name")
        self.CategoryTable.column("catid", width=100)
        self.CategoryTable.column("name", width=200)
        self.CategoryTable.grid(row=3, column=0, columnspan=3, padx=10, pady=10)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)

        # dummy data (in-memory)
        self.cat_list = [("C001", "Electronics"), ("C002", "Clothing")]
        self.show()

    def add(self):
        if self.var_cat_id.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "All fields are required", parent=self.root)
            return
        # check duplicate
        for cat in self.cat_list:
            if cat[0] == self.var_cat_id.get():
                messagebox.showerror("Error", "Category ID already exists", parent=self.root)
                return
        self.cat_list.append((self.var_cat_id.get(), self.var_name.get()))
        self.show()
        self.clear()

    def clear(self):
        self.var_cat_id.set("")
        self.var_name.set("")

    def delete(self):
        selected = self.CategoryTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select a category to delete", parent=self.root)
            return
        item = self.CategoryTable.item(selected)
        cat_id = item['values'][0]
        for i, cat in enumerate(self.cat_list):
            if cat[0] == cat_id:
                del self.cat_list[i]
                break
        self.show()

    def get_data(self, ev):
        selected = self.CategoryTable.selection()
        if selected:
            item = self.CategoryTable.item(selected)
            self.var_cat_id.set(item['values'][0])
            self.var_name.set(item['values'][1])

    def show(self):
        self.CategoryTable.delete(*self.CategoryTable.get_children())
        for cat in self.cat_list:
            self.CategoryTable.insert("", END, values=cat)


class employeeClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Employee")
        self.root.geometry("800x600")
        self.root.config(bg="white")

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
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()

        self.txt_address = Text(self.root, width=30, height=3, font=("times new roman", 13))

        # Labels and entries
        labels = ["Emp ID", "Name", "Email", "Gender", "Contact", "DOB", "DOJ", "Password", "User Type", "Salary", "Address"]
        row = 0
        entries = []
        for i, lbl_text in enumerate(labels):
            Label(self.root, text=lbl_text, font=("times new roman", 13), bg="white").grid(row=row, column=0, padx=10, pady=5, sticky="w")
            if lbl_text == "Address":
                self.txt_address.grid(row=row, column=1, padx=10, pady=5, sticky="w")
            else:
                var = getattr(self, f"var_{lbl_text.lower().replace(' ', '_').replace('emp_id', 'emp_id').replace('user_type', 'utype')}")
                if var is not None:
                    ent = Entry(self.root, textvariable=var, font=("times new roman", 13), bg="lightyellow")
                    ent.grid(row=row, column=1, padx=10, pady=5, sticky="w")
            row += 1

        # Buttons
        btn_frame = Frame(self.root, bg="white")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        Button(btn_frame, text="Add", command=self.add, font=("times new roman", 12), bg="#4CAF50", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update, font=("times new roman", 12), bg="#2196F3", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, font=("times new roman", 12), bg="#f44336", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, font=("times new roman", 12), bg="#607d8b", fg="white").pack(side=LEFT, padx=5)

        # Search
        search_frame = Frame(self.root, bg="white")
        search_frame.grid(row=row+1, column=0, columnspan=2, pady=10)
        Label(search_frame, text="Search By", font=("times new roman", 12), bg="white").pack(side=LEFT, padx=5)
        cmb_search = ttk.Combobox(search_frame, textvariable=self.var_searchby, values=["emp_id", "name", "email"], state="readonly", width=10)
        cmb_search.pack(side=LEFT, padx=5)
        cmb_search.current(0)
        Entry(search_frame, textvariable=self.var_searchtxt, font=("times new roman", 12), bg="lightyellow", width=15).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search, font=("times new roman", 12), bg="#FFC107").pack(side=LEFT, padx=5)

        # Employee Table
        self.EmployeeTable = ttk.Treeview(self.root, columns=("1","2","3","4","5","6","7","8","9","10","11"), show='headings', height=10)
        self.EmployeeTable.heading("1", text="Emp ID")
        self.EmployeeTable.heading("2", text="Name")
        self.EmployeeTable.heading("3", text="Email")
        self.EmployeeTable.heading("4", text="Gender")
        self.EmployeeTable.heading("5", text="Contact")
        self.EmployeeTable.heading("6", text="DOB")
        self.EmployeeTable.heading("7", text="DOJ")
        self.EmployeeTable.heading("8", text="Pass")
        self.EmployeeTable.heading("9", text="User Type")
        self.EmployeeTable.heading("10", text="Salary")
        self.EmployeeTable.heading("11", text="Address")
        self.EmployeeTable.column("1", width=50)
        self.EmployeeTable.column("2", width=80)
        self.EmployeeTable.grid(row=row+2, column=0, columnspan=2, padx=10, pady=10)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)

        # in-memory employee data
        self.emp_list = []
        self.show()

    def add(self):
        # validation simplified
        if self.var_emp_id.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "Required fields missing", parent=self.root)
            return
        # check duplicate ID
        for emp in self.emp_list:
            if emp[0] == self.var_emp_id.get():
                messagebox.showerror("Error", "Employee ID already exists", parent=self.root)
                return
        data = (
            self.var_emp_id.get(),
            self.var_name.get(),
            self.var_email.get(),
            self.var_gender.get(),
            self.var_contact.get(),
            self.var_dob.get(),
            self.var_doj.get(),
            self.var_pass.get(),
            self.var_utype.get(),
            self.var_salary.get(),
            self.txt_address.get("1.0", END).strip()
        )
        self.emp_list.append(data)
        self.show()
        self.clear()

    def update(self):
        selected = self.EmployeeTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select an employee to update", parent=self.root)
            return
        item = self.EmployeeTable.item(selected)
        old_id = item['values'][0]
        # find and update
        for i, emp in enumerate(self.emp_list):
            if emp[0] == old_id:
                self.emp_list[i] = (
                    self.var_emp_id.get(),
                    self.var_name.get(),
                    self.var_email.get(),
                    self.var_gender.get(),
                    self.var_contact.get(),
                    self.var_dob.get(),
                    self.var_doj.get(),
                    self.var_pass.get(),
                    self.var_utype.get(),
                    self.var_salary.get(),
                    self.txt_address.get("1.0", END).strip()
                )
                break
        self.show()

    def delete(self):
        selected = self.EmployeeTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select an employee to delete", parent=self.root)
            return
        item = self.EmployeeTable.item(selected)
        emp_id = item['values'][0]
        for i, emp in enumerate(self.emp_list):
            if emp[0] == emp_id:
                del self.emp_list[i]
                break
        self.show()

    def clear(self):
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_email.set("")
        self.var_gender.set("")
        self.var_contact.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_pass.set("")
        self.var_utype.set("")
        self.var_salary.set("")
        self.txt_address.delete("1.0", END)

    def get_data(self, ev):
        selected = self.EmployeeTable.selection()
        if selected:
            item = self.EmployeeTable.item(selected)
            vals = item['values']
            self.var_emp_id.set(vals[0])
            self.var_name.set(vals[1])
            self.var_email.set(vals[2])
            self.var_gender.set(vals[3])
            self.var_contact.set(vals[4])
            self.var_dob.set(vals[5])
            self.var_doj.set(vals[6])
            self.var_pass.set(vals[7])
            self.var_utype.set(vals[8])
            self.var_salary.set(vals[9])
            self.txt_address.delete("1.0", END)
            self.txt_address.insert(END, vals[10])

    def search(self):
        search_by = self.var_searchby.get()
        search_txt = self.var_searchtxt.get().lower()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for emp in self.emp_list:
            if search_by == "emp_id" and search_txt in emp[0].lower():
                self.EmployeeTable.insert("", END, values=emp)
            elif search_by == "name" and search_txt in emp[1].lower():
                self.EmployeeTable.insert("", END, values=emp)
            elif search_by == "email" and search_txt in emp[2].lower():
                self.EmployeeTable.insert("", END, values=emp)
            elif search_txt == "":
                self.EmployeeTable.insert("", END, values=emp)

    def show(self):
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for emp in self.emp_list:
            self.EmployeeTable.insert("", END, values=emp)


class productClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Product")
        self.root.geometry("800x600")
        self.root.config(bg="white")

        self.var_pid = StringVar()
        self.var_name = StringVar()
        self.var_price = StringVar()
        self.var_qty = StringVar()
        self.var_status = StringVar()
        self.var_cat = StringVar()
        self.var_sup = StringVar()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()

        self.cat_list = [("C001", "Electronics"), ("C002", "Clothing")]
        self.sup_list = [("S001", "Supplier1"), ("S002", "Supplier2")]

        # Labels and Entries
        lbls = ["Product ID", "Name", "Price", "Qty", "Status", "Category", "Supplier"]
        row=0
        for lbl_text in lbls:
            Label(self.root, text=lbl_text, font=("times new roman", 13), bg="white").grid(row=row, column=0, padx=10, pady=5, sticky="w")
            var_name_attr = lbl_text.lower().replace(" ", "_")  # simplified
            # handle specific names
            if lbl_text == "Product ID":
                var = self.var_pid
            elif lbl_text == "Name":
                var = self.var_name
            elif lbl_text == "Price":
                var = self.var_price
            elif lbl_text == "Qty":
                var = self.var_qty
            elif lbl_text == "Status":
                var = self.var_status
            elif lbl_text == "Category":
                var = self.var_cat
            elif lbl_text == "Supplier":
                var = self.var_sup
            ent = Entry(self.root, textvariable=var, font=("times new roman", 13), bg="lightyellow")
            ent.grid(row=row, column=1, padx=10, pady=5, sticky="w")
            row += 1

        # Buttons
        btn_frame = Frame(self.root, bg="white")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        Button(btn_frame, text="Add", command=self.add, font=("times new roman", 12), bg="#4CAF50", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update, font=("times new roman", 12), bg="#2196F3", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, font=("times new roman", 12), bg="#f44336", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, font=("times new roman", 12), bg="#607d8b", fg="white").pack(side=LEFT, padx=5)

        # Search
        search_frame = Frame(self.root, bg="white")
        search_frame.grid(row=row+1, column=0, columnspan=2, pady=10)
        Label(search_frame, text="Search By", font=("times new roman", 12), bg="white").pack(side=LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=["pid", "name", "category", "supplier"], state="readonly", width=12).pack(side=LEFT, padx=5)
        self.var_searchby.set("pid")
        Entry(search_frame, textvariable=self.var_searchtxt, font=("times new roman", 12), bg="lightyellow", width=15).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search, font=("times new roman", 12), bg="#FFC107").pack(side=LEFT, padx=5)

        # Product Table
        self.ProductTable = ttk.Treeview(self.root, columns=("1","2","3","4","5","6","7"), show='headings', height=10)
        self.ProductTable.heading("1", text="PID")
        self.ProductTable.heading("2", text="Name")
        self.ProductTable.heading("3", text="Price")
        self.ProductTable.heading("4", text="Qty")
        self.ProductTable.heading("5", text="Status")
        self.ProductTable.heading("6", text="Category")
        self.ProductTable.heading("7", text="Supplier")
        self.ProductTable.column("1", width=60)
        self.ProductTable.grid(row=row+2, column=0, columnspan=2, padx=10, pady=10)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)

        # in-memory product data
        self.prod_list = [("P001", "Laptop", "50000", "10", "Active", "Electronics", "Supplier1"),
                           ("P002", "Shirt", "1000", "50", "Active", "Clothing", "Supplier2")]
        self.show()

    def fetch_cat_sup(self):
        # Could be used to refresh dropdown lists, but simplified
        pass

    def add(self):
        if self.var_pid.get() == "" or self.var_name.get() == "" or self.var_price.get() == "" or self.var_qty.get() == "":
            messagebox.showerror("Error", "Required fields missing", parent=self.root)
            return
        # Validate numeric
        try:
            float(self.var_price.get())
            int(self.var_qty.get())
        except ValueError:
            messagebox.showerror("Error", "Price and Qty must be numbers", parent=self.root)
            return
        # Check duplicate
        for prod in self.prod_list:
            if prod[0] == self.var_pid.get():
                messagebox.showerror("Error", "Product ID already exists", parent=self.root)
                return
        data = (self.var_pid.get(), self.var_name.get(), self.var_price.get(), self.var_qty.get(),
                self.var_status.get(), self.var_cat.get(), self.var_sup.get())
        self.prod_list.append(data)
        self.show()
        self.clear()

    def update(self):
        selected = self.ProductTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select a product to update", parent=self.root)
            return
        item = self.ProductTable.item(selected)
        old_pid = item['values'][0]
        for i, prod in enumerate(self.prod_list):
            if prod[0] == old_pid:
                self.prod_list[i] = (self.var_pid.get(), self.var_name.get(), self.var_price.get(),
                                     self.var_qty.get(), self.var_status.get(), self.var_cat.get(), self.var_sup.get())
                break
        self.show()

    def delete(self):
        selected = self.ProductTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select a product to delete", parent=self.root)
            return
        item = self.ProductTable.item(selected)
        pid = item['values'][0]
        for i, prod in enumerate(self.prod_list):
            if prod[0] == pid:
                del self.prod_list[i]
                break
        self.show()

    def clear(self):
        self.var_pid.set("")
        self.var_name.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("")
        self.var_cat.set("")
        self.var_sup.set("")

    def get_data(self, ev):
        selected = self.ProductTable.selection()
        if selected:
            item = self.ProductTable.item(selected)
            vals = item['values']
            self.var_pid.set(vals[0])
            self.var_name.set(vals[1])
            self.var_price.set(vals[2])
            self.var_qty.set(vals[3])
            self.var_status.set(vals[4])
            self.var_cat.set(vals[5])
            self.var_sup.set(vals[6])

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get().lower()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for prod in self.prod_list:
            if by == "pid" and txt in prod[0].lower():
                self.ProductTable.insert("", END, values=prod)
            elif by == "name" and txt in prod[1].lower():
                self.ProductTable.insert("", END, values=prod)
            elif by == "category" and txt in prod[5].lower():
                self.ProductTable.insert("", END, values=prod)
            elif by == "supplier" and txt in prod[6].lower():
                self.ProductTable.insert("", END, values=prod)
            elif txt == "":
                self.ProductTable.insert("", END, values=prod)

    def show(self):
        self.ProductTable.delete(*self.ProductTable.get_children())
        for prod in self.prod_list:
            self.ProductTable.insert("", END, values=prod)


class supplierClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Supplier")
        self.root.geometry("700x500")
        self.root.config(bg="white")

        self.var_sup_invoice = StringVar()
        self.var_name = StringVar()
        self.var_contact = StringVar()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()
        self.txt_desc = Text(self.root, width=30, height=3, font=("times new roman", 13))

        # Labels and entries
        labels = ["Invoice No", "Name", "Contact", "Description"]
        row = 0
        for lbl_text in labels:
            Label(self.root, text=lbl_text, font=("times new roman", 13), bg="white").grid(row=row, column=0, padx=10, pady=5, sticky="w")
            if lbl_text == "Description":
                self.txt_desc.grid(row=row, column=1, padx=10, pady=5, sticky="w")
            else:
                var = getattr(self, f"var_{lbl_text.lower().replace(' ', '').replace('invoiceno', 'sup_invoice')}") if lbl_text != "Invoice No" else self.var_sup_invoice
                if var:
                    ent = Entry(self.root, textvariable=var, font=("times new roman", 13), bg="lightyellow")
                    ent.grid(row=row, column=1, padx=10, pady=5, sticky="w")
            row += 1

        # Buttons
        btn_frame = Frame(self.root, bg="white")
        btn_frame.grid(row=row, column=0, columnspan=2, pady=10)
        Button(btn_frame, text="Add", command=self.add, font=("times new roman", 12), bg="#4CAF50", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update, font=("times new roman", 12), bg="#2196F3", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, font=("times new roman", 12), bg="#f44336", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, font=("times new roman", 12), bg="#607d8b", fg="white").pack(side=LEFT, padx=5)

        # Search
        search_frame = Frame(self.root, bg="white")
        search_frame.grid(row=row+1, column=0, columnspan=2, pady=10)
        Label(search_frame, text="Search By", font=("times new roman", 12), bg="white").pack(side=LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=["invoice", "name"], state="readonly", width=12).pack(side=LEFT, padx=5)
        self.var_searchby.set("invoice")
        Entry(search_frame, textvariable=self.var_searchtxt, font=("times new roman", 12), bg="lightyellow", width=15).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search, font=("times new roman", 12), bg="#FFC107").pack(side=LEFT, padx=5)

        # Supplier Table
        self.SupplierTable = ttk.Treeview(self.root, columns=("1","2","3","4"), show='headings', height=10)
        self.SupplierTable.heading("1", text="Invoice")
        self.SupplierTable.heading("2", text="Name")
        self.SupplierTable.heading("3", text="Contact")
        self.SupplierTable.heading("4", text="Desc")
        self.SupplierTable.column("1", width=80)
        self.SupplierTable.grid(row=row+2, column=0, columnspan=2, padx=10, pady=10)
        self.SupplierTable.bind("<ButtonRelease-1>", self.get_data)

        self.sup_list = [("S001", "Supplier1", "9876543210", "Electronics supplier"),
                         ("S002", "Supplier2", "9988776655", "Clothing supplier")]
        self.show()

    def add(self):
        if self.var_sup_invoice.get() == "" or self.var_name.get() == "":
            messagebox.showerror("Error", "Required fields missing", parent=self.root)
            return
        for sup in self.sup_list:
            if sup[0] == self.var_sup_invoice.get():
                messagebox.showerror("Error", "Invoice already exists", parent=self.root)
                return
        data = (self.var_sup_invoice.get(), self.var_name.get(), self.var_contact.get(), self.txt_desc.get("1.0", END).strip())
        self.sup_list.append(data)
        self.show()
        self.clear()

    def update(self):
        selected = self.SupplierTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select a supplier to update", parent=self.root)
            return
        item = self.SupplierTable.item(selected)
        old_inv = item['values'][0]
        for i, sup in enumerate(self.sup_list):
            if sup[0] == old_inv:
                self.sup_list[i] = (self.var_sup_invoice.get(), self.var_name.get(), self.var_contact.get(),
                                    self.txt_desc.get("1.0", END).strip())
                break
        self.show()

    def delete(self):
        selected = self.SupplierTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select a supplier to delete", parent=self.root)
            return
        item = self.SupplierTable.item(selected)
        inv = item['values'][0]
        for i, sup in enumerate(self.sup_list):
            if sup[0] == inv:
                del self.sup_list[i]
                break
        self.show()

    def clear(self):
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete("1.0", END)

    def get_data(self, ev):
        selected = self.SupplierTable.selection()
        if selected:
            item = self.SupplierTable.item(selected)
            vals = item['values']
            self.var_sup_invoice.set(vals[0])
            self.var_name.set(vals[1])
            self.var_contact.set(vals[2])
            self.txt_desc.delete("1.0", END)
            self.txt_desc.insert(END, vals[3])

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get().lower()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for sup in self.sup_list:
            if by == "invoice" and txt in sup[0].lower():
                self.SupplierTable.insert("", END, values=sup)
            elif by == "name" and txt in sup[1].lower():
                self.SupplierTable.insert("", END, values=sup)
            elif txt == "":
                self.SupplierTable.insert("", END, values=sup)

    def show(self):
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for sup in self.sup_list:
            self.SupplierTable.insert("", END, values=sup)


class salesClass:
    def __init__(self, root):
        self.root = root
        self.root.title("Sales")
        self.root.geometry("700x500")
        self.root.config(bg="white")

        self.var_invoice = StringVar()
        self.blll_list = []  # sales history list

        # Label and entry for invoice
        Label(self.root, text="Invoice No", font=("times new roman", 15), bg="white").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        Entry(self.root, textvariable=self.var_invoice, font=("times new roman", 15), bg="lightyellow").grid(row=0, column=1, padx=10, pady=10, sticky="w")
        Button(self.root, text="Search", command=self.search, font=("times new roman", 12), bg="#FFC107").grid(row=0, column=2, padx=10)
        Button(self.root, text="Clear", command=self.clear, font=("times new roman", 12), bg="#607d8b", fg="white").grid(row=1, column=2, padx=10, pady=5)

        # Sales listbox (showing invoices)
        self.Sales_List = Listbox(self.root, font=("times new roman", 13), height=8)
        self.Sales_List.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.Sales_List.bind('<<ListboxSelect>>', self.get_data)

        # Bill display area (Text)
        self.bill_area = Text(self.root, font=("courier", 10), height=12, width=50)
        self.bill_area.grid(row=3, column=0, columnspan=3, padx=10, pady=10)

        self.bill_photo = None  # for photo of bill

        # populate some dummy sales
        self.blll_list.append({
            "invoice": "INV-001",
            "date": "01/01/2024",
            "customer": "John Doe",
            "items": [("Laptop", 1, 50000)],
            "total": 50000
        })
        self.show()

    def clear(self):
        self.var_invoice.set("")
        self.bill_area.delete("1.0", END)

    def get_data(self, ev):
        selected = self.Sales_List.curselection()
        if selected:
            index = selected[0]
            invoice = self.Sales_List.get(index).split()[0]  # assume format "INV-001"
            self.var_invoice.set(invoice)
            # find and display bill
            for sale in self.blll_list:
                if sale["invoice"] == invoice:
                    self.display_bill(sale)
                    break

    def search(self):
        inv = self.var_invoice.get().strip()
        if inv == "":
            return
        for sale in self.blll_list:
            if sale["invoice"] == inv:
                self.display_bill(sale)
                return
        messagebox.showerror("Error", "Invoice not found", parent=self.root)

    def show(self):
        self.Sales_List.delete(0, END)
        for sale in self.blll_list:
            self.Sales_List.insert(END, f"{sale['invoice']} : {sale['customer']} - {sale['date']}")

    def display_bill(self, sale):
        self.bill_area.delete("1.0", END)
        self.bill_area.insert(END, f"Invoice: {sale['invoice']}\n")
        self.bill_area.insert(END, f"Date: {sale['date']}\n")
        self.bill_area.insert(END, f"Customer: {sale['customer']}\n")
        self.bill_area.insert(END, "-"*40 + "\n")
        total = 0
        for item in sale['items']:
            self.bill_area.insert(END, f"{item[0]:<20} {item[1]:>3} x {item[2]:>8}\n")
            total += item[1] * item[2]
        self.bill_area.insert(END, "-"*40 + "\n")
        self.bill_area.insert(END, f"Total: {total}\n")


class billClass:
    def __init__(self, root=None):
        # This class is used to generate bills, might be opened from sales or product window.
        # For simplicity, we'll implement it as a standalone window with cart and billing.
        if root is None:
            self.root = Toplevel()
        else:
            self.root = root
        self.root.title("Billing")
        self.root.geometry("1000x700")
        self.root.config(bg="white")

        # Variables
        self.var_pid = StringVar()
        self.var_pname = StringVar()
        self.var_price = StringVar()
        self.var_qty = StringVar()
        self.var_stock = StringVar()
        self.var_cname = StringVar()
        self.var_contact = StringVar()
        self.var_search = StringVar()
        self.var_cal_input = StringVar()

        self.cart_list = []
        self.bill_amnt = 0
        self.chk_print = 0
        self.discount = 0
        self.siscount = 0  # note misspelling in spec
        self.net_pay = 0.0

        self.icon_title = None

        # Layout: top, middle, bottom
        self.bill_top()
        self.bill_middle()
        self.bill_bottom()
        self.update_date_time()
        self.show()
        self.show_cart()

    def bill_top(self):
        top_frame = Frame(self.root, bg="#020a33", bd=5, relief=GROOVE)
        top_frame.pack(fill=X)

        self.lbl_clock = Label(top_frame, text="", font=("times new roman", 15), bg="#020a33", fg="white")
        self.lbl_clock.pack(side=LEFT, padx=20, pady=5)

        self.cartTitle = Label(top_frame, text="Cart", font=("times new roman", 20, "bold"), bg="#020a33", fg="white")
        self.cartTitle.pack(side=LEFT, padx=50)

        # Customer info
        cus_frame = Frame(top_frame, bg="#020a33")
        cus_frame.pack(side=RIGHT, padx=20)
        Label(cus_frame, text="Customer:", font=("times new roman", 12), bg="#020a33", fg="white").grid(row=0, column=0)
        Entry(cus_frame, textvariable=self.var_cname, font=("times new roman", 12), width=15).grid(row=0, column=1, padx=5)
        Label(cus_frame, text="Contact:", font=("times new roman", 12), bg="#020a33", fg="white").grid(row=0, column=2)
        Entry(cus_frame, textvariable=self.var_contact, font=("times new roman", 12), width=15).grid(row=0, column=3, padx=5)

    def bill_middle(self):
        middle_frame = Frame(self.root, bg="white")
        middle_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)

        # Product Search & Add Section
        left_frame = Frame(middle_frame, bg="white", bd=2, relief=RIDGE)
        left_frame.pack(side=LEFT, fill=Y, padx=5)

        Label(left_frame, text="Product ID/Name", font=("times new roman", 12), bg="white").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        Entry(left_frame, textvariable=self.var_search, font=("times new roman", 12), width=15).grid(row=0, column=1, padx=5)
        Button(left_frame, text="Search", command=self.search, font=("times new roman", 10), bg="#FFC107").grid(row=0, column=2, padx=5)

        # Product details display (Treeview for available products)
        self.product_Table = ttk.Treeview(left_frame, columns=("pid","pname","price","stock"), show='headings', height=8)
        self.product_Table.heading("pid", text="PID")
        self.product_Table.heading("pname", text="Name")
        self.product_Table.heading("price", text="Price")
        self.product_Table.heading("stock", text="Stock")
        self.product_Table.column("pid", width=60)
        self.product_Table.grid(row=1, column=0, columnspan=3, padx=5, pady=5)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)

        # Add to cart frame
        add_frame = Frame(left_frame, bg="white")
        add_frame.grid(row=2, column=0, columnspan=3, pady=5)
        Label(add_frame, text="Qty", font=("times new roman", 12), bg="white").pack(side=LEFT, padx=5)
        Entry(add_frame, textvariable=self.var_qty, font=("times new roman", 12), width=5).pack(side=LEFT)
        Button(add_frame, text="Add to Cart", command=self.add_update_cart, bg="#4CAF50", fg="white").pack(side=LEFT, padx=10)

        # Cart Table (right side)
        right_frame = Frame(middle_frame, bg="white", bd=2, relief=RIDGE)
        right_frame.pack(side=RIGHT, fill=Y, padx=5)

        self.CartTable = ttk.Treeview(right_frame, columns=("pid","pname","price","qty","total"), show='headings', height=10)
        self.CartTable.heading("pid", text="PID")
        self.CartTable.heading("pname", text="Name")
        self.CartTable.heading("price", text="Price")
        self.CartTable.heading("qty", text="Qty")
        self.CartTable.heading("total", text="Total")
        self.CartTable.column("pid", width=60)
        self.CartTable.pack(fill=BOTH, expand=True)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        # Buttons below cart
        cart_btn_frame = Frame(right_frame, bg="white")
        cart_btn_frame.pack(pady=5)
        Button(cart_btn_frame, text="Clear Cart", command=self.clear_cart, bg="#f44336", fg="white").pack(side=LEFT, padx=5)
        Button(cart_btn_frame, text="Generate Bill", command=self.generate_bill, bg="#2196F3", fg="white").pack(side=LEFT, padx=5)

    def bill_bottom(self):
        bottom_frame = Frame(self.root, bg="white", bd=2, relief=GROOVE)
        bottom_frame.pack(fill=X, padx=10, pady=5)

        # Bill display area
        self.txt_bill_area = Text(bottom_frame, width=60, height=10, font=("courier", 10))
        self.txt_bill_area.pack(side=LEFT, padx=5)

        # Calculator and total section
        right_bottom = Frame(bottom_frame, bg="white")
        right_bottom.pack(side=RIGHT, padx=5)
        self.lbl_amnt = Label(right_bottom, text="", font=("times new roman", 15), bg="white")
        self.lbl_amnt.pack()
        self.lbl_discount = Label(right_bottom, text="Discount: 0", font=("times new roman", 12), bg="white")
        self.lbl_discount.pack()
        self.lbl_net_pay = Label(right_bottom, text="Net Pay: 0", font=("times new roman", 15, "bold"), bg="white")
        self.lbl_net_pay.pack()
        self.lbl_inStock = Label(right_bottom, text="", font=("times new roman", 12), bg="white", fg="red")
        self.lbl_inStock.pack()

        # Calculator input and buttons
        calc_frame = Frame(right_bottom, bg="white")
        calc_frame.pack(pady=10)
        self.txt_cal_input = Entry(calc_frame, textvariable=self.var_cal_input, font=("times new roman", 12), width=15)
        self.txt_cal_input.grid(row=0, column=0, columnspan=4, pady=5)
        buttons = ['7','8','9','+','4','5','6','-','1','2','3','*','C','0','=','/']
        row=1; col=0
        for btn in buttons:
            Button(calc_frame, text=btn, width=3, command=lambda b=btn: self.get_input(b) if b!="=" else self.perform_cal()).grid(row=row, column=col, padx=2, pady=2)
            col += 1
            if col>3:
                col=0
                row+=1

    def add_update_cart(self):
        pid = self.var_pid.get()
        pname = self.var_pname.get()
        price = self.var_price.get()
        qty = self.var_qty.get()
        stock_str = self.var_stock.get()

        if pid == "" or qty == "":
            messagebox.showerror("Error", "Select product and enter quantity", parent=self.root)
            return
        try:
            price_val = float(price)
            qty_val = int(qty)
            stock_val = int(stock_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid numeric values", parent=self.root)
            return

        if qty_val <= 0:
            messagebox.showerror("Error", "Quantity must be >0", parent=self.root)
            return
        if qty_val > stock_val:
            messagebox.showerror("Error", f"Insufficient stock! Available: {stock_val}", parent=self.root)
            return

        # Check if product already in cart
        for item in self.cart_list:
            if item['pid'] == pid:
                # update qty and total
                new_qty = item['qty'] + qty_val
                if new_qty > stock_val:
                    messagebox.showerror("Error", "Total cart qty exceeds stock", parent=self.root)
                    return
                item['qty'] = new_qty
                item['total'] = new_qty * price_val
                self.show_cart()
                self.bill_update()
                return

        # add new item
        self.cart_list.append({
            'pid': pid,
            'pname': pname,
            'price': price_val,
            'qty': qty_val,
            'total': qty_val * price_val
        })
        self.show_cart()
        self.bill_update()

    def bill_update(self):
        self.bill_amnt = sum(item['total'] for item in self.cart_list)
        # apply discount if any (for now fixed discount)
        self.discount = 0  # could be computed
        self.net_pay = self.bill_amnt - self.discount
        self.lbl_amnt.config(text=f"Bill Amount: {self.bill_amnt}")
        self.lbl_discount.config(text=f"Discount: {self.discount}")
        self.lbl_net_pay.config(text=f"Net Pay: {self.net_pay}")

    def clear_all(self):
        self.clear_cart()
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")
        self.var_cname.set("")
        self.var_contact.set("")
        self.txt_bill_area.delete("1.0", END)

    def clear_cal(self):
        self.var_cal_input.set("")

    def clear_cart(self):
        self.cart_list = []
        self.show_cart()
        self.bill_update()

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty", parent=self.root)
            return
        # Generate invoice number
        inv = "INV-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        # Build bill text
        bill_lines = []
        bill_lines.append(f"Invoice: {inv}")
        bill_lines.append(f"Date: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        bill_lines.append(f"Customer: {self.var_cname.get()}  Contact: {self.var_contact.get()}")
        bill_lines.append("-"*40)
        for item in self.cart_list:
            line = f"{item['pid']}: {item['pname'][:15]:<15} Qty:{item['qty']:>3} × {item['price']:>8} = {item['total']:>10}"
            bill_lines.append(line)
        bill_lines.append("-"*40)
        bill_lines.append(f"Total: {self.bill_amnt}")
        bill_lines.append(f"Discount: {self.discount}")
        bill_lines.append(f"Net Pay: {self.net_pay}")
        self.txt_bill_area.delete("1.0", END)
        self.txt_bill_area.insert(END, "\n".join(bill_lines))

        # For sales history
        sales_data = {
            "invoice": inv,
            "date": datetime.datetime.now().strftime("%d/%m/%Y"),
            "customer": self.var_cname.get(),
            "items": [(item['pname'], item['qty'], item['price']) for item in self.cart_list],
            "total": self.net_pay
        }
        # Ideally would store globally; for simplicity we can place in a global list if needed, but spec doesn't require.
        self.clear_cart()

    def get_data(self, ev):
        selected = self.product_Table.selection()
        if selected:
            item = self.product_Table.item(selected)
            vals = item['values']
            self.var_pid.set(vals[0])
            self.var_pname.set(vals[1])
            self.var_price.set(vals[2])
            self.var_stock.set(vals[3])

    def get_data_cart(self, ev):
        selected = self.CartTable.selection()
        if selected:
            item = self.CartTable.item(selected)
            vals = item['values']
            # populate entries for update? Not needed but could be
            self.var_pid.set(vals[0])
            self.var_pname.set(vals[1])
            self.var_price.set(vals[2])
            self.var_qty.set(vals[3])

    def get_input(self, num):
        if num == "C":
            self.clear_cal()
        else:
            current = self.var_cal_input.get()
            self.var_cal_input.set(current + num)

    def perform_cal(self):
        try:
            result = eval(self.var_cal_input.get())
            self.var_cal_input.set(result)
        except Exception as e:
            messagebox.showerror("Error", "Invalid calculation", parent=self.root)

    def print_bill(self):
        # Not implemented, could use printing library
        pass

    def search(self):
        search_txt = self.var_search.get().lower()
        # Simulated product search from global product list
        # For demonstration, we'll use the product list from productClass if accessible; but here we'll use dummy
        dummy_products = [("P001", "Laptop", "50000", "10"), ("P002", "Shirt", "1000", "50")]
        self.product_Table.delete(*self.product_Table.get_children())
        for prod in dummy_products:
            if search_txt in prod[0].lower() or search_txt in prod[1].lower():
                self.product_Table.insert("", END, values=prod)

    def show(self):
        # could refresh product table
        pass

    def show_cart(self):
        self.CartTable.delete(*self.CartTable.get_children())
        for item in self.cart_list:
            self.CartTable.insert("", END, values=(item['pid'], item['pname'], item['price'], item['qty'], item['total']))

    def update_date_time(self):
        now = datetime.datetime.now()
        dt = now.strftime("%d/%m/%Y %H:%M:%S")
        if hasattr(self, 'lbl_clock') and self.lbl_clock:
            self.lbl_clock.config(text=dt)
        self.root.after(1000, self.update_date_time)


# Main execution
if __name__ == "__main__":
    root = Tk()
    obj = IMS(root)
    root.mainloop()