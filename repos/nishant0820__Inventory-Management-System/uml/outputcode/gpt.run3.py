from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import datetime
import math
import uuid


class PhotoImage:
    def __init__(self, data: Any = None) -> None:
        self.data = data


class Label:
    def __init__(self, text: str = "") -> None:
        self.text = text

    def config(self, text: Optional[str] = None) -> None:
        if text is not None:
            self.text = text


class Entry:
    def __init__(self, text: str = "") -> None:
        self.text = text

    def get(self) -> str:
        return self.text

    def set(self, value: str) -> None:
        self.text = value


class Text:
    def __init__(self, text: str = "") -> None:
        self._text = text

    def get(self) -> str:
        return self._text

    def set(self, value: str) -> None:
        self._text = value

    def clear(self) -> None:
        self._text = ""


class StringVar:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value


class Toplevel:
    def __init__(self, root: Any = None) -> None:
        self.root = root


class Treeview:
    def __init__(self) -> None:
        self._rows: List[Dict[str, Any]] = []
        self._selection_index: Optional[int] = None

    def insert(self, values: Dict[str, Any]) -> None:
        self._rows.append(dict(values))

    def clear(self) -> None:
        self._rows.clear()
        self._selection_index = None

    def get_children(self) -> List[int]:
        return list(range(len(self._rows)))

    def item(self, index: int) -> Dict[str, Any]:
        return dict(self._rows[index])

    def delete(self, index: int) -> None:
        if index < 0 or index >= len(self._rows):
            raise IndexError("Row index out of range")
        del self._rows[index]
        if self._selection_index == index:
            self._selection_index = None
        elif self._selection_index is not None and self._selection_index > index:
            self._selection_index -= 1

    def selection_set(self, index: int) -> None:
        if index < 0 or index >= len(self._rows):
            raise IndexError("Row index out of range")
        self._selection_index = index

    def selection(self) -> Optional[int]:
        return self._selection_index

    def all_rows(self) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._rows]


class Listbox:
    def __init__(self) -> None:
        self._items: List[str] = []
        self._selection_index: Optional[int] = None

    def insert(self, item: str) -> None:
        self._items.append(item)

    def clear(self) -> None:
        self._items.clear()
        self._selection_index = None

    def get(self, index: int) -> str:
        return self._items[index]

    def delete(self, index: int) -> None:
        del self._items[index]
        if self._selection_index == index:
            self._selection_index = None
        elif self._selection_index is not None and self._selection_index > index:
            self._selection_index -= 1

    def size(self) -> int:
        return len(self._items)

    def selection_set(self, index: int) -> None:
        if index < 0 or index >= len(self._items):
            raise IndexError("Index out of range")
        self._selection_index = index

    def curselection(self) -> Optional[int]:
        return self._selection_index

    def all_items(self) -> List[str]:
        return list(self._items)


@dataclass
class Category:
    cat_id: str
    name: str


@dataclass
class Supplier:
    sup_invoice: str
    name: str
    contact: str
    desc: str


@dataclass
class Employee:
    emp_id: str
    name: str
    email: str
    gender: str
    contact: str
    dob: str
    doj: str
    passw: str
    utype: str
    salary: str
    address: str


@dataclass
class Product:
    pid: str
    name: str
    cat: str
    sup: str
    price: float
    qty: int
    status: str


@dataclass
class CartItem:
    pid: str
    pname: str
    price: float
    qty: int
    stock: int

    @property
    def amount(self) -> float:
        return float(self.price) * int(self.qty)


@dataclass
class Invoice:
    invoice_id: str
    customer_name: str
    contact: str
    items: List[CartItem]
    bill_amount: float
    discount: float
    net_pay: float
    created_at: datetime.datetime
    text: str


class InMemoryDB:
    def __init__(self) -> None:
        self.categories: Dict[str, Category] = {}
        self.suppliers: Dict[str, Supplier] = {}
        self.employees: Dict[str, Employee] = {}
        self.products: Dict[str, Product] = {}
        self.invoices: Dict[str, Invoice] = {}

    def next_invoice_id(self) -> str:
        return datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]


