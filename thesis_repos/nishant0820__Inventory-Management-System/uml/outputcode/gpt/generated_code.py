from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import datetime
import itertools


class StringVar:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = "" if value is None else str(value)


class PhotoImage:
    def __init__(self, data: Any = None) -> None:
        self.data = data


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

    def delete(self, start: int, end: Optional[int] = None) -> None:
        self.text = ""

    def insert(self, index: int, value: str) -> None:
        self.text = str(value)


class Text:
    def __init__(self, text: str = "") -> None:
        self._text = text

    def get(self, start: str = "1.0", end: str = "end") -> str:
        return self._text

    def delete(self, start: str = "1.0", end: str = "end") -> None:
        self._text = ""

    def insert(self, index: str, value: str) -> None:
        self._text += str(value)


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
            self.items.append(str(item))
        else:
            self.items.insert(index, str(item))

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
        self._rows: List[Tuple[Any, ...]] = []
        self._selection_index: Optional[int] = None

    def delete(self, *items: Any) -> None:
        self._rows.clear()
        self._selection_index = None

    def insert(self, parent: str, index: str, values: Tuple[Any, ...]) -> None:
        self._rows.append(tuple(values))

    def get_children(self) -> List[int]:
        return list(range(len(self._rows)))

    def item(self, item_id: int, option: str = "values") -> Dict[str, Any]:
        if option != "values":
            return {}
        return {"values": self._rows[item_id]}

    def selection(self) -> Tuple[int, ...]:
        return () if self._selection_index is None else (self._selection_index,)

    def selection_set(self, item_id: int) -> None:
        if 0 <= item_id < len(self._rows):
            self._selection_index = item_id
        else:
            self._selection_index = None

    def clear(self) -> None:
        self._rows.clear()
        self._selection_index = None

    @property
    def rows(self) -> List[Tuple[Any, ...]]:
        return list(self._rows)


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
    price: str
    qty: str
    status: str


@dataclass
class BillLine:
    pid: str
    pname: str
    price: float
    qty: int
    stock_at_add: int

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

    def reset(self) -> None:
        self.__init__()


_DB = _InMemoryDB()


def _now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _require_non_empty(value: str, field: str) -> None:
    if value is None or str(value).strip() == "":
        raise ValueError(f"{field} is required")


def _to_int(value: str, field: str) -> int:
    _require_non_empty(value, field)
    try:
        return int(str(value))
    except Exception as e:
        raise ValueError(f"{field} must be an integer") from e


