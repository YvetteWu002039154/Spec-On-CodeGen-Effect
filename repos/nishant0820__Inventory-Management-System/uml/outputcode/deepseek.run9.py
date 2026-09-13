from tkinter import *
from tkinter import ttk, messagebox
import datetime
import random
import string
import tkinter as tk

# Global data stores
categories = []
employees = []
products = []
suppliers = []
sales = []


class categoryClass:
    def __init__(self, root):
        self.root = Toplevel(root)
        self.root.title("Category Management")
        self.root.geometry("800x500")
        self.root.resizable(False, False)

        self.var_cat_id = StringVar()
        self.var_name = StringVar()

        # images
        self.im1 = None
        self.im2 = None
        self.lbl_im1 = Label(self.root, image=self.im1)
        self.lbl_im2 = Label(self.root, image=self.im2)

        # title
        title = Label(self.root, text="Manage Categories", font=("Arial", 16, "bold"), bg="#0B5E82", fg="white")
        title.pack(side=TOP, fill=X)

        # form frame
        form_frame = Frame(self.root, bd=2, relief=RIDGE)
        form_frame.place(x=20, y=60, width=350, height=200)

        lbl_cid = Label(form_frame, text="Category ID", font=("Arial", 12))
        lbl_cid.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        Entry(form_frame, textvariable=self.var_cat_id, font=("Arial", 12), state='readonly').grid(row=0, column=1,
                                                                                                     padx=10, pady=10)

        lbl_name = Label(form_frame, text="Category Name", font=("Arial", 12))
        lbl_name.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        Entry(form_frame, textvariable=self.var_name, font=("Arial", 12)).grid(row=1, column=1, padx=10, pady=10)

        btn_frame = Frame(form_frame)
        btn_frame.grid(row=2, columnspan=2, pady=20)
        Button(btn_frame, text="Add", command=self.add, width=10, bg="green", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, width=10, bg="red", fg="white").pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, width=10, bg="grey", fg="white").pack(side=LEFT, padx=5)

        # tree frame
        tree_frame = Frame(self.root, bd=2, relief=RIDGE)
        tree_frame.place(x=400, y=60, width=380, height=400)

        scrolly = Scrollbar(tree_frame, orient=VERTICAL)
        scrollx = Scrollbar(tree_frame, orient=HORIZONTAL)
        self.CategoryTable = ttk.Treeview(tree_frame, columns=("cid", "name"), yscrollcommand=scrolly.set,
                                          xscrollcommand=scrollx.set)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.config(command=self.CategoryTable.yview)
        scrollx.config(command=self.CategoryTable.xview)
        self.CategoryTable.heading("cid", text="Category ID")
        self.CategoryTable.heading("name", text="Name")
        self.CategoryTable["show"] = "headings"
        self.CategoryTable.column("cid", width=100)
        self.CategoryTable.column("name", width=200)
        self.CategoryTable.pack(fill=BOTH, expand=1)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def show(self):
        for row in self.CategoryTable.get_children():
            self.CategoryTable.delete(row)
        for cat in categories:
            self.CategoryTable.insert("", END, values=(cat["cid"], cat["name"]))

    def add(self):
        cid = self.var_cat_id.get()
        name = self.var_name.get().strip()
        if not cid:
            cid = "CAT" + str(random.randint(1000, 9999))
            self.var_cat_id.set(cid)
        else:
            cid = cid.strip()
        if not name:
            messagebox.showerror("Error", "Category name required", parent=self.root)
            return
        if any(cat["cid"] == cid for cat in categories):
            messagebox.showerror("Error", "Category ID already exists", parent=self.root)
            return
        categories.append({"cid": cid, "name": name})
        self.show()
        self.clear()
        messagebox.showinfo("Success", "Category added", parent=self.root)

    def delete(self):
        selected = self.CategoryTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select a category to delete", parent=self.root)
            return
        for item in selected:
            row = self.CategoryTable.item(item)["values"]
            cid = row[0]
            for i, cat in enumerate(categories):
                if cat["cid"] == cid:
                    del categories[i]
                    break
        self.show()
        self.clear()

    def clear(self):
        self.var_cat_id.set("")
        self.var_name.set("")

    def get_data(self, ev):
        selected = self.CategoryTable.focus()
        if not selected:
            return
        row = self.CategoryTable.item(selected)["values"]
        if row:
            self.var_cat_id.set(row[0])
            self.var_name.set(row[1])