class categoryClass:
    def __init__(self, root: Any = None, db: Optional[InMemoryDB] = None) -> None:
        self.root = root
        self._db = db if db is not None else InMemoryDB()

        self.CategoryTable: Treeview = Treeview()
        self.im1: Optional[PhotoImage] = None
        self.im2: Optional[PhotoImage] = None
        self.lbl_im1: Label = Label()
        self.lbl_im2: Label = Label()

        self.var_cat_id: StringVar = StringVar()
        self.var_name: StringVar = StringVar()

    def add(self) -> None:
        cat_id = self.var_cat_id.get().strip()
        name = self.var_name.get().strip()
        if not cat_id:
            raise ValueError("Category ID is required")
        if not name:
            raise ValueError("Category name is required")
        if cat_id in self._db.categories:
            raise ValueError("Category ID already exists")
        self._db.categories[cat_id] = Category(cat_id=cat_id, name=name)
        self.show()
        self.clear()

    def clear(self) -> None:
        self.var_cat_id.set("")
        self.var_name.set("")

    def delete(self) -> None:
        cat_id = self.var_cat_id.get().strip()
        if not cat_id:
            raise ValueError("Category ID is required for delete")
        if cat_id not in self._db.categories:
            raise ValueError("Category not found")
        del self._db.categories[cat_id]
        self.show()
        self.clear()

    def get_data(self, ev: Any) -> None:
        index = self.CategoryTable.selection()
        if index is None:
            return
        row = self.CategoryTable.item(index)
        self.var_cat_id.set(str(row.get("cat_id", "")))
        self.var_name.set(str(row.get("name", "")))

    def show(self) -> None:
        self.CategoryTable.clear()
        for cat in sorted(self._db.categories.values(), key=lambda c: c.cat_id):
            self.CategoryTable.insert({"cat_id": cat.cat_id, "name": cat.name})


