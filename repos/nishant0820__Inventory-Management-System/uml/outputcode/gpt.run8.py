from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import datetime
import itertools


class PhotoImage:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs


class Label:
    def __init__(self, text: str = "") -> None:
        self.text = text

    def config(self, **kwargs: Any) -> None:
        if "text" in kwargs:
            self.text = str(kwargs["text"])


class Entry:
    def __init__(self, text: str = "") -> None:
        self.text = text

    def get(self) -> str:
        return self.text

    def delete(self, start: int = 0, end: Optional[int] = None) -> None:
        self.text = ""

    def insert(self, index: int, value: str) -> None:
        self.text = value


class Text:
    def __init__(self, text: str = "") -> None:
        self._text = text

    def get(self, start: str = "1.0", end: str = "end") -> str:
        return self._text

    def delete(self, start: str = "1.0", end: str = "end") -> None:
        self._text = ""

    def insert(self, index: str, value: str) -> None:
        self._text += value


class Listbox:
    def __init__(self) -> None:
        self.items: List[str] = []
        self._selection_index: Optional[int] = None

    def delete(self, start: int, end: Optional[int] = None) -> None:
        if end is None:
            end = start
        if start < 0:
            start = 0
        if end >= len(self.items):
            end = len(self.items) - 1
        if start <= end and self.items:
            del self.items[start : end + 1]
        self._selection_index = None

    def insert(self, index: int, item: str) -> None:
        if index < 0 or index > len(self.items):
            self.items.append(item)
        else:
            self.items.insert(index, item)

    def get(self, index: int) -> str:
        return self.items[index]

    def curselection(self) -> Tuple[int, ...]:
        return () if self._selection_index is None else (self._selection_index,)

    def select_set(self, index: int) -> None:
        if 0 <= index < len(self.items):
            self._selection_index = index
        else:
            self._selection_index = None


class Treeview:
    def __init__(self) -> None:
        self._rows: List[Dict[str, Any]] = []
        self._selection_index: Optional[int] = None

    def insert(self, parent: str, index: str, values: Tuple[Any, ...]) -> None:
        self._rows.append({"values": values})

    def get_children(self) -> List[int]:
        return list(range(len(self._rows)))

    def delete(self, item: int) -> None:
        if 0 <= item < len(self._rows):
            del self._rows[item]
            if self._selection_index == item:
                self._selection_index = None
            elif self._selection_index is not None and self._selection_index > item:
                self._selection_index -= 1

    def item(self, item: int, option: str = "values") -> Any:
        if option != "values":
            raise ValueError("Only 'values' option is supported")
        return self._rows[item]["values"]

    def selection(self) -> Tuple[int, ...]:
        return () if self._selection_index is None else (self._selection_index,)

    def select_set(self, item: int) -> None:
        if 0 <= item < len(self._rows):
            self._selection_index = item
        else:
            self._selection_index = None

    def clear(self) -> None:
        self._rows.clear()
        self._selection_index = None

    @property
    def rows(self) -> List[Tuple[Any, ...]]:
        return [r["values"] for r in self._rows]


class StringVar:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = "" if value is None else str(value)


class Toplevel:
    def __init__(self, root: Any = None) -> None:
        self.root = root


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
    def amount(self) -> float:
        return float(self.price) * int(self.qty)


class _InMemoryDB:
    def __init__(self) -> None:
        self.categories: Dict[str, CategoryRecord] = {}
        self.suppliers: Dict[str, SupplierRecord] = {}
        self.employees: Dict[str, EmployeeRecord] = {}
        self.products: Dict[str, ProductRecord] = {}
        self.sales: Dict[str, str] = {}

    def next_invoice(self) -> str:
        existing = [int(k) for k in self.sales.keys() if k.isdigit()]
        nxt = (max(existing) + 1) if existing else 1
        return f"{nxt:06d}"


_GLOBAL_DB = _InMemoryDB()


def _now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _require_non_empty(value: str, field: str) -> None:
    if value is None or str(value).strip() == "":
        raise ValueError(f"{field} is required")


def _to_int(value: str, field: str) -> int:
    _require_non_empty(value, field)
    try:
        iv = int(str(value).strip())
    except Exception as e:
        raise ValueError(f"{field} must be an integer") from e
    return iv