def _to_float(value: str, field: str) -> float:
    _require_non_empty(value, field)
    try:
        return float(str(value))
    except Exception as e:
        raise ValueError(f"{field} must be a number") from e


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
        if cat_id in _DB.categories:
            raise ValueError("Category ID already exists")
        _DB.categories[cat_id] = CategoryRecord(cat_id=cat_id, name=name)
        self.show()

    def clear(self) -> None:
        self.var_cat_id.set("")
        self.var_name.set("")
        self.CategoryTable.clear()

    def delete(self) -> None:
        cat_id = self.var_cat_id.get().strip()
        _require_non_empty(cat_id, "Category ID")
        if cat_id not in _DB.categories:
            raise ValueError("Category not found")
        del _DB.categories[cat_id]
        self.show()

    def get_data(self, ev: Any) -> None:
        sel = self.CategoryTable.selection()
        if not sel:
            return
        values = self.CategoryTable.item(sel[0], "values").get("values", ())
        if len(values) >= 2:
            self.var_cat_id.set(str(values[0]))
            self.var_name.set(str(values[1]))

    def show(self) -> None:
        self.CategoryTable.clear()
        for rec in _DB.categories.values():
            self.CategoryTable.insert("", "end", (rec.cat_id, rec.name))


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
        desc = self.txt_desc.get().strip()
        _require_non_empty(sup_invoice, "Supplier Invoice")
        _require_non_empty(name, "Supplier Name")
        _require_non_empty(contact, "Supplier Contact")
        if sup_invoice in _DB.suppliers:
            raise ValueError("Supplier invoice already exists")
        _DB.suppliers[sup_invoice] = SupplierRecord(
            sup_invoice=sup_invoice, name=name, contact=contact, desc=desc
        )
        self.show()

    def clear(self) -> None:
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.var_searchby.set("")
        self.var_searchtxt.set("")
        self.txt_desc.delete("1.0", "end")
        self.SupplierTable.clear()

    def delete(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        _require_non_empty(sup_invoice, "Supplier Invoice")
        if sup_invoice not in _DB.suppliers:
            raise ValueError("Supplier not found")
        del _DB.suppliers[sup_invoice]
        self.show()

    def get_data(self, ev: Any) -> None:
        sel = self.SupplierTable.selection()
        if not sel:
            return
        values = self.SupplierTable.item(sel[0], "values").get("values", ())
        if len(values) >= 4:
            self.var_sup_invoice.set(str(values[0]))
            self.var_name.set(str(values[1]))
            self.var_contact.set(str(values[2]))
            self.txt_desc.delete("1.0", "end")
            self.txt_desc.insert("1.0", str(values[3]))

    def search(self) -> None:
        by = self.var_searchby.get().strip()
        txt = self.var_searchtxt.get().strip()
        if by == "" or txt == "":
            self.show()
            return
        by_l = by.lower()
        txt_l = txt.lower()
        results: List[SupplierRecord] = []
        for rec in _DB.suppliers.values():
            if by_l in ("invoice", "sup_invoice", "supplier invoice"):
                if txt_l in rec.sup_invoice.lower():
                    results.append(rec)
            elif by_l in ("name", "supplier name"):
                if txt_l in rec.name.lower():
                    results.append(rec)
            elif by_l in ("contact", "supplier contact"):
                if txt_l in rec.contact.lower():
                    results.append(rec)
            else:
                if (
                    txt_l in rec.sup_invoice.lower()
                    or txt_l in rec.name.lower()
                    or txt_l in rec.contact.lower()
                    or txt_l in rec.desc.lower()
                ):
                    results.append(rec)
        self.SupplierTable.clear()
        for rec in results:
            self.SupplierTable.insert("", "end", (rec.sup_invoice, rec.name, rec.contact, rec.desc))

    def show(self) -> None:
        self.SupplierTable.clear()
        for rec in _DB.suppliers.values():
            self.SupplierTable.insert("", "end", (rec.sup_invoice, rec.name, rec.contact, rec.desc))

    def update(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        _require_non_empty(sup_invoice, "Supplier Invoice")
        if sup_invoice not in _DB.suppliers:
            raise ValueError("Supplier not found")
        name = self.var_name.get().strip()
        contact = self.var_contact.get().strip()
        desc = self.txt_desc.get().strip()
        _require_non_empty(name, "Supplier Name")
        _require_non_empty(contact, "Supplier Contact")
        _DB.suppliers[sup_invoice] = SupplierRecord(
            sup_invoice=sup_invoice, name=name, contact=contact, desc=desc
        )
        self.show()


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

        _require_non_empty(emp_id, "Employee ID")
        _require_non_empty(name, "Employee Name")
        _require_non_empty(pass_, "Password")
        _require_non_empty(utype, "User Type")
        if emp_id in _DB.employees:
            raise ValueError("Employee ID already exists")

        _DB.employees[emp_id] = EmployeeRecord(
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
        self.txt_address.delete("1.0", "end")
        self.EmployeeTable.clear()

    def delete(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        _require_non_empty(emp_id, "Employee ID")
        if emp_id not in _DB.employees:
            raise ValueError("Employee not found")
        del _DB.employees[emp_id]
        self.show()

    def get_data(self, ev: Any) -> None:
        sel = self.EmployeeTable.selection()
        if not sel:
            return
        values = self.EmployeeTable.item(sel[0], "values").get("values", ())
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
            self.txt_address.insert("1.0", str(values[9]))
            self.var_salary.set(str(values[10]))

    def search(self) -> None:
        by = self.var_searchby.get().strip()
        txt = self.var_searchtxt.get().strip()
        if by == "" or txt == "":
            self.show()
            return
        by_l = by.lower()
        txt_l = txt.lower()
        results: List[EmployeeRecord] = []
        for rec in _DB.employees.values():
            if by_l in ("emp_id", "id", "employee id"):
                if txt_l in rec.emp_id.lower():
                    results.append(rec)
            elif by_l in ("name", "employee name"):
                if txt_l in rec.name.lower():
                    results.append(rec)
            elif by_l in ("email",):
                if txt_l in rec.email.lower():
                    results.append(rec)
            elif by_l in ("contact",):
                if txt_l in rec.contact.lower():
                    results.append(rec)
            elif by_l in ("utype", "user type"):
                if txt_l in rec.utype.lower():
                    results.append(rec)
            else:
                blob = " ".join(
                    [
                        rec.emp_id,
                        rec.name,
                        rec.email,
                        rec.gender,
                        rec.contact,
                        rec.dob,
                        rec.doj,
                        rec.utype,
                        rec.address,
                        rec.salary,
                    ]
                ).lower()
                if txt_l in blob:
                    results.append(rec)
        self.EmployeeTable.clear()
        for rec in results:
            self.EmployeeTable.insert(
                "",
                "end",
                (
                    rec.emp_id,
                    rec.name,
                    rec.email,
                    rec.gender,
                    rec.contact,
                    rec.dob,
                    rec.doj,
                    rec.pass_,
                    rec.utype,
                    rec.address,
                    rec.salary,
                ),
            )

    def show(self) -> None:
        self.EmployeeTable.clear()
        for rec in _DB.employees.values():
            self.EmployeeTable.insert(
                "",
                "end",
                (
                    rec.emp_id,
                    rec.name,
                    rec.email,
                    rec.gender,
                    rec.contact,
                    rec.dob,
                    rec.doj,
                    rec.pass_,
                    rec.utype,
                    rec.address,
                    rec.salary,
                ),
            )

    def update(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        _require_non_empty(emp_id, "Employee ID")
        if emp_id not in _DB.employees:
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

        _require_non_empty(name, "Employee Name")
        _require_non_empty(pass_, "Password")
        _require_non_empty(utype, "User Type")

        _DB.employees[emp_id] = EmployeeRecord(
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

    def fetch_cat_sup(self) -> None:
        self.cat_list = [rec.name for rec in _DB.categories.values()]
        self.sup_list = [rec.name for rec in _DB.suppliers.values()]

    def add(self) -> None:
        pid = self.var_pid.get().strip()
        name = self.var_name.get().strip()
        cat = self.var_cat.get().strip()
        sup = self.var_sup.get().strip()
        price = self.var_price.get().strip()
        qty = self.var_qty.get().strip()
        status = self.var_status.get().strip()

        _require_non_empty(pid, "Product ID")
        _require_non_empty(name, "Product Name")
        _require_non_empty(cat, "Category")
        _require_non_empty(sup, "Supplier")
        _to_float(price, "Price")
        q = _to_int(qty, "Quantity")
        if q < 0:
            raise ValueError("Quantity cannot be negative")
        _require_non_empty(status, "Status")

        if pid in _DB.products:
            raise ValueError("Product ID already exists")

        _DB.products[pid] = ProductRecord(
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
        self.ProductTable.clear()

    def delete(self) -> None:
        pid = self.var_pid.get().strip()
        _require_non_empty(pid, "Product ID")
        if pid not in _DB.products:
            raise ValueError("Product not found")
        del _DB.products[pid]
        self.show()

    def get_data(self, ev: Any) -> None:
        sel = self.ProductTable.selection()
        if not sel:
            return
        values = self.ProductTable.item(sel[0], "values").get("values", ())
        if len(values) >= 7:
            self.var_pid.set(str(values[0]))
            self.var_name.set(str(values[1]))
            self.var_cat.set(str(values[2]))
            self.var_sup.set(str(values[3]))
            self.var_price.set(str(values[4]))
            self.var_qty.set(str(values[5]))
            self.var_status.set(str(values[6]))

    def search(self) -> None:
        by = self.var_searchby.get().strip()
        txt = self.var_searchtxt.get().strip()
        if by == "" or txt == "":
            self.show()
            return
        by_l = by.lower()
        txt_l = txt.lower()
        results: List[ProductRecord] = []
        for rec in _DB.products.values():
            if by_l in ("pid", "id", "product id"):
                if txt_l in rec.pid.lower():
                    results.append(rec)
            elif by_l in ("name", "product name"):
                if txt_l in rec.name.lower():
                    results.append(rec)
            elif by_l in ("category", "cat"):
                if txt_l in rec.cat.lower():
                    results.append(rec)
            elif by_l in ("supplier", "sup"):
                if txt_l in rec.sup.lower():
                    results.append(rec)
            elif by_l in ("status",):
                if txt_l in rec.status.lower():
                    results.append(rec)
            else:
                blob = " ".join([rec.pid, rec.name, rec.cat, rec.sup, rec.price, rec.qty, rec.status]).lower()
                if txt_l in blob:
                    results.append(rec)
        self.ProductTable.clear()
        for rec in results:
            self.ProductTable.insert("", "end", (rec.pid, rec.name, rec.cat, rec.sup, rec.price, rec.qty, rec.status))

    def show(self) -> None:
        self.ProductTable.clear()
        for rec in _DB.products.values():
            self.ProductTable.insert("", "end", (rec.pid, rec.name, rec.cat, rec.sup, rec.price, rec.qty, rec.status))

    def update(self) -> None:
        pid = self.var_pid.get().strip()
        _require_non_empty(pid, "Product ID")
        if pid not in _DB.products:
            raise ValueError("Product not found")

        name = self.var_name.get().strip()
        cat = self.var_cat.get().strip()
        sup = self.var_sup.get().strip()
        price = self.var_price.get().strip()
        qty = self.var_qty.get().strip()
        status = self.var_status.get().strip()

        _require_non_empty(name, "Product Name")
        _require_non_empty(cat, "Category")
        _require_non_empty(sup, "Supplier")
        _to_float(price, "Price")
        q = _to_int(qty, "Quantity")
        if q < 0:
            raise ValueError("Quantity cannot be negative")
        _require_non_empty(status, "Status")

        _DB.products[pid] = ProductRecord(
            pid=pid, name=name, cat=cat, sup=sup, price=price, qty=qty, status=status
        )
        self.show()


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
        content = _DB.sales.get(invoice, "")
        self.bill_area.delete("1.0", "end")
        self.bill_area.insert("1.0", content)

    def search(self) -> None:
        invoice = self.var_invoice.get().strip()
        self.Sales_List.delete(0, len(self.Sales_List.items) - 1 if self.Sales_List.items else 0)
        self.blll_list = []
        if invoice == "":
            self.show()
            return
        for inv in sorted(_DB.sales.keys()):
            if invoice.lower() in inv.lower():
                self.Sales_List.insert(len(self.Sales_List.items), inv)
                self.blll_list.append(inv)

    def show(self) -> None:
        self.Sales_List.delete(0, len(self.Sales_List.items) - 1 if self.Sales_List.items else 0)
        self.blll_list = []
        for inv in sorted(_DB.sales.keys()):
            self.Sales_List.insert(len(self.Sales_List.items), inv)
            self.blll_list.append(inv)


class billClass:
    _invoice_counter = itertools.count(1)

    def __init__(self, root: Any = None) -> None:
        self.root = root
        self.CartTable: Treeview = Treeview()
        self.product_Table: Treeview = Treeview()

        self.bill_amnt: int = 0
        self.discount: float = 0.0
        self.net_pay: Union[float, int] = 0
        self.chk_print: int = 0
        self.siscount: int = 0

        self.cart_list: List[BillLine] = []
        self.invoice: str = ""

        self.icon_title: PhotoImage = PhotoImage()

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

        self.bill_top()
        self.bill_middle()
        self.bill_bottom()
        self.update_date_time()
        self.show()
        self.show_cart()

    def bill_top(self) -> None:
        if self.invoice == "":
            self.invoice = f"INV{next(self._invoice_counter):06d}"

    def bill_middle(self) -> None:
        return

    def bill_bottom(self) -> None:
        return

    def update_date_time(self) -> None:
        self.lbl_clock.config(text=_now_str())

    def show(self) -> None:
        self.product_Table.clear()
        for rec in _DB.products.values():
            self.product_Table.insert(
                "",
                "end",
                (rec.pid, rec.name, rec.price, rec.qty, rec.status, rec.cat, rec.sup),
            )

    def search(self) -> None:
        txt = self.var_search.get().strip().lower()
        if txt == "":
            self.show()
            return
        self.product_Table.clear()
        for rec in _DB.products.values():
            blob = " ".join([rec.pid, rec.name, rec.price, rec.qty, rec.status, rec.cat, rec.sup]).lower()
            if txt in blob:
                self.product_Table.insert(
                    "",
                    "end",
                    (rec.pid, rec.name, rec.price, rec.qty, rec.status, rec.cat, rec.sup),
                )

    def get_data(self, ev: Any) -> None:
        sel = self.product_Table.selection()
        if not sel:
            return
        values = self.product_Table.item(sel[0], "values").get("values", ())
        if len(values) >= 4:
            pid = str(values[0])
            pname = str(values[1])
            price = str(values[2])
            stock = str(values[3])
            self.var_pid.set(pid)
            self.var_pname.set(pname)
            self.var_price.set(price)
            self.var_stock.set(stock)
            self.lbl_inStock.config(text=stock)

    def get_data_cart(self, ev: Any) -> None:
        sel = self.CartTable.selection()
        if not sel:
            return
        values = self.CartTable.item(sel[0], "values").get("values", ())
        if len(values) >= 4:
            self.var_pid.set(str(values[0]))
            self.var_pname.set(str(values[1]))
            self.var_price.set(str(values[2]))
            self.var_qty.set(str(values[3]))

    def add_update_cart(self) -> None:
        pid = self.var_pid.get().strip()
        pname = self.var_pname.get().strip()
        price_s = self.var_price.get().strip()
        qty_s = self.var_qty.get().strip()

        _require_non_empty(pid, "Product ID")
        _require_non_empty(pname, "Product Name")
        price = _to_float(price_s, "Price")
        qty = _to_int(qty_s, "Quantity")
        if qty <= 0:
            raise ValueError("Quantity must be greater than 0")

        if pid not in _DB.products:
            raise ValueError("Product not found")
        prod = _DB.products[pid]
        stock = _to_int(prod.qty, "Stock")
        if qty > stock:
            raise ValueError("Insufficient stock")

        existing = next((i for i, line in enumerate(self.cart_list) if line.pid == pid), None)
        if existing is None:
            self.cart_list.append(BillLine(pid=pid, pname=pname, price=price, qty=qty, stock_at_add=stock))
        else:
            self.cart_list[existing] = BillLine(pid=pid, pname=pname, price=price, qty=qty, stock_at_add=stock)

        self.show_cart()
        self.bill_update()

    def show_cart(self) -> None:
        self.CartTable.clear()
        for line in self.cart_list:
            self.CartTable.insert("", "end", (line.pid, line.pname, f"{line.price:.2f}", str(line.qty), f"{line.amount:.2f}"))

    def clear_cart(self) -> None:
        self.cart_list = []
        self.show_cart()
        self.bill_update()

    def clear_all(self) -> None:
        self.var_cname.set("")
        self.var_contact.set("")
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_search.set("")
        self.var_stock.set("")
        self.txt_bill_area.delete("1.0", "end")
        self.clear_cart()
        self.bill_top()
        self.update_date_time()

    def bill_update(self) -> None:
        total = sum(line.amount for line in self.cart_list)
        self.bill_amnt = int(round(total))
        self.discount = float(self.siscount) if isinstance(self.siscount, int) else float(self.discount)
        disc = float(self.discount)
        if disc < 0:
            disc = 0.0
        if disc > total:
            disc = total
        net = total - disc
        self.net_pay = net
        self.lbl_amnt.config(text=f"{total:.2f}")
        self.lbl_discount.config(text=f"{disc:.2f}")
        self.lbl_net_pay.config(text=f"{net:.2f}")

    def generate_bill(self) -> None:
        cname = self.var_cname.get().strip()
        contact = self.var_contact.get().strip()
        if not self.cart_list:
            raise ValueError("Cart is empty")

        for line in self.cart_list:
            if line.pid not in _DB.products:
                raise ValueError("Product not found during billing")
            prod = _DB.products[line.pid]
            stock = _to_int(prod.qty, "Stock")
            if line.qty > stock:
                raise ValueError("Insufficient stock during billing")

        total = sum(line.amount for line in self.cart_list)
        disc = float(self.discount)
        if disc < 0:
            disc = 0.0
        if disc > total:
            disc = total
        net = total - disc

        lines: List[str] = []
        lines.append("INVENTORY MANAGEMENT SYSTEM - BILL")
        lines.append(f"Invoice: {self.invoice}")
        lines.append(f"DateTime: {_now_str()}")
        lines.append(f"Customer: {cname if cname else '-'}")
        lines.append(f"Contact: {contact if contact else '-'}")
        lines.append("-" * 50)
        lines.append(f"{'PID':<10}{'Name':<20}{'Qty':>5}{'Price':>7}{'Amt':>8}")
        lines.append("-" * 50)
        for line in self.cart_list:
            lines.append(
                f"{line.pid:<10}{line.pname[:20]:<20}{line.qty:>5}{line.price:>7.2f}{line.amount:>8.2f}"
            )
        lines.append("-" * 50)
        lines.append(f"{'Total':<40}{total:>10.2f}")
        lines.append(f"{'Discount':<40}{disc:>10.2f}")
        lines.append(f"{'Net Pay':<40}{net:>10.2f}")
        lines.append("-" * 50)

        bill_text = "\n".join(lines)
        self.txt_bill_area.delete("1.0", "end")
        self.txt_bill_area.insert("1.0", bill_text)

        for line in self.cart_list:
            prod = _DB.products[line.pid]
            stock = _to_int(prod.qty, "Stock")
            new_stock = stock - line.qty
            _DB.products[line.pid] = ProductRecord(
                pid=prod.pid,
                name=prod.name,
                cat=prod.cat,
                sup=prod.sup,
                price=prod.price,
                qty=str(new_stock),
                status=prod.status,
            )

        _DB.sales[self.invoice] = bill_text
        self.chk_print = 1
        self.show()
        self.bill_update()

    def print_bill(self) -> None:
        if self.chk_print != 1:
            raise ValueError("No bill generated to print")
        self.chk_print = 2

    def clear_cal(self) -> None:
        self.var_cal_input.set("")
        self.txt_cal_input.delete(0, None)

    def get_input(self, num: Any) -> None:
        current = self.var_cal_input.get()
        current += str(num)
        self.var_cal_input.set(current)
        self.txt_cal_input.delete(0, None)
        self.txt_cal_input.insert(0, current)

    def perform_cal(self) -> None:
        expr = self.var_cal_input.get().strip()
        if expr == "":
            return
        allowed = set("0123456789+-*/(). ")
        if any(ch not in allowed for ch in expr):
            raise ValueError("Invalid calculator input")
        try:
            result = eval(expr, {"__builtins__": {}}, {})
        except Exception as e:
            raise ValueError("Calculator error") from e
        self.var_cal_input.set(str(result))
        self.txt_cal_input.delete(0, None)
        self.txt_cal_input.insert(0, str(result))


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

        self.update_content()

    def update_content(self) -> None:
        self.lbl_clock.config(text=_now_str())
        self.lbl_category.config(text=str(len(_DB.categories)))
        self.lbl_supplier.config(text=str(len(_DB.suppliers)))
        self.lbl_employee.config(text=str(len(_DB.employees)))
        self.lbl_product.config(text=str(len(_DB.products)))
        self.lbl_sales.config(text=str(len(_DB.sales)))

    def category(self) -> categoryClass:
        self.new_win = Toplevel(self.root)
        self.new_obj = categoryClass(self.new_win)
        self.update_content()
        return self.new_obj

    def employee(self) -> employeeClass:
        self.new_win = Toplevel(self.root)
        self.new_obj = employeeClass(self.new_win)
        self.update_content()
        return self.new_obj

    def product(self) -> productClass:
        self.new_win = Toplevel(self.root)
        self.new_obj = productClass(self.new_win)
        self.new_obj.fetch_cat_sup()
        self.update_content()
        return self.new_obj

    def sales(self) -> salesClass:
        self.new_win = Toplevel(self.root)
        self.new_obj = salesClass(self.new_win)
        self.new_obj.show()
        self.update_content()
        return self.new_obj

    def supplier(self) -> supplierClass:
        self.new_win = Toplevel(self.root)
        self.new_obj = supplierClass(self.new_win)
        self.update_content()
        return self.new_obj


__all__ = [
    "IMS",
    "billClass",
    "categoryClass",
    "employeeClass",
    "productClass",
    "salesClass",
    "supplierClass",
    "StringVar",
    "PhotoImage",
    "Label",
    "Entry",
    "Text",
    "Listbox",
    "Treeview",
    "Toplevel",
]