class employeeClass:
    def __init__(self, root):
        self.root = Toplevel(root)
        self.root.title("Employee Management")
        self.root.geometry("1100x600")
        self.root.resizable(False, False)

        self.var_emp_id = StringVar()
        self.var_name = StringVar()
        self.var_contact = StringVar()
        self.var_dob = StringVar()
        self.var_doj = StringVar()
        self.var_email = StringVar()
        self.var_gender = StringVar()
        self.var_pass = StringVar()
        self.var_salary = StringVar()
        self.var_utype = StringVar()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()

        title = Label(self.root, text="Employee Management", font=("Arial", 16, "bold"), bg="#0B5E82", fg="white")
        title.pack(side=TOP, fill=X)

        # form frame
        form_frame = Frame(self.root, bd=2, relief=RIDGE)
        form_frame.place(x=20, y=60, width=400, height=500)

        labels = ["Emp ID", "Name", "Contact", "DOB (YYYY-MM-DD)", "DOJ (YYYY-MM-DD)", "Email", "Gender", "Password",
                  "Salary", "User Type"]
        vars_list = [self.var_emp_id, self.var_name, self.var_contact, self.var_dob, self.var_doj, self.var_email,
                     self.var_gender, self.var_pass, self.var_salary, self.var_utype]
        genders = ["Male", "Female", "Other"]
        usertypes = ["Admin", "Staff"]

        for i, label in enumerate(labels):
            lbl = Label(form_frame, text=label, font=("Arial", 11))
            lbl.grid(row=i, column=0, padx=10, pady=5, sticky="w")
            if i == 6:  # gender combobox
                ttk.Combobox(form_frame, textvariable=self.var_gender, values=genders, state="readonly",
                             font=("Arial", 11)).grid(row=i, column=1, padx=10, pady=5, sticky="w")
            elif i == 9:  # user type combobox
                ttk.Combobox(form_frame, textvariable=self.var_utype, values=usertypes, state="readonly",
                             font=("Arial", 11)).grid(row=i, column=1, padx=10, pady=5, sticky="w")
            elif i == 7:  # password entry hidden
                Entry(form_frame, textvariable=self.var_pass, show="*", font=("Arial", 11)).grid(row=i, column=1,
                                                                                                 padx=10, pady=5)
            else:
                ent = Entry(form_frame, textvariable=vars_list[i], font=("Arial", 11))
                ent.grid(row=i, column=1, padx=10, pady=5, sticky="w")
        # address
        lbl_addr = Label(form_frame, text="Address", font=("Arial", 11))
        lbl_addr.grid(row=10, column=0, padx=10, pady=5, sticky="w")
        self.txt_address = Text(form_frame, height=3, width=30, font=("Arial", 11))
        self.txt_address.grid(row=10, column=1, padx=10, pady=5)

        btn_frame = Frame(form_frame)
        btn_frame.grid(row=11, columnspan=2, pady=10)
        Button(btn_frame, text="Add", command=self.add, bg="green", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update, bg="blue", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, bg="red", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, bg="grey", fg="white", width=8).pack(side=LEFT, padx=5)

        # search frame
        search_frame = Frame(self.root, bd=2, relief=RIDGE)
        search_frame.place(x=440, y=60, width=640, height=60)
        lbl_search = Label(search_frame, text="Search By", font=("Arial", 11))
        lbl_search.grid(row=0, column=0, padx=5, pady=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=["Emp ID", "Name", "Contact"],
                     state="readonly", font=("Arial", 11), width=10).grid(row=0, column=1, padx=5, pady=5)
        Entry(search_frame, textvariable=self.var_searchtxt, font=("Arial", 11)).grid(row=0, column=2, padx=5, pady=5)
        Button(search_frame, text="Search", command=self.search, bg="orange", fg="white").grid(row=0, column=3, padx=5,
                                                                                               pady=5)

        # tree frame
        tree_frame = Frame(self.root, bd=2, relief=RIDGE)
        tree_frame.place(x=440, y=130, width=640, height=430)
        scrolly = Scrollbar(tree_frame, orient=VERTICAL)
        scrollx = Scrollbar(tree_frame, orient=HORIZONTAL)
        self.EmployeeTable = ttk.Treeview(tree_frame, columns=(
        "eid", "name", "contact", "dob", "doj", "email", "gender", "salary", "utype"),
                                          yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.config(command=self.EmployeeTable.yview)
        scrollx.config(command=self.EmployeeTable.xview)
        columns = ["Emp ID", "Name", "Contact", "DOB", "DOJ", "Email", "Gender", "Salary", "User Type"]
        for col, heading in zip(self.EmployeeTable["columns"], columns):
            self.EmployeeTable.heading(col, text=heading)
            self.EmployeeTable.column(col, width=80)
        self.EmployeeTable["show"] = "headings"
        self.EmployeeTable.pack(fill=BOTH, expand=1)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def show(self):
        for row in self.EmployeeTable.get_children():
            self.EmployeeTable.delete(row)
        for emp in employees:
            self.EmployeeTable.insert("", END, values=(
            emp["eid"], emp["name"], emp["contact"], emp["dob"], emp["doj"], emp["email"], emp["gender"],
            emp["salary"], emp["utype"]))

    def add(self):
        eid = self.var_emp_id.get().strip()
        if not eid:
            eid = "EMP" + str(random.randint(10000, 99999))
            self.var_emp_id.set(eid)
        if any(e["eid"] == eid for e in employees):
            messagebox.showerror("Error", "Employee ID already exists", parent=self.root)
            return
        if not self.var_name.get():
            messagebox.showerror("Error", "Name required", parent=self.root)
            return
        emp = {
            "eid": eid,
            "name": self.var_name.get(),
            "contact": self.var_contact.get(),
            "dob": self.var_dob.get(),
            "doj": self.var_doj.get(),
            "email": self.var_email.get(),
            "gender": self.var_gender.get(),
            "pass": self.var_pass.get(),
            "salary": self.var_salary.get(),
            "utype": self.var_utype.get(),
            "address": self.txt_address.get("1.0", END).strip()
        }
        employees.append(emp)
        self.show()
        self.clear()
        messagebox.showinfo("Success", "Employee added", parent=self.root)

    def update(self):
        selected = self.EmployeeTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select an employee to update", parent=self.root)
            return
        eid = self.EmployeeTable.item(selected[0])["values"][0]
        for emp in employees:
            if emp["eid"] == eid:
                emp["name"] = self.var_name.get()
                emp["contact"] = self.var_contact.get()
                emp["dob"] = self.var_dob.get()
                emp["doj"] = self.var_doj.get()
                emp["email"] = self.var_email.get()
                emp["gender"] = self.var_gender.get()
                emp["pass"] = self.var_pass.get()
                emp["salary"] = self.var_salary.get()
                emp["utype"] = self.var_utype.get()
                emp["address"] = self.txt_address.get("1.0", END).strip()
                break
        self.show()
        self.clear()
        messagebox.showinfo("Success", "Employee updated", parent=self.root)

    def delete(self):
        selected = self.EmployeeTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select an employee to delete", parent=self.root)
            return
        for item in selected:
            eid = self.EmployeeTable.item(item)["values"][0]
            for i, emp in enumerate(employees):
                if emp["eid"] == eid:
                    del employees[i]
                    break
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
        self.var_pass.set("")
        self.var_salary.set("")
        self.var_utype.set("")
        self.txt_address.delete("1.0", END)

    def search(self):
        query = self.var_searchtxt.get().strip().lower()
        by = self.var_searchby.get()
        if not query or not by:
            messagebox.showerror("Error", "Enter search criteria", parent=self.root)
            return
        for row in self.EmployeeTable.get_children():
            self.EmployeeTable.delete(row)
        for emp in employees:
            val = emp.get(by.lower().replace(" ", "_"), "").lower()
            if query in val:
                self.EmployeeTable.insert("", END, values=(
                emp["eid"], emp["name"], emp["contact"], emp["dob"], emp["doj"], emp["email"], emp["gender"],
                emp["salary"], emp["utype"]))

    def get_data(self, ev):
        selected = self.EmployeeTable.focus()
        if not selected:
            return
        vals = self.EmployeeTable.item(selected)["values"]
        self.var_emp_id.set(vals[0])
        self.var_name.set(vals[1])
        self.var_contact.set(vals[2])
        self.var_dob.set(vals[3])
        self.var_doj.set(vals[4])
        self.var_email.set(vals[5])
        self.var_gender.set(vals[6])
        self.var_salary.set(vals[7])
        self.var_utype.set(vals[8])
        # find address
        for emp in employees:
            if emp["eid"] == vals[0]:
                self.txt_address.delete("1.0", END)
                self.txt_address.insert(END, emp.get("address", ""))
                self.var_pass.set(emp.get("pass", ""))
                break


class supplierClass:
    def __init__(self, root):
        self.root = Toplevel(root)
        self.root.title("Supplier Management")
        self.root.geometry("1000x550")
        self.root.resizable(False, False)

        self.var_sup_invoice = StringVar()
        self.var_name = StringVar()
        self.var_contact = StringVar()
        self.var_searchby = StringVar()
        self.var_searchtxt = StringVar()

        title = Label(self.root, text="Supplier Management", font=("Arial", 16, "bold"), bg="#0B5E82", fg="white")
        title.pack(side=TOP, fill=X)

        form_frame = Frame(self.root, bd=2, relief=RIDGE)
        form_frame.place(x=20, y=60, width=350, height=300)

        lbl_inv = Label(form_frame, text="Supplier Invoice", font=("Arial", 11))
        lbl_inv.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        Entry(form_frame, textvariable=self.var_sup_invoice, font=("Arial", 11)).grid(row=0, column=1, padx=10, pady=5)

        lbl_name = Label(form_frame, text="Name", font=("Arial", 11))
        lbl_name.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        Entry(form_frame, textvariable=self.var_name, font=("Arial", 11)).grid(row=1, column=1, padx=10, pady=5)

        lbl_contact = Label(form_frame, text="Contact", font=("Arial", 11))
        lbl_contact.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        Entry(form_frame, textvariable=self.var_contact, font=("Arial", 11)).grid(row=2, column=1, padx=10, pady=5)

        lbl_desc = Label(form_frame, text="Description", font=("Arial", 11))
        lbl_desc.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.txt_desc = Text(form_frame, height=4, width=30, font=("Arial", 11))
        self.txt_desc.grid(row=3, column=1, padx=10, pady=5)

        btn_frame = Frame(form_frame)
        btn_frame.grid(row=4, columnspan=2, pady=10)
        Button(btn_frame, text="Add", command=self.add, bg="green", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update, bg="blue", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, bg="red", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, bg="grey", fg="white", width=8).pack(side=LEFT, padx=5)

        search_frame = Frame(self.root, bd=2, relief=RIDGE)
        search_frame.place(x=400, y=60, width=580, height=60)
        Label(search_frame, text="Search By", font=("Arial", 11)).grid(row=0, column=0, padx=5, pady=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=["Invoice", "Name", "Contact"],
                     state="readonly", width=10).grid(row=0, column=1, padx=5, pady=5)
        Entry(search_frame, textvariable=self.var_searchtxt, font=("Arial", 11)).grid(row=0, column=2, padx=5, pady=5)
        Button(search_frame, text="Search", command=self.search, bg="orange", fg="white").grid(row=0, column=3, padx=5,
                                                                                               pady=5)

        tree_frame = Frame(self.root, bd=2, relief=RIDGE)
        tree_frame.place(x=400, y=130, width=580, height=380)
        scrolly = Scrollbar(tree_frame, orient=VERTICAL)
        scrollx = Scrollbar(tree_frame, orient=HORIZONTAL)
        self.SupplierTable = ttk.Treeview(tree_frame, columns=("invoice", "name", "contact", "desc"),
                                          yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.config(command=self.SupplierTable.yview)
        scrollx.config(command=self.SupplierTable.xview)
        for col, heading in zip(self.SupplierTable["columns"], ["Invoice", "Name", "Contact", "Description"]):
            self.SupplierTable.heading(col, text=heading)
            self.SupplierTable.column(col, width=120)
        self.SupplierTable["show"] = "headings"
        self.SupplierTable.pack(fill=BOTH, expand=1)
        self.SupplierTable.bind("<ButtonRelease-1>", self.get_data)
        self.show()

    def show(self):
        for row in self.SupplierTable.get_children():
            self.SupplierTable.delete(row)
        for sup in suppliers:
            self.SupplierTable.insert("", END,
                                      values=(sup["invoice"], sup["name"], sup["contact"], sup.get("desc", "")))

    def add(self):
        inv = self.var_sup_invoice.get().strip()
        if not inv:
            inv = "SUP" + str(random.randint(1000, 9999))
            self.var_sup_invoice.set(inv)
        if any(s["invoice"] == inv for s in suppliers):
            messagebox.showerror("Error", "Invoice ID exists", parent=self.root)
            return
        if not self.var_name.get():
            messagebox.showerror("Error", "Name required", parent=self.root)
            return
        suppliers.append({
            "invoice": inv,
            "name": self.var_name.get(),
            "contact": self.var_contact.get(),
            "desc": self.txt_desc.get("1.0", END).strip()
        })
        self.show()
        self.clear()
        messagebox.showinfo("Success", "Supplier added", parent=self.root)

    def update(self):
        selected = self.SupplierTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select a supplier", parent=self.root)
            return
        inv = self.SupplierTable.item(selected[0])["values"][0]
        for sup in suppliers:
            if sup["invoice"] == inv:
                sup["name"] = self.var_name.get()
                sup["contact"] = self.var_contact.get()
                sup["desc"] = self.txt_desc.get("1.0", END).strip()
                break
        self.show()
        self.clear()
        messagebox.showinfo("Success", "Supplier updated", parent=self.root)

    def delete(self):
        selected = self.SupplierTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select a supplier", parent=self.root)
            return
        for item in selected:
            inv = self.SupplierTable.item(item)["values"][0]
            for i, sup in enumerate(suppliers):
                if sup["invoice"] == inv:
                    del suppliers[i]
                    break
        self.show()
        self.clear()

    def clear(self):
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete("1.0", END)

    def search(self):
        query = self.var_searchtxt.get().strip().lower()
        by = self.var_searchby.get()
        if not query or not by:
            messagebox.showerror("Error", "Enter search criteria", parent=self.root)
            return
        for row in self.SupplierTable.get_children():
            self.SupplierTable.delete(row)
        for sup in suppliers:
            val = sup.get(by.lower(), "").lower()
            if query in val:
                self.SupplierTable.insert("", END,
                                          values=(sup["invoice"], sup["name"], sup["contact"], sup.get("desc", "")))

    def get_data(self, ev):
        selected = self.SupplierTable.focus()
        if not selected:
            return
        vals = self.SupplierTable.item(selected)["values"]
        self.var_sup_invoice.set(vals[0])
        self.var_name.set(vals[1])
        self.var_contact.set(vals[2])
        self.txt_desc.delete("1.0", END)
        self.txt_desc.insert(END, vals[3] if len(vals) > 3 else "")


class productClass:
    def __init__(self, root):
        self.root = Toplevel(root)
        self.root.title("Product Management")
        self.root.geometry("1100x600")
        self.root.resizable(False, False)

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

        title = Label(self.root, text="Product Management", font=("Arial", 16, "bold"), bg="#0B5E82", fg="white")
        title.pack(side=TOP, fill=X)

        form_frame = Frame(self.root, bd=2, relief=RIDGE)
        form_frame.place(x=20, y=60, width=400, height=350)

        labels = ["Product ID", "Name", "Price", "Quantity", "Status", "Category", "Supplier"]
        vars_list = [self.var_pid, self.var_name, self.var_price, self.var_qty, self.var_status, self.var_cat,
                     self.var_sup]
        for i, label in enumerate(labels):
            Label(form_frame, text=label, font=("Arial", 11)).grid(row=i, column=0, padx=10, pady=5, sticky="w")
            if i == 5:  # category combobox
                self.cat_combo = ttk.Combobox(form_frame, textvariable=self.var_cat, state="readonly",
                                              font=("Arial", 11))
                self.cat_combo.grid(row=i, column=1, padx=10, pady=5, sticky="w")
            elif i == 6:  # supplier combobox
                self.sup_combo = ttk.Combobox(form_frame, textvariable=self.var_sup, state="readonly",
                                              font=("Arial", 11))
                self.sup_combo.grid(row=i, column=1, padx=10, pady=5, sticky="w")
            else:
                Entry(form_frame, textvariable=vars_list[i], font=("Arial", 11)).grid(row=i, column=1, padx=10, pady=5,
                                                                                      sticky="w")

        btn_frame = Frame(form_frame)
        btn_frame.grid(row=7, columnspan=2, pady=10)
        Button(btn_frame, text="Add", command=self.add, bg="green", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Update", command=self.update, bg="blue", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Delete", command=self.delete, bg="red", fg="white", width=8).pack(side=LEFT, padx=5)
        Button(btn_frame, text="Clear", command=self.clear, bg="grey", fg="white", width=8).pack(side=LEFT, padx=5)

        search_frame = Frame(self.root, bd=2, relief=RIDGE)
        search_frame.place(x=440, y=60, width=640, height=60)
        Label(search_frame, text="Search By", font=("Arial", 11)).grid(row=0, column=0, padx=5, pady=5)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=["PID", "Name", "Category"],
                     state="readonly", width=10).grid(row=0, column=1, padx=5, pady=5)
        Entry(search_frame, textvariable=self.var_searchtxt, font=("Arial", 11)).grid(row=0, column=2, padx=5, pady=5)
        Button(search_frame, text="Search", command=self.search, bg="orange", fg="white").grid(row=0, column=3, padx=5,
                                                                                               pady=5)

        tree_frame = Frame(self.root, bd=2, relief=RIDGE)
        tree_frame.place(x=440, y=130, width=640, height=440)
        scrolly = Scrollbar(tree_frame, orient=VERTICAL)
        scrollx = Scrollbar(tree_frame, orient=HORIZONTAL)
        self.ProductTable = ttk.Treeview(tree_frame, columns=("pid", "name", "price", "qty", "cat", "sup", "status"),
                                         yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.config(command=self.ProductTable.yview)
        scrollx.config(command=self.ProductTable.xview)
        columns = ["PID", "Name", "Price", "Qty", "Category", "Supplier", "Status"]
        for col, heading in zip(self.ProductTable["columns"], columns):
            self.ProductTable.heading(col, text=heading)
            self.ProductTable.column(col, width=90)
        self.ProductTable["show"] = "headings"
        self.ProductTable.pack(fill=BOTH, expand=1)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)
        self.fetch_cat_sup()
        self.show()

    def fetch_cat_sup(self):
        self.cat_list = [cat["name"] for cat in categories]
        self.sup_list = [sup["name"] for sup in suppliers]
        self.cat_combo["values"] = self.cat_list
        self.sup_combo["values"] = self.sup_list

    def show(self):
        for row in self.ProductTable.get_children():
            self.ProductTable.delete(row)
        for prod in products:
            self.ProductTable.insert("", END, values=(
            prod["pid"], prod["name"], prod["price"], prod["qty"], prod.get("cat", ""), prod.get("sup", ""),
            prod.get("status", "Active")))

    def add(self):
        pid = self.var_pid.get().strip()
        if not pid:
            pid = "PROD" + str(random.randint(1000, 9999))
            self.var_pid.set(pid)
        if any(p["pid"] == pid for p in products):
            messagebox.showerror("Error", "Product ID exists", parent=self.root)
            return
        try:
            float(self.var_price.get())
            int(self.var_qty.get())
        except:
            messagebox.showerror("Error", "Invalid price or quantity", parent=self.root)
            return
        products.append({
            "pid": pid,
            "name": self.var_name.get(),
            "price": self.var_price.get(),
            "qty": self.var_qty.get(),
            "cat": self.var_cat.get(),
            "sup": self.var_sup.get(),
            "status": self.var_status.get() if self.var_status.get() else "Active"
        })
        self.show()
        self.clear()
        messagebox.showinfo("Success", "Product added", parent=self.root)

    def update(self):
        selected = self.ProductTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select a product", parent=self.root)
            return
        pid = self.ProductTable.item(selected[0])["values"][0]
        for prod in products:
            if prod["pid"] == pid:
                prod["name"] = self.var_name.get()
                prod["price"] = self.var_price.get()
                prod["qty"] = self.var_qty.get()
                prod["cat"] = self.var_cat.get()
                prod["sup"] = self.var_sup.get()
                prod["status"] = self.var_status.get()
                break
        self.show()
        self.clear()
        messagebox.showinfo("Success", "Product updated", parent=self.root)

    def delete(self):
        selected = self.ProductTable.selection()
        if not selected:
            messagebox.showerror("Error", "Select a product", parent=self.root)
            return
        for item in selected:
            pid = self.ProductTable.item(item)["values"][0]
            for i, p in enumerate(products):
                if p["pid"] == pid:
                    del products[i]
                    break
        self.show()
        self.clear()

    def clear(self):
        self.var_pid.set("")
        self.var_name.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("")
        self.var_cat.set("")
        self.var_sup.set("")

    def search(self):
        query = self.var_searchtxt.get().strip().lower()
        by = self.var_searchby.get()
        if not query or not by:
            messagebox.showerror("Error", "Enter search criteria", parent=self.root)
            return
        for row in self.ProductTable.get_children():
            self.ProductTable.delete(row)
        for prod in products:
            val = prod.get(by.lower(), "").lower()
            if query in val:
                self.ProductTable.insert("", END, values=(
                prod["pid"], prod["name"], prod["price"], prod["qty"], prod.get("cat", ""), prod.get("sup", ""),
                prod.get("status", "Active")))

    def get_data(self, ev):
        selected = self.ProductTable.focus()
        if not selected:
            return
        vals = self.ProductTable.item(selected)["values"]
        self.var_pid.set(vals[0])
        self.var_name.set(vals[1])
        self.var_price.set(vals[2])
        self.var_qty.set(vals[3])
        self.var_cat.set(vals[4])
        self.var_sup.set(vals[5])
        self.var_status.set(vals[6])


class salesClass:
    def __init__(self, root):
        self.root = Toplevel(root)
        self.root.title("Sales Records")
        self.root.geometry("900x600")
        self.root.resizable(False, False)

        self.var_invoice = StringVar()
        self.blll_list = []

        title = Label(self.root, text="Sales History", font=("Arial", 16, "bold"), bg="#0B5E82", fg="white")
        title.pack(side=TOP, fill=X)

        list_frame = Frame(self.root, bd=2, relief=RIDGE)
        list_frame.place(x=20, y=60, width=250, height=500)
        Label(list_frame, text="Invoice List", font=("Arial", 12, "bold")).pack(side=TOP, fill=X)
        scroll = Scrollbar(list_frame)
        scroll.pack(side=RIGHT, fill=Y)
        self.Sales_List = Listbox(list_frame, yscrollcommand=scroll.set, font=("Arial", 11))
        scroll.config(command=self.Sales_List.yview)
        self.Sales_List.pack(fill=BOTH, expand=1)
        self.Sales_List.bind("<<ListboxSelect>>", self.get_data)

        detail_frame = Frame(self.root, bd=2, relief=RIDGE)
        detail_frame.place(x=290, y=60, width=590, height=500)
        Label(detail_frame, text="Bill Details", font=("Arial", 12, "bold")).pack(side=TOP, fill=X)
        self.bill_area = Text(detail_frame, font=("Courier", 10))
        self.bill_area.pack(fill=BOTH, expand=1)

        self.bill_photo = None
        self.show()

    def show(self):
        self.Sales_List.delete(0, END)
        for sale in sales:
            self.Sales_List.insert(END, sale["invoice"])

    def get_data(self, ev):
        selection = self.Sales_List.curselection()
        if not selection:
            return
        index = selection[0]
        if index < len(sales):
            sale = sales[index]
            self.var_invoice.set(sale["invoice"])
            self.bill_area.delete("1.0", END)
            details = f"Invoice: {sale['invoice']}\nDate: {sale['date']}\nCustomer: {sale['customer']}\nContact: {sale.get('contact', '')}\n\n"
            details += "Items:\n" + "-" * 40 + "\n"
            for item in sale["items"]:
                details += f"{item['name']} x {item['qty']} @ {item['price']} = {item['total']}\n"
            details += "-" * 40 + "\n"
            details += f"Total: {sale['total']}\nDiscount: {sale['discount']}%\nNet Pay: {sale['net']}\n"
            self.bill_area.insert(END, details)

    def search(self):
        query = self.var_invoice.get().strip().lower()
        if not query:
            self.show()
            return
        self.Sales_List.delete(0, END)
        for sale in sales:
            if query in sale["invoice"].lower():
                self.Sales_List.insert(END, sale["invoice"])

    def clear(self):
        self.var_invoice.set("")
        self.bill_area.delete("1.0", END)
        self.show()


class billClass:
    def __init__(self, root):
        self.root = Toplevel(root)
        self.root.title("Billing")
        self.root.geometry("1200x700")
        self.root.resizable(False, False)

        self.var_pid = StringVar()
        self.var_pname = StringVar()
        self.var_price = StringVar()
        self.var_stock = StringVar()
        self.var_qty = StringVar()
        self.var_cname = StringVar()
        self.var_contact = StringVar()
        self.var_search = StringVar()
        self.var_cal_input = StringVar()

        self.cart_list = []
        self.bill_amnt = 0
        self.discount = 0.0
        self.net_pay = 0.0
        self.chk_print = 0
        self.invoice = None
        self.siscount = StringVar()

        self.icon_title = None
        self.cartTitle = Label(self.root, text="Cart", font=("Arial", 12, "bold"))

        self.bill_top()
        self.bill_middle()
        self.bill_bottom()
        self.update_date_time()
        self.show()

    def bill_top(self):
        top = Frame(self.root, bd=2, relief=RIDGE)
        top.place(x=0, y=0, width=1200, height=80)
        title = Label(top, text="Billing System", font=("Arial", 18, "bold"), bg="#0B5E82", fg="white")
        title.pack(fill=BOTH, expand=1)
        self.lbl_clock = Label(top, text="", font=("Arial", 10))
        self.lbl_clock.place(x=10, y=5)

    def bill_middle(self):
        mid = Frame(self.root, bd=2, relief=RIDGE)
        mid.place(x=0, y=80, width=1200, height=370)

        # customer frame
        cust_frame = LabelFrame(mid, text="Customer Details", font=("Arial", 11, "bold"), bd=2, relief=RIDGE)
        cust_frame.place(x=10, y=10, width=300, height=130)
        Label(cust_frame, text="Name", font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        Entry(cust_frame, textvariable=self.var_cname, font=("Arial", 10)).grid(row=0, column=1, padx=5, pady=5)
        Label(cust_frame, text="Contact", font=("Arial", 10)).grid(row=1, column=0, padx=5, pady=5, sticky="w")
        Entry(cust_frame, textvariable=self.var_contact, font=("Arial", 10)).grid(row=1, column=1, padx=5, pady=5)

        # product table frame
        prod_frame = LabelFrame(mid, text="Product List", font=("Arial", 11, "bold"), bd=2, relief=RIDGE)
        prod_frame.place(x=320, y=10, width=550, height=350)
        # search
        search_frm = Frame(prod_frame)
        search_frm.pack(fill=X, padx=5, pady=5)
        Label(search_frm, text="Search", font=("Arial", 10)).pack(side=LEFT, padx=5)
        Entry(search_frm, textvariable=self.var_search, font=("Arial", 10), width=15).pack(side=LEFT, padx=5)
        Button(search_frm, text="Search", command=self.search, bg="orange", fg="white").pack(side=LEFT, padx=5)
        Button(search_frm, text="Show All", command=self.show).pack(side=LEFT, padx=5)

        tree_prod = Frame(prod_frame)
        tree_prod.pack(fill=BOTH, expand=1, padx=5, pady=5)
        scrolly = Scrollbar(tree_prod, orient=VERTICAL)
        scrollx = Scrollbar(tree_prod, orient=HORIZONTAL)
        self.product_Table = ttk.Treeview(tree_prod, columns=("pid", "name", "price", "stock"),
                                          yscrollcommand=scrolly.set, xscrollcommand=scrollx.set)
        scrolly.pack(side=RIGHT, fill=Y)
        scrollx.pack(side=BOTTOM, fill=X)
        scrolly.config(command=self.product_Table.yview)
        scrollx.config(command=self.product_Table.xview)
        for col, heading in zip(self.product_Table["columns"], ["PID", "Name", "Price", "Stock"]):
            self.product_Table.heading(col, text=heading)
            self.product_Table.column(col, width=120)
        self.product_Table["show"] = "headings"
        self.product_Table.pack(fill=BOTH, expand=1)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)

        # selected product frame
        sel_frame = LabelFrame(mid, text="Selected Product", font=("Arial", 11, "bold"), bd=2, relief=RIDGE)
        sel_frame.place(x=880, y=10, width=300, height=350)
        label_texts = ["PID", "Name", "Price", "Stock", "Qty"]
        vars_ = [self.var_pid, self.var_pname, self.var_price, self.var_stock, self.var_qty]
        for i, text in enumerate(label_texts):
            Label(sel_frame, text=text, font=("Arial", 10)).grid(row=i, column=0, padx=5, pady=5, sticky="w")
            ent = Entry(sel_frame, textvariable=vars_[i], font=("Arial", 10), width=10)
            ent.grid(row=i, column=1, padx=5, pady=5)
            if i <= 3:
                ent.configure(state="readonly")
        Button(sel_frame, text="Add to Cart", command=self.add_update_cart, bg="green", fg="white").place(x=80, y=160,
                                                                                                          width=120)
        Button(sel_frame, text="Clear", command=self.clear_all, bg="grey", fg="white").place(x=80, y=200, width=120)
        self.lbl_inStock = Label(sel_frame, text="", font=("Arial", 10), fg="red")
        self.lbl_inStock.place(x=20, y=240)

        # calculator
        calc_frame = LabelFrame(mid, text="Calculator", font=("Arial", 11, "bold"), bd=2, relief=RIDGE)
        calc_frame.place(x=10, y=150, width=300, height=200)
        self.txt_cal_input = Entry(calc_frame, textvariable=self.var_cal_input, font=("Arial", 12), justify=RIGHT)
        self.txt_cal_input.pack(fill=X, padx=5, pady=5)
        buttons = [
            ("7", lambda: self.get_input("7")), ("8", lambda: self.get_input("8")), ("9", lambda: self.get_input("9")),
            ("/", lambda: self.get_input("/")),
            ("4", lambda: self.get_input("4")), ("5", lambda: self.get_input("5")), ("6", lambda: self.get_input("6")),
            ("*", lambda: self.get_input("*")),
            ("1", lambda: self.get_input("1")), ("2", lambda: self.get_input("2")), ("3", lambda: self.get_input("3")),
            ("-", lambda: self.get_input("-")),
            ("0", lambda: self.get_input("0")), (".", lambda: self.get_input(".")), ("Clear", self.clear_cal),
            ("+", lambda: self.get_input("+")),
            ("=", self.perform_cal)
        ]
        rows = [1, 2, 3, 4, 5]
        for i, (text, cmd) in enumerate(buttons):
            row = rows[i // 4]
            col = i % 4
            btn = Button(calc_frame, text=text, command=cmd, width=5, font=("Arial", 10))
            btn.grid(row=row, column=col, padx=2, pady=2)

    def bill_bottom(self):
        bot = Frame(self.root, bd=2, relief=RIDGE)
        bot.place(x=0, y=450, width=1200, height=250)

        cart_frame = LabelFrame(bot, text="Cart", font=("Arial", 11, "bold"), bd=2, relief=RIDGE)
        cart_frame.place(x=10, y=10, width=750, height=230)
        self.cartTitle = Label(cart_frame, text="Cart Items", font=("Arial", 10, "bold"))
        self.cartTitle.pack(side=TOP, fill=X)
        tree_cart = Frame(cart_frame)
        tree_cart.pack(fill=BOTH, expand=1, padx=5, pady=5)
        scrolly = Scrollbar(tree_cart, orient=VERTICAL)
        self.CartTable = ttk.Treeview(tree_cart, columns=("pid", "name", "price", "qty", "total"),
                                      yscrollcommand=scrolly.set)
        scrolly.pack(side=RIGHT, fill=Y)
        scrolly.config(command=self.CartTable.yview)
        for col, heading in zip(self.CartTable["columns"], ["PID", "Name", "Price", "Qty", "Total"]):
            self.CartTable.heading(col, text=heading)
            self.CartTable.column(col, width=120)
        self.CartTable["show"] = "headings"
        self.CartTable.pack(fill=BOTH, expand=1)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        Button(cart_frame, text="Clear Cart", command=self.clear_cart, bg="red", fg="white").pack(side=LEFT, padx=10,
                                                                                                  pady=5)

        bill_frame = LabelFrame(bot, text="Bill Summary", font=("Arial", 11, "bold"), bd=2, relief=RIDGE)
        bill_frame.place(x=770, y=10, width=420, height=230)
        self.lbl_amnt = Label(bill_frame, text="Bill Amount: 0", font=("Arial", 12))
        self.lbl_amnt.pack(anchor="w", padx=10, pady=5)
        self.lbl_discount = Label(bill_frame, text="Discount: 0%", font=("Arial", 12))
        self.lbl_discount.pack(anchor="w", padx=10, pady=5)
        self.lbl_net_pay = Label(bill_frame, text="Net Pay: 0", font=("Arial", 12, "bold"))
        self.lbl_net_pay.pack(anchor="w", padx=10, pady=5)

        self.txt_bill_area = Text(bill_frame, height=8, width=50, font=("Courier", 10), state=NORMAL)
        self.txt_bill_area.pack(side=LEFT, fill=BOTH, expand=1, padx=5, pady=5)

        Button(bill_frame, text="Generate Bill", command=self.generate_bill, bg="blue", fg="white").pack(side=BOTTOM,
                                                                                                         pady=5)
        Button(bill_frame, text="Print", command=self.print_bill, bg="orange", fg="white").pack(side=BOTTOM, pady=5)

    def show(self):
        for row in self.product_Table.get_children():
            self.product_Table.delete(row)
        for prod in products:
            self.product_Table.insert("", END,
                                      values=(prod["pid"], prod["name"], prod["price"], prod["qty"] if "qty" in prod else "0"))

    def search(self):
        query = self.var_search.get().strip().lower()
        if not query:
            self.show()
            return
        for row in self.product_Table.get_children():
            self.product_Table.delete(row)
        for prod in products:
            if query in prod["name"].lower() or query in prod["pid"].lower():
                self.product_Table.insert("", END, values=(prod["pid"], prod["name"], prod["price"], prod["qty"]))

    def get_data(self, ev):
        selected = self.product_Table.focus()
        if not selected:
            return
        vals = self.product_Table.item(selected)["values"]
        self.var_pid.set(vals[0])
        self.var_pname.set(vals[1])
        self.var_price.set(vals[2])
        self.var_stock.set(vals[3])
        self.var_qty.set("1")

    def add_update_cart(self):
        pid = self.var_pid.get()
        qty = self.var_qty.get().strip()
        stock = int(self.var_stock.get()) if self.var_stock.get().isdigit() else 0
        if not pid or not qty.isdigit():
            messagebox.showerror("Error", "Select product and valid quantity", parent=self.root)
            return
        qty = int(qty)
        if qty > stock:
            messagebox.showerror("Error", f"Insufficient stock ({stock})", parent=self.root)
            return
        price = float(self.var_price.get())
        existing = False
        for item in self.cart_list:
            if item["pid"] == pid:
                item["qty"] += qty
                item["total"] = item["qty"] * price
                existing = True
                break
        if not existing:
            self.cart_list.append({
                "pid": pid,
                "name": self.var_pname.get(),
                "price": price,
                "qty": qty,
                "total": qty * price
            })
        self.show_cart()
        self.bill_update()
        self.clear_all()
        self.lbl_inStock.config(text=f"Stock remaining: {stock - qty}")

    def show_cart(self):
        for row in self.CartTable.get_children():
            self.CartTable.delete(row)
        for item in self.cart_list:
            self.CartTable.insert("", END,
                                  values=(item["pid"], item["name"], item["price"], item["qty"], item["total"]))

    def get_data_cart(self, ev):
        selected = self.CartTable.focus()
        if not selected:
            return
        vals = self.CartTable.item(selected)["values"]
        self.var_pid.set(vals[0])
        self.var_pname.set(vals[1])
        self.var_price.set(vals[2])
        self.var_qty.set(vals[3])
        # stock not available, can fetch
        for prod in products:
            if prod["pid"] == vals[0]:
                self.var_stock.set(prod["qty"])
                break

    def bill_update(self):
        subtotal = sum(item["total"] for item in self.cart_list)
        self.bill_amnt = subtotal
        self.lbl_amnt.config(text=f"Bill Amount: {subtotal}")
        self.net_pay = subtotal - (subtotal * self.discount / 100)
        self.lbl_net_pay.config(text=f"Net Pay: {self.net_pay}")

    def clear_all(self):
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_stock.set("")
        self.var_qty.set("")

    def clear_cal(self):
        self.var_cal_input.set("")

    def get_input(self, num):
        current = self.var_cal_input.get()
        self.var_cal_input.set(current + str(num))

    def perform_cal(self):
        expr = self.var_cal_input.get()
        try:
            result = eval(expr)
            self.var_cal_input.set(str(result))
        except:
            self.var_cal_input.set("Error")

    def clear_cart(self):
        self.cart_list.clear()
        self.show_cart()
        self.bill_update()
        self.lbl_net_pay.config(text="Net Pay: 0")

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty", parent=self.root)
            return
        cname = self.var_cname.get().strip()
        if not cname:
            cname = "Walk-in Customer"
        invoice_no = "INV" + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        items = []
        for item in self.cart_list:
            items.append({
                "pid": item["pid"],
                "name": item["name"],
                "qty": item["qty"],
                "price": item["price"],
                "total": item["total"]
            })
            # reduce stock
            for prod in products:
                if prod["pid"] == item["pid"]:
                    prod["qty"] = str(int(prod["qty"]) - item["qty"])
                    break
        sale = {
            "invoice": invoice_no,
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "customer": cname,
            "contact": self.var_contact.get(),
            "items": items,
            "total": self.bill_amnt,
            "discount": self.discount,
            "net": self.net_pay
        }
        sales.append(sale)
        self.invoice = invoice_no
        self.txt_bill_area.delete("1.0", END)
        bill_text = f"Invoice: {invoice_no}\nCustomer: {cname}\nContact: {self.var_contact.get()}\n\nItems:\n"
        for it in items:
            bill_text += f"{it['name']} x {it['qty']} @ {it['price']} = {it['total']}\n"
        bill_text += f"\nTotal: {self.bill_amnt}\nDiscount: {self.discount}%\nNet Pay: {self.net_pay}"
        self.txt_bill_area.insert(END, bill_text)
        self.clear_cart()
        self.show()
        messagebox.showinfo("Success", f"Bill generated: {invoice_no}", parent=self.root)

    def print_bill(self):
        if not self.invoice:
            messagebox.showerror("Error", "Generate bill first", parent=self.root)
            return
        # simulate print: just show message
        messagebox.showinfo("Print", f"Printing invoice {self.invoice}...\n(check console)", parent=self.root)
        print(self.txt_bill_area.get("1.0", END))

    def update_date_time(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.config(text=now)
        self.root.after(1000, self.update_date_time)


class IMS:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("800x600")
        self.root.resizable(False, False)

        self.MenuLogo = None
        self.icon_side = None
        self.icon_title = None
        self.new_win = None
        self.new_obj = None

        # top title
        title_frame = Frame(self.root, bd=2, relief=RIDGE, bg="#0B5E82")
        title_frame.pack(side=TOP, fill=X)
        lbl = Label(title_frame, text="Inventory Management System", font=("Arial", 20, "bold"), bg="#0B5E82",
                    fg="white")
        lbl.pack(pady=10)

        # clock
        self.lbl_clock = Label(self.root, text="", font=("Arial", 10))
        self.lbl_clock.place(x=10, y=10)
        self.update_content()

        # dashboard buttons and stats
        main_frame = Frame(self.root, bd=2, relief=RIDGE)
        main_frame.pack(fill=BOTH, expand=1, padx=20, pady=20)

        btn_frame = Frame(main_frame)
        btn_frame.pack(side=LEFT, fill=Y, padx=10, pady=10)

        Button(btn_frame, text="Category", command=self.category, width=15, height=2, bg="#0077B6", fg="white").pack(
            pady=5)
        Button(btn_frame, text="Employee", command=self.employee, width=15, height=2, bg="#0077B6", fg="white").pack(
            pady=5)
        Button(btn_frame, text="Product", command=self.product, width=15, height=2, bg="#0077B6", fg="white").pack(pady=5)
        Button(btn_frame, text="Supplier", command=self.supplier, width=15, height=2, bg="#0077B6", fg="white").pack(
            pady=5)
        Button(btn_frame, text="Sales", command=self.sales, width=15, height=2, bg="#0077B6", fg="white").pack(pady=5)
        Button(btn_frame, text="Billing", command=self.billing, width=15, height=2, bg="#0077B6", fg="white").pack(pady=5)

        stats_frame = LabelFrame(main_frame, text="Statistics", font=("Arial", 12, "bold"), bd=2, relief=RIDGE)
        stats_frame.pack(side=RIGHT, fill=BOTH, expand=1, padx=10, pady=10)

        self.lbl_category = Label(stats_frame, text="Categories: 0", font=("Arial", 11))
        self.lbl_category.pack(anchor="w", padx=20, pady=5)
        self.lbl_employee = Label(stats_frame, text="Employees: 0", font=("Arial", 11))
        self.lbl_employee.pack(anchor="w", padx=20, pady=5)
        self.lbl_product = Label(stats_frame, text="Products: 0", font=("Arial", 11))
        self.lbl_product.pack(anchor="w", padx=20, pady=5)
        self.lbl_supplier = Label(stats_frame, text="Suppliers: 0", font=("Arial", 11))
        self.lbl_supplier.pack(anchor="w", padx=20, pady=5)
        self.lbl_sales = Label(stats_frame, text="Sales: 0", font=("Arial", 11))
        self.lbl_sales.pack(anchor="w", padx=20, pady=5)

    def update_content(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.config(text=now)
        self.lbl_category.config(text=f"Categories: {len(categories)}")
        self.lbl_employee.config(text=f"Employees: {len(employees)}")
        self.lbl_product.config(text=f"Products: {len(products)}")
        self.lbl_supplier.config(text=f"Suppliers: {len(suppliers)}")
        self.lbl_sales.config(text=f"Sales: {len(sales)}")
        self.root.after(1000, self.update_content)

    def category(self):
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_obj = categoryClass(self.root)
        self.new_win = self.new_obj.root

    def employee(self):
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_obj = employeeClass(self.root)
        self.new_win = self.new_obj.root

    def product(self):
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_obj = productClass(self.root)
        self.new_win = self.new_obj.root

    def supplier(self):
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_obj = supplierClass(self.root)
        self.new_win = self.new_obj.root

    def sales(self):
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_obj = salesClass(self.root)
        self.new_win = self.new_obj.root

    def billing(self):
        if self.new_win is not None:
            self.new_win.destroy()
        self.new_obj = billClass(self.root)
        self.new_win = self.new_obj.root


if __name__ == "__main__":
    root = Tk()
    app = IMS(root)
    root.mainloop()