def _to_float(value: str, field: str) -> float:
    _require_non_empty(value, field)
    try:
        fv = float(str(value).strip())
    except Exception as e:
        raise ValueError(f"{field} must be a number") from e
    return fv


class categoryClass:
    def __init__(self, root: Any = None) -> None:
        self.root = root
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
        _require_non_empty(cat_id, "Category ID")
        _require_non_empty(name, "Category Name")
        if cat_id in _GLOBAL_DB.categories:
            raise ValueError("Category ID already exists")
        _GLOBAL_DB.categories[cat_id] = CategoryRecord(cat_id=cat_id, name=name)
        self.show()
        self.clear()

    def clear(self) -> None:
        self.var_cat_id.set("")
        self.var_name.set("")
        self.CategoryTable.select_set(-1)

    def delete(self) -> None:
        cat_id = self.var_cat_id.get().strip()
        _require_non_empty(cat_id, "Category ID")
        if cat_id not in _GLOBAL_DB.categories:
            raise ValueError("Category not found")
        del _GLOBAL_DB.categories[cat_id]
        self.show()
        self.clear()

    def get_data(self, ev: Any) -> None:
        sel = self.CategoryTable.selection()
        if not sel:
            return
        values = self.CategoryTable.item(sel[0], "values")
        if len(values) >= 2:
            self.var_cat_id.set(str(values[0]))
            self.var_name.set(str(values[1]))

    def show(self) -> None:
        self.CategoryTable.clear()
        for cat in sorted(_GLOBAL_DB.categories.values(), key=lambda c: c.cat_id):
            self.CategoryTable.insert("", "end", (cat.cat_id, cat.name))


