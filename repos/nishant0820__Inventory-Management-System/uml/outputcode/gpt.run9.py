from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import datetime
import itertools


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


class Listbox:
    def __init__(self) -> None:
        self.items: List[str] = []
        self.selected_index: Optional[int] = None

    def insert(self, item: str) -> None:
        self.items.append(item)

    def delete_all(self) -> None:
        self.items.clear()
        self.selected_index = None

    def select(self, index: int) -> None:
        if index < 0 or index >= len(self.items):
            raise IndexError("Listbox selection out of range")
        self.selected_index = index

    def get_selected(self) -> Optional[str]:
        if self.selected_index is None:
            return None
        return self.items[self.selected_index]


class Treeview:
    def __init__(self) -> None:
        self.rows: List[Dict[str, Any]] = []
        self.selected_index: Optional[int] = None

    def insert(self, row: Dict[str, Any]) -> None:
        self.rows.append(dict(row))

    def clear(self) -> None:
        self.rows.clear()
        self.selected_index = None

    def select(self, index: int) -> None:
        if index < 0 or index >= len(self.rows):
            raise IndexError("Treeview selection out of range")
        self.selected_index = index

    def get_selected(self) -> Optional[Dict[str, Any]]:
        if self.selected_index is None:
            return None
        return dict(self.rows[self.selected_index])

    def update_selected(self, row: Dict[str, Any]) -> None:
        if self.selected_index is None:
            raise ValueError("No row selected")
        self.rows[self.selected_index] = dict(row)

    def delete_selected(self) -> None:
        if self.selected_index is None:
            raise ValueError("No row selected")
        del self.rows[self.selected_index]
        self.selected_index = None


class Toplevel:
    def __init__(self, root: Any = None) -> None:
        self.root = root


class Event:
    def __init__(self, index: Optional[int] = None) -> None:
        self.index = index


@dataclass
class CategoryRecord:
    cat_id: str
    name: str


@dataclass
class SupplierRecord:
    sup_invoice: str
    name: str
    contact: str
    desc: str


@dataclass
class EmployeeRecord:
    emp_id: str
    name: str
    email: str
    gender: str
    contact: str
    dob: str
    doj: str
    pass_: str
    utype: str
    address: str
    salary: str


@dataclass
class ProductRecord:
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
    def total(self) -> float:
        return float(self.price) * int(self.qty)


@dataclass
class InvoiceRecord:
    invoice: str
    cname: str
    contact: str
    items: List[CartItem]
    bill_amnt: float
    discount: float
    net_pay: float
    created_at: str
    text: str


class InventoryDB:
    def __init__(self) -> None:
        self.categories: Dict[str, CategoryRecord] = {}
        self.suppliers: Dict[str, SupplierRecord] = {}
        self.employees: Dict[str, EmployeeRecord] = {}
        self.products: Dict[str, ProductRecord] = {}
        self.invoices: Dict[str, InvoiceRecord] = {}

    def category_names(self) -> List[str]:
        return [c.name for c in self.categories.values()]

    def supplier_names(self) -> List[str]:
        return [s.name for s in self.suppliers.values()]


GLOBAL_DB = InventoryDB()


def _now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _require_non_empty(value: str, field: str) -> None:
    if value is None or str(value).strip() == "":
        raise ValueError(f"{field} is required")


def _parse_float(value: str, field: str) -> float:
    _require_non_empty(value, field)
    try:
        return float(value)
    except Exception as e:
        raise ValueError(f"{field} must be a number") from e


def _parse_int(value: str, field: str) -> int:
    _require_non_empty(value, field)
    try:
        return int(float(value))
    except Exception as e:
        raise ValueError(f"{field} must be an integer") from e


