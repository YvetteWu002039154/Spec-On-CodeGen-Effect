import tkinter as tk
from tkinter import ttk, messagebox, Text, Listbox
try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None
import sqlite3
from datetime import datetime
import os
from typing import Optional, Any

# ------------------------------ Database Setup ------------------------------
class Database:
    _instance = None
    def __init__(self, db_name='ims.db'):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_tables(self):
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS category (
                cid INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS employee (
                eid INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dob TEXT,
                doj TEXT,
                gender TEXT,
                contact TEXT,
                email TEXT,
                password TEXT,
                utype TEXT,
                address TEXT,
                salary REAL
            )"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS supplier (
                invoice INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT,
                desc TEXT
            )"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS product (
                pid INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category INTEGER,
                supplier INTEGER,
                price REAL,
                qty INTEGER,
                status TEXT,
                FOREIGN KEY (category) REFERENCES category (cid),
                FOREIGN KEY (supplier) REFERENCES supplier (invoice)
            )"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS sales (
                sid INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice TEXT NOT NULL,
                date TEXT NOT NULL,
                total_amount REAL,
                discount REAL,
                net_pay REAL
            )"""
        )
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS sales_item (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sales_invoice TEXT NOT NULL,
                pid INTEGER,
                product_name TEXT,
                price REAL,
                qty INTEGER,
                total REAL,
                FOREIGN KEY (pid) REFERENCES product (pid)
            )"""
        )
        self.conn.commit()

# ------------------------------ Helper Functions ----------------------------
def load_photo(path: str) -> tk.PhotoImage:
    if os.path.exists(path) and ImageTk:
        img = Image.open(path)
        return ImageTk.PhotoImage(img)
    else:
        return tk.PhotoImage()  # return empty

