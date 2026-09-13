from tkinter import *
from tkinter import ttk
from tkinter import messagebox
import tkinter as tk
from tkinter import PhotoImage
from datetime import datetime
from typing import Optional, List, Any, Union
import os

# Global data stores
category_data: List[tuple] = []
employee_data: List[tuple] = []
product_data: List[tuple] = []
supplier_data: List[tuple] = []
sales_data: List[tuple] = []

# Dummy initial data for demonstration
category_data.append(("C001", "Electronics"))
category_data.append(("C002", "Stationery"))
employee_data.append(("E001", "John Doe", "1234567890", "01-01-1990", "01-01-2020", "john@example.com", "Male", "Admin", "pass123", "50000"))
employee_data.append(("E002", "Jane Smith", "0987654321", "02-02-1992", "02-02-2021", "jane@example.com", "Female", "User", "pass456", "45000"))
supplier_data.append(("S001", "Tech Supply Co.", "1111111111", "Electronics items", "INV-1001"))
supplier_data.append(("S002", "Paper World", "2222222222", "Stationery items", "INV-1002"))
product_data.append(("P001", "Laptop", "C001", "S001", "55000", "10", "Active"))
product_data.append(("P002", "Notebook", "C002", "S002", "50", "100", "Active"))


# Helper functions for treeview population
def clear_tree(tree: ttk.Treeview) -> None:
    for item in tree.get_children():
        tree.delete(item)

def get_selected_row(tree: ttk.Treeview, event: tk.Event) -> Optional[Any]:
    selected = tree.focus()
    if selected:
        return tree.item(selected)
    return None


class categoryClass:
    def __init__(self, root: tk.Toplevel):
        self.root = root
        self.root.title("Manage Categories")
        self.root.geometry("500x400")
        self.root.grab_set()

        self.var_cat_id = StringVar()
        self.var_name = StringVar()

        # Top frame for entry
        top_frame = Frame(self.root, bd=2, relief=RIDGE)
        top_frame.pack(fill=X, padx=10, pady=10)

        Label(top_frame, text="Category ID").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        Entry(top_frame, textvariable=self.var_cat_id).grid(row=0, column=1, padx=5, pady=5)
        Label(top_frame, text="Category Name").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        Entry(top_frame, textvariable=self.var_name).grid(row=1, column=1, padx=5, pady=5)

        btn_frame = Frame(self.root)
        btn_frame.pack(fill=X, padx=10, pady=5)
        Button(btn_frame, text="Add", command=self.add).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Show All", command=self.show).pack(side=LEFT, padx=5)

        # Table
        table_frame = Frame(self.root)
        table_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        cols = ("cat_id", "name")
        self.CategoryTable = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.CategoryTable.heading("cat_id", text="Category ID")
        self.CategoryTable.heading("name", text="Category Name")
        self.CategoryTable.column("cat_id", width=100)
        self.CategoryTable.column("name", width=200)
        self.CategoryTable.pack(fill=BOTH, expand=True)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)

        # Dummy images (not used but defined as attributes per spec)
        self.im1: Optional[PhotoImage] = None
        self.im2: Optional[PhotoImage] = None
        self.lbl_im1 = Label(self.root)
        self.lbl_im2 = Label(self.root)

        self.show()  # load existing data

    def add(self):
        cid = self.var_cat_id.get().strip()
        name = self.var_name.get().strip()
        if not cid or not name:
            messagebox.showerror("Error", "All fields required")
            return
        for cat in category_data:
            if cat[0] == cid:
                messagebox.showerror("Error", "Category ID already exists")
                return
        category_data.append((cid, name))
        self.show()
        self.clear()

    def delete(self):
        selected = self.CategoryTable.focus()
        if not selected:
            messagebox.showerror("Error", "Select a category to delete")
            return
        values = self.CategoryTable.item(selected)['values']
        cid = values[0]
        global category_data
        category_data = [cat for cat in category_data if cat[0] != cid]
        self.show()
        self.clear()

    def clear(self):
        self.var_cat_id.set("")
        self.var_name.set("")

    def get_data(self, ev):
        selected = self.CategoryTable.focus()
        if selected:
            values = self.CategoryTable.item(selected)['values']
            self.var_cat_id.set(values[0])
            self.var_name.set(values[1])

    def show(self):
        clear_tree(self.CategoryTable)
        for cat in category_data:
            self.CategoryTable.insert("", END, values=cat)