class categoryClass:
    def __init__(self, root: Any = None, db: InventoryDB = GLOBAL_DB) -> None:
        self.root = root
        self.db = db

        self.CategoryTable: Treeview = Treeview()
        self.im1: Optional[PhotoImage] = None
        self.im2: Optional[PhotoImage] = None
        self.lbl_im1: Label = Label()
        self.lbl_im2: Label = Label()

        self.var_cat_id: StringVar = StringVar("")
        self.var_name: StringVar = StringVar("")

    def add(self) -> None:
        cat_id = self.var_cat_id.get().strip()
        name = self.var_name.get().strip()
        _require_non_empty(cat_id, "Category ID")
        _require_non_empty(name, "Category Name")
        if cat_id in self.db.categories:
            raise ValueError("Category ID already exists")
        self.db.categories[cat_id] = CategoryRecord(cat_id=cat_id, name=name)
        self.show()

    def clear(self) -> None:
        self.var_cat_id.set("")
        self.var_name.set("")
        self.CategoryTable.selected_index = None

    def delete(self) -> None:
        cat_id = self.var_cat_id.get().strip()
        _require_non_empty(cat_id, "Category ID")
        if cat_id not in self.db.categories:
            raise ValueError("Category not found")
        del self.db.categories[cat_id]
        self.clear()
        self.show()

    def get_data(self, ev: Any) -> None:
        index = getattr(ev, "index", None)
        if index is None:
            selected = self.CategoryTable.get_selected()
        else:
            self.CategoryTable.select(index)
            selected = self.CategoryTable.get_selected()
        if not selected:
            return
        self.var_cat_id.set(str(selected.get("cat_id", "")))
        self.var_name.set(str(selected.get("name", "")))

    def show(self) -> None:
        self.CategoryTable.clear()
        for rec in sorted(self.db.categories.values(), key=lambda r: r.cat_id):
            self.CategoryTable.insert({"cat_id": rec.cat_id, "name": rec.name})


