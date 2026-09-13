import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
import sqlite3
import os
import datetime
from tkinter import filedialog

# ----------------------------- Database Setup -----------------------------
DB_NAME = "inventory.db"

def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT,
            email TEXT,
            role TEXT
        );
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT,
            email TEXT,
            address TEXT
        );
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        );
        CREATE TABLE IF NOT EXISTS bills (
            invoice_no TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            customer_name TEXT,
            contact TEXT,
            total_amount REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS bill_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT NOT NULL,
            product_id INTEGER,
            product_name TEXT,
            price REAL,
            quantity INTEGER,
            total REAL,
            FOREIGN KEY (invoice_no) REFERENCES bills(invoice_no),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    """)
    conn.commit()
    conn.close()

# ----------------------------- Main Application Class -----------------------------
class InventoryManagementSystem(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inventory Management System")
        self.geometry("1100x700")
        self.configure(bg="#f0f0f0")
        self.iconbitmap(self._get_icon_path())
        setup_database()
        self.conn = sqlite3.connect(DB_NAME)
        self.create_widgets()
        self.update_clock()
    
    def _get_icon_path(self):
        # Try to load a default icon if exists; else return empty string
        for path in ["icon.ico", "inventory.ico"]:
            if os.path.exists(path):
                return path
        return ""
    
    def create_widgets(self):
        # Left navigation panel
        nav_frame = tk.Frame(self, bg="#2c3e50", width=200)
        nav_frame.pack(side="left", fill="y")
        nav_frame.pack_propagate(False)
        
        tk.Label(nav_frame, text="Dashboard", font=("Arial", 16, "bold"), bg="#2c3e50", fg="white").pack(pady=20)
        
        buttons = [
            ("Employee", self.show_employee_mgmt),
            ("Supplier", self.show_supplier_mgmt),
            ("Category", self.show_category_mgmt),
            ("Product", self.show_product_mgmt),
            ("Billing", self.show_billing),
            ("Bill History", self.show_bill_history),
            ("Exit", self.exit_app)
        ]
        
        for text, cmd in buttons:
            btn = tk.Button(nav_frame, text=text, font=("Arial", 12), bg="#34495e", fg="white",
                            activebackground="#1abc9c", relief="flat", command=cmd, width=18, pady=5)
            btn.pack(pady=5)
        
        # Right content area
        self.content_frame = tk.Frame(self, bg="#ecf0f1")
        self.content_frame.pack(side="right", expand=True, fill="both")
        
        # Welcome/Clock header
        self.header_label = tk.Label(self.content_frame, text="Inventory Management System",
                                     font=("Arial", 20, "bold"), bg="#ecf0f1", fg="#2c3e50")
        self.header_label.pack(pady=10)
        self.clock_label = tk.Label(self.content_frame, font=("Arial", 14), bg="#ecf0f1", fg="#7f8c8d")
        self.clock_label.pack()
        
        # Dashboard container frame (holds buttons/images)
        self.dashboard_frame = tk.Frame(self.content_frame, bg="#ecf0f1")
        self.dashboard_frame.pack(expand=True, fill="both", pady=20)
        
        self.show_dashboard()
    
    def update_clock(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        self.clock_label.config(text=now)
        self.after(1000, self.update_clock)
    
    def clear_content(self):
        for widget in self.dashboard_frame.winfo_children():
            widget.destroy()
    
    def show_dashboard(self):
        self.clear_content()
        # Load and display an image (placeholder)
        try:
            image = Image.open("inventory_bg.png")
            image = image.resize((600, 400), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            img_label = tk.Label(self.dashboard_frame, image=photo, bg="#ecf0f1")
            img_label.image = photo
            img_label.pack(pady=10)
        except Exception:
            pass
        
        # Dashboard quick stat buttons (just visual)
        btn_frame = tk.Frame(self.dashboard_frame, bg="#ecf0f1")
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="Manage Employees", command=self.show_employee_mgmt, bg="#3498db", fg="white",
                  font=("Arial", 12), width=18).grid(row=0, column=0, padx=10, pady=5)
        tk.Button(btn_frame, text="Manage Suppliers", command=self.show_supplier_mgmt, bg="#3498db", fg="white",
                  font=("Arial", 12), width=18).grid(row=0, column=1, padx=10, pady=5)
        tk.Button(btn_frame, text="Manage Categories", command=self.show_category_mgmt, bg="#3498db", fg="white",
                  font=("Arial", 12), width=18).grid(row=0, column=2, padx=10, pady=5)
        tk.Button(btn_frame, text="Manage Products", command=self.show_product_mgmt, bg="#3498db", fg="white",
                  font=("Arial", 12), width=18).grid(row=1, column=0, padx=10, pady=5)
        tk.Button(btn_frame, text="New Bill", command=self.show_billing, bg="#e67e22", fg="white",
                  font=("Arial", 12), width=18).grid(row=1, column=1, padx=10, pady=5)
        tk.Button(btn_frame, text="Bill History", command=self.show_bill_history, bg="#e67e22", fg="white",
                  font=("Arial", 12), width=18).grid(row=1, column=2, padx=10, pady=5)
    
    # ------------------- Common CRUD Template -------------------
    def generic_crud_window(self, title, table, columns, id_col='id', ref_widgets=None):
        window = tk.Toplevel(self)
        window.title(title)
        window.geometry("800x500")
        window.resizable(False, False)
        
        # Form frame
        form_frame = tk.Frame(window, bg="#bdc3c7", pady=10)
        form_frame.pack(fill="x", padx=10, pady=5)
        
        entries = {}
        row = 0
        for col in columns:
            if col == id_col:
                continue  # skip ID, auto-increment
            tk.Label(form_frame, text=col.capitalize()+":", bg="#bdc3c7", font=("Arial", 10)).grid(row=row, column=0, padx=5, pady=5, sticky="e")
            if col == 'category_id' and ref_widgets:
                # special dropdown for categories
                combo = ttk.Combobox(form_frame, values=ref_widgets, state="readonly", width=20)
                combo.grid(row=row, column=1, padx=5, pady=5, sticky="w")
                entries[col] = combo
            else:
                entry = tk.Entry(form_frame, width=25)
                entry.grid(row=row, column=1, padx=5, pady=5, sticky="w")
                entries[col] = entry
            row += 1
        
        # Buttons
        btn_frame = tk.Frame(window, bg="#bdc3c7")
        btn_frame.pack(fill="x", pady=5)
        
        def clear_form():
            for e in entries.values():
                if isinstance(e, ttk.Combobox):
                    e.set('')
                else:
                    e.delete(0, tk.END)
        
        def add_record():
            values = []
            for col in columns:
                if col == id_col:
                    continue
                val = entries[col].get()
                if not val and col != 'category_id':
                    messagebox.showerror("Error", f"{col} cannot be empty")
                    return
                values.append(val)
            placeholders = ','.join(['?']*len(values))
            sql = f"INSERT INTO {table} ({','.join([c for c in columns if c!=id_col])}) VALUES ({placeholders})"
            try:
                self.conn.execute(sql, values)
                self.conn.commit()
                messagebox.showinfo("Success", "Record added")
                clear_form()
                refresh_tree()
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        def update_record():
            selected = tree.selection()
            if not selected:
                messagebox.showerror("Error", "Select a record to update")
                return
            record_id = tree.item(selected[0], 'values')[0]
            values = []
            set_clause = []
            for col in columns:
                if col == id_col:
                    continue
                val = entries[col].get()
                if not val and col != 'category_id':
                    messagebox.showerror("Error", f"{col} cannot be empty")
                    return
                set_clause.append(f"{col}=?")
                values.append(val)
            values.append(record_id)
            sql = f"UPDATE {table} SET {','.join(set_clause)} WHERE {id_col}=?"
            try:
                self.conn.execute(sql, values)
                self.conn.commit()
                messagebox.showinfo("Success", "Record updated")
                clear_form()
                refresh_tree()
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        def delete_record():
            selected = tree.selection()
            if not selected:
                messagebox.showerror("Error", "Select a record to delete")
                return
            if messagebox.askyesno("Confirm", "Delete this record?"):
                record_id = tree.item(selected[0], 'values')[0]
                sql = f"DELETE FROM {table} WHERE {id_col}=?"
                try:
                    self.conn.execute(sql, (record_id,))
                    self.conn.commit()
                    refresh_tree()
                except Exception as e:
                    messagebox.showerror("Error", str(e))
        
        def on_tree_select(event):
            selected = tree.selection()
            if selected:
                values = tree.item(selected[0], 'values')
                i = 0
                for col in columns:
                    if col == id_col:
                        i += 1
                        continue
                    if col == 'category_id' and ref_widgets:
                        entries[col].set(values[i])
                    else:
                        entries[col].delete(0, tk.END)
                        entries[col].insert(0, values[i])
                    i += 1
        
        tk.Button(btn_frame, text="Add", command=add_record, bg="#27ae60", fg="white", width=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Update", command=update_record, bg="#2980b9", fg="white", width=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Delete", command=delete_record, bg="#c0392b", fg="white", width=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Clear", command=clear_form, bg="#95a5a6", fg="white", width=10).pack(side="left", padx=5)
        
        # Treeview
        tree_frame = tk.Frame(window)
        tree_frame.pack(expand=True, fill="both", padx=10, pady=5)
        tree_scroll_y = tk.Scrollbar(tree_frame, orient="vertical")
        tree_scroll_x = tk.Scrollbar(tree_frame, orient="horizontal")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                            yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        tree_scroll_y.config(command=tree.yview)
        tree_scroll_x.config(command=tree.xview)
        tree_scroll_y.pack(side="right", fill="y")
        tree_scroll_x.pack(side="bottom", fill="x")
        tree.pack(expand=True, fill="both")
        
        for col in columns:
            tree.heading(col, text=col.capitalize())
            tree.column(col, width=100, anchor="center")
        
        tree.bind("<<TreeviewSelect>>", on_tree_select)
        
        def refresh_tree():
            for item in tree.get_children():
                tree.delete(item)
            cur = self.conn.cursor()
            cur.execute(f"SELECT * FROM {table}")
            rows = cur.fetchall()
            for row in rows:
                tree.insert("", "end", values=row)
        
        refresh_tree()
        return window
    
    # ------------------- Module Methods -------------------
    def show_employee_mgmt(self):
        self.clear_content()
        self.generic_crud_window("Employee Management", "employees", 
                                 columns=["id", "name", "contact", "email", "role"])
    
    def show_supplier_mgmt(self):
        self.clear_content()
        self.generic_crud_window("Supplier Management", "suppliers",
                                 columns=["id", "name", "contact", "email", "address"])
    
    def show_category_mgmt(self):
        self.clear_content()
        self.generic_crud_window("Category Management", "categories",
                                 columns=["id", "name"])
    
    def show_product_mgmt(self):
        self.clear_content()
        # Fetch categories for dropdown
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM categories")
        cat_names = [row[0] for row in cur.fetchall()]
        if not cat_names:
            messagebox.showwarning("Warning", "Add categories first!")
            return
        self.generic_crud_window("Product Management", "products",
                                 columns=["id", "name", "category_id", "price", "quantity"],
                                 ref_widgets=cat_names)
    
    # ------------------- Billing Module -------------------
    def show_billing(self):
        self.clear_content()
        bill_window = tk.Toplevel(self)
        bill_window.title("New Billing")
        bill_window.geometry("900x650")
        bill_window.resizable(False, False)
        
        # Customer info
        top_frame = tk.Frame(bill_window, bg="#ecf0f1", pady=10)
        top_frame.pack(fill="x", padx=10)
        tk.Label(top_frame, text="Customer Name:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        customer_name = tk.Entry(top_frame, width=25)
        customer_name.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(top_frame, text="Contact:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        customer_contact = tk.Entry(top_frame, width=25)
        customer_contact.grid(row=0, column=3, padx=5, pady=5)
        
        # Product selection
        selection_frame = tk.Frame(bill_window, bg="#bdc3c7", pady=10)
        selection_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(selection_frame, text="Select Product:").grid(row=0, column=0, padx=5, pady=5)
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, price, quantity FROM products")
        products = cur.fetchall()
        product_list = [f"{p[0]} - {p[1]} (₹{p[2]})" for p in products] if products else ["No products"]
        product_var = tk.StringVar()
        product_combo = ttk.Combobox(selection_frame, textvariable=product_var, values=product_list, state="readonly", width=40)
        product_combo.grid(row=0, column=1, padx=5, pady=5)
        if products:
            product_combo.current(0)
        
        tk.Label(selection_frame, text="Quantity:").grid(row=0, column=2, padx=5, pady=5)
        qty_entry = tk.Entry(selection_frame, width=10)
        qty_entry.grid(row=0, column=3, padx=5, pady=5)
        qty_entry.insert(0, "1")
        
        # Buttons to add item
        cart = []  # each item: [id, name, price, qty, total]
        cart_tree = None
        
        def add_to_cart():
            nonlocal cart_tree
            selected = product_combo.get()
            if not selected or selected == "No products":
                messagebox.showerror("Error", "Select a product")
                return
            pid = int(selected.split(" - ")[0])
            pname = selected.split(" - ")[1].split(" (")[0]
            price = float(selected.split("(₹")[1].strip(")"))
            try:
                qty = int(qty_entry.get())
                if qty <= 0:
                    raise ValueError
            except:
                messagebox.showerror("Error", "Invalid quantity")
                return
            # Check stock
            stock = next((p[3] for p in products if p[0]==pid), 0)
            already_in_cart = sum(item[3] for item in cart if item[0]==pid)
            if (already_in_cart + qty) > stock:
                messagebox.showerror("Error", f"Insufficient stock. Available: {stock - already_in_cart}")
                return
            total = price * qty
            cart.append([pid, pname, price, qty, total])
            refresh_cart()
        
        def refresh_cart():
            nonlocal cart_tree
            cart_tree.delete(*cart_tree.get_children())
            total_bill = 0
            for item in cart:
                cart_tree.insert("", "end", values=(item[0], item[1], f"₹{item[2]}", item[3], f"₹{item[4]}"))
                total_bill += item[4]
            total_label.config(text=f"Total: ₹{total_bill:.2f}")
        
        def remove_item():
            nonlocal cart_tree
            selected = cart_tree.selection()
            if not selected:
                return
            index = cart_tree.index(selected[0])
            cart.pop(index)
            refresh_cart()
        
        # Cart frame
        cart_frame = tk.Frame(bill_window)
        cart_frame.pack(expand=True, fill="both", padx=10, pady=10)
        cart_tree = ttk.Treeview(cart_frame, columns=("pid", "name", "price", "qty", "total"), show="headings")
        cart_tree.heading("pid", text="Product ID")
        cart_tree.heading("name", text="Product Name")
        cart_tree.heading("price", text="Unit Price")
        cart_tree.heading("qty", text="Quantity")
        cart_tree.heading("total", text="Total")
        cart_tree.column("pid", width=80)
        cart_tree.column("name", width=200)
        cart_tree.column("price", width=100)
        cart_tree.column("qty", width=80)
        cart_tree.column("total", width=100)
        cart_tree.pack(side="left", fill="both", expand=True)
        
        scroll_cart = tk.Scrollbar(cart_frame, orient="vertical", command=cart_tree.yview)
        cart_tree.configure(yscrollcommand=scroll_cart.set)
        scroll_cart.pack(side="right", fill="y")
        
        total_label = tk.Label(bill_window, text="Total: ₹0.00", font=("Arial", 14, "bold"), bg="#ecf0f1")
        total_label.pack(pady=5)
        
        # Add/Remove buttons
        btn_frame = tk.Frame(bill_window, bg="#ecf0f1")
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="Add to Cart", command=add_to_cart, bg="#27ae60", fg="white", width=15).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Remove Selected", command=remove_item, bg="#c0392b", fg="white", width=15).pack(side="left", padx=10)
        
        # Generate invoice
        def generate_invoice():
            if not cart:
                messagebox.showerror("Error", "Cart is empty")
                return
            cname = customer_name.get().strip()
            if not cname:
                cname = "Walk-in Customer"
            contact = customer_contact.get().strip()
            # Generate invoice number: INV-YYYYMMDD-HHMMSS
            now = datetime.datetime.now()
            invoice_no = f"INV-{now.strftime('%Y%m%d-%H%M%S')}"
            total_amount = sum(item[4] for item in cart)
            try:
                self.conn.execute("INSERT INTO bills (invoice_no, date, customer_name, contact, total_amount) VALUES (?,?,?,?,?)",
                                  (invoice_no, now.strftime("%Y-%m-%d %H:%M:%S"), cname, contact, total_amount))
                for item in cart:
                    self.conn.execute("INSERT INTO bill_items (invoice_no, product_id, product_name, price, quantity, total) VALUES (?,?,?,?,?,?)",
                                      (invoice_no, item[0], item[1], item[2], item[3], item[4]))
                    # Update stock
                    self.conn.execute("UPDATE products SET quantity = quantity - ? WHERE id = ?", (item[3], item[0]))
                self.conn.commit()
                messagebox.showinfo("Success", f"Invoice {invoice_no} generated. Total: ₹{total_amount:.2f}")
                # Save invoice to text file
                self.save_invoice_file(invoice_no, cname, contact, cart, total_amount)
                bill_window.destroy()
            except Exception as e:
                self.conn.rollback()
                messagebox.showerror("Error", str(e))
        
        tk.Button(bill_window, text="Generate Invoice", command=generate_invoice, bg="#e67e22", fg="white",
                  font=("Arial", 12, "bold"), width=20).pack(pady=10)
    
    def save_invoice_file(self, invoice_no, customer_name, contact, items, total):
        try:
            file_path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=f"{invoice_no}.txt",
                                                     filetypes=[("Text files", "*.txt")])
            if file_path:
                with open(file_path, "w") as f:
                    f.write(f"Invoice No: {invoice_no}\n")
                    f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Customer: {customer_name}\n")
                    f.write(f"Contact: {contact}\n")
                    f.write("-"*40 + "\n")
                    f.write(f"{'Product':<20}{'Qty':>5}{'Price':>10}{'Total':>10}\n")
                    f.write("-"*40 + "\n")
                    for item in items:
                        f.write(f"{item[1]:<20}{item[3]:>5}{item[2]:>10.2f}{item[4]:>10.2f}\n")
                    f.write("-"*40 + "\n")
                    f.write(f"{'Grand Total':>35}{total:>10.2f}\n")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save file: {e}")
    
    def show_bill_history(self):
        self.clear_content()
        window = tk.Toplevel(self)
        window.title("Bill History")
        window.geometry("900x500")
        
        search_frame = tk.Frame(window)
        search_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(search_frame, text="Invoice No:").pack(side="left", padx=5)
        invoice_entry = tk.Entry(search_frame, width=20)
        invoice_entry.pack(side="left", padx=5)
        
        tree = ttk.Treeview(window, columns=("invoice_no", "date", "customer", "contact", "total"), show="headings")
        tree.heading("invoice_no", text="Invoice No")
        tree.heading("date", text="Date")
        tree.heading("customer", text="Customer")
        tree.heading("contact", text="Contact")
        tree.heading("total", text="Total Amount")
        tree.column("invoice_no", width=150)
        tree.column("date", width=120)
        tree.column("customer", width=150)
        tree.column("contact", width=120)
        tree.column("total", width=100)
        tree.pack(expand=True, fill="both", padx=10, pady=5)
        
        def load_all():
            for item in tree.get_children():
                tree.delete(item)
            cur = self.conn.cursor()
            cur.execute("SELECT invoice_no, date, customer_name, contact, total_amount FROM bills ORDER BY date DESC")
            for row in cur.fetchall():
                tree.insert("", "end", values=row)
        
        def search_invoice():
            inv = invoice_entry.get().strip()
            if not inv:
                load_all()
                return
            for item in tree.get_children():
                tree.delete(item)
            cur = self.conn.cursor()
            cur.execute("SELECT invoice_no, date, customer_name, contact, total_amount FROM bills WHERE invoice_no LIKE ?", ('%'+inv+'%',))
            rows = cur.fetchall()
            for row in rows:
                tree.insert("", "end", values=row)
            if not rows:
                messagebox.showinfo("Not Found", "No matching invoice")
        
        def show_invoice_details():
            selected = tree.selection()
            if not selected:
                return
            inv_no = tree.item(selected[0], 'values')[0]
            detail_window = tk.Toplevel(window)
            detail_window.title(f"Invoice {inv_no}")
            detail_window.geometry("600x400")
            tk.Label(detail_window, text=f"Invoice No: {inv_no}", font=("Arial", 14, "bold")).pack(pady=5)
            
            cur = self.conn.cursor()
            cur.execute("SELECT customer_name, contact, date, total_amount FROM bills WHERE invoice_no=?", (inv_no,))
            bill = cur.fetchone()
            if bill:
                tk.Label(detail_window, text=f"Customer: {bill[0]}").pack()
                tk.Label(detail_window, text=f"Contact: {bill[1]}").pack()
                tk.Label(detail_window, text=f"Date: {bill[2]}").pack()
            tk.Label(detail_window, text="Items:", font=("Arial", 12, "bold")).pack(pady=10)
            
            items_tree = ttk.Treeview(detail_window, columns=("name", "price", "qty", "total"), show="headings")
            items_tree.heading("name", text="Product")
            items_tree.heading("price", text="Unit Price")
            items_tree.heading("qty", text="Quantity")
            items_tree.heading("total", text="Total")
            items_tree.column("name", width=200)
            items_tree.column("price", width=100)
            items_tree.column("qty", width=80)
            items_tree.column("total", width=100)
            items_tree.pack(expand=True, fill="both", padx=10, pady=5)
            
            cur.execute("SELECT product_name, price, quantity, total FROM bill_items WHERE invoice_no=?", (inv_no,))
            for row in cur.fetchall():
                items_tree.insert("", "end", values=row)
            
            total_label = tk.Label(detail_window, text=f"Grand Total: ₹{bill[3]:.2f}", font=("Arial", 12, "bold"))
            total_label.pack(pady=5)
        
        btn_frame = tk.Frame(window)
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="Load All", command=load_all, bg="#3498db", fg="white").pack(side="left", padx=10)
        tk.Button(btn_frame, text="Search", command=search_invoice, bg="#27ae60", fg="white").pack(side="left", padx=10)
        tk.Button(btn_frame, text="View Details", command=show_invoice_details, bg="#e67e22", fg="white").pack(side="left", padx=10)
        
        load_all()
    
    def exit_app(self):
        if messagebox.askyesno("Exit", "Are you sure?"):
            self.conn.close()
            self.destroy()

# ----------------------------- Run Application -----------------------------
if __name__ == "__main__":
    app = InventoryManagementSystem()
    app.mainloop()