# ------------------------------ billClass ----------------------------------
class billClass:
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel(self.root)
        self.window.title("Billing Console")
        self.window.geometry("1350x700+0+0")
        self.window.config(bg="white")

        # Variables
        self.var_cname = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_pname = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_stock = tk.StringVar()
        self.var_search = tk.StringVar()
        self.var_pid = tk.StringVar()
        self.var_cal_input = tk.StringVar()

        self.cart_list = []
        self.chk_print = 0
        self.discount = 0.0
        self.net_pay = 0.0
        self.bill_amnt = 0
        self.siscount = 0

        self.icon_title = tk.PhotoImage()  # placeholder
        self.lbl_clock = tk.Label(self.window, text="", font=("times new roman", 12))
        self.lbl_clock.place(x=0, y=0, width=200, height=30)

        self.update_date_time()

        self.bill_top()
        self.bill_middle()
        self.bill_bottom()

        self.show()  # populate product table

    def update_date_time(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.config(text=now)
        self.lbl_clock.after(1000, self.update_date_time)

    # Top Frame
    def bill_top(self):
        top_frame = tk.Frame(self.window, bd=2, relief=tk.RIDGE, bg="white")
        top_frame.place(x=0, y=30, width=1350, height=250)

        # Customer Frame
        cust_frame = tk.LabelFrame(top_frame, text="Customer Details", font=("times new roman", 12, "bold"),
                                   bg="white", fg="black", bd=2, relief=tk.GROOVE)
        cust_frame.place(x=10, y=10, width=500, height=220)

        lbl_cname = tk.Label(cust_frame, text="Name", font=("times new roman", 14), bg="white")
        lbl_cname.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        txt_cname = tk.Entry(cust_frame, textvariable=self.var_cname, font=("times new roman", 14))
        txt_cname.grid(row=0, column=1, padx=10, pady=10)

        lbl_contact = tk.Label(cust_frame, text="Contact", font=("times new roman", 14), bg="white")
        lbl_contact.grid(row=1, column=0, padx=10, pady=10, sticky="w")
        txt_contact = tk.Entry(cust_frame, textvariable=self.var_contact, font=("times new roman", 14))
        txt_contact.grid(row=1, column=1, padx=10, pady=10)

        # Search Frame
        search_frame = tk.LabelFrame(top_frame, text="Search Product", font=("times new roman", 12, "bold"),
                                     bg="white", fg="black", bd=2, relief=tk.GROOVE)
        search_frame.place(x=520, y=10, width=400, height=220)

        lbl_search = tk.Label(search_frame, text="Product Name", font=("times new roman", 14), bg="white")
        lbl_search.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        txt_search = tk.Entry(search_frame, textvariable=self.var_search, font=("times new roman", 14))
        txt_search.grid(row=0, column=1, padx=10, pady=10)
        btn_search = tk.Button(search_frame, text="Search", command=self.search, font=("times new roman", 14), bg="lightgray")
        btn_search.grid(row=1, column=0, columnspan=2, padx=10, pady=10)

        self.lbl_inStock = tk.Label(search_frame, text="", font=("times new roman", 14), bg="white")
        self.lbl_inStock.grid(row=2, column=0, columnspan=2)

        # Bill area frame
        bill_frame = tk.LabelFrame(top_frame, text="Bill Area", font=("times new roman", 12, "bold"),
                                   bg="white", fg="black", bd=2, relief=tk.GROOVE)
        bill_frame.place(x=930, y=10, width=400, height=220)

        scroll_y = tk.Scrollbar(bill_frame, orient=tk.VERTICAL)
        self.txt_bill_area = tk.Text(bill_frame, yscrollcommand=scroll_y.set)
        scroll_y.config(command=self.txt_bill_area.yview)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_bill_area.pack(fill=tk.BOTH, expand=1)

    # Middle Frame
    def bill_middle(self):
        mid_frame = tk.Frame(self.window, bd=2, relief=tk.RIDGE, bg="white")
        mid_frame.place(x=0, y=280, width=1350, height=200)

        # Product Table
        product_frame = tk.LabelFrame(mid_frame, text="Product Details", font=("times new roman", 12, "bold"),
                                      bg="white", fg="black", bd=2, relief=tk.GROOVE)
        product_frame.place(x=10, y=10, width=600, height=180)

        scroll_y_prod = tk.Scrollbar(product_frame, orient=tk.VERTICAL)
        scroll_x_prod = tk.Scrollbar(product_frame, orient=tk.HORIZONTAL)
        self.product_Table = ttk.Treeview(product_frame, columns=("pid", "name", "price", "qty"),
                                          yscrollcommand=scroll_y_prod.set, xscrollcommand=scroll_x_prod.set)
        scroll_y_prod.config(command=self.product_Table.yview)
        scroll_x_prod.config(command=self.product_Table.xview)
        scroll_y_prod.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x_prod.pack(side=tk.BOTTOM, fill=tk.X)
        self.product_Table.heading("pid", text="PID")
        self.product_Table.heading("name", text="Name")
        self.product_Table.heading("price", text="Price")
        self.product_Table.heading("qty", text="Qty")
        self.product_Table["show"] = "headings"
        self.product_Table.column("pid", width=60)
        self.product_Table.column("name", width=200)
        self.product_Table.column("price", width=100)
        self.product_Table.column("qty", width=100)
        self.product_Table.pack(fill=tk.BOTH, expand=1)
        self.product_Table.bind("<ButtonRelease-1>", self.get_data)

        # Cart Frame
        cart_frame = tk.LabelFrame(mid_frame, text="Cart", font=("times new roman", 12, "bold"),
                                   bg="white", fg="black", bd=2, relief=tk.GROOVE)
        cart_frame.place(x=620, y=10, width=350, height=180)

        scroll_y_cart = tk.Scrollbar(cart_frame, orient=tk.VERTICAL)
        self.CartTable = ttk.Treeview(cart_frame, columns=("pid", "name", "price", "qty", "total"),
                                      yscrollcommand=scroll_y_cart.set)
        scroll_y_cart.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_y_cart.config(command=self.CartTable.yview)
        self.CartTable.heading("pid", text="PID")
        self.CartTable.heading("name", text="Name")
        self.CartTable.heading("price", text="Price")
        self.CartTable.heading("qty", text="Qty")
        self.CartTable.heading("total", text="Total")
        self.CartTable["show"] = "headings"
        self.CartTable.column("pid", width=60)
        self.CartTable.column("name", width=100)
        self.CartTable.column("price", width=80)
        self.CartTable.column("qty", width=50)
        self.CartTable.column("total", width=80)
        self.CartTable.pack(fill=tk.BOTH, expand=1)
        self.CartTable.bind("<ButtonRelease-1>", self.get_data_cart)

        self.cartTitle = tk.Label(cart_frame, text="", font=("times new roman", 12, "bold"), bg="white")
        self.cartTitle.pack(side=tk.BOTTOM)
        # Buttons
        btn_frame = tk.Frame(mid_frame, bg="white")
        btn_frame.place(x=980, y=10, width=350, height=180)

        btn_add = tk.Button(btn_frame, text="Add to Cart", command=self.add_update_cart, font=("times new roman", 14), bg="lightgreen")
        btn_add.grid(row=0, column=0, padx=5, pady=5)
        btn_clear_cart = tk.Button(btn_frame, text="Clear Cart", command=self.clear_cart, font=("times new roman", 14), bg="lightgray")
        btn_clear_cart.grid(row=0, column=1, padx=5, pady=5)
        btn_clear_all = tk.Button(btn_frame, text="Clear All", command=self.clear_all, font=("times new roman", 14), bg="lightgray")
        btn_clear_all.grid(row=1, column=0, padx=5, pady=5)
        btn_generate = tk.Button(btn_frame, text="Generate Bill", command=self.generate_bill, font=("times new roman", 14), bg="lightblue")
        btn_generate.grid(row=1, column=1, padx=5, pady=5)

    # Bottom Frame
    def bill_bottom(self):
        bottom_frame = tk.Frame(self.window, bd=2, relief=tk.RIDGE, bg="white")
        bottom_frame.place(x=0, y=480, width=1350, height=200)

        calc_frame = tk.LabelFrame(bottom_frame, text="Calculator", font=("times new roman", 12, "bold"),
                                  bg="white", fg="black", bd=2, relief=tk.GROOVE)
        calc_frame.place(x=10, y=10, width=400, height=180)

        self.txt_cal_input = tk.Entry(calc_frame, textvariable=self.var_cal_input, font=("times new roman", 16), justify='right')
        self.txt_cal_input.grid(row=0, column=0, columnspan=4, padx=5, pady=5, sticky="we")

        buttons = [
            ('7',1,0),('8',1,1),('9',1,2),('/',1,3),
            ('4',2,0),('5',2,1),('6',2,2),('*',2,3),
            ('1',3,0),('2',3,1),('3',3,2),('-',3,3),
            ('0',4,0),('.',4,1),('C',4,2),('+',4,3),
            ('=',5,0,1,4)
        ]
        for b in buttons:
            if len(b)==4:
                text,row,col = b[0],b[1],b[2]
                btn = tk.Button(calc_frame, text=text, command=lambda t=text: self.get_input(t), font=("times new roman", 14), width=5)
                btn.grid(row=row, column=col, padx=2, pady=2)
            else:
                text,row,col,rowspan,colspan = b
                btn = tk.Button(calc_frame, text=text, command=lambda t=text: self.get_input(t), font=("times new roman", 14))
                btn.grid(row=row, column=col, rowspan=rowspan, columnspan=colspan, padx=2, pady=2)

        bill_total_frame = tk.LabelFrame(bottom_frame, text="Bill Summary", font=("times new roman", 12, "bold"),
                                        bg="white", fg="black", bd=2, relief=tk.GROOVE)
        bill_total_frame.place(x=420, y=10, width=300, height=180)

        self.lbl_amnt = tk.Label(bill_total_frame, text="Bill Amount:", font=("times new roman", 14), bg="white")
        self.lbl_amnt.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.lbl_discount = tk.Label(bill_total_frame, text="Discount:", font=("times new roman", 14), bg="white")
        self.lbl_discount.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.lbl_net_pay = tk.Label(bill_total_frame, text="Net Pay:", font=("times new roman", 14), bg="white")
        self.lbl_net_pay.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        print_frame = tk.Frame(bottom_frame, bg="white")
        print_frame.place(x=730, y=10, width=600, height=180)

        btn_print = tk.Button(print_frame, text="Print Bill", command=self.print_bill, font=("times new roman", 14), bg="lightyellow")
        btn_print.pack(side=tk.LEFT, padx=20)

    def show(self):
        db = Database.get_instance()
        db.cursor.execute("SELECT pid, name, price, qty FROM product WHERE status='Active' AND qty>0")
        rows = db.cursor.fetchall()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", tk.END, values=row)

    def get_data(self, ev):
        selected = self.product_Table.focus()
        if selected:
            values = self.product_Table.item(selected, 'values')
            self.var_pid.set(values[0])
            self.var_pname.set(values[1])
            self.var_price.set(values[2])
            self.var_stock.set(values[3])
            self.var_qty.set("1")

    def get_data_cart(self, ev):
        selected = self.CartTable.focus()
        if selected:
            values = self.CartTable.item(selected, 'values')
            self.var_pid.set(values[0])
            self.var_pname.set(values[1])
            self.var_price.set(values[2])
            self.var_qty.set(values[3])
            self.var_stock.set("")  # stock unknown from cart

    def search(self):
        name = self.var_search.get()
        db = Database.get_instance()
        db.cursor.execute("SELECT pid, name, price, qty FROM product WHERE name LIKE ? AND status='Active' AND qty>0", ('%'+name+'%',))
        rows = db.cursor.fetchall()
        self.product_Table.delete(*self.product_Table.get_children())
        for row in rows:
            self.product_Table.insert("", tk.END, values=row)
        if rows:
            self.lbl_inStock.config(text=f"{len(rows)} product(s) found")
        else:
            self.lbl_inStock.config(text="Product not found")

    def add_update_cart(self):
        pid = self.var_pid.get()
        pname = self.var_pname.get()
        price = self.var_price.get()
        qty = self.var_qty.get()
        stock = self.var_stock.get()
        if not all([pid, pname, price, qty]):
            messagebox.showerror("Error", "Please select a product and enter quantity")
            return
        try:
            qty = int(qty)
            stock = int(stock)
        except:
            messagebox.showerror("Error", "Invalid quantity")
            return
        if qty > stock:
            messagebox.showerror("Error", f"Insufficient stock. Only {stock} available")
            return

        total = float(price) * qty

        # Check if already in cart
        for item in self.cart_list:
            if item[0] == pid:
                new_qty = item[3] + qty
                if new_qty > stock:
                    messagebox.showerror("Error", f"Insufficient stock. Only {stock} available")
                    return
                item[3] = new_qty
                item[4] = float(price) * new_qty
                self.show_cart()
                return
        self.cart_list.append([pid, pname, float(price), qty, total])
        self.show_cart()

    def show_cart(self):
        self.CartTable.delete(*self.CartTable.get_children())
        for item in self.cart_list:
            self.CartTable.insert("", tk.END, values=item)
        self.cartTitle.config(text=f"Total items: {len(self.cart_list)}")

    def clear_cart(self):
        self.cart_list.clear()
        self.show_cart()

    def clear_all(self):
        self.clear_cart()
        self.var_cname.set("")
        self.var_contact.set("")
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")
        self.var_search.set("")
        self.txt_bill_area.delete("1.0", tk.END)
        self.lbl_amnt.config(text="Bill Amount:")
        self.lbl_discount.config(text="Discount:")
        self.lbl_net_pay.config(text="Net Pay:")

    def generate_bill(self):
        if not self.cart_list:
            messagebox.showerror("Error", "Cart is empty")
            return
        if not self.var_cname.get():
            messagebox.showerror("Error", "Please enter customer name")
            return

        # Compute totals
        total_amt = sum(item[4] for item in self.cart_list)
        # fixed discount 10% if total > 500 else 0
        discount = total_amt * 0.1 if total_amt > 500 else 0
        net_pay = total_amt - discount
        self.bill_amnt = total_amt
        self.discount = discount
        self.net_pay = net_pay

        self.lbl_amnt.config(text=f"Bill Amount: {total_amt:.2f}")
        self.lbl_discount.config(text=f"Discount: {discount:.2f}")
        self.lbl_net_pay.config(text=f"Net Pay: {net_pay:.2f}")

        # Generate invoice number
        invoice_no = "INV-" + datetime.now().strftime("%Y%m%d%H%M%S")
        self.invoice = invoice_no

        # Display bill text
        bill_text = f"\t\tCustomer: {self.var_cname.get()}\n"
        bill_text += f"\t\tContact: {self.var_contact.get()}\n"
        bill_text += f"\t\tInvoice No: {invoice_no}\n"
        bill_text += "-"*40 + "\n"
        bill_text += "Product\tQty\tPrice\tTotal\n"
        for item in self.cart_list:
            bill_text += f"{item[1]}\t{item[3]}\t{item[2]}\t{item[4]}\n"
        bill_text += "-"*40 + "\n"
        bill_text += f"Total Amount: {total_amt:.2f}\n"
        bill_text += f"Discount: {discount:.2f}\n"
        bill_text += f"Net Payable: {net_pay:.2f}\n"
        self.txt_bill_area.delete("1.0", tk.END)
        self.txt_bill_area.insert(tk.END, bill_text)

        # Save to database
        db = Database.get_instance()
        db.cursor.execute("INSERT INTO sales (invoice, date, total_amount, discount, net_pay) VALUES (?, ?, ?, ?, ?)",
                          (invoice_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total_amt, discount, net_pay))
        for item in self.cart_list:
            db.cursor.execute("INSERT INTO sales_item (sales_invoice, pid, product_name, price, qty, total) VALUES (?, ?, ?, ?, ?, ?)",
                              (invoice_no, item[0], item[1], item[2], item[3], item[4]))
            # Update stock
            db.cursor.execute("UPDATE product SET qty = qty - ? WHERE pid = ?", (item[3], item[0]))
        db.conn.commit()
        messagebox.showinfo("Success", f"Bill generated: {invoice_no}")
        self.chk_print = 1

    def print_bill(self):
        if self.chk_print == 0:
            messagebox.showerror("Error", "Please generate bill first")
            return
        # Simulate printing
        messagebox.showinfo("Print", "Bill sent to printer (simulated)")

    def get_input(self, num):
        if num == '=':
            self.perform_cal()
        elif num == 'C':
            self.var_cal_input.set("")
        else:
            current = self.var_cal_input.get()
            self.var_cal_input.set(current + num)

    def perform_cal(self):
        try:
            expr = self.var_cal_input.get()
            result = eval(expr)
            self.var_cal_input.set(str(result))
        except:
            self.var_cal_input.set("Error")

    def clear_cal(self):
        self.var_cal_input.set("")

    def bill_update(self):
        self.show()

# ------------------------------ categoryClass -------------------------------
class categoryClass:
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel(self.root)
        self.window.title("Category Management")
        self.window.geometry("800x500+200+100")
        self.window.config(bg="white")

        self.var_cat_id = tk.StringVar()
        self.var_name = tk.StringVar()

        # Images placeholder
        self.im1 = None
        self.im2 = None
        if ImageTk:
            try:
                self.im1 = ImageTk.PhotoImage(Image.new("RGB", (50,50), (100,100,255)))
                self.im2 = ImageTk.PhotoImage(Image.new("RGB", (50,50), (255,100,100)))
            except:
                pass
        self.lbl_im1 = tk.Label(self.window, image=self.im1, bg="white")
        self.lbl_im2 = tk.Label(self.window, image=self.im2, bg="white")

        # Entry section
        frame_top = tk.LabelFrame(self.window, text="Category Details", font=("times new roman", 14, "bold"),
                                  bg="white", bd=2, relief=tk.GROOVE)
        frame_top.place(x=20, y=20, width=760, height=150)

        tk.Label(frame_top, text="Category ID:", font=("times new roman", 14), bg="white").grid(row=0, column=0, padx=10, pady=10)
        tk.Entry(frame_top, textvariable=self.var_cat_id, state='readonly', font=("times new roman", 14)).grid(row=0, column=1, padx=10, pady=10)

        tk.Label(frame_top, text="Name:", font=("times new roman", 14), bg="white").grid(row=1, column=0, padx=10, pady=10)
        tk.Entry(frame_top, textvariable=self.var_name, font=("times new roman", 14)).grid(row=1, column=1, padx=10, pady=10)

        btn_frame = tk.Frame(frame_top, bg="white")
        btn_frame.grid(row=0, column=2, rowspan=2, padx=20, pady=20)
        tk.Button(btn_frame, text="Add", command=self.add, width=10, font=("times new roman", 14), bg="lightgreen").pack(pady=5)
        tk.Button(btn_frame, text="Delete", command=self.delete, width=10, font=("times new roman", 14), bg="lightcoral").pack(pady=5)
        tk.Button(btn_frame, text="Clear", command=self.clear, width=10, font=("times new roman", 14), bg="lightgray").pack(pady=5)

        # Treeview
        tree_frame = tk.LabelFrame(self.window, text="Category List", font=("times new roman", 12, "bold"),
                                   bg="white", bd=2, relief=tk.GROOVE)
        tree_frame.place(x=20, y=180, width=760, height=280)

        scroll_y = tk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        self.CategoryTable = ttk.Treeview(tree_frame, columns=("id", "name"),
                                         yscrollcommand=scroll_y.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_y.config(command=self.CategoryTable.yview)
        self.CategoryTable.heading("id", text="ID")
        self.CategoryTable.heading("name", text="Name")
        self.CategoryTable["show"] = "headings"
        self.CategoryTable.column("id", width=100)
        self.CategoryTable.column("name", width=200)
        self.CategoryTable.pack(fill=tk.BOTH, expand=1)
        self.CategoryTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def show(self):
        db = Database.get_instance()
        db.cursor.execute("SELECT * FROM category")
        rows = db.cursor.fetchall()
        self.CategoryTable.delete(*self.CategoryTable.get_children())
        for row in rows:
            self.CategoryTable.insert("", tk.END, values=row)

    def get_data(self, ev):
        selected = self.CategoryTable.focus()
        if selected:
            values = self.CategoryTable.item(selected, 'values')
            self.var_cat_id.set(values[0])
            self.var_name.set(values[1])

    def clear(self):
        self.var_cat_id.set("")
        self.var_name.set("")

    def add(self):
        if not self.var_name.get():
            messagebox.showerror("Error", "Category name is required")
            return
        db = Database.get_instance()
        db.cursor.execute("INSERT INTO category (name) VALUES (?)", (self.var_name.get(),))
        db.conn.commit()
        messagebox.showinfo("Success", "Category added")
        self.show()
        self.clear()

    def delete(self):
        if not self.var_cat_id.get():
            messagebox.showerror("Error", "Select a category to delete")
            return
        db = Database.get_instance()
        db.cursor.execute("DELETE FROM category WHERE cid=?", (self.var_cat_id.get(),))
        db.conn.commit()
        messagebox.showinfo("Success", "Category deleted")
        self.show()
        self.clear()

# ------------------------------ employeeClass --------------------------------
class employeeClass:
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel(self.root)
        self.window.title("Employee Management")
        self.window.geometry("1200x600+100+50")
        self.window.config(bg="white")

        self.var_emp_id = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_dob = tk.StringVar()
        self.var_doj = tk.StringVar()
        self.var_gender = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_email = tk.StringVar()
        self.var_pass = tk.StringVar()
        self.var_utype = tk.StringVar()
        self.var_salary = tk.StringVar()
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()

        self.txt_address = None  # will be Text widget

        # Layout
        top_frame = tk.LabelFrame(self.window, text="Employee Details", font=("times new roman", 14, "bold"),
                                  bg="white", bd=2, relief=tk.GROOVE)
        top_frame.place(x=20, y=20, width=1150, height=250)

        # Row 0
        tk.Label(top_frame, text="Emp ID:", font=("times new roman", 13), bg="white").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        tk.Entry(top_frame, textvariable=self.var_emp_id, state='readonly', font=("times new roman", 13)).grid(row=0, column=1, padx=10, pady=5)

        tk.Label(top_frame, text="Name:", font=("times new roman", 13), bg="white").grid(row=0, column=2, padx=10, pady=5, sticky="w")
        tk.Entry(top_frame, textvariable=self.var_name, font=("times new roman", 13)).grid(row=0, column=3, padx=10, pady=5)

        tk.Label(top_frame, text="DOB:", font=("times new roman", 13), bg="white").grid(row=0, column=4, padx=10, pady=5, sticky="w")
        tk.Entry(top_frame, textvariable=self.var_dob, font=("times new roman", 13)).grid(row=0, column=5, padx=10, pady=5)

        # Row 1
        tk.Label(top_frame, text="DOJ:", font=("times new roman", 13), bg="white").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        tk.Entry(top_frame, textvariable=self.var_doj, font=("times new roman", 13)).grid(row=1, column=1, padx=10, pady=5)

        tk.Label(top_frame, text="Gender:", font=("times new roman", 13), bg="white").grid(row=1, column=2, padx=10, pady=5, sticky="w")
        ttk.Combobox(top_frame, textvariable=self.var_gender, values=["Male", "Female", "Other"], state="readonly").grid(row=1, column=3, padx=10, pady=5)

        tk.Label(top_frame, text="Contact:", font=("times new roman", 13), bg="white").grid(row=1, column=4, padx=10, pady=5, sticky="w")
        tk.Entry(top_frame, textvariable=self.var_contact, font=("times new roman", 13)).grid(row=1, column=5, padx=10, pady=5)

        # Row 2
        tk.Label(top_frame, text="Email:", font=("times new roman", 13), bg="white").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        tk.Entry(top_frame, textvariable=self.var_email, font=("times new roman", 13)).grid(row=2, column=1, padx=10, pady=5)

        tk.Label(top_frame, text="Password:", font=("times new roman", 13), bg="white").grid(row=2, column=2, padx=10, pady=5, sticky="w")
        tk.Entry(top_frame, textvariable=self.var_pass, font=("times new roman", 13), show="*").grid(row=2, column=3, padx=10, pady=5)

        tk.Label(top_frame, text="User Type:", font=("times new roman", 13), bg="white").grid(row=2, column=4, padx=10, pady=5, sticky="w")
        ttk.Combobox(top_frame, textvariable=self.var_utype, values=["Admin", "Employee"], state="readonly").grid(row=2, column=5, padx=10, pady=5)

        # Row 3
        tk.Label(top_frame, text="Salary:", font=("times new roman", 13), bg="white").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        tk.Entry(top_frame, textvariable=self.var_salary, font=("times new roman", 13)).grid(row=3, column=1, padx=10, pady=5)

        tk.Label(top_frame, text="Address:", font=("times new roman", 13), bg="white").grid(row=3, column=2, padx=10, pady=5, sticky="w")
        self.txt_address = tk.Text(top_frame, font=("times new roman", 13), width=25, height=3)
        self.txt_address.grid(row=3, column=3, columnspan=2, padx=10, pady=5)

        # Buttons
        btn_frame = tk.Frame(top_frame, bg="white")
        btn_frame.grid(row=0, column=6, rowspan=4, padx=20)
        tk.Button(btn_frame, text="Add", command=self.add, width=10, font=("times new roman", 14), bg="lightgreen").pack(pady=5)
        tk.Button(btn_frame, text="Update", command=self.update, width=10, font=("times new roman", 14), bg="lightblue").pack(pady=5)
        tk.Button(btn_frame, text="Delete", command=self.delete, width=10, font=("times new roman", 14), bg="lightcoral").pack(pady=5)
        tk.Button(btn_frame, text="Clear", command=self.clear, width=10, font=("times new roman", 14), bg="lightgray").pack(pady=5)

        # Search frame
        search_frame = tk.LabelFrame(self.window, text="Search", font=("times new roman", 12, "bold"),
                                     bg="white", bd=2, relief=tk.GROOVE)
        search_frame.place(x=20, y=280, width=1150, height=70)

        tk.Label(search_frame, text="Search By:", font=("times new roman", 13), bg="white").grid(row=0, column=0, padx=10)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=["emp_id", "name", "email"], state="readonly").grid(row=0, column=1, padx=10)
        tk.Label(search_frame, text="Search Text:", font=("times new roman", 13), bg="white").grid(row=0, column=2, padx=10)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, font=("times new roman", 13)).grid(row=0, column=3, padx=10)
        tk.Button(search_frame, text="Search", command=self.search, font=("times new roman", 13), bg="lightyellow").grid(row=0, column=4, padx=10)

        # Treeview
        tree_frame = tk.LabelFrame(self.window, text="Employee List", font=("times new roman", 12, "bold"),
                                   bg="white", bd=2, relief=tk.GROOVE)
        tree_frame.place(x=20, y=360, width=1150, height=210)

        scroll_y = tk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        self.EmployeeTable = ttk.Treeview(tree_frame,
                                          columns=("id","name","dob","doj","gender","contact","email","utype","salary","address"),
                                          yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.config(command=self.EmployeeTable.yview)
        scroll_x.config(command=self.EmployeeTable.xview)
        self.EmployeeTable["show"] = "headings"
        columns = ("id","name","dob","doj","gender","contact","email","utype","salary","address")
        widths = (60,100,80,80,70,100,120,80,80,150)
        for col, w in zip(columns, widths):
            self.EmployeeTable.heading(col, text=col.capitalize())
            self.EmployeeTable.column(col, width=w)
        self.EmployeeTable.pack(fill=tk.BOTH, expand=1)
        self.EmployeeTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def clear(self):
        self.var_emp_id.set("")
        self.var_name.set("")
        self.var_dob.set("")
        self.var_doj.set("")
        self.var_gender.set("")
        self.var_contact.set("")
        self.var_email.set("")
        self.var_pass.set("")
        self.var_utype.set("")
        self.var_salary.set("")
        self.txt_address.delete("1.0", tk.END)

    def add(self):
        if not self.var_name.get() or not self.var_email.get():
            messagebox.showerror("Error", "Name and Email are required")
            return
        db = Database.get_instance()
        db.cursor.execute("""INSERT INTO employee (name, dob, doj, gender, contact, email, password, utype, address, salary)
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                          (self.var_name.get(), self.var_dob.get(), self.var_doj.get(),
                           self.var_gender.get(), self.var_contact.get(), self.var_email.get(),
                           self.var_pass.get(), self.var_utype.get(),
                           self.txt_address.get("1.0", tk.END).strip(), self.var_salary.get()))
        db.conn.commit()
        messagebox.showinfo("Success", "Employee added")
        self.show()
        self.clear()

    def update(self):
        if not self.var_emp_id.get():
            messagebox.showerror("Error", "Select employee to update")
            return
        db = Database.get_instance()
        db.cursor.execute("""UPDATE employee SET name=?, dob=?, doj=?, gender=?, contact=?, email=?, password=?,
                             utype=?, address=?, salary=? WHERE eid=?""",
                          (self.var_name.get(), self.var_dob.get(), self.var_doj.get(),
                           self.var_gender.get(), self.var_contact.get(), self.var_email.get(),
                           self.var_pass.get(), self.var_utype.get(),
                           self.txt_address.get("1.0", tk.END).strip(), self.var_salary.get(),
                           self.var_emp_id.get()))
        db.conn.commit()
        messagebox.showinfo("Success", "Employee updated")
        self.show()
        self.clear()

    def delete(self):
        if not self.var_emp_id.get():
            messagebox.showerror("Error", "Select employee to delete")
            return
        db = Database.get_instance()
        db.cursor.execute("DELETE FROM employee WHERE eid=?", (self.var_emp_id.get(),))
        db.conn.commit()
        messagebox.showinfo("Success", "Employee deleted")
        self.show()
        self.clear()

    def show(self):
        db = Database.get_instance()
        db.cursor.execute("SELECT * FROM employee")
        rows = db.cursor.fetchall()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for row in rows:
            self.EmployeeTable.insert("", tk.END, values=row)

    def get_data(self, ev):
        selected = self.EmployeeTable.focus()
        if selected:
            values = self.EmployeeTable.item(selected, 'values')
            self.var_emp_id.set(values[0])
            self.var_name.set(values[1])
            self.var_dob.set(values[2])
            self.var_doj.set(values[3])
            self.var_gender.set(values[4])
            self.var_contact.set(values[5])
            self.var_email.set(values[6])
            self.var_pass.set(values[7])  # password field might be stored plain; ignore
            self.var_utype.set(values[8])
            self.var_salary.set(values[9])
            self.txt_address.delete("1.0", tk.END)
            self.txt_address.insert(tk.END, values[10])

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get()
        if not by or not txt:
            messagebox.showerror("Error", "Select search criteria and enter text")
            return
        db = Database.get_instance()
        query = f"SELECT * FROM employee WHERE {by} LIKE ?"
        db.cursor.execute(query, ('%'+txt+'%',))
        rows = db.cursor.fetchall()
        self.EmployeeTable.delete(*self.EmployeeTable.get_children())
        for row in rows:
            self.EmployeeTable.insert("", tk.END, values=row)

# ------------------------------ productClass ---------------------------------
class productClass:
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel(self.root)
        self.window.title("Product Management")
        self.window.geometry("1200x600+100+50")
        self.window.config(bg="white")

        self.var_pid = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_cat = tk.StringVar()
        self.var_sup = tk.StringVar()
        self.var_price = tk.StringVar()
        self.var_qty = tk.StringVar()
        self.var_status = tk.StringVar()
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()

        self.cat_list = []
        self.sup_list = []
        self.fetch_cat_sup()

        # Layout
        top_frame = tk.LabelFrame(self.window, text="Product Details", font=("times new roman", 14, "bold"),
                                  bg="white", bd=2, relief=tk.GROOVE)
        top_frame.place(x=20, y=20, width=1150, height=200)

        # Row 0
        tk.Label(top_frame, text="PID:", font=("times new roman", 13), bg="white").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        tk.Entry(top_frame, textvariable=self.var_pid, state='readonly', font=("times new roman", 13)).grid(row=0, column=1, padx=10, pady=5)

        tk.Label(top_frame, text="Name:", font=("times new roman", 13), bg="white").grid(row=0, column=2, padx=10, pady=5, sticky="w")
        tk.Entry(top_frame, textvariable=self.var_name, font=("times new roman", 13)).grid(row=0, column=3, padx=10, pady=5)

        tk.Label(top_frame, text="Category:", font=("times new roman", 13), bg="white").grid(row=0, column=4, padx=10, pady=5, sticky="w")
        self.combo_cat = ttk.Combobox(top_frame, textvariable=self.var_cat, values=self.cat_list, state="readonly")
        self.combo_cat.grid(row=0, column=5, padx=10, pady=5)

        # Row 1
        tk.Label(top_frame, text="Supplier:", font=("times new roman", 13), bg="white").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.combo_sup = ttk.Combobox(top_frame, textvariable=self.var_sup, values=self.sup_list, state="readonly")
        self.combo_sup.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(top_frame, text="Price:", font=("times new roman", 13), bg="white").grid(row=1, column=2, padx=10, pady=5, sticky="w")
        tk.Entry(top_frame, textvariable=self.var_price, font=("times new roman", 13)).grid(row=1, column=3, padx=10, pady=5)

        tk.Label(top_frame, text="Quantity:", font=("times new roman", 13), bg="white").grid(row=1, column=4, padx=10, pady=5, sticky="w")
        tk.Entry(top_frame, textvariable=self.var_qty, font=("times new roman", 13)).grid(row=1, column=5, padx=10, pady=5)

        # Row 2
        tk.Label(top_frame, text="Status:", font=("times new roman", 13), bg="white").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        ttk.Combobox(top_frame, textvariable=self.var_status, values=["Active", "Inactive"], state="readonly").grid(row=2, column=1, padx=10, pady=5)

        # Buttons
        btn_frame = tk.Frame(top_frame, bg="white")
        btn_frame.grid(row=0, column=6, rowspan=3, padx=20)
        tk.Button(btn_frame, text="Add", command=self.add, width=10, font=("times new roman", 14), bg="lightgreen").pack(pady=5)
        tk.Button(btn_frame, text="Update", command=self.update, width=10, font=("times new roman", 14), bg="lightblue").pack(pady=5)
        tk.Button(btn_frame, text="Delete", command=self.delete, width=10, font=("times new roman", 14), bg="lightcoral").pack(pady=5)
        tk.Button(btn_frame, text="Clear", command=self.clear, width=10, font=("times new roman", 14), bg="lightgray").pack(pady=5)

        # Search
        search_frame = tk.LabelFrame(self.window, text="Search", font=("times new roman", 12, "bold"),
                                     bg="white", bd=2, relief=tk.GROOVE)
        search_frame.place(x=20, y=230, width=1150, height=70)

        tk.Label(search_frame, text="Search By:", font=("times new roman", 13), bg="white").grid(row=0, column=0, padx=10)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=["pid", "name", "category", "supplier"], state="readonly").grid(row=0, column=1, padx=10)
        tk.Label(search_frame, text="Search Text:", font=("times new roman", 13), bg="white").grid(row=0, column=2, padx=10)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, font=("times new roman", 13)).grid(row=0, column=3, padx=10)
        tk.Button(search_frame, text="Search", command=self.search, font=("times new roman", 13), bg="lightyellow").grid(row=0, column=4, padx=10)

        # Treeview
        tree_frame = tk.LabelFrame(self.window, text="Product List", font=("times new roman", 12, "bold"),
                                   bg="white", bd=2, relief=tk.GROOVE)
        tree_frame.place(x=20, y=310, width=1150, height=260)

        scroll_y = tk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scroll_x = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        self.ProductTable = ttk.Treeview(tree_frame,
                                         columns=("pid","name","category","supplier","price","qty","status"),
                                         yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.config(command=self.ProductTable.yview)
        scroll_x.config(command=self.ProductTable.xview)
        self.ProductTable["show"] = "headings"
        columns = ("pid","name","category","supplier","price","qty","status")
        widths = (60,150,100,100,80,80,80)
        for col, w in zip(columns, widths):
            self.ProductTable.heading(col, text=col.capitalize())
            self.ProductTable.column(col, width=w)
        self.ProductTable.pack(fill=tk.BOTH, expand=1)
        self.ProductTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def fetch_cat_sup(self):
        db = Database.get_instance()
        db.cursor.execute("SELECT name FROM category")
        self.cat_list = [row[0] for row in db.cursor.fetchall()]
        db.cursor.execute("SELECT name FROM supplier")
        self.sup_list = [row[0] for row in db.cursor.fetchall()]
        if hasattr(self, 'combo_cat'):
            self.combo_cat['values'] = self.cat_list
        if hasattr(self, 'combo_sup'):
            self.combo_sup['values'] = self.sup_list

    def clear(self):
        self.var_pid.set("")
        self.var_name.set("")
        self.var_cat.set("")
        self.var_sup.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("")

    def add(self):
        if not self.var_name.get() or not self.var_cat.get() or not self.var_sup.get():
            messagebox.showerror("Error", "Name, Category, Supplier are required")
            return
        db = Database.get_instance()
        # get category id
        db.cursor.execute("SELECT cid FROM category WHERE name=?", (self.var_cat.get(),))
        cat = db.cursor.fetchone()
        if not cat:
            messagebox.showerror("Error", "Invalid category")
            return
        db.cursor.execute("SELECT invoice FROM supplier WHERE name=?", (self.var_sup.get(),))
        sup = db.cursor.fetchone()
        if not sup:
            messagebox.showerror("Error", "Invalid supplier")
            return
        db.cursor.execute("INSERT INTO product (name, category, supplier, price, qty, status) VALUES (?, ?, ?, ?, ?, ?)",
                          (self.var_name.get(), cat[0], sup[0], self.var_price.get(), self.var_qty.get(), self.var_status.get()))
        db.conn.commit()
        messagebox.showinfo("Success", "Product added")
        self.show()
        self.clear()

    def update(self):
        if not self.var_pid.get():
            messagebox.showerror("Error", "Select product to update")
            return
        db = Database.get_instance()
        db.cursor.execute("SELECT cid FROM category WHERE name=?", (self.var_cat.get(),))
        cat = db.cursor.fetchone()
        if not cat:
            messagebox.showerror("Error", "Invalid category")
            return
        db.cursor.execute("SELECT invoice FROM supplier WHERE name=?", (self.var_sup.get(),))
        sup = db.cursor.fetchone()
        if not sup:
            messagebox.showerror("Error", "Invalid supplier")
            return
        db.cursor.execute("UPDATE product SET name=?, category=?, supplier=?, price=?, qty=?, status=? WHERE pid=?",
                          (self.var_name.get(), cat[0], sup[0], self.var_price.get(), self.var_qty.get(), self.var_status.get(), self.var_pid.get()))
        db.conn.commit()
        messagebox.showinfo("Success", "Product updated")
        self.show()
        self.clear()

    def delete(self):
        if not self.var_pid.get():
            messagebox.showerror("Error", "Select product to delete")
            return
        db = Database.get_instance()
        db.cursor.execute("DELETE FROM product WHERE pid=?", (self.var_pid.get(),))
        db.conn.commit()
        messagebox.showinfo("Success", "Product deleted")
        self.show()
        self.clear()

    def show(self):
        db = Database.get_instance()
        db.cursor.execute("""SELECT p.pid, p.name, c.name, s.name, p.price, p.qty, p.status
                             FROM product p
                             LEFT JOIN category c ON p.category = c.cid
                             LEFT JOIN supplier s ON p.supplier = s.invoice""")
        rows = db.cursor.fetchall()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for row in rows:
            self.ProductTable.insert("", tk.END, values=row)

    def get_data(self, ev):
        selected = self.ProductTable.focus()
        if selected:
            values = self.ProductTable.item(selected, 'values')
            self.var_pid.set(values[0])
            self.var_name.set(values[1])
            self.var_cat.set(values[2])
            self.var_sup.set(values[3])
            self.var_price.set(values[4])
            self.var_qty.set(values[5])
            self.var_status.set(values[6])

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get()
        if not by or not txt:
            messagebox.showerror("Error", "Select search criteria")
            return
        db = Database.get_instance()
        if by == "category":
            query = """SELECT p.pid, p.name, c.name, s.name, p.price, p.qty, p.status
                       FROM product p
                       LEFT JOIN category c ON p.category = c.cid
                       LEFT JOIN supplier s ON p.supplier = s.invoice
                       WHERE c.name LIKE ?"""
        elif by == "supplier":
            query = """SELECT p.pid, p.name, c.name, s.name, p.price, p.qty, p.status
                       FROM product p
                       LEFT JOIN category c ON p.category = c.cid
                       LEFT JOIN supplier s ON p.supplier = s.invoice
                       WHERE s.name LIKE ?"""
        elif by == "pid":
            query = """SELECT p.pid, p.name, c.name, s.name, p.price, p.qty, p.status
                       FROM product p
                       LEFT JOIN category c ON p.category = c.cid
                       LEFT JOIN supplier s ON p.supplier = s.invoice
                       WHERE p.pid LIKE ?"""
        else:  # name
            query = """SELECT p.pid, p.name, c.name, s.name, p.price, p.qty, p.status
                       FROM product p
                       LEFT JOIN category c ON p.category = c.cid
                       LEFT JOIN supplier s ON p.supplier = s.invoice
                       WHERE p.name LIKE ?"""
        db.cursor.execute(query, ('%'+txt+'%',))
        rows = db.cursor.fetchall()
        self.ProductTable.delete(*self.ProductTable.get_children())
        for row in rows:
            self.ProductTable.insert("", tk.END, values=row)

# ------------------------------ salesClass ----------------------------------
class salesClass:
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel(self.root)
        self.window.title("Sales Records")
        self.window.geometry("1100x550+150+80")
        self.window.config(bg="white")

        self.var_invoice = tk.StringVar()
        self.blll_list = []
        self.bill_photo = None  # placeholder

        # Top search
        search_frame = tk.LabelFrame(self.window, text="Search Invoice", font=("times new roman", 12, "bold"),
                                     bg="white", bd=2, relief=tk.GROOVE)
        search_frame.place(x=20, y=20, width=1060, height=70)

        tk.Label(search_frame, text="Invoice No:", font=("times new roman", 13), bg="white").grid(row=0, column=0, padx=10)
        tk.Entry(search_frame, textvariable=self.var_invoice, font=("times new roman", 13)).grid(row=0, column=1, padx=10)
        tk.Button(search_frame, text="Search", command=self.search, font=("times new roman", 13), bg="lightyellow").grid(row=0, column=2, padx=10)
        tk.Button(search_frame, text="Clear", command=self.clear, font=("times new roman", 13), bg="lightgray").grid(row=0, column=3, padx=10)

        # Sales list
        list_frame = tk.LabelFrame(self.window, text="Sales List", font=("times new roman", 12, "bold"),
                                   bg="white", bd=2, relief=tk.GROOVE)
        list_frame.place(x=20, y=100, width=400, height=400)

        self.Sales_List = tk.Listbox(list_frame, font=("times new roman", 12))
        self.Sales_List.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        scroll_y_list = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.Sales_List.yview)
        scroll_y_list.pack(side=tk.RIGHT, fill=tk.Y)
        self.Sales_List.config(yscrollcommand=scroll_y_list.set)
        self.Sales_List.bind("<<ListboxSelect>>", self.get_data)

        # Bill display
        bill_frame = tk.LabelFrame(self.window, text="Bill Details", font=("times new roman", 12, "bold"),
                                   bg="white", bd=2, relief=tk.GROOVE)
        bill_frame.place(x=440, y=100, width=640, height=400)

        self.bill_area = tk.Text(bill_frame, font=("times new roman", 12), state=tk.DISABLED)
        self.bill_area.pack(fill=tk.BOTH, expand=1)

        self.show()

    def show(self):
        db = Database.get_instance()
        db.cursor.execute("SELECT invoice, date FROM sales ORDER BY date DESC")
        rows = db.cursor.fetchall()
        self.Sales_List.delete(0, tk.END)
        self.blll_list = rows
        for row in rows:
            self.Sales_List.insert(tk.END, f"{row[0]} - {row[1]}")

    def get_data(self, ev):
        selection = self.Sales_List.curselection()
        if selection:
            index = selection[0]
            invoice_no = self.blll_list[index][0]
            self.var_invoice.set(invoice_no)
            self.display_bill(invoice_no)

    def search(self):
        invoice = self.var_invoice.get()
        if not invoice:
            messagebox.showerror("Error", "Enter invoice number")
            return
        db = Database.get_instance()
        db.cursor.execute("SELECT * FROM sales WHERE invoice=?", (invoice,))
        sale = db.cursor.fetchone()
        if not sale:
            messagebox.showerror("Not Found", "Invoice not found")
            return
        self.display_bill(invoice)

    def clear(self):
        self.var_invoice.set("")
        self.bill_area.config(state=tk.NORMAL)
        self.bill_area.delete("1.0", tk.END)
        self.bill_area.config(state=tk.DISABLED)

    def display_bill(self, invoice):
        db = Database.get_instance()
        db.cursor.execute("SELECT * FROM sales WHERE invoice=?", (invoice,))
        sale = db.cursor.fetchone()
        db.cursor.execute("SELECT * FROM sales_item WHERE sales_invoice=?", (invoice,))
        items = db.cursor.fetchall()

        bill_text = f"Invoice: {sale[1]}\n"
        bill_text += f"Date: {sale[2]}\n"
        bill_text += "-"*40 + "\n"
        bill_text += "Product\tQty\tPrice\tTotal\n"
        total = 0
        for item in items:
            bill_text += f"{item[3]}\t{item[5]}\t{item[4]}\t{item[6]}\n"
            total += item[6]
        bill_text += "-"*40 + "\n"
        bill_text += f"Total: {sale[3]}\n"
        bill_text += f"Discount: {sale[4]}\n"
        bill_text += f"Net Pay: {sale[5]}\n"
        self.bill_area.config(state=tk.NORMAL)
        self.bill_area.delete("1.0", tk.END)
        self.bill_area.insert(tk.END, bill_text)
        self.bill_area.config(state=tk.DISABLED)

# ------------------------------ supplierClass -------------------------------
class supplierClass:
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel(self.root)
        self.window.title("Supplier Management")
        self.window.geometry("1000x600+150+50")
        self.window.config(bg="white")

        self.var_sup_invoice = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_contact = tk.StringVar()
        self.var_searchby = tk.StringVar()
        self.var_searchtxt = tk.StringVar()

        self.txt_desc = None

        # Top
        top_frame = tk.LabelFrame(self.window, text="Supplier Details", font=("times new roman", 14, "bold"),
                                  bg="white", bd=2, relief=tk.GROOVE)
        top_frame.place(x=20, y=20, width=960, height=200)

        tk.Label(top_frame, text="Invoice:", font=("times new roman", 13), bg="white").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        tk.Entry(top_frame, textvariable=self.var_sup_invoice, state='readonly', font=("times new roman", 13)).grid(row=0, column=1, padx=10, pady=5)

        tk.Label(top_frame, text="Name:", font=("times new roman", 13), bg="white").grid(row=0, column=2, padx=10, pady=5, sticky="w")
        tk.Entry(top_frame, textvariable=self.var_name, font=("times new roman", 13)).grid(row=0, column=3, padx=10, pady=5)

        tk.Label(top_frame, text="Contact:", font=("times new roman", 13), bg="white").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        tk.Entry(top_frame, textvariable=self.var_contact, font=("times new roman", 13)).grid(row=1, column=1, padx=10, pady=5)

        tk.Label(top_frame, text="Description:", font=("times new roman", 13), bg="white").grid(row=1, column=2, padx=10, pady=5, sticky="w")
        self.txt_desc = tk.Text(top_frame, font=("times new roman", 13), width=25, height=3)
        self.txt_desc.grid(row=1, column=3, padx=10, pady=5)

        btn_frame = tk.Frame(top_frame, bg="white")
        btn_frame.grid(row=0, column=4, rowspan=2, padx=20)
        tk.Button(btn_frame, text="Add", command=self.add, width=10, font=("times new roman", 14), bg="lightgreen").pack(pady=5)
        tk.Button(btn_frame, text="Update", command=self.update, width=10, font=("times new roman", 14), bg="lightblue").pack(pady=5)
        tk.Button(btn_frame, text="Delete", command=self.delete, width=10, font=("times new roman", 14), bg="lightcoral").pack(pady=5)
        tk.Button(btn_frame, text="Clear", command=self.clear, width=10, font=("times new roman", 14), bg="lightgray").pack(pady=5)

        # Search
        search_frame = tk.LabelFrame(self.window, text="Search", font=("times new roman", 12, "bold"),
                                     bg="white", bd=2, relief=tk.GROOVE)
        search_frame.place(x=20, y=230, width=960, height=70)

        tk.Label(search_frame, text="Search By:", font=("times new roman", 13), bg="white").grid(row=0, column=0, padx=10)
        ttk.Combobox(search_frame, textvariable=self.var_searchby, values=["invoice", "name"], state="readonly").grid(row=0, column=1, padx=10)
        tk.Label(search_frame, text="Search Text:", font=("times new roman", 13), bg="white").grid(row=0, column=2, padx=10)
        tk.Entry(search_frame, textvariable=self.var_searchtxt, font=("times new roman", 13)).grid(row=0, column=3, padx=10)
        tk.Button(search_frame, text="Search", command=self.search, font=("times new roman", 13), bg="lightyellow").grid(row=0, column=4, padx=10)

        # Tree
        tree_frame = tk.LabelFrame(self.window, text="Supplier List", font=("times new roman", 12, "bold"),
                                   bg="white", bd=2, relief=tk.GROOVE)
        tree_frame.place(x=20, y=310, width=960, height=260)

        scroll_y = tk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        self.SupplierTable = ttk.Treeview(tree_frame, columns=("invoice","name","contact","desc"),
                                          yscrollcommand=scroll_y.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_y.config(command=self.SupplierTable.yview)
        self.SupplierTable.heading("invoice", text="Invoice")
        self.SupplierTable.heading("name", text="Name")
        self.SupplierTable.heading("contact", text="Contact")
        self.SupplierTable.heading("desc", text="Description")
        self.SupplierTable["show"] = "headings"
        self.SupplierTable.column("invoice", width=80)
        self.SupplierTable.column("name", width=150)
        self.SupplierTable.column("contact", width=120)
        self.SupplierTable.column("desc", width=200)
        self.SupplierTable.pack(fill=tk.BOTH, expand=1)
        self.SupplierTable.bind("<ButtonRelease-1>", self.get_data)

        self.show()

    def clear(self):
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete("1.0", tk.END)

    def add(self):
        if not self.var_name.get():
            messagebox.showerror("Error", "Supplier name required")
            return
        db = Database.get_instance()
        db.cursor.execute("INSERT INTO supplier (name, contact, desc) VALUES (?, ?, ?)",
                          (self.var_name.get(), self.var_contact.get(), self.txt_desc.get("1.0", tk.END).strip()))
        db.conn.commit()
        messagebox.showinfo("Success", "Supplier added")
        self.show()
        self.clear()

    def update(self):
        if not self.var_sup_invoice.get():
            messagebox.showerror("Error", "Select supplier to update")
            return
        db = Database.get_instance()
        db.cursor.execute("UPDATE supplier SET name=?, contact=?, desc=? WHERE invoice=?",
                          (self.var_name.get(), self.var_contact.get(), self.txt_desc.get("1.0", tk.END).strip(), self.var_sup_invoice.get()))
        db.conn.commit()
        messagebox.showinfo("Success", "Supplier updated")
        self.show()
        self.clear()

    def delete(self):
        if not self.var_sup_invoice.get():
            messagebox.showerror("Error", "Select supplier to delete")
            return
        db = Database.get_instance()
        db.cursor.execute("DELETE FROM supplier WHERE invoice=?", (self.var_sup_invoice.get(),))
        db.conn.commit()
        messagebox.showinfo("Success", "Supplier deleted")
        self.show()
        self.clear()

    def show(self):
        db = Database.get_instance()
        db.cursor.execute("SELECT * FROM supplier")
        rows = db.cursor.fetchall()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert("", tk.END, values=row)

    def get_data(self, ev):
        selected = self.SupplierTable.focus()
        if selected:
            values = self.SupplierTable.item(selected, 'values')
            self.var_sup_invoice.set(values[0])
            self.var_name.set(values[1])
            self.var_contact.set(values[2])
            self.txt_desc.delete("1.0", tk.END)
            self.txt_desc.insert(tk.END, values[3])

    def search(self):
        by = self.var_searchby.get()
        txt = self.var_searchtxt.get()
        if not by or not txt:
            messagebox.showerror("Error", "Select search criteria")
            return
        db = Database.get_instance()
        if by == "invoice":
            query = "SELECT * FROM supplier WHERE invoice LIKE ?"
        else:
            query = "SELECT * FROM supplier WHERE name LIKE ?"
        db.cursor.execute(query, ('%'+txt+'%',))
        rows = db.cursor.fetchall()
        self.SupplierTable.delete(*self.SupplierTable.get_children())
        for row in rows:
            self.SupplierTable.insert("", tk.END, values=row)

# ------------------------------ IMS Dashboard ---------------------------------
class IMS:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Inventory Management System")
        self.root.geometry("1200x700+100+50")
        self.root.config(bg="white")

        self.new_obj = None  # placeholder
        self.new_win = None

        # Images
        self.MenuLogo = None
        self.icon_side = tk.PhotoImage(width=50, height=50) if tk.PhotoImage else None
        self.icon_title = tk.PhotoImage(width=100, height=50) if tk.PhotoImage else None

        # Top bar
        title_frame = tk.Frame(self.root, bg="darkblue", bd=2, relief=tk.RAISED)
        title_frame.place(x=0, y=0, width=1200, height=80)

        tk.Label(title_frame, text="Inventory Management System", font=("times new roman", 25, "bold"), bg="darkblue", fg="white").pack(pady=15)

        # Side menu frame
        menu_frame = tk.Frame(self.root, bg="darkblue", width=200, height=600)
        menu_frame.place(x=0, y=80, width=200, height=600)

        # Side buttons
        buttons = [
            ("Category", self.category),
            ("Employee", self.employee),
            ("Product", self.product),
            ("Supplier", self.supplier),
            ("Sales", self.sales),
            ("Billing", self.billing),
        ]
        y_pos = 30
        for text, cmd in buttons:
            btn = tk.Button(menu_frame, text=text, command=cmd, font=("times new roman", 14, "bold"),
                            bg="white", fg="darkblue", width=15, relief=tk.RAISED, border=2)
            btn.place(x=15, y=y_pos, width=170, height=45)
            y_pos += 65

        # Main content area placeholder
        content_frame = tk.Frame(self.root, bg="white", bd=2, relief=tk.SUNKEN)
        content_frame.place(x=200, y=80, width=1000, height=600)

        self.lbl_clock = tk.Label(content_frame, font=("times new roman", 15), bg="white")
        self.lbl_clock.pack(pady=5)
        self.update_content()

        self.lbl_category = tk.Label(content_frame, text="Click on Category to manage", font=("times new roman", 18), bg="white")
        self.lbl_employee = tk.Label(content_frame, text="Click on Employee to manage", font=("times new roman", 18), bg="white")
        self.lbl_product = tk.Label(content_frame, text="Click on Product to manage", font=("times new roman", 18), bg="white")
        self.lbl_supplier = tk.Label(content_frame, text="Click on Supplier to manage", font=("times new roman", 18), bg="white")
        self.lbl_sales = tk.Label(content_frame, text="Click on Sales to view records", font=("times new roman", 18), bg="white")

        # hide all initially
        for lbl in [self.lbl_category, self.lbl_employee, self.lbl_product, self.lbl_supplier, self.lbl_sales]:
            lbl.pack_forget()

    def update_content(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.config(text=now)
        self.root.after(1000, self.update_content)

    def category(self):
        self.new_obj = categoryClass(self.root)
        self.new_win = self.new_obj.window

    def employee(self):
        self.new_obj = employeeClass(self.root)
        self.new_win = self.new_obj.window

    def product(self):
        self.new_obj = productClass(self.root)
        self.new_win = self.new_obj.window

    def sales(self):
        self.new_obj = salesClass(self.root)
        self.new_win = self.new_obj.window

    def supplier(self):
        self.new_obj = supplierClass(self.root)
        self.new_win = self.new_obj.window

    def billing(self):
        self.new_obj = billClass(self.root)
        self.new_win = self.new_obj.window

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = IMS()
    app.run()