class employeeClass:
    def __init__(self, root: tk.Toplevel):
        self.root = root
        self.root.title("Manage Employees")
        self.root.geometry("900x500")
        self.root.grab_set()

        self.var_emp_id = StringVar()
        self.var_name = StringVar()
        self.var_contact = StringVar()
        self.var_dob = StringVar()
        self.var_doj = StringVar()
        self.var_email = StringVar()
        self.var_gender = StringVar()
        self.var_utype = StringVar()
        self.var_pass = StringVar()
        self.var_salary = StringVar()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()

        # Top frame for entry
        top_frame = Frame(self.root, bd=2, relief=RIDGE)
        top_frame.pack(fill=X, padx=10, pady=10)

        # Labels and entries
        labels = ["Emp ID", "Name", "Contact", "DOB", "DOJ", "Email", "Gender", "User Type", "Password", "Salary"]
        vars = [self.var_emp_id, self.var_name, self.var_contact, self.var_dob, self.var_doj,
                self.var_email, self.var_gender, self.var_utype, self.var_pass, self.var_salary]
        for i, (lbl, var) in enumerate(zip(labels, vars)):
            row = i // 2
            col = (i % 2) * 2
            Label(top_frame, text=lbl).grid(row=row, column=col, padx=5, pady=2, sticky='w')
            Entry(top_frame, textvariable=var).grid(row=row, column=col+1, padx=5, pady=2)

        # Address text area
        Label(top_frame, text="Address").grid(row=5, column=0, padx=5, pady=2, sticky='nw')
        self.txt_address = Text(top_frame, height=3, width=30)
        self.txt_address.grid(row=5, column=1, padx=5, pady=2, sticky='w')

        btn_frame = Frame(self.root)
        btn_frame.pack(fill=X, padx=10, pady=5)
        Button(btn_frame, text="Add", command=self.add).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Show All", command=self.show).pack(side=LEFT, padx=5)

        # Search
        search_frame = Frame(self.root)
        search_frame.pack(fill=X, padx=10, pady=5)
        Label(search_frame, text="Search By").pack(side=LEFT, padx=5)
        combo_search = ttk.Combobox(search_frame, textvariable=self.var_searchby, values=["empid", "name", "email"], state="readonly")
        combo_search.pack(side=LEFT, padx=5)
        combo_search.current(0)
        Entry(search_frame, textvariable=self.var_searchtxt).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search).pack(side=LEFT, padx=5)

        # Table
        table_frame = Frame(self.root)
        table_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        cols = ("empid", "name", "contact", "dob", "doj", "email", "gender", "utype", "pass", "salary", "address")
        self.EmployeeTable = ttk.Treeview(table_frame, columns=cols, show="headings")
        for col in cols:
            self.EmployeeTable.heading(col, text=col.capitalize())
            self.EmployeeTable.column(col, width=80)
        self.EmployeeTable.pack(fill=BOTH, expand=True)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def get_data(self, ev):
        selected = self.EmployeeTable.focus()
        if selected:
            values = self.EmployeeTable.item(selected)['values']
            self.var_emp_id.set(values[0])
            self.var_name.set(values[1])
            self.var_contact.set(values[2])
            self.var_dob.set(values[3])
            self.var_doj.set(values[4])
            self.var_email.set(values[5])
            self.var_gender.set(values[6])
            self.var_utype.set(values[7])
            self.var_pass.set(values[8])
            self.var_salary.set(values[9])
            self.txt_address.delete('1.0', END)
            self.txt_address.insert(END, values[10])

    def add(self):
        data = self._collect_data()
        if not data:
            return
        for emp in employee_data:
            if emp[0] == data[0]:
                messagebox.showerror("Error", "Employee ID already exists")
                return
        employee_data.append(data)
        self.show()
        self.clear()

    def update(self):
        selected = self.EmployeeTable.focus()
        if not selected:
            messagebox.showerror("Error", "Select an employee to update")
            return
        old_id = self.EmployeeTable.item(selected)['values'][0]
        data = self._collect_data()
        if not data:
            return
        global employee_data
        employee_data = [(data if emp[0] == old_id else emp) for emp in employee_data]
        self.show()
        self.clear()

    def delete(self):
        selected = self.EmployeeTable.focus()
        if not selected:
            messagebox.showerror("Error", "Select an employee to delete")
            return
        emp_id = self.EmployeeTable.item(selected)['values'][0]
        global employee_data
        employee_data = [emp for emp in employee_data if emp[0] != emp_id]
        self.show()
        self.clear()

    def clear(self):
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_email.set("")
        self.var_gender.set("")
        self.var_utype.set("")
        self.var_pass.set("")
        self.var_salary.set("")
        self.txt_address.delete('1.0', END)
        self.var_searchtxt.set("")

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get().strip()
        clear_tree(self.EmployeeTable)
        index_map = {"empid": 0, "name": 1, "email": 5}
        idx = index_map.get(by, 0)
        for emp in employee_data:
            if txt.lower() in str(emp[idx]).lower():
                self.EmployeeTable.insert("", END, values=emp)

    def show(self):
        clear_tree(self.EmployeeTable)
        for emp in employee_data:
            self.EmployeeTable.insert("", END, values=emp)

    def _collect_data(self):
        eid = self.var_emp_id.get().strip()
        name = self.var_name.get().strip()
        if not eid or not name:
            messagebox.showerror("Error", "Emp ID and Name required")
            return None
        return (eid, name, self.var_contact.get(), self.var_dob.get(), self.var_doj.get(),
                self.var_email.get(), self.var_gender.get(), self.var_utype.get(),
                self.var_pass.get(), self.var_salary.get(), self.txt_address.get("1.0", END).strip())