class supplierClass:
    def __init__(self, root: Any = None) -> None:
        self.root = root
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
        desc = self.txt_desc.get("1.0", "end").strip()
        _require_non_empty(sup_invoice, "Supplier Invoice")
        _require_non_empty(name, "Supplier Name")
        _require_non_empty(contact, "Supplier Contact")
        if sup_invoice in _GLOBAL_DB.suppliers:
            raise ValueError("Supplier invoice already exists")
        _GLOBAL_DB.suppliers[sup_invoice] = SupplierRecord(
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
        self.txt_desc.delete("1.0", "end")
        self.SupplierTable.select_set(-1)

    def delete(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        _require_non_empty(sup_invoice, "Supplier Invoice")
        if sup_invoice not in _GLOBAL_DB.suppliers:
            raise ValueError("Supplier not found")
        del _GLOBAL_DB.suppliers[sup_invoice]
        self.show()
        self.clear()

    def get_data(self, ev: Any) -> None:
        sel = self.SupplierTable.selection()
        if not sel:
            return
        values = self.SupplierTable.item(sel[0], "values")
        if len(values) >= 4:
            self.var_sup_invoice.set(str(values[0]))
            self.var_name.set(str(values[1]))
            self.var_contact.set(str(values[2]))
            self.txt_desc.delete("1.0", "end")
            self.txt_desc.insert("end", str(values[3]))

    def search(self) -> None:
        by = self.var_searchby.get().strip().lower()
        txt = self.var_searchtxt.get().strip().lower()
        if by == "" or txt == "":
            self.show()
            return

        def match(s: SupplierRecord) -> bool:
            if by in ("invoice", "sup_invoice", "supplier invoice"):
                return txt in s.sup_invoice.lower()
            if by in ("name", "supplier name"):
                return txt in s.name.lower()
            if by in ("contact", "phone"):
                return txt in s.contact.lower()
            return False

        self.SupplierTable.clear()
        for s in sorted(_GLOBAL_DB.suppliers.values(), key=lambda r: r.sup_invoice):
            if match(s):
                self.SupplierTable.insert("", "end", (s.sup_invoice, s.name, s.contact, s.desc))

    def show(self) -> None:
        self.SupplierTable.clear()
        for s in sorted(_GLOBAL_DB.suppliers.values(), key=lambda r: r.sup_invoice):
            self.SupplierTable.insert("", "end", (s.sup_invoice, s.name, s.contact, s.desc))

    def update(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        _require_non_empty(sup_invoice, "Supplier Invoice")
        if sup_invoice not in _GLOBAL_DB.suppliers:
            raise ValueError("Supplier not found")
        name = self.var_name.get().strip()
        contact = self.var_contact.get().strip()
        desc = self.txt_desc.get("1.0", "end").strip()
        _require_non_empty(name, "Supplier Name")
        _require_non_empty(contact, "Supplier Contact")
        _GLOBAL_DB.suppliers[sup_invoice] = SupplierRecord(
            sup_invoice=sup_invoice, name=name, contact=contact, desc=desc
        )
        self.show()
        self.clear()


class employeeClass:
    def __init__(self, root: Any = None) -> None:
        self.root = root
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
        _require_non_empty(emp_id, "Employee ID")
        if emp_id in _GLOBAL_DB.employees:
            raise ValueError("Employee ID already exists")
        name = self.var_name.get().strip()
        email = self.var_email.get().strip()
        gender = self.var_gender.get().strip()
        contact = self.var_contact.get().strip()
        dob = self.var_dob.get().strip()
        doj = self.var_doj.get().strip()
        pass_ = self.var_pass.get().strip()
        utype = self.var_utype.get().strip()
        salary = self.var_salary.get().strip()
        address = self.txt_address.get("1.0", "end").strip()

        _require_non_empty(name, "Name")
        _require_non_empty(email, "Email")
        _require_non_empty(gender, "Gender")
        _require_non_empty(contact, "Contact")
        _require_non_empty(dob, "DOB")
        _require_non_empty(doj, "DOJ")
        _require_non_empty(pass_, "Password")
        _require_non_empty(utype, "User Type")
        _require_non_empty(salary, "Salary")
        _require_non_empty(address, "Address")

        _GLOBAL_DB.employees[emp_id] = EmployeeRecord(
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
        self.txt_address.delete("1.0", "end")
        self.EmployeeTable.select_set(-1)

    def delete(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        _require_non_empty(emp_id, "Employee ID")
        if emp_id not in _GLOBAL_DB.employees:
            raise ValueError("Employee not found")
        del _GLOBAL_DB.employees[emp_id]
        self.show()
        self.clear()

    def get_data(self, ev: Any) -> None:
        sel = self.EmployeeTable.selection()
        if not sel:
            return
        values = self.EmployeeTable.item(sel[0], "values")
        if len(values) >= 11:
            self.var_emp_id.set(str(values[0]))
            self.var_name.set(str(values[1]))
            self.var_email.set(str(values[2]))
            self.var_gender.set(str(values[3]))
            self.var_contact.set(str(values[4]))
            self.var_dob.set(str(values[5]))
            self.var_doj.set(str(values[6]))
            self.var_pass.set(str(values[7]))
            self.var_utype.set(str(values[8]))
            self.txt_address.delete("1.0", "end")
            self.txt_address.insert("end", str(values[9]))
            self.var_salary.set(str(values[10]))

    def search(self) -> None:
        by = self.var_searchby.get().strip().lower()
        txt = self.var_searchtxt.get().strip().lower()
        if by == "" or txt == "":
            self.show()
            return

        def match(e: EmployeeRecord) -> bool:
            if by in ("emp_id", "id", "employee id"):
                return txt in e.emp_id.lower()
            if by in ("name", "employee name"):
                return txt in e.name.lower()
            if by in ("email",):
                return txt in e.email.lower()
            if by in ("contact", "phone"):
                return txt in e.contact.lower()
            if by in ("utype", "user type"):
                return txt in e.utype.lower()
            return False

        self.EmployeeTable.clear()
        for e in sorted(_GLOBAL_DB.employees.values(), key=lambda r: r.emp_id):
            if match(e):
                self.EmployeeTable.insert(
                    "", "end",
                    (
                        e.emp_id, e.name, e.email, e.gender, e.contact,
                        e.dob, e.doj, e.pass_, e.utype, e.address, e.salary
                    ),
                )

    def show(self) -> None:
        self.EmployeeTable.clear()
        for e in sorted(_GLOBAL_DB.employees.values(), key=lambda r: r.emp_id):
            self.EmployeeTable.insert(
                "", "end",
                (
                    e.emp_id, e.name, e.email, e.gender, e.contact,
                    e.dob, e.doj, e.pass_, e.utype, e.address, e.salary
                ),
            )

    def update(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        _require_non_empty(emp_id, "Employee ID")
        if emp_id not in _GLOBAL_DB.employees:
            raise ValueError("Employee not found")
        name = self.var_name.get().strip()
        email = self.var_email.get().strip()
        gender = self.var_gender.get().strip()
        contact = self.var_contact.get().strip()
        dob = self.var_dob.get().strip()
        doj = self.var_doj.get().strip()
        pass_ = self.var_pass.get().strip()
        utype = self.var_utype.get().strip()
        salary = self.var_salary.get().strip()
        address = self.txt_address.get("1.0", "end").strip()

        _require_non_empty(name, "Name")
        _require_non_empty(email, "Email")
        _require_non_empty(gender, "Gender")
        _require_non_empty(contact, "Contact")
        _require_non_empty(dob, "DOB")
        _require_non_empty(doj, "DOJ")
        _require_non_empty(pass_, "Password")
        _require_non_empty(utype, "User Type")
        _require_non_empty(salary, "Salary")
        _require_non_empty(address, "Address")

        _GLOBAL_DB.employees[emp_id] = EmployeeRecord(
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
        self.clear()


class productClass:
    def __init__(self, root: Any = None) -> None:
        self.root = root
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
        self.cat_list = [c.name for c in _GLOBAL_DB.categories.values()]
        self.sup_list = [s.name for s in _GLOBAL_DB.suppliers.values()]

    def add(self) -> None:
        pid = self.var_pid.get().strip()
        _require_non_empty(pid, "Product ID")
        if pid in _GLOBAL_DB.products:
            raise ValueError("Product ID already exists")
        name = self.var_name.get().strip()
        cat = self.var_cat.get().strip()
        sup = self.var_sup.get().strip()
        price = _to_float(self.var_price.get().strip(), "Price")
        qty = _to_int(self.var_qty.get().strip(), "Quantity")
        status = self.var_status.get().strip()

        _require_non_empty(name, "Product Name")
        _require_non_empty(cat, "Category")
        _require_non_empty(sup, "Supplier")
        _require_non_empty(status, "Status")
        if qty < 0:
            raise ValueError("Quantity cannot be negative")
        if price < 0:
            raise ValueError("Price cannot be negative")

        _GLOBAL_DB.products[pid] = ProductRecord(
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
        self.ProductTable.select_set(-1)

    def delete(self) -> None:
        pid = self.var_pid.get().strip()
        _require_non_empty(pid, "Product ID")
        if pid not in _GLOBAL_DB.products:
            raise ValueError("Product not found")
        del _GLOBAL_DB.products[pid]
        self.show()
        self.clear()

    def get_data(self, ev: Any) -> None:
        sel = self.ProductTable.selection()
        if not sel:
            return
        values = self.ProductTable.item(sel[0], "values")
        if len(values) >= 8:
            self.var_pid.set(str(values[0]))
            self.var_cat.set(str(values[1]))
            self.var_sup.set(str(values[2]))
            self.var_name.set(str(values[3]))
            self.var_price.set(str(values[4]))
            self.var_qty.set(str(values[5]))
            self.var_status.set(str(values[6]))

    def search(self) -> None:
        by = self.var_searchby.get().strip().lower()
        txt = self.var_searchtxt.get().strip().lower()
        if by == "" or txt == "":
            self.show()
            return

        def match(p: ProductRecord) -> bool:
            if by in ("pid", "id", "product id"):
                return txt in p.pid.lower()
            if by in ("name", "product name"):
                return txt in p.name.lower()
            if by in ("category", "cat"):
                return txt in p.cat.lower()
            if by in ("supplier", "sup"):
                return txt in p.sup.lower()
            if by in ("status",):
                return txt in p.status.lower()
            return False

        self.ProductTable.clear()
        for p in sorted(_GLOBAL_DB.products.values(), key=lambda r: r.pid):
            if match(p):
                self.ProductTable.insert(
                    "", "end",
                    (p.pid, p.cat, p.sup, p.name, f"{p.price:.2f}", p.qty, p.status, "N/A"),
                )

    def show(self) -> None:
        self.ProductTable.clear()
        for p in sorted(_GLOBAL_DB.products.values(), key=lambda r: r.pid):
            self.ProductTable.insert(
                "", "end",
                (p.pid, p.cat, p.sup, p.name, f"{p.price:.2f}", p.qty, p.status, "N/A"),
            )

    def update(self) -> None:
        pid = self.var_pid.get().strip()
        _require_non_empty(pid, "Product ID")
        if pid not in _GLOBAL_DB.products:
            raise ValueError("Product not found")
        name = self.var_name.get().strip()
        cat = self.var_cat.get().strip()
        sup = self.var_sup.get().strip()
        price = _to_float(self.var_price.get().strip(), "Price")
        qty = _to_int(self.var_qty.get().strip(), "Quantity")
        status = self.var_status.get().strip()

        _require_non_empty(name, "Product Name")
        _require_non_empty(cat, "Category")
        _require_non_empty(sup, "Supplier")
        _require_non_empty(status, "Status")
        if qty < 0:
            raise ValueError("Quantity cannot be negative")
        if price < 0:
            raise ValueError("Price cannot be negative")

        _GLOBAL_DB.products[pid] = ProductRecord(
            pid=pid, name=name, cat=cat, sup=sup, price=price, qty=qty, status=status
        )
        self.fetch_cat_sup()
        self.show()
        self.clear()


class salesClass:
    def __init__(self, root: Any = None) -> None:
        self.root = root
        self.Sales_List: Listbox = Listbox()
        self.bill_area: Text = Text()
        self.bill_photo: Optional[PhotoImage] = None
        self.blll_list: List[str] = []
        self.var_invoice: StringVar = StringVar()

    def clear(self) -> None:
        self.var_invoice.set("")
        self.bill_area.delete("1.0", "end")
        self.Sales_List.delete(0, len(self.Sales_List.items) - 1 if self.Sales_List.items else 0)
        self.blll_list = []

    def get_data(self, ev: Any) -> None:
        sel = self.Sales_List.curselection()
        if not sel:
            return
        invoice = self.Sales_List.get(sel[0])
        self.var_invoice.set(invoice)
        content = _GLOBAL_DB.sales.get(invoice, "")
        self.bill_area.delete("1.0", "end")
        self.bill_area.insert("end", content)

    def search(self) -> None:
        invoice = self.var_invoice.get().strip()
        if invoice == "":
            self.show()
            return
        self.Sales_List.delete(0, len(self.Sales_List.items) - 1 if self.Sales_List.items else 0)
        self.blll_list = []
        for inv in sorted(_GLOBAL_DB.sales.keys()):
            if invoice in inv:
                self.Sales_List.insert(len(self.Sales_List.items), inv)
                self.blll_list.append(inv)

    def show(self) -> None:
        self.Sales_List.delete(0, len(self.Sales_List.items) - 1 if self.Sales_List.items else 0)
        self.blll_list = []
        for inv in sorted(_GLOBAL_DB.sales.keys()):
            self.Sales_List.insert(len(self.Sales_List.items), inv)
            self.blll_list.append(inv)


class billClass:
    def __init__(self, root: Any = None) -> None:
        self.root = root
        self.CartTable: Treeview = Treeview()
        self.product_Table: Treeview = Treeview()
        self.bill_amnt: int = 0
        self.cartTitle: Label = Label()
        self.cart_list: List[CartItem] = []
        self.chk_print: int = 0
        self.discount: float = 0.0
        self.icon_title: PhotoImage = PhotoImage()
        self.invoice: str = _GLOBAL_DB.next_invoice()
        self.lbl_amnt: Label = Label()
        self.lbl_clock: Label = Label()
        self.lbl_discount: Label = Label()
        self.lbl_inStock: Label = Label()
        self.lbl_net_pay: Label = Label()
        self.net_pay: Union[float, int] = 0.0
        self.siscount: int = 0
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
        self.show()
        self.update_date_time()

    def bill_top(self) -> None:
        cname = self.var_cname.get().strip()
        contact = self.var_contact.get().strip()
        header = []
        header.append("INVENTORY MANAGEMENT SYSTEM")
        header.append(f"Invoice: {self.invoice}")
        header.append(f"Date: {_now_str()}")
        header.append(f"Customer: {cname if cname else 'N/A'}")
        header.append(f"Contact: {contact if contact else 'N/A'}")
        header.append("-" * 40)
        header.append(f"{'PID':<8}{'Name':<16}{'Qty':>4}{'Price':>6}{'Amt':>6}")
        header.append("-" * 40)
        self.txt_bill_area.delete("1.0", "end")
        self.txt_bill_area.insert("end", "\n".join(header) + "\n")

    def bill_middle(self) -> None:
        for item in self.cart_list:
            line = f"{item.pid:<8}{item.pname[:15]:<16}{item.qty:>4}{item.price:>6.2f}{item.amount:>6.2f}"
            self.txt_bill_area.insert("end", line + "\n")

    def bill_bottom(self) -> None:
        self.bill_update()
        footer = []
        footer.append("-" * 40)
        footer.append(f"Bill Amount: {float(self.bill_amnt):.2f}")
        footer.append(f"Discount: {float(self.discount):.2f}")
        footer.append(f"Net Pay: {float(self.net_pay):.2f}")
        footer.append("-" * 40)
        self.txt_bill_area.insert("end", "\n".join(footer) + "\n")

    def bill_update(self) -> None:
        total = sum(ci.amount for ci in self.cart_list)
        self.bill_amnt = int(round(total))
        disc = float(self.discount) if self.discount else 0.0
        if disc < 0:
            disc = 0.0
        if disc > total:
            disc = total
        self.discount = disc
        self.net_pay = total - disc
        self.lbl_amnt.config(text=f"{total:.2f}")
        self.lbl_discount.config(text=f"{disc:.2f}")
        self.lbl_net_pay.config(text=f"{float(self.net_pay):.2f}")

    def clear_all(self) -> None:
        self.clear_cart()
        self.var_cname.set("")
        self.var_contact.set("")
        self.discount = 0.0
        self.siscount = 0
        self.chk_print = 0
        self.invoice = _GLOBAL_DB.next_invoice()
        self.txt_bill_area.delete("1.0", "end")
        self.bill_update()

    def clear_cal(self) -> None:
        self.var_cal_input.set("")
        self.txt_cal_input.delete(0, None)

    def clear_cart(self) -> None:
        self.cart_list = []
        self.CartTable.clear()
        self.bill_update()

    def show(self) -> None:
        self.product_Table.clear()
        for p in sorted(_GLOBAL_DB.products.values(), key=lambda r: r.pid):
            self.product_Table.insert(
                "", "end",
                (p.pid, p.name, f"{p.price:.2f}", p.qty, p.status),
            )

    def search(self) -> None:
        txt = self.var_search.get().strip().lower()
        if txt == "":
            self.show()
            return
        self.product_Table.clear()
        for p in sorted(_GLOBAL_DB.products.values(), key=lambda r: r.pid):
            if txt in p.pid.lower() or txt in p.name.lower():
                self.product_Table.insert(
                    "", "end",
                    (p.pid, p.name, f"{p.price:.2f}", p.qty, p.status),
                )

    def get_data(self, ev: Any) -> None:
        sel = self.product_Table.selection()
        if not sel:
            return
        values = self.product_Table.item(sel[0], "values")
        if len(values) >= 5:
            pid = str(values[0])
            pname = str(values[1])
            price = str(values[2])
            stock = str(values[3])
            self.var_pid.set(pid)
            self.var_pname.set(pname)
            self.var_price.set(price)
            self.var_stock.set(stock)
            self.lbl_inStock.config(text=stock)

    def show_cart(self) -> None:
        self.CartTable.clear()
        for ci in self.cart_list:
            self.CartTable.insert(
                "", "end",
                (ci.pid, ci.pname, f"{ci.price:.2f}", ci.qty, f"{ci.amount:.2f}"),
            )
        self.bill_update()

    def get_data_cart(self, ev: Any) -> None:
        sel = self.CartTable.selection()
        if not sel:
            return
        values = self.CartTable.item(sel[0], "values")
        if len(values) >= 4:
            self.var_pid.set(str(values[0]))
            self.var_pname.set(str(values[1]))
            self.var_price.set(str(values[2]))
            self.var_qty.set(str(values[3]))

    def add_update_cart(self) -> None:
        pid = self.var_pid.get().strip()
        _require_non_empty(pid, "Product ID")
        if pid not in _GLOBAL_DB.products:
            raise ValueError("Product not found")
        p = _GLOBAL_DB.products[pid]
        qty = _to_int(self.var_qty.get().strip(), "Quantity")
        if qty <= 0:
            raise ValueError("Quantity must be greater than 0")
        if qty > p.qty:
            raise ValueError("Quantity exceeds stock")

        existing = next((ci for ci in self.cart_list if ci.pid == pid), None)
        if existing is None:
            self.cart_list.append(
                CartItem(pid=p.pid, pname=p.name, price=p.price, qty=qty, stock=p.qty)
            )
        else:
            if qty > p.qty:
                raise ValueError("Quantity exceeds stock")
            existing.qty = qty
            existing.stock = p.qty
            existing.price = p.price
            existing.pname = p.name

        self.show_cart()
        self.var_qty.set("")

    def generate_bill(self) -> None:
        if not self.cart_list:
            raise ValueError("Cart is empty")
        self.bill_top()
        self.bill_middle()
        self.bill_bottom()
        _GLOBAL_DB.sales[self.invoice] = self.txt_bill_area.get("1.0", "end")
        for ci in self.cart_list:
            if ci.pid in _GLOBAL_DB.products:
                pr = _GLOBAL_DB.products[ci.pid]
                new_qty = pr.qty - ci.qty
                if new_qty < 0:
                    raise ValueError("Insufficient stock during billing")
                _GLOBAL_DB.products[ci.pid] = ProductRecord(
                    pid=pr.pid,
                    name=pr.name,
                    cat=pr.cat,
                    sup=pr.sup,
                    price=pr.price,
                    qty=new_qty,
                    status=pr.status,
                )
        self.chk_print = 1
        self.show()

    def print_bill(self) -> None:
        if self.chk_print != 1:
            raise ValueError("Bill not generated")
        self.chk_print = 2

    def update_date_time(self) -> None:
        self.lbl_clock.config(text=_now_str())

    def get_input(self, num: Union[int, str]) -> None:
        current = self.var_cal_input.get()
        self.var_cal_input.set(current + str(num))
        self.txt_cal_input.delete(0, None)
        self.txt_cal_input.insert(0, self.var_cal_input.get())

    def perform_cal(self) -> None:
        expr = self.var_cal_input.get().strip()
        if expr == "":
            return
        allowed = set("0123456789.+-*/() ")
        if any(ch not in allowed for ch in expr):
            raise ValueError("Invalid calculator input")
        try:
            result = eval(expr, {"__builtins__": {}}, {})
        except Exception as e:
            raise ValueError("Invalid expression") from e
        self.var_cal_input.set(str(result))
        self.txt_cal_input.delete(0, None)
        self.txt_cal_input.insert(0, self.var_cal_input.get())


class IMS:
    def __init__(self, root: Any = None) -> None:
        self.root = root
        self.MenuLogo: Optional[Union[None, PhotoImage]] = None
        self.icon_side: PhotoImage = PhotoImage()
        self.icon_title: PhotoImage = PhotoImage()
        self.lbl_category: Label = Label()
        self.lbl_clock: Label = Label()
        self.lbl_employee: Label = Label()
        self.lbl_product: Label = Label()
        self.lbl_sales: Label = Label()
        self.lbl_supplier: Label = Label()
        self.new_obj: Optional[Union[categoryClass, employeeClass, productClass, salesClass, supplierClass]] = None
        self.new_win: Optional[Toplevel] = None

    def category(self) -> categoryClass:
        self.new_win = Toplevel(self.root)
        self.new_obj = categoryClass(self.new_win)
        return self.new_obj

    def employee(self) -> employeeClass:
        self.new_win = Toplevel(self.root)
        self.new_obj = employeeClass(self.new_win)
        return self.new_obj

    def product(self) -> productClass:
        self.new_win = Toplevel(self.root)
        self.new_obj = productClass(self.new_win)
        return self.new_obj

    def sales(self) -> salesClass:
        self.new_win = Toplevel(self.root)
        self.new_obj = salesClass(self.new_win)
        return self.new_obj

    def supplier(self) -> supplierClass:
        self.new_win = Toplevel(self.root)
        self.new_obj = supplierClass(self.new_win)
        return self.new_obj

    def update_content(self) -> None:
        self.lbl_clock.config(text=_now_str())
        self.lbl_category.config(text=str(len(_GLOBAL_DB.categories)))
        self.lbl_supplier.config(text=str(len(_GLOBAL_DB.suppliers)))
        self.lbl_product.config(text=str(len(_GLOBAL_DB.products)))
        self.lbl_employee.config(text=str(len(_GLOBAL_DB.employees)))
        self.lbl_sales.config(text=str(len(_GLOBAL_DB.sales)))