class supplierClass:
    def __init__(self, root: Any = None, db: InventoryDB = GLOBAL_DB) -> None:
        self.root = root
        self.db = db

        self.SupplierTable: Treeview = Treeview()
        self.txt_desc: Text = Text()

        self.var_sup_invoice: StringVar = StringVar("")
        self.var_name: StringVar = StringVar("")
        self.var_contact: StringVar = StringVar("")
        self.var_searchby: StringVar = StringVar("")
        self.var_searchtxt: StringVar = StringVar("")

    def add(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        name = self.var_name.get().strip()
        contact = self.var_contact.get().strip()
        desc = self.txt_desc.get().strip()

        _require_non_empty(sup_invoice, "Supplier Invoice")
        _require_non_empty(name, "Supplier Name")
        _require_non_empty(contact, "Supplier Contact")

        if sup_invoice in self.db.suppliers:
            raise ValueError("Supplier invoice already exists")

        self.db.suppliers[sup_invoice] = SupplierRecord(
            sup_invoice=sup_invoice, name=name, contact=contact, desc=desc
        )
        self.show()

    def clear(self) -> None:
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.var_searchby.set("")
        self.var_searchtxt.set("")
        self.txt_desc.clear()
        self.SupplierTable.selected_index = None

    def delete(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        _require_non_empty(sup_invoice, "Supplier Invoice")
        if sup_invoice not in self.db.suppliers:
            raise ValueError("Supplier not found")
        del self.db.suppliers[sup_invoice]
        self.clear()
        self.show()

    def get_data(self, ev: Any) -> None:
        index = getattr(ev, "index", None)
        if index is None:
            selected = self.SupplierTable.get_selected()
        else:
            self.SupplierTable.select(index)
            selected = self.SupplierTable.get_selected()
        if not selected:
            return
        self.var_sup_invoice.set(str(selected.get("sup_invoice", "")))
        self.var_name.set(str(selected.get("name", "")))
        self.var_contact.set(str(selected.get("contact", "")))
        self.txt_desc.set(str(selected.get("desc", "")))

    def search(self) -> None:
        by = self.var_searchby.get().strip().lower()
        txt = self.var_searchtxt.get().strip().lower()
        self.SupplierTable.clear()

        def match(rec: SupplierRecord) -> bool:
            if txt == "":
                return True
            if by in ("invoice", "sup_invoice"):
                return txt in rec.sup_invoice.lower()
            if by == "name":
                return txt in rec.name.lower()
            if by == "contact":
                return txt in rec.contact.lower()
            return (
                txt in rec.sup_invoice.lower()
                or txt in rec.name.lower()
                or txt in rec.contact.lower()
                or txt in rec.desc.lower()
            )

        for rec in sorted(self.db.suppliers.values(), key=lambda r: r.sup_invoice):
            if match(rec):
                self.SupplierTable.insert(
                    {
                        "sup_invoice": rec.sup_invoice,
                        "name": rec.name,
                        "contact": rec.contact,
                        "desc": rec.desc,
                    }
                )

    def show(self) -> None:
        self.SupplierTable.clear()
        for rec in sorted(self.db.suppliers.values(), key=lambda r: r.sup_invoice):
            self.SupplierTable.insert(
                {
                    "sup_invoice": rec.sup_invoice,
                    "name": rec.name,
                    "contact": rec.contact,
                    "desc": rec.desc,
                }
            )

    def update(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        _require_non_empty(sup_invoice, "Supplier Invoice")
        if sup_invoice not in self.db.suppliers:
            raise ValueError("Supplier not found")

        name = self.var_name.get().strip()
        contact = self.var_contact.get().strip()
        desc = self.txt_desc.get().strip()

        _require_non_empty(name, "Supplier Name")
        _require_non_empty(contact, "Supplier Contact")

        self.db.suppliers[sup_invoice] = SupplierRecord(
            sup_invoice=sup_invoice, name=name, contact=contact, desc=desc
        )
        self.show()


class employeeClass:
    def __init__(self, root: Any = None, db: InventoryDB = GLOBAL_DB) -> None:
        self.root = root
        self.db = db

        self.EmployeeTable: Treeview = Treeview()
        self.txt_address: Text = Text()

        self.var_emp_id: StringVar = StringVar("")
        self.var_name: StringVar = StringVar("")
        self.var_email: StringVar = StringVar("")
        self.var_gender: StringVar = StringVar("")
        self.var_contact: StringVar = StringVar("")
        self.var_dob: StringVar = StringVar("")
        self.var_doj: StringVar = StringVar("")
        self.var_pass: StringVar = StringVar("")
        self.var_utype: StringVar = StringVar("")
        self.var_salary: StringVar = StringVar("")
        self.var_searchby: StringVar = StringVar("")
        self.var_searchtxt: StringVar = StringVar("")

    def add(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        _require_non_empty(emp_id, "Employee ID")
        if emp_id in self.db.employees:
            raise ValueError("Employee ID already exists")

        name = self.var_name.get().strip()
        email = self.var_email.get().strip()
        gender = self.var_gender.get().strip()
        contact = self.var_contact.get().strip()
        dob = self.var_dob.get().strip()
        doj = self.var_doj.get().strip()
        pass_ = self.var_pass.get().strip()
        utype = self.var_utype.get().strip()
        address = self.txt_address.get().strip()
        salary = self.var_salary.get().strip()

        _require_non_empty(name, "Name")
        _require_non_empty(contact, "Contact")
        _require_non_empty(pass_, "Password")
        _require_non_empty(utype, "User Type")

        self.db.employees[emp_id] = EmployeeRecord(
            emp_id=emp_id,
            name=name,
            email=email,
            gender=gender,
            contact=contact,
            dob=dob,
            doj=doj,
            pass_=pass_,
            utype=utype,
            address=address,
            salary=salary,
        )
        self.show()

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
        self.EmployeeTable.selected_index = None

    def delete(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        _require_non_empty(emp_id, "Employee ID")
        if emp_id not in self.db.employees:
            raise ValueError("Employee not found")
        del self.db.employees[emp_id]
        self.clear()
        self.show()

    def get_data(self, ev: Any) -> None:
        index = getattr(ev, "index", None)
        if index is None:
            selected = self.EmployeeTable.get_selected()
        else:
            self.EmployeeTable.select(index)
            selected = self.EmployeeTable.get_selected()
        if not selected:
            return
        self.var_emp_id.set(str(selected.get("emp_id", "")))
        self.var_name.set(str(selected.get("name", "")))
        self.var_email.set(str(selected.get("email", "")))
        self.var_gender.set(str(selected.get("gender", "")))
        self.var_contact.set(str(selected.get("contact", "")))
        self.var_dob.set(str(selected.get("dob", "")))
        self.var_doj.set(str(selected.get("doj", "")))
        self.var_pass.set(str(selected.get("pass", "")))
        self.var_utype.set(str(selected.get("utype", "")))
        self.var_salary.set(str(selected.get("salary", "")))
        self.txt_address.set(str(selected.get("address", "")))

    def search(self) -> None:
        by = self.var_searchby.get().strip().lower()
        txt = self.var_searchtxt.get().strip().lower()
        self.EmployeeTable.clear()

        def match(rec: EmployeeRecord) -> bool:
            if txt == "":
                return True
            if by in ("id", "emp_id"):
                return txt in rec.emp_id.lower()
            if by == "name":
                return txt in rec.name.lower()
            if by == "contact":
                return txt in rec.contact.lower()
            if by == "email":
                return txt in rec.email.lower()
            if by in ("utype", "user_type"):
                return txt in rec.utype.lower()
            return (
                txt in rec.emp_id.lower()
                or txt in rec.name.lower()
                or txt in rec.email.lower()
                or txt in rec.contact.lower()
                or txt in rec.utype.lower()
            )

        for rec in sorted(self.db.employees.values(), key=lambda r: r.emp_id):
            if match(rec):
                self.EmployeeTable.insert(
                    {
                        "emp_id": rec.emp_id,
                        "name": rec.name,
                        "email": rec.email,
                        "gender": rec.gender,
                        "contact": rec.contact,
                        "dob": rec.dob,
                        "doj": rec.doj,
                        "pass": rec.pass_,
                        "utype": rec.utype,
                        "address": rec.address,
                        "salary": rec.salary,
                    }
                )

    def show(self) -> None:
        self.EmployeeTable.clear()
        for rec in sorted(self.db.employees.values(), key=lambda r: r.emp_id):
            self.EmployeeTable.insert(
                {
                    "emp_id": rec.emp_id,
                    "name": rec.name,
                    "email": rec.email,
                    "gender": rec.gender,
                    "contact": rec.contact,
                    "dob": rec.dob,
                    "doj": rec.doj,
                    "pass": rec.pass_,
                    "utype": rec.utype,
                    "address": rec.address,
                    "salary": rec.salary,
                }
            )

    def update(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        _require_non_empty(emp_id, "Employee ID")
        if emp_id not in self.db.employees:
            raise ValueError("Employee not found")

        name = self.var_name.get().strip()
        email = self.var_email.get().strip()
        gender = self.var_gender.get().strip()
        contact = self.var_contact.get().strip()
        dob = self.var_dob.get().strip()
        doj = self.var_doj.get().strip()
        pass_ = self.var_pass.get().strip()
        utype = self.var_utype.get().strip()
        address = self.txt_address.get().strip()
        salary = self.var_salary.get().strip()

        _require_non_empty(name, "Name")
        _require_non_empty(contact, "Contact")
        _require_non_empty(pass_, "Password")
        _require_non_empty(utype, "User Type")

        self.db.employees[emp_id] = EmployeeRecord(
            emp_id=emp_id,
            name=name,
            email=email,
            gender=gender,
            contact=contact,
            dob=dob,
            doj=doj,
            pass_=pass_,
            utype=utype,
            address=address,
            salary=salary,
        )
        self.show()


class productClass:
    def __init__(self, root: Any = None, db: InventoryDB = GLOBAL_DB) -> None:
        self.root = root
        self.db = db

        self.ProductTable: Treeview = Treeview()
        self.cat_list: List[str] = []
        self.sup_list: List[str] = []

        self.var_pid: StringVar = StringVar("")
        self.var_name: StringVar = StringVar("")
        self.var_cat: StringVar = StringVar("")
        self.var_sup: StringVar = StringVar("")
        self.var_price: StringVar = StringVar("")
        self.var_qty: StringVar = StringVar("")
        self.var_status: StringVar = StringVar("")
        self.var_searchby: StringVar = StringVar("")
        self.var_searchtxt: StringVar = StringVar("")

        self.fetch_cat_sup()

    def fetch_cat_sup(self) -> None:
        self.cat_list = self.db.category_names()
        self.sup_list = self.db.supplier_names()

    def add(self) -> None:
        pid = self.var_pid.get().strip()
        _require_non_empty(pid, "Product ID")
        if pid in self.db.products:
            raise ValueError("Product ID already exists")

        name = self.var_name.get().strip()
        cat = self.var_cat.get().strip()
        sup = self.var_sup.get().strip()
        price = _parse_float(self.var_price.get().strip(), "Price")
        qty = _parse_int(self.var_qty.get().strip(), "Quantity")
        status = self.var_status.get().strip()

        _require_non_empty(name, "Product Name")
        _require_non_empty(cat, "Category")
        _require_non_empty(sup, "Supplier")
        _require_non_empty(status, "Status")
        if qty < 0:
            raise ValueError("Quantity cannot be negative")
        if price < 0:
            raise ValueError("Price cannot be negative")

        self.db.products[pid] = ProductRecord(
            pid=pid, name=name, cat=cat, sup=sup, price=price, qty=qty, status=status
        )
        self.show()

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
        self.ProductTable.selected_index = None

    def delete(self) -> None:
        pid = self.var_pid.get().strip()
        _require_non_empty(pid, "Product ID")
        if pid not in self.db.products:
            raise ValueError("Product not found")
        del self.db.products[pid]
        self.clear()
        self.show()

    def get_data(self, ev: Any) -> None:
        index = getattr(ev, "index", None)
        if index is None:
            selected = self.ProductTable.get_selected()
        else:
            self.ProductTable.select(index)
            selected = self.ProductTable.get_selected()
        if not selected:
            return
        self.var_pid.set(str(selected.get("pid", "")))
        self.var_name.set(str(selected.get("name", "")))
        self.var_cat.set(str(selected.get("cat", "")))
        self.var_sup.set(str(selected.get("sup", "")))
        self.var_price.set(str(selected.get("price", "")))
        self.var_qty.set(str(selected.get("qty", "")))
        self.var_status.set(str(selected.get("status", "")))

    def search(self) -> None:
        by = self.var_searchby.get().strip().lower()
        txt = self.var_searchtxt.get().strip().lower()
        self.ProductTable.clear()

        def match(rec: ProductRecord) -> bool:
            if txt == "":
                return True
            if by in ("id", "pid"):
                return txt in rec.pid.lower()
            if by == "name":
                return txt in rec.name.lower()
            if by in ("cat", "category"):
                return txt in rec.cat.lower()
            if by in ("sup", "supplier"):
                return txt in rec.sup.lower()
            if by == "status":
                return txt in rec.status.lower()
            return (
                txt in rec.pid.lower()
                or txt in rec.name.lower()
                or txt in rec.cat.lower()
                or txt in rec.sup.lower()
                or txt in rec.status.lower()
            )

        for rec in sorted(self.db.products.values(), key=lambda r: r.pid):
            if match(rec):
                self.ProductTable.insert(
                    {
                        "pid": rec.pid,
                        "name": rec.name,
                        "cat": rec.cat,
                        "sup": rec.sup,
                        "price": rec.price,
                        "qty": rec.qty,
                        "status": rec.status,
                    }
                )

    def show(self) -> None:
        self.fetch_cat_sup()
        self.ProductTable.clear()
        for rec in sorted(self.db.products.values(), key=lambda r: r.pid):
            self.ProductTable.insert(
                {
                    "pid": rec.pid,
                    "name": rec.name,
                    "cat": rec.cat,
                    "sup": rec.sup,
                    "price": rec.price,
                    "qty": rec.qty,
                    "status": rec.status,
                }
            )

    def update(self) -> None:
        pid = self.var_pid.get().strip()
        _require_non_empty(pid, "Product ID")
        if pid not in self.db.products:
            raise ValueError("Product not found")

        name = self.var_name.get().strip()
        cat = self.var_cat.get().strip()
        sup = self.var_sup.get().strip()
        price = _parse_float(self.var_price.get().strip(), "Price")
        qty = _parse_int(self.var_qty.get().strip(), "Quantity")
        status = self.var_status.get().strip()

        _require_non_empty(name, "Product Name")
        _require_non_empty(cat, "Category")
        _require_non_empty(sup, "Supplier")
        _require_non_empty(status, "Status")
        if qty < 0:
            raise ValueError("Quantity cannot be negative")
        if price < 0:
            raise ValueError("Price cannot be negative")

        self.db.products[pid] = ProductRecord(
            pid=pid, name=name, cat=cat, sup=sup, price=price, qty=qty, status=status
        )
        self.show()


class salesClass:
    def __init__(self, root: Any = None, db: InventoryDB = GLOBAL_DB) -> None:
        self.root = root
        self.db = db

        self.Sales_List: Listbox = Listbox()
        self.bill_area: Text = Text()
        self.bill_photo: Optional[PhotoImage] = None
        self.blll_list: List[str] = []

        self.var_invoice: StringVar = StringVar("")

    def clear(self) -> None:
        self.var_invoice.set("")
        self.bill_area.clear()
        self.Sales_List.selected_index = None

    def get_data(self, ev: Any) -> None:
        index = getattr(ev, "index", None)
        if index is not None:
            self.Sales_List.select(index)
        selected = self.Sales_List.get_selected()
        if not selected:
            return
        self.var_invoice.set(selected)
        inv = self.db.invoices.get(selected)
        if inv:
            self.bill_area.set(inv.text)
        else:
            self.bill_area.set("")

    def search(self) -> None:
        txt = self.var_invoice.get().strip().lower()
        self.Sales_List.delete_all()
        self.blll_list = []
        for inv_id in sorted(self.db.invoices.keys()):
            if txt == "" or txt in inv_id.lower():
                self.Sales_List.insert(inv_id)
                self.blll_list.append(inv_id)

    def show(self) -> None:
        self.Sales_List.delete_all()
        self.blll_list = []
        for inv_id in sorted(self.db.invoices.keys()):
            self.Sales_List.insert(inv_id)
            self.blll_list.append(inv_id)


class billClass:
    _invoice_counter = itertools.count(1)

    def __init__(self, root: Any = None, db: InventoryDB = GLOBAL_DB) -> None:
        self.root = root
        self.db = db

        self.CartTable: Treeview = Treeview()
        self.product_Table: Treeview = Treeview()

        self.cartTitle: Label = Label()
        self.lbl_amnt: Label = Label()
        self.lbl_discount: Label = Label()
        self.lbl_net_pay: Label = Label()
        self.lbl_inStock: Label = Label()
        self.lbl_clock: Label = Label()
        self.icon_title: PhotoImage = PhotoImage()

        self.txt_bill_area: Text = Text()
        self.txt_cal_input: Entry = Entry()
        self.var_cal_input: StringVar = StringVar("")

        self.var_search: StringVar = StringVar("")
        self.var_pid: StringVar = StringVar("")
        self.var_pname: StringVar = StringVar("")
        self.var_price: StringVar = StringVar("")
        self.var_qty: StringVar = StringVar("")
        self.var_stock: StringVar = StringVar("")
        self.var_cname: StringVar = StringVar("")
        self.var_contact: StringVar = StringVar("")

        self.cart_list: List[CartItem] = []
        self.bill_amnt: int = 0
        self.discount: float = 0.0
        self.net_pay: Union[float, int] = 0.0
        self.siscount: int = 0
        self.chk_print: int = 0
        self.invoice: str = ""

        self.show()
        self.update_date_time()

    def bill_top(self) -> str:
        cname = self.var_cname.get().strip()
        contact = self.var_contact.get().strip()
        inv = self.invoice.strip()
        dt = _now_str()
        lines = [
            "INVENTORY MANAGEMENT SYSTEM",
            f"Invoice: {inv}",
            f"Date: {dt}",
            f"Customer: {cname}",
            f"Contact: {contact}",
            "-" * 40,
            f"{'PID':<8}{'Name':<16}{'Qty':>5}{'Price':>9}",
            "-" * 40,
        ]
        return "\n".join(lines) + "\n"

    def bill_middle(self) -> str:
        lines: List[str] = []
        for it in self.cart_list:
            name = (it.pname[:15] + "…") if len(it.pname) > 16 else it.pname
            lines.append(f"{it.pid:<8}{name:<16}{it.qty:>5}{it.total:>9.2f}")
        return "\n".join(lines) + ("\n" if lines else "")

    def bill_bottom(self) -> str:
        lines = [
            "-" * 40,
            f"Bill Amount: {float(self.bill_amnt):.2f}",
            f"Discount: {float(self.discount):.2f}",
            f"Net Pay: {float(self.net_pay):.2f}",
            "-" * 40,
        ]
        return "\n".join(lines) + "\n"

    def update_date_time(self) -> None:
        self.lbl_clock.config(text=_now_str())

    def show(self) -> None:
        self.product_Table.clear()
        for rec in sorted(self.db.products.values(), key=lambda r: r.pid):
            self.product_Table.insert(
                {
                    "pid": rec.pid,
                    "name": rec.name,
                    "cat": rec.cat,
                    "sup": rec.sup,
                    "price": rec.price,
                    "qty": rec.qty,
                    "status": rec.status,
                }
            )

    def search(self) -> None:
        txt = self.var_search.get().strip().lower()
        self.product_Table.clear()
        for rec in sorted(self.db.products.values(), key=lambda r: r.pid):
            if (
                txt == ""
                or txt in rec.pid.lower()
                or txt in rec.name.lower()
                or txt in rec.cat.lower()
                or txt in rec.sup.lower()
                or txt in rec.status.lower()
            ):
                self.product_Table.insert(
                    {
                        "pid": rec.pid,
                        "name": rec.name,
                        "cat": rec.cat,
                        "sup": rec.sup,
                        "price": rec.price,
                        "qty": rec.qty,
                        "status": rec.status,
                    }
                )

    def get_data(self, ev: Any) -> None:
        index = getattr(ev, "index", None)
        if index is None:
            selected = self.product_Table.get_selected()
        else:
            self.product_Table.select(index)
            selected = self.product_Table.get_selected()
        if not selected:
            return
        self.var_pid.set(str(selected.get("pid", "")))
        self.var_pname.set(str(selected.get("name", "")))
        self.var_price.set(str(selected.get("price", "")))
        self.var_stock.set(str(selected.get("qty", "")))
        self.lbl_inStock.config(text=str(selected.get("qty", "")))

    def get_data_cart(self, ev: Any) -> None:
        index = getattr(ev, "index", None)
        if index is None:
            selected = self.CartTable.get_selected()
        else:
            self.CartTable.select(index)
            selected = self.CartTable.get_selected()
        if not selected:
            return
        self.var_pid.set(str(selected.get("pid", "")))
        self.var_pname.set(str(selected.get("pname", "")))
        self.var_price.set(str(selected.get("price", "")))
        self.var_qty.set(str(selected.get("qty", "")))
        self.var_stock.set(str(selected.get("stock", "")))
        self.lbl_inStock.config(text=str(selected.get("stock", "")))

    def show_cart(self) -> None:
        self.CartTable.clear()
        for it in self.cart_list:
            self.CartTable.insert(
                {
                    "pid": it.pid,
                    "pname": it.pname,
                    "price": it.price,
                    "qty": it.qty,
                    "stock": it.stock,
                    "total": it.total,
                }
            )

    def clear_cart(self) -> None:
        self.cart_list.clear()
        self.show_cart()
        self.bill_update()

    def clear_all(self) -> None:
        self.var_search.set("")
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")
        self.var_cname.set("")
        self.var_contact.set("")
        self.txt_bill_area.clear()
        self.clear_cart()
        self.chk_print = 0
        self.invoice = ""
        self.bill_amnt = 0
        self.discount = 0.0
        self.net_pay = 0.0
        self.siscount = 0
        self.lbl_inStock.config(text="")
        self.bill_update()
        self.show()

    def bill_update(self) -> None:
        total = sum(it.total for it in self.cart_list)
        self.bill_amnt = int(round(total))
        self.discount = float(self.siscount)
        if self.discount < 0:
            self.discount = 0.0
        net = float(total) - float(self.discount)
        if net < 0:
            net = 0.0
        self.net_pay = net
        self.lbl_amnt.config(text=f"{float(total):.2f}")
        self.lbl_discount.config(text=f"{float(self.discount):.2f}")
        self.lbl_net_pay.config(text=f"{float(self.net_pay):.2f}")
        self.cartTitle.config(text=f"Cart ({len(self.cart_list)})")

    def add_update_cart(self) -> None:
        pid = self.var_pid.get().strip()
        _require_non_empty(pid, "Product ID")
        if pid not in self.db.products:
            raise ValueError("Product not found")

        rec = self.db.products[pid]
        if rec.status.strip().lower() not in ("active", "1", "true", "yes", "available"):
            raise ValueError("Product is not active")

        qty = _parse_int(self.var_qty.get().strip(), "Quantity")
        if qty <= 0:
            raise ValueError("Quantity must be greater than 0")

        stock = int(rec.qty)
        if qty > stock:
            raise ValueError("Quantity exceeds stock")

        price = float(rec.price)
        pname = rec.name

        existing_index = next((i for i, it in enumerate(self.cart_list) if it.pid == pid), None)
        if existing_index is None:
            self.cart_list.append(CartItem(pid=pid, pname=pname, price=price, qty=qty, stock=stock))
        else:
            new_qty = self.cart_list[existing_index].qty + qty
            if new_qty > stock:
                raise ValueError("Total quantity in cart exceeds stock")
            self.cart_list[existing_index] = CartItem(
                pid=pid, pname=pname, price=price, qty=new_qty, stock=stock
            )

        self.show_cart()
        self.bill_update()

    def generate_bill(self) -> None:
        cname = self.var_cname.get().strip()
        contact = self.var_contact.get().strip()
        _require_non_empty(cname, "Customer Name")
        _require_non_empty(contact, "Customer Contact")
        if not self.cart_list:
            raise ValueError("Cart is empty")

        for it in self.cart_list:
            if it.pid not in self.db.products:
                raise ValueError("Product not found during billing")
            rec = self.db.products[it.pid]
            if it.qty > rec.qty:
                raise ValueError("Insufficient stock during billing")

        inv_id = f"INV{next(self._invoice_counter):06d}"
        self.invoice = inv_id

        total = sum(it.total for it in self.cart_list)
        discount = float(self.siscount)
        if discount < 0:
            discount = 0.0
        net = total - discount
        if net < 0:
            net = 0.0

        for it in self.cart_list:
            rec = self.db.products[it.pid]
            self.db.products[it.pid] = ProductRecord(
                pid=rec.pid,
                name=rec.name,
                cat=rec.cat,
                sup=rec.sup,
                price=rec.price,
                qty=int(rec.qty) - int(it.qty),
                status=rec.status,
            )

        self.bill_amnt = int(round(total))
        self.discount = discount
        self.net_pay = net

        bill_text = self.bill_top() + self.bill_middle() + self.bill_bottom()
        self.txt_bill_area.set(bill_text)

        self.db.invoices[inv_id] = InvoiceRecord(
            invoice=inv_id,
            cname=cname,
            contact=contact,
            items=[CartItem(**it.__dict__) for it in self.cart_list],
            bill_amnt=float(total),
            discount=float(discount),
            net_pay=float(net),
            created_at=_now_str(),
            text=bill_text,
        )

        self.chk_print = 1
        self.show()
        self.bill_update()

    def print_bill(self) -> None:
        if not self.invoice or self.invoice not in self.db.invoices:
            raise ValueError("No bill generated to print")
        self.chk_print = 1

    def get_input(self, num: str) -> None:
        current = self.var_cal_input.get()
        self.var_cal_input.set(current + str(num))
        self.txt_cal_input.set(self.var_cal_input.get())

    def clear_cal(self) -> None:
        self.var_cal_input.set("")
        self.txt_cal_input.set("")

    def perform_cal(self) -> None:
        expr = self.var_cal_input.get().strip()
        if expr == "":
            return
        allowed = set("0123456789+-*/(). ")
        if any(ch not in allowed for ch in expr):
            raise ValueError("Invalid characters in calculator input")
        try:
            result = eval(expr, {"__builtins__": {}}, {})
        except Exception as e:
            raise ValueError("Invalid expression") from e
        self.var_cal_input.set(str(result))
        self.txt_cal_input.set(self.var_cal_input.get())


class IMS:
    def __init__(self, root: Any = None, db: InventoryDB = GLOBAL_DB) -> None:
        self.root = root
        self.db = db

        self.MenuLogo: Union[None, PhotoImage] = None
        self.icon_side: PhotoImage = PhotoImage()
        self.icon_title: PhotoImage = PhotoImage()

        self.lbl_category: Label = Label()
        self.lbl_employee: Label = Label()
        self.lbl_product: Label = Label()
        self.lbl_sales: Label = Label()
        self.lbl_supplier: Label = Label()
        self.lbl_clock: Label = Label()

        self.new_obj: Optional[Union[categoryClass, employeeClass, productClass, salesClass, supplierClass]] = None
        self.new_win: Toplevel = Toplevel(root=self.root)

        self.update_content()

    def category(self) -> categoryClass:
        self.new_obj = categoryClass(root=self.new_win, db=self.db)
        self.new_obj.show()
        return self.new_obj

    def employee(self) -> employeeClass:
        self.new_obj = employeeClass(root=self.new_win, db=self.db)
        self.new_obj.show()
        return self.new_obj

    def product(self) -> productClass:
        self.new_obj = productClass(root=self.new_win, db=self.db)
        self.new_obj.show()
        return self.new_obj

    def sales(self) -> salesClass:
        self.new_obj = salesClass(root=self.new_win, db=self.db)
        self.new_obj.show()
        return self.new_obj

    def supplier(self) -> supplierClass:
        self.new_obj = supplierClass(root=self.new_win, db=self.db)
        self.new_obj.show()
        return self.new_obj

    def update_content(self) -> None:
        self.lbl_category.config(text=str(len(self.db.categories)))
        self.lbl_supplier.config(text=str(len(self.db.suppliers)))
        self.lbl_product.config(text=str(len(self.db.products)))
        self.lbl_employee.config(text=str(len(self.db.employees)))
        self.lbl_sales.config(text=str(len(self.db.invoices)))
        self.lbl_clock.config(text=_now_str())