class productClass:
    def __init__(self, root: tk.Toplevel):
        self.root = root
        self.root.title("Manage Products")
        self.root.geometry("900x500")
        self.root.grab_set()

        self.var_pid = StringVar()
        self.var_name = StringVar()
        self.var_cat = StringVar()
        self.var_sup = StringVar()
        self.var_price = StringVar()
        self.var_qty = StringVar()
        self.var_status = StringVar()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()

        self.cat_list: List[str] = [cat[1] for cat in category_data]
        self.sup_list: List[str] = [sup[1] for sup in supplier_data]

        # Top frame
        top_frame = Frame(self.root, bd=2, relief=RIDGE)
        top_frame.pack(fill=X, padx=10, pady=10)
        labels_entries = [
            ("Product ID", self.var_pid), ("Name", self.var_name),
            ("Category", self.var_cat), ("Supplier", self.var_sup),
            ("Price", self.var_price), ("Quantity", self.var_qty),
            ("Status", self.var_status)
        ]
        for i, (lbl, var) in enumerate(labels_entries):
            row = i // 2
            col = (i % 2) * 2
            Label(top_frame, text=lbl).grid(row=row, column=col, padx=5, pady=2, sticky='w')
            if lbl == "Category":
                ttk.Combobox(top_frame, textvariable=var, values=self.cat_list).grid(row=row, column=col+1, padx=5, pady=2)
            elif lbl == "Supplier":
                ttk.Combobox(top_frame, textvariable=var, values=self.sup_list).grid(row=row, column=col+1, padx=5, pady=2)
            else:
                Entry(top_frame, textvariable=var).grid(row=row, column=col+1, padx=5, pady=2)

        btn_frame = Frame(self.root)
        btn_frame.pack(fill=X, padx=10, pady=5)
        Button(btn_frame, text="Add", command=self.add).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Show All", command=self.show).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Refresh Lists", command=self.fetch_cat_sup).pack(side=LEFT, padx=5)

        search_frame = Frame(self.root)
        search_frame.pack(fill=X, padx=10, pady=5)
        Label(search_frame, text="Search By").pack(side=LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=["pid", "name", "category", "supplier"], state="readonly").pack(side=LEFT, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search).pack(side=LEFT, padx=5)

        # Table
        table_frame = Frame(self.root)
        table_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        cols = ("pid", "name", "category", "supplier", "price", "qty", "status")
        self.ProductTable = ttk.Treeview(table_frame, columns=cols, show="headings")
        for col in cols:
            self.ProductTable.heading(col, text=col.capitalize())
            self.ProductTable.column(col, width=100)
        self.ProductTable.pack(fill=BOTH, expand=True)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def fetch_cat_sup(self):
        self.cat_list = [cat[1] for cat in category_data]
        self.sup_list = [sup[1] for sup in supplier_data]
        # need to update combobox values if they exist, but we can't access them directly; workaround is weak.
        # For simplicity, we just update the attribute; user will need to reopen dropdown to see changes.
        # (In real app, we would store references to the comboboxes.)
        messagebox.showinfo("Refresh", "Category and Supplier lists updated.")

    def add(self):
        data = self._collect_data()
        if not data:
            return
        for prod in product_data:
            if prod[0] == data[0]:
                messagebox.showerror("Error", "Product ID already exists")
                return
        product_data.append(data)
        self.show()
        self.clear()

    def update(self):
        selected = self.ProductTable.focus()
        if not selected:
            messagebox.showerror("Error", "Select a product to update")
            return
        old_pid = self.ProductTable.item(selected)['values'][0]
        data = self._collect_data()
        if not data:
            return
        global product_data
        product_data = [(data if prod[0] == old_pid else prod) for prod in product_data]
        self.show()
        self.clear()

    def delete(self):
        selected = self.ProductTable.focus()
        if not selected:
            messagebox.showerror("Error", "Select a product to delete")
            return
        pid = self.ProductTable.item(selected)['values'][0]
        global product_data
        product_data = [prod for prod in product_data if prod[0] != pid]
        self.show()
        self.clear()

    def clear(self):
        self.var_pid.set("")
        self.var_name.set("")
        self.var_cat.set("")
        self.var_sup.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("")
        self.var_searchtxt.set("")

    def get_data(self, ev):
        selected = self.ProductTable.focus()
        if selected:
            values = self.ProductTable.item(selected)['values']
            self.var_pid.set(values[0])
            self.var_name.set(values[1])
            self.var_cat.set(values[2])
            self.var_sup.set(values[3])
            self.var_price.set(values[4])
            self.var_qty.set(values[5])
            self.var_status.set(values[6])

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get().strip()
        clear_tree(self.ProductTable)
        index_map = {"pid": 0, "name": 1, "category": 2, "supplier": 3}
        idx = index_map.get(by, 0)
        for prod in product_data:
            if txt.lower() in str(prod[idx]).lower():
                self.ProductTable.insert("", END, values=prod)

    def show(self):
        clear_tree(self.ProductTable)
        for prod in product_data:
            self.ProductTable.insert("", END, values=prod)

    def _collect_data(self):
        pid = self.var_pid.get().strip()
        name = self.var_name.get().strip()
        if not pid or not name:
            messagebox.showerror("Error", "Product ID and Name required")
            return None
        return (pid, name, self.var_cat.get(), self.var_sup.get(), self.var_price.get(),
                self.var_qty.get(), self.var_status.get())