class supplierClass:
    def __init__(self, root: Any = None, db: Optional[InMemoryDB] = None) -> None:
        self.root = root
        self._db = db if db is not None else InMemoryDB()

        self.SupplierTable: Treeview = Treeview()
        self.txt_desc: Text = Text()

        self.var_contact: StringVar = StringVar()
        self.var_name: StringVar = StringVar()
        self.var_searchby: StringVar = StringVar()
        self.var_searchtxt: StringVar = StringVar()
        self.var_sup_invoice: StringVar = StringVar()

    def add(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        name = self.var_name.get().strip()
        contact = self.var_contact.get().strip()
        desc = self.txt_desc.get().strip()
        if not sup_invoice:
            raise ValueError("Supplier invoice is required")
        if not name:
            raise ValueError("Supplier name is required")
        if not contact:
            raise ValueError("Supplier contact is required")
        if sup_invoice in self._db.suppliers:
            raise ValueError("Supplier invoice already exists")
        self._db.suppliers[sup_invoice] = Supplier(
            sup_invoice=sup_invoice, name=name, contact=contact, desc=desc
        )
        self.show()
        self.clear()

    def clear(self) -> None:
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.var_searchby.set("")
        self.var_searchtxt.set("")
        self.txt_desc.clear()

    def delete(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        if not sup_invoice:
            raise ValueError("Supplier invoice is required for delete")
        if sup_invoice not in self._db.suppliers:
            raise ValueError("Supplier not found")
        del self._db.suppliers[sup_invoice]
        self.show()
        self.clear()

    def get_data(self, ev: Any) -> None:
        index = self.SupplierTable.selection()
        if index is None:
            return
        row = self.SupplierTable.item(index)
        self.var_sup_invoice.set(str(row.get("sup_invoice", "")))
        self.var_name.set(str(row.get("name", "")))
        self.var_contact.set(str(row.get("contact", "")))
        self.txt_desc.set(str(row.get("desc", "")))

    def search(self) -> None:
        by = self.var_searchby.get().strip()
        txt = self.var_searchtxt.get().strip().lower()
        self.SupplierTable.clear()
        if not by or not txt:
            self.show()
            return

        def match(s: Supplier) -> bool:
            if by == "sup_invoice":
                return txt in s.sup_invoice.lower()
            if by == "name":
                return txt in s.name.lower()
            if by == "contact":
                return txt in s.contact.lower()
            return False

        for s in sorted(self._db.suppliers.values(), key=lambda x: x.sup_invoice):
            if match(s):
                self.SupplierTable.insert(
                    {"sup_invoice": s.sup_invoice, "name": s.name, "contact": s.contact, "desc": s.desc}
                )

    def show(self) -> None:
        self.SupplierTable.clear()
        for s in sorted(self._db.suppliers.values(), key=lambda x: x.sup_invoice):
            self.SupplierTable.insert(
                {"sup_invoice": s.sup_invoice, "name": s.name, "contact": s.contact, "desc": s.desc}
            )

    def update(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        if not sup_invoice:
            raise ValueError("Supplier invoice is required for update")
        if sup_invoice not in self._db.suppliers:
            raise ValueError("Supplier not found")
        name = self.var_name.get().strip()
        contact = self.var_contact.get().strip()
        desc = self.txt_desc.get().strip()
        if not name:
            raise ValueError("Supplier name is required")
        if not contact:
            raise ValueError("Supplier contact is required")
        self._db.suppliers[sup_invoice] = Supplier(
            sup_invoice=sup_invoice, name=name, contact=contact, desc=desc
        )
        self.show()
        self.clear()


class employeeClass:
    def __init__(self, root: Any = None, db: Optional[InMemoryDB] = None) -> None:
        self.root = root
        self._db = db if db is not None else InMemoryDB()

        self.EmployeeTable: Treeview = Treeview()
        self.txt_address: Text = Text()

        self.var_contact: StringVar = StringVar()
        self.var_dob: StringVar = StringVar()
        self.var_doj: StringVar = StringVar()
        self.var_email: StringVar = StringVar()
        self.var_emp_id: StringVar = StringVar()
        self.var_gender: StringVar = StringVar()
        self.var_name: StringVar = StringVar()
        self.var_pass: StringVar = StringVar()
        self.var_salary: StringVar = StringVar()
        self.var_searchby: StringVar = StringVar()
        self.var_searchtxt: StringVar = StringVar()
        self.var_utype: StringVar = StringVar()

    def add(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        if not emp_id:
            raise ValueError("Employee ID is required")
        if emp_id in self._db.employees:
            raise ValueError("Employee ID already exists")

        name = self.var_name.get().strip()
        email = self.var_email.get().strip()
        gender = self.var_gender.get().strip()
        contact = self.var_contact.get().strip()
        dob = self.var_dob.get().strip()
        doj = self.var_doj.get().strip()
        passw = self.var_pass.get().strip()
        utype = self.var_utype.get().strip()
        salary = self.var_salary.get().strip()
        address = self.txt_address.get().strip()

        if not name:
            raise ValueError("Employee name is required")
        if not passw:
            raise ValueError("Employee password is required")
        if not utype:
            raise ValueError("Employee user type is required")

        self._db.employees[emp_id] = Employee(
            emp_id=emp_id,
            name=name,
            email=email,
            gender=gender,
            contact=contact,
            dob=dob,
            doj=doj,
            passw=passw,
            utype=utype,
            salary=salary,
            address=address,
        )
        self.show()
        self.clear()

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
        self.var_salary.set("")
        self.var_searchby.set("")
        self.var_searchtxt.set("")
        self.txt_address.clear()

    def delete(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        if not emp_id:
            raise ValueError("Employee ID is required for delete")
        if emp_id not in self._db.employees:
            raise ValueError("Employee not found")
        del self._db.employees[emp_id]
        self.show()
        self.clear()

    def get_data(self, ev: Any) -> None:
        index = self.EmployeeTable.selection()
        if index is None:
            return
        row = self.EmployeeTable.item(index)
        self.var_emp_id.set(str(row.get("emp_id", "")))
        self.var_name.set(str(row.get("name", "")))
        self.var_email.set(str(row.get("email", "")))
        self.var_gender.set(str(row.get("gender", "")))
        self.var_contact.set(str(row.get("contact", "")))
        self.var_dob.set(str(row.get("dob", "")))
        self.var_doj.set(str(row.get("doj", "")))
        self.var_pass.set(str(row.get("passw", "")))
        self.var_utype.set(str(row.get("utype", "")))
        self.var_salary.set(str(row.get("salary", "")))
        self.txt_address.set(str(row.get("address", "")))

    def search(self) -> None:
        by = self.var_searchby.get().strip()
        txt = self.var_searchtxt.get().strip().lower()
        self.EmployeeTable.clear()
        if not by or not txt:
            self.show()
            return

        def match(e: Employee) -> bool:
            if by == "emp_id":
                return txt in e.emp_id.lower()
            if by == "name":
                return txt in e.name.lower()
            if by == "contact":
                return txt in e.contact.lower()
            if by == "email":
                return txt in e.email.lower()
            if by == "utype":
                return txt in e.utype.lower()
            return False

        for e in sorted(self._db.employees.values(), key=lambda x: x.emp_id):
            if match(e):
                self.EmployeeTable.insert(
                    {
                        "emp_id": e.emp_id,
                        "name": e.name,
                        "email": e.email,
                        "gender": e.gender,
                        "contact": e.contact,
                        "dob": e.dob,
                        "doj": e.doj,
                        "passw": e.passw,
                        "utype": e.utype,
                        "salary": e.salary,
                        "address": e.address,
                    }
                )

    def show(self) -> None:
        self.EmployeeTable.clear()
        for e in sorted(self._db.employees.values(), key=lambda x: x.emp_id):
            self.EmployeeTable.insert(
                {
                    "emp_id": e.emp_id,
                    "name": e.name,
                    "email": e.email,
                    "gender": e.gender,
                    "contact": e.contact,
                    "dob": e.dob,
                    "doj": e.doj,
                    "passw": e.passw,
                    "utype": e.utype,
                    "salary": e.salary,
                    "address": e.address,
                }
            )

    def update(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        if not emp_id:
            raise ValueError("Employee ID is required for update")
        if emp_id not in self._db.employees:
            raise ValueError("Employee not found")

        name = self.var_name.get().strip()
        email = self.var_email.get().strip()
        gender = self.var_gender.get().strip()
        contact = self.var_contact.get().strip()
        dob = self.var_dob.get().strip()
        doj = self.var_doj.get().strip()
        passw = self.var_pass.get().strip()
        utype = self.var_utype.get().strip()
        salary = self.var_salary.get().strip()
        address = self.txt_address.get().strip()

        if not name:
            raise ValueError("Employee name is required")
        if not passw:
            raise ValueError("Employee password is required")
        if not utype:
            raise ValueError("Employee user type is required")

        self._db.employees[emp_id] = Employee(
            emp_id=emp_id,
            name=name,
            email=email,
            gender=gender,
            contact=contact,
            dob=dob,
            doj=doj,
            passw=passw,
            utype=utype,
            salary=salary,
            address=address,
        )
        self.show()
        self.clear()


class productClass:
    def __init__(self, root: Any = None, db: Optional[InMemoryDB] = None) -> None:
        self.root = root
        self._db = db if db is not None else InMemoryDB()

        self.ProductTable: Treeview = Treeview()
        self.cat_list: List[str] = []
        self.sup_list: List[str] = []

        self.var_cat: StringVar = StringVar()
        self.var_name: StringVar = StringVar()
        self.var_pid: StringVar = StringVar()
        self.var_price: StringVar = StringVar()
        self.var_qty: StringVar = StringVar()
        self.var_searchby: StringVar = StringVar()
        self.var_searchtxt: StringVar = StringVar()
        self.var_status: StringVar = StringVar()
        self.var_sup: StringVar = StringVar()

        self.fetch_cat_sup()

    def fetch_cat_sup(self) -> None:
        self.cat_list = [c.name for c in sorted(self._db.categories.values(), key=lambda x: x.name.lower())]
        self.sup_list = [s.name for s in sorted(self._db.suppliers.values(), key=lambda x: x.name.lower())]

    def _parse_price(self, value: str) -> float:
        v = value.strip()
        if not v:
            raise ValueError("Price is required")
        try:
            p = float(v)
        except ValueError as e:
            raise ValueError("Invalid price") from e
        if p < 0:
            raise ValueError("Price cannot be negative")
        return p

    def _parse_qty(self, value: str) -> int:
        v = value.strip()
        if not v:
            raise ValueError("Quantity is required")
        try:
            q = int(v)
        except ValueError as e:
            raise ValueError("Invalid quantity") from e
        if q < 0:
            raise ValueError("Quantity cannot be negative")
        return q

    def add(self) -> None:
        pid = self.var_pid.get().strip()
        name = self.var_name.get().strip()
        cat = self.var_cat.get().strip()
        sup = self.var_sup.get().strip()
        status = self.var_status.get().strip()
        price = self._parse_price(self.var_price.get())
        qty = self._parse_qty(self.var_qty.get())

        if not pid:
            raise ValueError("Product ID is required")
        if pid in self._db.products:
            raise ValueError("Product ID already exists")
        if not name:
            raise ValueError("Product name is required")
        if not cat:
            raise ValueError("Category is required")
        if not sup:
            raise ValueError("Supplier is required")
        if not status:
            raise ValueError("Status is required")

        self._db.products[pid] = Product(
            pid=pid, name=name, cat=cat, sup=sup, price=price, qty=qty, status=status
        )
        self.fetch_cat_sup()
        self.show()
        self.clear()

    def clear(self) -> None:
        self.var_pid.set("")
        self.var_name.set("")
        self.var_cat.set("")
        self.var_sup.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_status.set("")
        self.var_searchby.set("")
        self.var_searchtxt.set("")

    def delete(self) -> None:
        pid = self.var_pid.get().strip()
        if not pid:
            raise ValueError("Product ID is required for delete")
        if pid not in self._db.products:
            raise ValueError("Product not found")
        del self._db.products[pid]
        self.show()
        self.clear()

    def get_data(self, ev: Any) -> None:
        index = self.ProductTable.selection()
        if index is None:
            return
        row = self.ProductTable.item(index)
        self.var_pid.set(str(row.get("pid", "")))
        self.var_name.set(str(row.get("name", "")))
        self.var_cat.set(str(row.get("cat", "")))
        self.var_sup.set(str(row.get("sup", "")))
        self.var_price.set(str(row.get("price", "")))
        self.var_qty.set(str(row.get("qty", "")))
        self.var_status.set(str(row.get("status", "")))

    def search(self) -> None:
        by = self.var_searchby.get().strip()
        txt = self.var_searchtxt.get().strip().lower()
        self.ProductTable.clear()
        if not by or not txt:
            self.show()
            return

        def match(p: Product) -> bool:
            if by == "pid":
                return txt in p.pid.lower()
            if by == "name":
                return txt in p.name.lower()
            if by == "cat":
                return txt in p.cat.lower()
            if by == "sup":
                return txt in p.sup.lower()
            if by == "status":
                return txt in p.status.lower()
            return False

        for p in sorted(self._db.products.values(), key=lambda x: x.pid):
            if match(p):
                self.ProductTable.insert(
                    {
                        "pid": p.pid,
                        "name": p.name,
                        "cat": p.cat,
                        "sup": p.sup,
                        "price": p.price,
                        "qty": p.qty,
                        "status": p.status,
                    }
                )

    def show(self) -> None:
        self.ProductTable.clear()
        for p in sorted(self._db.products.values(), key=lambda x: x.pid):
            self.ProductTable.insert(
                {
                    "pid": p.pid,
                    "name": p.name,
                    "cat": p.cat,
                    "sup": p.sup,
                    "price": p.price,
                    "qty": p.qty,
                    "status": p.status,
                }
            )

    def update(self) -> None:
        pid = self.var_pid.get().strip()
        if not pid:
            raise ValueError("Product ID is required for update")
        if pid not in self._db.products:
            raise ValueError("Product not found")

        name = self.var_name.get().strip()
        cat = self.var_cat.get().strip()
        sup = self.var_sup.get().strip()
        status = self.var_status.get().strip()
        price = self._parse_price(self.var_price.get())
        qty = self._parse_qty(self.var_qty.get())

        if not name:
            raise ValueError("Product name is required")
        if not cat:
            raise ValueError("Category is required")
        if not sup:
            raise ValueError("Supplier is required")
        if not status:
            raise ValueError("Status is required")

        self._db.products[pid] = Product(
            pid=pid, name=name, cat=cat, sup=sup, price=price, qty=qty, status=status
        )
        self.fetch_cat_sup()
        self.show()
        self.clear()


class salesClass:
    def __init__(self, root: Any = None, db: Optional[InMemoryDB] = None) -> None:
        self.root = root
        self._db = db if db is not None else InMemoryDB()

        self.Sales_List: Listbox = Listbox()
        self.bill_area: Text = Text()
        self.bill_photo: Optional[PhotoImage] = None
        self.blll_list: List[str] = []

        self.var_invoice: StringVar = StringVar()

    def clear(self) -> None:
        self.var_invoice.set("")
        self.bill_area.clear()

    def get_data(self, ev: Any) -> None:
        idx = self.Sales_List.curselection()
        if idx is None:
            return
        invoice_id = self.Sales_List.get(idx)
        self.var_invoice.set(invoice_id)
        inv = self._db.invoices.get(invoice_id)
        if inv is None:
            self.bill_area.set("")
        else:
            self.bill_area.set(inv.text)

    def search(self) -> None:
        txt = self.var_invoice.get().strip().lower()
        self.Sales_List.clear()
        if not txt:
            self.show()
            return
        for inv_id in sorted(self._db.invoices.keys()):
            if txt in inv_id.lower():
                self.Sales_List.insert(inv_id)

    def show(self) -> None:
        self.Sales_List.clear()
        self.blll_list = sorted(self._db.invoices.keys())
        for inv_id in self.blll_list:
            self.Sales_List.insert(inv_id)


class billClass:
    def __init__(self, root: Any = None, db: Optional[InMemoryDB] = None) -> None:
        self.root = root
        self._db = db if db is not None else InMemoryDB()

        self.CartTable: Treeview = Treeview()
        self.product_Table: Treeview = Treeview()

        self.bill_amnt: int = 0
        self.discount: float = 0.0
        self.net_pay: Union[float, int] = 0.0
        self.chk_print: int = 0
        self.siscount: int = 0

        self.icon_title: PhotoImage = PhotoImage()
        self.invoice: str = ""

        self.cartTitle: Label = Label()
        self.lbl_amnt: Label = Label()
        self.lbl_clock: Label = Label()
        self.lbl_discount: Label = Label()
        self.lbl_inStock: Label = Label()
        self.lbl_net_pay: Label = Label()

        self.txt_bill_area: Text = Text()
        self.txt_cal_input: Entry = Entry()
        self.var_cal_input: StringVar = StringVar()

        self.var_cname: StringVar = StringVar()
        self.var_contact: StringVar = StringVar()
        self.var_pid: StringVar = StringVar()
        self.var_pname: StringVar = StringVar()
        self.var_price: StringVar = StringVar()
        self.var_qty: StringVar = StringVar()
        self.var_search: StringVar = StringVar()
        self.var_stock: StringVar = StringVar()

        self.cart_list: List[CartItem] = []

        self.show()
        self.update_date_time()

    def bill_top(self) -> None:
        inv = self.invoice or self._db.next_invoice_id()
        self.invoice = inv
        cname = self.var_cname.get().strip()
        contact = self.var_contact.get().strip()
        now = datetime.datetime.now()
        header = [
            "INVENTORY MANAGEMENT SYSTEM",
            f"Invoice: {inv}",
            f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Customer: {cname}",
            f"Contact: {contact}",
            "-" * 40,
            f"{'PID':<8}{'Name':<16}{'Qty':>4}{'Price':>6}{'Amt':>6}",
            "-" * 40,
        ]
        self.txt_bill_area.set("\n".join(header) + "\n")

    def bill_middle(self) -> None:
        lines: List[str] = []
        for it in self.cart_list:
            pid = it.pid[:8]
            name = it.pname[:16]
            qty = it.qty
            price = it.price
            amt = it.amount
            lines.append(f"{pid:<8}{name:<16}{qty:>4}{price:>6.2f}{amt:>6.2f}")
        current = self.txt_bill_area.get()
        self.txt_bill_area.set(current + "\n".join(lines) + ("\n" if lines else ""))

    def bill_bottom(self) -> None:
        self.bill_update()
        footer = [
            "-" * 40,
            f"Bill Amount: {float(self.bill_amnt):.2f}",
            f"Discount: {float(self.discount):.2f}",
            f"Net Pay: {float(self.net_pay):.2f}",
            "-" * 40,
        ]
        current = self.txt_bill_area.get()
        self.txt_bill_area.set(current + "\n".join(footer) + "\n")

    def _find_product(self, pid: str) -> Product:
        if pid not in self._db.products:
            raise ValueError("Product not found")
        return self._db.products[pid]

    def _parse_int(self, s: str, field: str) -> int:
        v = s.strip()
        if not v:
            raise ValueError(f"{field} is required")
        try:
            i = int(v)
        except ValueError as e:
            raise ValueError(f"Invalid {field}") from e
        return i

    def _parse_float(self, s: str, field: str) -> float:
        v = s.strip()
        if not v:
            raise ValueError(f"{field} is required")
        try:
            f = float(v)
        except ValueError as e:
            raise ValueError(f"Invalid {field}") from e
        return f

    def add_update_cart(self) -> None:
        pid = self.var_pid.get().strip()
        if not pid:
            raise ValueError("Product ID is required")
        p = self._find_product(pid)

        pname = self.var_pname.get().strip() or p.name
        price = self._parse_float(self.var_price.get() or str(p.price), "price")
        qty = self._parse_int(self.var_qty.get(), "quantity")
        if qty <= 0:
            raise ValueError("Quantity must be greater than 0")

        stock = p.qty
        if qty > stock:
            raise ValueError("Quantity exceeds stock")

        existing_index: Optional[int] = None
        for i, it in enumerate(self.cart_list):
            if it.pid == pid:
                existing_index = i
                break

        if existing_index is None:
            self.cart_list.append(CartItem(pid=pid, pname=pname, price=price, qty=qty, stock=stock))
        else:
            self.cart_list[existing_index] = CartItem(pid=pid, pname=pname, price=price, qty=qty, stock=stock)

        self.show_cart()
        self.bill_update()
        self.clear_cal()

    def bill_update(self) -> None:
        total = sum(it.amount for it in self.cart_list)
        self.bill_amnt = int(round(total))
        disc = float(self.discount) if self.discount is not None else 0.0
        if disc < 0:
            disc = 0.0
        net = total - disc
        if net < 0:
            net = 0.0
        self.net_pay = net

        self.lbl_amnt.config(text=f"{total:.2f}")
        self.lbl_discount.config(text=f"{disc:.2f}")
        self.lbl_net_pay.config(text=f"{net:.2f}")

    def clear_all(self) -> None:
        self.clear_cart()
        self.var_cname.set("")
        self.var_contact.set("")
        self.var_search.set("")
        self.txt_bill_area.clear()
        self.invoice = ""
        self.chk_print = 0
        self.discount = 0.0
        self.siscount = 0
        self.bill_update()

    def clear_cal(self) -> None:
        self.var_cal_input.set("")
        self.txt_cal_input.set("")

    def clear_cart(self) -> None:
        self.cart_list.clear()
        self.show_cart()
        self.bill_update()

    def generate_bill(self) -> None:
        if not self.cart_list:
            raise ValueError("Cart is empty")
        if not self.invoice:
            self.invoice = self._db.next_invoice_id()

        for it in self.cart_list:
            p = self._find_product(it.pid)
            if it.qty > p.qty:
                raise ValueError("Insufficient stock for one or more items")

        self.bill_top()
        self.bill_middle()
        self.bill_bottom()

        for it in self.cart_list:
            p = self._find_product(it.pid)
            self._db.products[it.pid] = Product(
                pid=p.pid,
                name=p.name,
                cat=p.cat,
                sup=p.sup,
                price=p.price,
                qty=p.qty - it.qty,
                status=p.status,
            )

        self.show()

        inv = Invoice(
            invoice_id=self.invoice,
            customer_name=self.var_cname.get().strip(),
            contact=self.var_contact.get().strip(),
            items=[CartItem(pid=i.pid, pname=i.pname, price=i.price, qty=i.qty, stock=i.stock) for i in self.cart_list],
            bill_amount=float(sum(i.amount for i in self.cart_list)),
            discount=float(self.discount),
            net_pay=float(self.net_pay),
            created_at=datetime.datetime.now(),
            text=self.txt_bill_area.get(),
        )
        self._db.invoices[self.invoice] = inv
        self.chk_print = 1

    def print_bill(self) -> None:
        if self.chk_print != 1:
            raise ValueError("Bill not generated")
        if not self.invoice or self.invoice not in self._db.invoices:
            raise ValueError("Invoice not found")
        self.chk_print = 2

    def get_data(self, ev: Any) -> None:
        index = self.product_Table.selection()
        if index is None:
            return
        row = self.product_Table.item(index)
        self.var_pid.set(str(row.get("pid", "")))
        self.var_pname.set(str(row.get("name", "")))
        self.var_price.set(str(row.get("price", "")))
        self.var_stock.set(str(row.get("qty", "")))
        self.lbl_inStock.config(text=str(row.get("qty", "")))

    def get_data_cart(self, ev: Any) -> None:
        index = self.CartTable.selection()
        if index is None:
            return
        row = self.CartTable.item(index)
        self.var_pid.set(str(row.get("pid", "")))
        self.var_pname.set(str(row.get("pname", "")))
        self.var_price.set(str(row.get("price", "")))
        self.var_qty.set(str(row.get("qty", "")))
        self.var_stock.set(str(row.get("stock", "")))
        self.lbl_inStock.config(text=str(row.get("stock", "")))

    def get_input(self, num: Union[int, str]) -> None:
        s = self.var_cal_input.get()
        s += str(num)
        self.var_cal_input.set(s)
        self.txt_cal_input.set(s)

    def perform_cal(self) -> None:
        expr = self.var_cal_input.get().strip()
        if not expr:
            return
        allowed = set("0123456789.+-*/() ")
        if any(ch not in allowed for ch in expr):
            raise ValueError("Invalid calculator input")
        try:
            result = eval(expr, {"__builtins__": {}}, {})
        except Exception as e:
            raise ValueError("Invalid expression") from e
        if not isinstance(result, (int, float)) or not math.isfinite(float(result)):
            raise ValueError("Invalid result")
        self.var_cal_input.set(str(result))
        self.txt_cal_input.set(str(result))

    def search(self) -> None:
        txt = self.var_search.get().strip().lower()
        self.product_Table.clear()
        if not txt:
            self.show()
            return
        for p in sorted(self._db.products.values(), key=lambda x: x.pid):
            if txt in p.pid.lower() or txt in p.name.lower():
                self.product_Table.insert(
                    {"pid": p.pid, "name": p.name, "price": p.price, "qty": p.qty, "status": p.status}
                )

    def show(self) -> None:
        self.product_Table.clear()
        for p in sorted(self._db.products.values(), key=lambda x: x.pid):
            self.product_Table.insert(
                {"pid": p.pid, "name": p.name, "price": p.price, "qty": p.qty, "status": p.status}
            )

    def show_cart(self) -> None:
        self.CartTable.clear()
        for it in self.cart_list:
            self.CartTable.insert(
                {"pid": it.pid, "pname": it.pname, "price": it.price, "qty": it.qty, "stock": it.stock, "amount": it.amount}
            )
        self.cartTitle.config(text=f"Cart ({len(self.cart_list)})")

    def update_date_time(self) -> None:
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))


class IMS:
    def __init__(self, root: Any = None) -> None:
        self.root = root
        self._db = InMemoryDB()

        self.MenuLogo: Union[None, PhotoImage] = None
        self.icon_side: PhotoImage = PhotoImage()
        self.icon_title: PhotoImage = PhotoImage()
        self.lbl_category: Label = Label()
        self.lbl_clock: Label = Label()
        self.lbl_employee: Label = Label()
        self.lbl_product: Label = Label()
        self.lbl_sales: Label = Label()
        self.lbl_supplier: Label = Label()

        self.new_obj: Any = None
        self.new_win: Toplevel = Toplevel(root=self.root)

        self._category_obj: Optional[categoryClass] = None
        self._employee_obj: Optional[employeeClass] = None
        self._product_obj: Optional[productClass] = None
        self._sales_obj: Optional[salesClass] = None
        self._supplier_obj: Optional[supplierClass] = None

        self.update_content()

    def category(self) -> categoryClass:
        self._category_obj = categoryClass(root=self.new_win, db=self._db)
        self.new_obj = self._category_obj
        self._category_obj.show()
        self.update_content()
        return self._category_obj

    def employee(self) -> employeeClass:
        self._employee_obj = employeeClass(root=self.new_win, db=self._db)
        self.new_obj = self._employee_obj
        self._employee_obj.show()
        self.update_content()
        return self._employee_obj

    def product(self) -> productClass:
        self._product_obj = productClass(root=self.new_win, db=self._db)
        self.new_obj = self._product_obj
        self._product_obj.show()
        self.update_content()
        return self._product_obj

    def sales(self) -> salesClass:
        self._sales_obj = salesClass(root=self.new_win, db=self._db)
        self.new_obj = self._sales_obj
        self._sales_obj.show()
        self.update_content()
        return self._sales_obj

    def supplier(self) -> supplierClass:
        self._supplier_obj = supplierClass(root=self.new_win, db=self._db)
        self.new_obj = self._supplier_obj
        self._supplier_obj.show()
        self.update_content()
        return self._supplier_obj

    def update_content(self) -> None:
        self.lbl_category.config(text=str(len(self._db.categories)))
        self.lbl_supplier.config(text=str(len(self._db.suppliers)))
        self.lbl_employee.config(text=str(len(self._db.employees)))
        self.lbl_product.config(text=str(len(self._db.products)))
        self.lbl_sales.config(text=str(len(self._db.invoices)))
        self.lbl_clock.config(text=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


# Namespace-like aliases to match diagram names
class dashboard:
    IMS = IMS


class billing:
    billClass = billClass


class category:
    categoryClass = categoryClass


class employee:
    employeeClass = employeeClass


class product:
    productClass = productClass


class sales:
    salesClass = salesClass


class supplier:
    supplierClass = supplierClass