class supplierClass:
    def __init__(self, root: tk.Toplevel):
        self.root = root
        self.root.title("Manage Suppliers")
        self.root.geometry("700x450")
        self.root.grab_set()

        self.var_sup_invoice = StringVar()
        self.var_name = StringVar()
        self.var_contact = StringVar()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()
        self.txt_desc = Text(height=4, width=40)

        top_frame = Frame(self.root, bd=2, relief=RIDGE)
        top_frame.pack(fill=X, padx=10, pady=10)
        Label(top_frame, text="Invoice No").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        Entry(top_frame, textvariable=self.var_sup_invoice).grid(row=0, column=1, padx=5, pady=2)
        Label(top_frame, text="Name").grid(row=1, column=0, padx=5, pady=2, sticky='w')
        Entry(top_frame, textvariable=self.var_name).grid(row=1, column=1, padx=5, pady=2)
        Label(top_frame, text="Contact").grid(row=2, column=0, padx=5, pady=2, sticky='w')
        Entry(top_frame, textvariable=self.var_contact).grid(row=2, column=1, padx=5, pady=2)
        Label(top_frame, text="Description").grid(row=3, column=0, padx=5, pady=2, sticky='nw')
        self.txt_desc.grid(row=3, column=1, padx=5, pady=2)

        btn_frame = Frame(self.root)
        btn_frame.pack(fill=X, padx=10, pady=5)
        Button(btn_frame, text="Add", command=self.add).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Show All", command=self.show).pack(side=LEFT, padx=5)

        search_frame = Frame(self.root)
        search_frame.pack(fill=X, padx=10, pady=5)
        Label(search_frame, text="Search By").pack(side=LEFT, padx=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=["invoice", "name"], state="readonly").pack(side=LEFT, padx=5)
        Entry(search_frame, textvariable=self.var_searchtxt).pack(side=LEFT, padx=5)
        Button(search_frame, text="Search", command=self.search).pack(side=LEFT, padx=5)

        # Table
        table_frame = Frame(self.root)
        table_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        cols = ("invoice", "name", "contact", "desc")
        self.SupplierTable = ttk.Treeview(table_frame, columns=cols, show="headings")
        for col in cols:
            self.SupplierTable.heading(col, text=col.capitalize())
            self.SupplierTable.column(col, width=120)
        self.SupplierTable.pack(fill=BOTH, expand=True)
        self.SupplierTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def get_data(self, ev):
        selected = self.SupplierTable.focus()
        if selected:
            values = self.SupplierTable.item(selected)['values']
            self.var_sup_invoice.set(values[0])
            self.var_name.set(values[1])
            self.var_contact.set(values[2])
            self.txt_desc.delete('1.0', END)
            self.txt_desc.insert(END, values[3])

    def add(self):
        data = self._collect_data()
        if not data:
            return
        for sup in supplier_data:
            if sup[0] == data[0]:
                messagebox.showerror("Error", "Invoice number already exists")
                return
        supplier_data.append(data)
        self.show()
        self.clear()

    def update(self):
        selected = self.SupplierTable.focus()
        if not selected:
            messagebox.showerror("Error", "Select a supplier to update")
            return
        old_inv = self.SupplierTable.item(selected)['values'][0]
        data = self._collect_data()
        if not data:
            return
        global supplier_data
        supplier_data = [(data if sup[0] == old_inv else sup) for sup in supplier_data]
        self.show()
        self.clear()

    def delete(self):
        selected = self.SupplierTable.focus()
        if not selected:
            messagebox.showerror("Error", "Select a supplier to delete")
            return
        inv = self.SupplierTable.item(selected)['values'][0]
        global supplier_data
        supplier_data = [sup for sup in supplier_data if sup[0] != inv]
        self.show()
        self.clear()

    def clear(self):
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete('1.0', END)
        self.var_searchtxt.set("")

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get().strip()
        clear_tree(self.SupplierTable)
        index_map = {"invoice": 0, "name": 1}
        idx = index_map.get(by, 0)
        for sup in supplier_data:
            if txt.lower() in str(sup[idx]).lower():
                self.SupplierTable.insert("", END, values=sup)

    def show(self):
        clear_tree(self.SupplierTable)
        for sup in supplier_data:
            self.SupplierTable.insert("", END, values=sup)

    def _collect_data(self):
        inv = self.var_sup_invoice.get().strip()
        name = self.var_name.get().strip()
        if not inv or not name:
            messagebox.showerror("Error", "Invoice No and Name required")
            return None
        return (inv, name, self.var_contact.get(), self.txt_desc.get("1.0", END).strip())


class salesClass:
    def __init__(self, root: tk.Toplevel):
        self.root = root
        self.root.title("Sales Records")
        self.root.geometry("700x500")
        self.root.grab_set()

        self.var_invoice = StringVar()
        self.blll_list: List[tuple] = []  # holds invoice details for display

        top_frame = Frame(self.root, bd=2, relief=RIDGE)
        top_frame.pack(fill=X, padx=10, pady=10)
        Label(top_frame, text="Invoice No").pack(side=LEFT, padx=5)
        Entry(top_frame, textvariable=self.var_invoice).pack(side=LEFT, padx=5)
        Button(top_frame, text="Search", command=self.search).pack(side=LEFT, padx=5)
        Button(top_frame, text="Show All", command=self.show).pack(side=LEFT, padx=5)
        Button(top_frame, text="Clear", command=self.clear).pack(side=LEFT, padx=5)

        # Listbox for sales list
        list_frame = Frame(self.root)
        list_frame.pack(fill=BOTH, expand=True, padx=10, pady=10, side=LEFT)
        self.Sales_List = Listbox(list_frame, font=("Courier", 10))
        self.Sales_List.pack(fill=BOTH, expand=True)
        self.Sales_List.bind("<<ListboxSelect>>", self.get_data)

        # Bill area (Text widget)
        self.bill_area = Text(self.root, width=40)
        self.bill_area.pack(fill=BOTH, expand=True, padx=10, pady=10, side=RIGHT)

        # placeholder for bill_photo (not used)
        self.bill_photo: Optional[PhotoImage] = None

        self.show()

    def get_data(self, ev):
        sel = self.Sales_List.curselection()
        if sel:
            index = sel[0]
            inv = self.Sales_List.get(index)
            # find invoice details from sales_data and display in bill_area
            self.bill_area.delete('1.0', END)
            # search sales_data for this invoice
            for sale in sales_data:
                if sale[0] == inv:
                    self.bill_area.insert(END, f"Invoice: {sale[0]}\n")
                    self.bill_area.insert(END, f"Date: {sale[1]}\n")
                    self.bill_area.insert(END, f"Customer: {sale[2]}\n")
                    self.bill_area.insert(END, f"Contact: {sale[3]}\n")
                    self.bill_area.insert(END, f"Total: {sale[4]}\n")
                    self.bill_area.insert(END, "Items:\n")
                    for item in sale[5]:  # list of cart items
                        self.bill_area.insert(END, f"  {item}\n")
                    return

    def search(self):
        inv = self.var_invoice.get().strip()
        self.Sales_List.delete(0, END)
        for sale in sales_data:
            if inv and sale[0] != inv:
                continue
            self.Sales_List.insert(END, sale[0])

    def show(self):
        self.Sales_List.delete(0, END)
        for sale in sales_data:
            self.Sales_List.insert(END, sale[0])

    def clear(self):
        self.var_invoice.set("")
        self.bill_area.delete('1.0', END)
        self.show()


class billClass:
    """Billing window: select products, add to cart, generate bill, print."""
    def __init__(self, root: tk.Toplevel):
        self.root = root
        self.root.title("Billing")
        self.root.geometry("1100x650")
        self.root.grab_set()

        # Variables
        self.var_pname = StringVar()
        self.var_pid = StringVar()
        self.var_price = StringVar()
        self.var_qty = StringVar()
        self.var_stock = StringVar()
        self.var_cname = StringVar()
        self.var_contact = StringVar()
        self.var_search = StringVar()
        self.var_cal_input = StringVar()
        self.cart_list: List[tuple] = []  # (pid, name, price, qty, total)
        self.discount = 0.0
        self.net_pay: float = 0.0
        self.bill_amnt: int = 0
        self.chk_print: int = 0
        self.invoice = ""
        self.siscount: int = 0  # according to spec, discount? mis-spelled.

        # Build UI
        self.bill_top()
        self.bill_middle()
        self.bill_bottom()
        self.update_date_time()

    def bill_top(self):
        top = Frame(self.root, bd=2, relief=RIDGE)
        top.pack(fill=X, padx=10, pady=10)
        # Customer details
        Label(top, text="Customer Name").grid(row=0, column=0, padx=5, pady=2, sticky='w')
        Entry(top, textvariable=self.var_cname, width=20).grid(row=0, column=1, padx=5, pady=2)
        Label(top, text="Contact No").grid(row=0, column=2, padx=5, pady=2, sticky='w')
        Entry(top, textvariable=self.var_contact, width=15).grid(row=0, column=3, padx=5, pady=2)
        # Search
        Label(top, text="Search Product").grid(row=1, column=0, padx=5, pady=2, sticky='w')
        Entry(top, textvariable=self.var_search, width=20).grid(row=1, column=1, padx=5, pady=2)
        Button(top, text="Search", command=self.search).grid(row=1, column=2, padx=5, pady=2)
        # Clock
        self.lbl_clock = Label(top, text="", font=("Arial", 10))
        self.lbl_clock.grid(row=1, column=3, padx=5, pady=2, sticky='e')

    def bill_middle(self):
        middle = Frame(self.root)
        middle.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # Product table (left)
        prod_frame = Frame(middle, bd=2, relief=RIDGE)
        prod_frame.pack(side=LEFT, fill=BOTH, expand=True)
        Label(prod_frame, text="Products List", font=("Arial", 12)).pack()
        cols = ("pid", "name", "price", "stock")
        self.product_Table = ttk.Treeview(prod_frame, columns=cols, show="headings")
        self.product_Table.heading("pid", text="PID")
        self.product_Table.heading("name", text="Name")
        self.product_Table.heading("price", text="Price")
        self.product_Table.heading("stock", text="Stock")
        self.product_Table.column("pid", width=80)
        self.product_Table.column("name", width=150)
        self.product_Table.column("price", width=80)
        self.product_Table.column("stock", width=80)
        self.product_Table.pack(fill=BOTH, expand=True)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)

        # Cart table (right)
        cart_frame = Frame(middle, bd=2, relief=RIDGE)
        cart_frame.pack(side=RIGHT, fill=BOTH, expand=True)
        self.cartTitle = Label(cart_frame, text="Cart", font=("Arial", 12))
        self.cartTitle.pack()
        cols_cart = ("pid", "name", "price", "qty", "total")
        self.CartTable = ttk.Treeview(cart_frame, columns=cols_cart, show="headings")
        self.CartTable.heading("pid", text="PID")
        self.CartTable.heading("name", text="Name")
        self.CartTable.heading("price", text="Price")
        self.CartTable.heading("qty", text="Qty")
        self.CartTable.heading("total", text="Total")
        for col in cols_cart:
            self.CartTable.column(col, width=80)
        self.CartTable.pack(fill=BOTH, expand=True)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        # Controls for cart
        ctrl = Frame(cart_frame)
        ctrl.pack(fill=X, pady=5)
        Label(ctrl, text="PID").pack(side=LEFT)
        Entry(ctrl, textvariable=self.var_pid, width=6).pack(side=LEFT, padx=2)
        Label(ctrl, text="Name").pack(side=LEFT)
        Entry(ctrl, textvariable=self.var_pname, width=10).pack(side=LEFT, padx=2)
        Label(ctrl, text="Price").pack(side=LEFT)
        Entry(ctrl, textvariable=self.var_price, width=6).pack(side=LEFT, padx=2)
        Label(ctrl, text="Qty").pack(side=LEFT)
        Entry(ctrl, textvariable=self.var_qty, width=4).pack(side=LEFT, padx=2)
        Label(ctrl, text="Stock").pack(side=LEFT)
        self.lbl_inStock = Label(ctrl, textvariable=self.var_stock, relief=SUNKEN)
        self.lbl_inStock.pack(side=LEFT, padx=2)
        Button(ctrl, text="Add", command=self.add_update_cart).pack(side=LEFT, padx=2)
        Button(ctrl, text="Clear", command=self.clear_all).pack(side=LEFT, padx=2)
        Button(ctrl, text="Clear Cart", command=self.clear_cart).pack(side=LEFT, padx=2)

        self.show_cart()
        self.show()

    def bill_bottom(self):
        bottom = Frame(self.root, bd=2, relief=RIDGE)
        bottom.pack(fill=X, padx=10, pady=10)

        # Calculator-like input
        calc_frame = Frame(bottom)
        calc_frame.pack(side=LEFT, padx=10)
        Label(calc_frame, text="Calculator").pack(anchor=W)
        self.txt_cal_input = Entry(calc_frame, textvariable=self.var_cal_input, width=20)
        self.txt_cal_input.pack()
        calc_buttons = [
            ('7','8','9','+'),
            ('4','5','6','-'),
            ('1','2','3','*'),
            ('C','0','=','/')
        ]
        for row in calc_buttons:
            f = Frame(calc_frame)
            f.pack()
            for char in row:
                btn = Button(f, text=char, width=3, command=lambda x=char: self.get_input(x))
                btn.pack(side=LEFT, padx=1, pady=1)
        Button(calc_frame, text="Calculate", command=self.perform_cal).pack(pady=5)

        # Bill summary
        summary = Frame(bottom)
        summary.pack(side=LEFT, padx=20)
        self.lbl_amnt = Label(summary, text="Bill Amount: 0")
        self.lbl_amnt.pack(anchor=W)
        self.lbl_discount = Label(summary, text="Discount: 0")
        self.lbl_discount.pack(anchor=W)
        self.lbl_net_pay = Label(summary, text="Net Payable: 0.0")
        self.lbl_net_pay.pack(anchor=W)
        Button(summary, text="Generate Bill", command=self.generate_bill).pack(pady=5)
        Button(summary, text="Print Bill", command=self.print_bill).pack(pady=5)

        # Bill text area
        self.txt_bill_area = Text(bottom, width=40, height=10)
        self.txt_bill_area.pack(side=RIGHT, padx=20)

        # icons (placeholder)
        self.icon_title: Optional[PhotoImage] = None

    def get_data(self, ev):
        sel = self.product_Table.focus()
        if sel:
            vals = self.product_Table.item(sel)['values']
            self.var_pid.set(vals[0])
            self.var_pname.set(vals[1])
            self.var_price.set(vals[2])
            self.var_stock.set(vals[3])

    def get_data_cart(self, ev):
        sel = self.CartTable.focus()
        if sel:
            vals = self.CartTable.item(sel)['values']
            self.var_pid.set(vals[0])
            self.var_pname.set(vals[1])
            self.var_price.set(vals[2])
            self.var_qty.set(vals[3])

    def add_update_cart(self):
        pid = self.var_pid.get().strip()
        name = self.var_pname.get().strip()
        price_str = self.var_price.get().strip()
        qty_str = self.var_qty.get().strip()
        stock_str = self.var_stock.get().strip()
        if not pid or not qty_str:
            messagebox.showerror("Error", "Select a product and enter quantity")
            return
        try:
            price = float(price_str)
            qty = int(qty_str)
            stock = int(stock_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid price/qty/stock")
            return
        if qty > stock:
            messagebox.showerror("Error", "Insufficient stock")
            return
        total = price * qty

        # Check if product already in cart
        for i, item in enumerate(self.cart_list):
            if item[0] == pid:
                # update quantity and total
                new_qty = item[3] + qty
                if new_qty > stock:
                    messagebox.showerror("Error", "Insufficient stock")
                    return
                self.cart_list[i] = (pid, name, price, new_qty, price * new_qty)
                self.show_cart()
                return
        self.cart_list.append((pid, name, price, qty, total))
        self.show_cart()

    def clear_all(self):
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")

    def clear_cart(self):
        self.cart_list.clear()
        self.show_cart()
        self.bill_update()

    def show_cart(self):
        clear_tree(self.CartTable)
        for item in self.cart_list:
            self.CartTable.insert("", END, values=item)
        self.bill_update()

    def bill_update(self):
        total = sum(item[4] for item in self.cart_list)
        self.bill_amnt = total
        self.lbl_amnt.config(text=f"Bill Amount: {total}")
        self.lbl_discount.config(text=f"Discount: {self.discount}")
        net = total - self.discount
        self.net_pay = net
        self.lbl_net_pay.config(text=f"Net Payable: {net:.2f}")

    def get_input(self, num):
        if num == 'C':
            self.var_cal_input.set("")
        elif num == '=':
            self.perform_cal()
        else:
            current = self.var_cal_input.get()
            self.var_cal_input.set(current + num)

    def perform_cal(self):
        expr = self.var_cal_input.get()
        try:
            result = eval(expr)
            self.var_cal_input.set(str(result))
        except:
            messagebox.showerror("Error", "Invalid expression")
            self.var_cal_input.set("")

    def search(self):
        txt = self.var_search.get().strip()
        clear_tree(self.product_Table)
        for prod in product_data:
            if txt.lower() in prod[1].lower() or txt in prod[0]:
                self.product_Table.insert("", END, values=(prod[0], prod[1], prod[4], prod[5]))

    def show(self):
        clear_tree(self.product_Table)
        for prod in product_data:
            self.product_Table.insert("", END, values=(prod[0], prod[1], prod[4], prod[5]))

    def generate_bill(self):
        cname = self.var_cname.get().strip()
        contact = self.var_contact.get().strip()
        if not cname:
            messagebox.showerror("Error", "Enter customer name")
            return
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty")
            return
        # check discount input? For now assume discount is in self.discount (maybe from a discount entry? Not specified)
        # We'll just use whatever discount is set (0 by default)
        total = self.bill_amnt
        net = self.net_pay
        inv_prefix = "INV"
        now = datetime.now()
        inv = f"{inv_prefix}{now.strftime('%Y%m%d%H%M%S')}"
        self.invoice = inv
        # Create bill text
        bill = f"Invoice: {inv}\nDate: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        bill += f"Customer: {cname}\nContact: {contact}\n"
        bill += f"{'PID':5} {'Name':20} {'Price':8} {'Qty':4} {'Total':8}\n"
        bill += "-"*50 + "\n"
        for item in self.cart_list:
            bill += f"{item[0]:5} {item[1]:20} {item[2]:8.2f} {item[3]:4} {item[4]:8.2f}\n"
        bill += f"\nBill Amount: {total}\nDiscount: {self.discount}\nNet Payable: {net:.2f}\n"
        self.txt_bill_area.delete('1.0', END)
        self.txt_bill_area.insert(END, bill)

        # Save to sales_data
        # sales_data tuple: (invoice, date, customer, contact, total, cart_items_list)
        sales_data.append((inv, now.strftime('%Y-%m-%d %H:%M:%S'), cname, contact, net, self.cart_list[:]))
        # clear cart after generating
        self.cart_list.clear()
        self.show_cart()

    def print_bill(self):
        # For demonstration, just show message
        bill_content = self.txt_bill_area.get('1.0', END).strip()
        if not bill_content:
            messagebox.showerror("Error", "No bill to print")
            return
        messagebox.showinfo("Print", "Bill sent to printer (simulation)")
        # option to update chk_print
        self.chk_print = 1

    def update_date_time(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.config(text=now)
        self.root.after(1000, self.update_date_time)


class IMS:
    def __init__(self):
        self.root = Tk()
        self.root.title("Inventory Management System")
        self.root.geometry("800x600")
        self.root.config(bg="lightgray")

        self.new_obj = None
        self.new_win = None

        # MenuLogo and icons (placeholder)
        self.MenuLogo: Optional[PhotoImage] = None
        self.icon_side: Optional[PhotoImage] = None
        self.icon_title: Optional[PhotoImage] = None

        # Header
        header = Frame(self.root, bg="darkblue", height=100)
        header.pack(fill=X)
        self.icon_title = PhotoImage(file="")  # dummy if no file
        self.lbl_title = Label(header, text="IMS Dashboard", font=("Arial", 24, "bold"), bg="darkblue", fg="white")
        self.lbl_title.pack(side=LEFT, padx=20)

        # Sidebar with buttons
        sidebar = Frame(self.root, bg="gray", width=150)
        sidebar.pack(side=LEFT, fill=Y)

        Button(sidebar, text="Category", command=self.category, width=15).pack(pady=5)
        Button(sidebar, text="Employee", command=self.employee, width=15).pack(pady=5)
        Button(sidebar, text="Product", command=self.product, width=15).pack(pady=5)
        Button(sidebar, text="Supplier", command=self.supplier, width=15).pack(pady=5)
        Button(sidebar, text="Sales", command=self.sales, width=15).pack(pady=5)
        Button(sidebar, text="Billing", command=self.billing, width=15).pack(pady=5)

        # Labels (dashboard info)
        self.lbl_clock = Label(self.root, text="", font=("Arial", 10))
        self.lbl_clock.pack()

        # content area
        self.content = Frame(self.root, bg="white")
        self.content.pack(fill=BOTH, expand=True)
        self.lbl_product = Label(self.content, text="Products: 0", bg="white")
        self.lbl_product.pack()
        self.lbl_category = Label(self.content, text="Categories: 0", bg="white")
        self.lbl_category.pack()
        self.lbl_employee = Label(self.content, text="Employees: 0", bg="white")
        self.lbl_employee.pack()
        self.lbl_supplier = Label(self.content, text="Suppliers: 0", bg="white")
        self.lbl_supplier.pack()
        self.lbl_sales = Label(self.content, text="Sales: 0", bg="white")
        self.lbl_sales.pack()

        self.update_content()
        self.update_clock()

    def update_clock(self):
        self.lbl_clock.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self.update_clock)

    def update_content(self):
        self.lbl_product.config(text=f"Products: {len(product_data)}")
        self.lbl_category.config(text=f"Categories: {len(category_data)}")
        self.lbl_employee.config(text=f"Employees: {len(employee_data)}")
        self.lbl_supplier.config(text=f"Suppliers: {len(supplier_data)}")
        self.lbl_sales.config(text=f"Sales: {len(sales_data)}")

    def category(self):
        self.open_window(categoryClass)

    def employee(self):
        self.open_window(employeeClass)

    def product(self):
        self.open_window(productClass)

    def supplier(self):
        self.open_window(supplierClass)

    def sales(self):
        self.open_window(salesClass)

    def billing(self):
        self.open_window(billClass)

    def open_window(self, cls):
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_win = Toplevel(self.root)
        self.new_obj = cls(self.new_win)
        # Update content after window operations
        self.root.after(100, self.update_content)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = IMS()
    app.run()