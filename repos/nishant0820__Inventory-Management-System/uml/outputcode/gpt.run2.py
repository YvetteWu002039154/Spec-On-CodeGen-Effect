from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import datetime
import uuid


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
        self._text = text

    def get(self) -> str:
        return self._text

    def set(self, value: str) -> None:
        self._text = str(value)


class Text:
    def __init__(self, text: str = "") -> None:
        self._text = text

    def get(self, start: str = "1.0", end: str = "end") -> str:
        return self._text

    def delete(self, start: str = "1.0", end: str = "end") -> None:
        self._text = ""

    def insert(self, index: str, text: str) -> None:
        if index in ("end", "END"):
            self._text += str(text)
        else:
            self._text += str(text)


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
        if self._selection_index is not None and self._selection_index >= len(self.items):
            self._selection_index = None

    def insert(self, index: int, item: str) -> None:
        if index < 0:
            index = 0
        if index >= len(self.items):
            self.items.append(str(item))
        else:
            self.items.insert(index, str(item))

    def get(self, index: int) -> str:
        return self.items[index]

    def size(self) -> int:
        return len(self.items)

    def curselection(self) -> Tuple[int, ...]:
        if self._selection_index is None:
            return ()
        return (self._selection_index,)

    def select_set(self, index: int) -> None:
        if 0 <= index < len(self.items):
            self._selection_index = index
        else:
            self._selection_index = None


class Treeview:
    def __init__(self) -> None:
        self.rows: List[Dict[str, Any]] = []
        self._selection_index: Optional[int] = None

    def insert(self, values: Dict[str, Any]) -> None:
        self.rows.append(dict(values))

    def delete(self, index: int) -> None:
        if 0 <= index < len(self.rows):
            del self.rows[index]
        if self._selection_index is not None and self._selection_index >= len(self.rows):
            self._selection_index = None

    def clear(self) -> None:
        self.rows.clear()
        self._selection_index = None

    def get_children(self) -> List[int]:
        return list(range(len(self.rows)))

    def item(self, index: int) -> Dict[str, Any]:
        return self.rows[index]

    def selection(self) -> Tuple[int, ...]:
        if self._selection_index is None:
            return ()
        return (self._selection_index,)

    def selection_set(self, index: int) -> None:
        if 0 <= index < len(self.rows):
            self._selection_index = index
        else:
            self._selection_index = None


class StringVar:
    def __init__(self, value: str = "") -> None:
        self._value = str(value)

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = str(value)


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


class InMemoryDB:
    def __init__(self) -> None:
        self.categories: Dict[str, CategoryRecord] = {}
        self.suppliers: Dict[str, SupplierRecord] = {}
        self.employees: Dict[str, EmployeeRecord] = {}
        self.products: Dict[str, ProductRecord] = {}
        self.sales: Dict[str, str] = {}

    def reset(self) -> None:
        self.__init__()


GLOBAL_DB = InMemoryDB()


def _now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _require_non_empty(value: str, field: str) -> None:
    if value is None or str(value).strip() == "":
        raise ValueError(f"{field} is required")


def _parse_float(value: str, field: str) -> float:
    _require_non_empty(value, field)
    try:
        v = float(str(value))
    except Exception as e:
        raise ValueError(f"{field} must be a number") from e
    return v


def _parse_int(value: str, field: str) -> int:
    _require_non_empty(value, field)
    try:
        v = int(float(str(value)))
    except Exception as e:
        raise ValueError(f"{field} must be an integer") from e
    return v


class categoryClass:
    def __init__(self, root: Any = None) -> None:
        self.root = root
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
        if cat_id in GLOBAL_DB.categories:
            raise ValueError("Category ID already exists")
        GLOBAL_DB.categories[cat_id] = CategoryRecord(cat_id=cat_id, name=name)
        self.show()

    def clear(self) -> None:
        self.var_cat_id.set("")
        self.var_name.set("")
        self.CategoryTable.selection_set(-1)

    def delete(self) -> None:
        cat_id = self.var_cat_id.get().strip()
        _require_non_empty(cat_id, "Category ID")
        if cat_id not in GLOBAL_DB.categories:
            raise ValueError("Category not found")
        for p in GLOBAL_DB.products.values():
            if p.cat == cat_id:
                raise ValueError("Cannot delete category in use by products")
        del GLOBAL_DB.categories[cat_id]
        self.clear()
        self.show()

    def get_data(self, ev: Any) -> None:
        sel = self.CategoryTable.selection()
        if not sel:
            return
        idx = sel[0]
        row = self.CategoryTable.item(idx)
        self.var_cat_id.set(str(row.get("cat_id", "")))
        self.var_name.set(str(row.get("name", "")))

    def show(self) -> None:
        self.CategoryTable.clear()
        for cat in sorted(GLOBAL_DB.categories.values(), key=lambda c: c.cat_id):
            self.CategoryTable.insert({"cat_id": cat.cat_id, "name": cat.name})


class supplierClass:
    def __init__(self, root: Any = None) -> None:
        self.root = root
        self.SupplierTable: Treeview = Treeview()
        self.txt_desc: Text = Text()
        self.var_contact: StringVar = StringVar("")
        self.var_name: StringVar = StringVar("")
        self.var_searchby: StringVar = StringVar("")
        self.var_searchtxt: StringVar = StringVar("")
        self.var_sup_invoice: StringVar = StringVar("")

    def add(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        name = self.var_name.get().strip()
        contact = self.var_contact.get().strip()
        desc = self.txt_desc.get().strip()
        _require_non_empty(sup_invoice, "Supplier Invoice")
        _require_non_empty(name, "Supplier Name")
        _require_non_empty(contact, "Supplier Contact")
        if sup_invoice in GLOBAL_DB.suppliers:
            raise ValueError("Supplier invoice already exists")
        GLOBAL_DB.suppliers[sup_invoice] = SupplierRecord(
            sup_invoice=sup_invoice, name=name, contact=contact, desc=desc
        )
        self.show()

    def clear(self) -> None:
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete()
        self.var_searchby.set("")
        self.var_searchtxt.set("")
        self.SupplierTable.selection_set(-1)

    def delete(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        _require_non_empty(sup_invoice, "Supplier Invoice")
        if sup_invoice not in GLOBAL_DB.suppliers:
            raise ValueError("Supplier not found")
        for p in GLOBAL_DB.products.values():
            if p.sup == sup_invoice:
                raise ValueError("Cannot delete supplier in use by products")
        del GLOBAL_DB.suppliers[sup_invoice]
        self.clear()
        self.show()

    def get_data(self, ev: Any) -> None:
        sel = self.SupplierTable.selection()
        if not sel:
            return
        idx = sel[0]
        row = self.SupplierTable.item(idx)
        self.var_sup_invoice.set(str(row.get("sup_invoice", "")))
        self.var_name.set(str(row.get("name", "")))
        self.var_contact.set(str(row.get("contact", "")))
        self.txt_desc.delete()
        self.txt_desc.insert("end", str(row.get("desc", "")))

    def search(self) -> None:
        by = self.var_searchby.get().strip()
        txt = self.var_searchtxt.get().strip().lower()
        self.SupplierTable.clear()
        records = list(GLOBAL_DB.suppliers.values())
        if by and txt:
            if by not in {"sup_invoice", "name", "contact"}:
                raise ValueError("Invalid search field")
            def match(r: SupplierRecord) -> bool:
                val = getattr(r, by)
                return txt in str(val).lower()
            records = [r for r in records if match(r)]
        for r in sorted(records, key=lambda s: s.sup_invoice):
            self.SupplierTable.insert(
                {"sup_invoice": r.sup_invoice, "name": r.name, "contact": r.contact, "desc": r.desc}
            )

    def show(self) -> None:
        self.SupplierTable.clear()
        for r in sorted(GLOBAL_DB.suppliers.values(), key=lambda s: s.sup_invoice):
            self.SupplierTable.insert(
                {"sup_invoice": r.sup_invoice, "name": r.name, "contact": r.contact, "desc": r.desc}
            )

    def update(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        _require_non_empty(sup_invoice, "Supplier Invoice")
        if sup_invoice not in GLOBAL_DB.suppliers:
            raise ValueError("Supplier not found")
        name = self.var_name.get().strip()
        contact = self.var_contact.get().strip()
        desc = self.txt_desc.get().strip()
        _require_non_empty(name, "Supplier Name")
        _require_non_empty(contact, "Supplier Contact")
        GLOBAL_DB.suppliers[sup_invoice] = SupplierRecord(
            sup_invoice=sup_invoice, name=name, contact=contact, desc=desc
        )
        self.show()


class employeeClass:
    def __init__(self, root: Any = None) -> None:
        self.root = root
        self.EmployeeTable: Treeview = Treeview()
        self.txt_address: Text = Text()
        self.var_contact: StringVar = StringVar("")
        self.var_dob: StringVar = StringVar("")
        self.var_doj: StringVar = StringVar("")
        self.var_email: StringVar = StringVar("")
        self.var_emp_id: StringVar = StringVar("")
        self.var_gender: StringVar = StringVar("")
        self.var_name: StringVar = StringVar("")
        self.var_pass: StringVar = StringVar("")
        self.var_salary: StringVar = StringVar("")
        self.var_searchby: StringVar = StringVar("")
        self.var_searchtxt: StringVar = StringVar("")
        self.var_utype: StringVar = StringVar("")

    def add(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        _require_non_empty(emp_id, "Employee ID")
        if emp_id in GLOBAL_DB.employees:
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
        address = self.txt_address.get().strip()
        _require_non_empty(name, "Employee Name")
        _require_non_empty(pass_, "Password")
        _require_non_empty(utype, "User Type")
        GLOBAL_DB.employees[emp_id] = EmployeeRecord(
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
        self.txt_address.delete()
        self.var_searchby.set("")
        self.var_searchtxt.set("")
        self.EmployeeTable.selection_set(-1)

    def delete(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        _require_non_empty(emp_id, "Employee ID")
        if emp_id not in GLOBAL_DB.employees:
            raise ValueError("Employee not found")
        del GLOBAL_DB.employees[emp_id]
        self.clear()
        self.show()

    def get_data(self, ev: Any) -> None:
        sel = self.EmployeeTable.selection()
        if not sel:
            return
        idx = sel[0]
        row = self.EmployeeTable.item(idx)
        self.var_emp_id.set(str(row.get("emp_id", "")))
        self.var_name.set(str(row.get("name", "")))
        self.var_email.set(str(row.get("email", "")))
        self.var_gender.set(str(row.get("gender", "")))
        self.var_contact.set(str(row.get("contact", "")))
        self.var_dob.set(str(row.get("dob", "")))
        self.var_doj.set(str(row.get("doj", "")))
        self.var_pass.set(str(row.get("pass", "")))
        self.var_utype.set(str(row.get("utype", "")))
        self.var_salary.set(str(row.get("salary", "")))
        self.txt_address.delete()
        self.txt_address.insert("end", str(row.get("address", "")))

    def search(self) -> None:
        by = self.var_searchby.get().strip()
        txt = self.var_searchtxt.get().strip().lower()
        self.EmployeeTable.clear()
        records = list(GLOBAL_DB.employees.values())
        if by and txt:
            if by not in {"emp_id", "name", "email", "contact", "utype"}:
                raise ValueError("Invalid search field")
            def match(r: EmployeeRecord) -> bool:
                val = getattr(r, by)
                return txt in str(val).lower()
            records = [r for r in records if match(r)]
        for r in sorted(records, key=lambda e: e.emp_id):
            self.EmployeeTable.insert(
                {
                    "emp_id": r.emp_id,
                    "name": r.name,
                    "email": r.email,
                    "gender": r.gender,
                    "contact": r.contact,
                    "dob": r.dob,
                    "doj": r.doj,
                    "pass": r.pass_,
                    "utype": r.utype,
                    "address": r.address,
                    "salary": r.salary,
                }
            )

    def show(self) -> None:
        self.EmployeeTable.clear()
        for r in sorted(GLOBAL_DB.employees.values(), key=lambda e: e.emp_id):
            self.EmployeeTable.insert(
                {
                    "emp_id": r.emp_id,
                    "name": r.name,
                    "email": r.email,
                    "gender": r.gender,
                    "contact": r.contact,
                    "dob": r.dob,
                    "doj": r.doj,
                    "pass": r.pass_,
                    "utype": r.utype,
                    "address": r.address,
                    "salary": r.salary,
                }
            )

    def update(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        _require_non_empty(emp_id, "Employee ID")
        if emp_id not in GLOBAL_DB.employees:
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
        address = self.txt_address.get().strip()
        _require_non_empty(name, "Employee Name")
        _require_non_empty(pass_, "Password")
        _require_non_empty(utype, "User Type")
        GLOBAL_DB.employees[emp_id] = EmployeeRecord(
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
        self.var_cat: StringVar = StringVar("")
        self.var_name: StringVar = StringVar("")
        self.var_pid: StringVar = StringVar("")
        self.var_price: StringVar = StringVar("")
        self.var_qty: StringVar = StringVar("")
        self.var_searchby: StringVar = StringVar("")
        self.var_searchtxt: StringVar = StringVar("")
        self.var_status: StringVar = StringVar("")
        self.var_sup: StringVar = StringVar("")

    def fetch_cat_sup(self) -> None:
        self.cat_list = sorted(GLOBAL_DB.categories.keys())
        self.sup_list = sorted(GLOBAL_DB.suppliers.keys())

    def add(self) -> None:
        pid = self.var_pid.get().strip()
        _require_non_empty(pid, "Product ID")
        if pid in GLOBAL_DB.products:
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
        if cat not in GLOBAL_DB.categories:
            raise ValueError("Category not found")
        if sup not in GLOBAL_DB.suppliers:
            raise ValueError("Supplier not found")
        if price < 0:
            raise ValueError("Price cannot be negative")
        if qty < 0:
            raise ValueError("Quantity cannot be negative")
        GLOBAL_DB.products[pid] = ProductRecord(
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
        self.ProductTable.selection_set(-1)

    def delete(self) -> None:
        pid = self.var_pid.get().strip()
        _require_non_empty(pid, "Product ID")
        if pid not in GLOBAL_DB.products:
            raise ValueError("Product not found")
        del GLOBAL_DB.products[pid]
        self.clear()
        self.show()

    def get_data(self, ev: Any) -> None:
        sel = self.ProductTable.selection()
        if not sel:
            return
        idx = sel[0]
        row = self.ProductTable.item(idx)
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
        records = list(GLOBAL_DB.products.values())
        if by and txt:
            if by not in {"pid", "name", "cat", "sup", "status"}:
                raise ValueError("Invalid search field")
            def match(r: ProductRecord) -> bool:
                val = getattr(r, by)
                return txt in str(val).lower()
            records = [r for r in records if match(r)]
        for r in sorted(records, key=lambda p: p.pid):
            self.ProductTable.insert(
                {
                    "pid": r.pid,
                    "name": r.name,
                    "cat": r.cat,
                    "sup": r.sup,
                    "price": r.price,
                    "qty": r.qty,
                    "status": r.status,
                }
            )

    def show(self) -> None:
        self.ProductTable.clear()
        for r in sorted(GLOBAL_DB.products.values(), key=lambda p: p.pid):
            self.ProductTable.insert(
                {
                    "pid": r.pid,
                    "name": r.name,
                    "cat": r.cat,
                    "sup": r.sup,
                    "price": r.price,
                    "qty": r.qty,
                    "status": r.status,
                }
            )

    def update(self) -> None:
        pid = self.var_pid.get().strip()
        _require_non_empty(pid, "Product ID")
        if pid not in GLOBAL_DB.products:
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
        if cat not in GLOBAL_DB.categories:
            raise ValueError("Category not found")
        if sup not in GLOBAL_DB.suppliers:
            raise ValueError("Supplier not found")
        if price < 0:
            raise ValueError("Price cannot be negative")
        if qty < 0:
            raise ValueError("Quantity cannot be negative")
        GLOBAL_DB.products[pid] = ProductRecord(
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
        self.var_invoice: StringVar = StringVar("")

    def clear(self) -> None:
        self.var_invoice.set("")
        self.bill_area.delete()
        self.Sales_List.delete(0, self.Sales_List.size() - 1 if self.Sales_List.size() else 0)
        self.blll_list = []

    def get_data(self, ev: Any) -> None:
        sel = self.Sales_List.curselection()
        if not sel:
            return
        invoice = self.Sales_List.get(sel[0])
        self.var_invoice.set(invoice)
        content = GLOBAL_DB.sales.get(invoice, "")
        self.bill_area.delete()
        self.bill_area.insert("end", content)

    def search(self) -> None:
        invoice = self.var_invoice.get().strip()
        _require_non_empty(invoice, "Invoice")
        if invoice not in GLOBAL_DB.sales:
            raise ValueError("Invoice not found")
        self.bill_area.delete()
        self.bill_area.insert("end", GLOBAL_DB.sales[invoice])

    def show(self) -> None:
        self.Sales_List.delete(0, self.Sales_List.size() - 1 if self.Sales_List.size() else 0)
        self.blll_list = sorted(GLOBAL_DB.sales.keys())
        for i, inv in enumerate(self.blll_list):
            self.Sales_List.insert(i, inv)


class billClass:
    def __init__(self, root: Any = None) -> None:
        self.root = root
        self.CartTable: Treeview = Treeview()
        self.bill_amnt: int = 0
        self.cartTitle: Label = Label()
        self.cart_list: List[CartItem] = []
        self.chk_print: int = 0
        self.discount: float = 0.0
        self.icon_title: PhotoImage = PhotoImage()
        self.invoice: str = ""
        self.lbl_amnt: Label = Label()
        self.lbl_clock: Label = Label()
        self.lbl_discount: Label = Label()
        self.lbl_inStock: Label = Label()
        self.lbl_net_pay: Label = Label()
        self.net_pay: Union[float, int] = 0.0
        self.product_Table: Treeview = Treeview()
        self.siscount: int = 0
        self.txt_bill_area: Text = Text()
        self.txt_cal_input: Entry = Entry()
        self.var_cal_input: StringVar = StringVar("")
        self.var_cname: StringVar = StringVar("")
        self.var_contact: StringVar = StringVar("")
        self.var_pid: StringVar = StringVar("")
        self.var_pname: StringVar = StringVar("")
        self.var_price: StringVar = StringVar("")
        self.var_qty: StringVar = StringVar("")
        self.var_search: StringVar = StringVar("")
        self.var_stock: StringVar = StringVar("")
        self.update_date_time()
        self.show()

    def bill_top(self) -> None:
        self.invoice = self.invoice.strip() or self._new_invoice()
        cname = self.var_cname.get().strip()
        contact = self.var_contact.get().strip()
        header = []
        header.append("INVENTORY MANAGEMENT SYSTEM")
        header.append(f"Invoice: {self.invoice}")
        header.append(f"Date: {_now_str()}")
        header.append(f"Customer: {cname}")
        header.append(f"Contact: {contact}")
        header.append("-" * 40)
        header.append(f"{'PID':<8}{'Name':<16}{'Qty':>4}{'Price':>6}{'Amt':>6}")
        header.append("-" * 40)
        self.txt_bill_area.delete()
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
        self.discount = float(self.siscount) if self.siscount else float(self.discount)
        if self.discount < 0:
            self.discount = 0.0
        net = total - self.discount
        if net < 0:
            net = 0.0
        self.net_pay = net
        self.lbl_amnt.config(text=f"{total:.2f}")
        self.lbl_discount.config(text=f"{self.discount:.2f}")
        self.lbl_net_pay.config(text=f"{net:.2f}")

    def clear_all(self) -> None:
        self.clear_cart()
        self.var_cname.set("")
        self.var_contact.set("")
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")
        self.var_search.set("")
        self.siscount = 0
        self.discount = 0.0
        self.bill_amnt = 0
        self.net_pay = 0.0
        self.invoice = ""
        self.txt_bill_area.delete()
        self.chk_print = 0
        self.show()
        self.show_cart()
        self.update_date_time()

    def clear_cal(self) -> None:
        self.var_cal_input.set("")
        self.txt_cal_input.set("")

    def clear_cart(self) -> None:
        self.cart_list = []
        self.CartTable.clear()
        self.bill_update()

    def _new_invoice(self) -> str:
        return datetime.datetime.now().strftime("INV%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6].upper()

    def generate_bill(self) -> None:
        if not self.cart_list:
            raise ValueError("Cart is empty")
        self.invoice = self.invoice.strip() or self._new_invoice()
        self.bill_top()
        self.bill_middle()
        self.bill_bottom()
        GLOBAL_DB.sales[self.invoice] = self.txt_bill_area.get()
        self.chk_print = 1

    def print_bill(self) -> None:
        if not self.chk_print:
            raise ValueError("No bill generated to print")
        if not self.invoice or self.invoice not in GLOBAL_DB.sales:
            raise ValueError("Invoice not found")
        self.chk_print = 2

    def get_data(self, ev: Any) -> None:
        sel = self.product_Table.selection()
        if not sel:
            return
        idx = sel[0]
        row = self.product_Table.item(idx)
        pid = str(row.get("pid", ""))
        if pid and pid in GLOBAL_DB.products:
            p = GLOBAL_DB.products[pid]
            self.var_pid.set(p.pid)
            self.var_pname.set(p.name)
            self.var_price.set(f"{p.price:.2f}")
            self.var_stock.set(str(p.qty))
            self.lbl_inStock.config(text=str(p.qty))

    def get_data_cart(self, ev: Any) -> None:
        sel = self.CartTable.selection()
        if not sel:
            return
        idx = sel[0]
        row = self.CartTable.item(idx)
        self.var_pid.set(str(row.get("pid", "")))
        self.var_pname.set(str(row.get("pname", "")))
        self.var_price.set(str(row.get("price", "")))
        self.var_qty.set(str(row.get("qty", "")))
        self.var_stock.set(str(row.get("stock", "")))
        self.lbl_inStock.config(text=str(row.get("stock", "")))

    def add_update_cart(self) -> None:
        pid = self.var_pid.get().strip()
        _require_non_empty(pid, "Product ID")
        if pid not in GLOBAL_DB.products:
            raise ValueError("Product not found")
        p = GLOBAL_DB.products[pid]
        qty = _parse_int(self.var_qty.get().strip(), "Quantity")
        if qty <= 0:
            raise ValueError("Quantity must be greater than zero")
        if qty > p.qty:
            raise ValueError("Quantity exceeds stock")
        existing = next((ci for ci in self.cart_list if ci.pid == pid), None)
        if existing is None:
            self.cart_list.append(
                CartItem(pid=p.pid, pname=p.name, price=float(p.price), qty=qty, stock=int(p.qty))
            )
        else:
            existing.qty = qty
            existing.price = float(p.price)
            existing.stock = int(p.qty)
            existing.pname = p.name
        self.show_cart()
        self.bill_update()

    def show(self) -> None:
        self.product_Table.clear()
        search_txt = self.var_search.get().strip().lower()
        products = list(GLOBAL_DB.products.values())
        if search_txt:
            products = [p for p in products if search_txt in p.pid.lower() or search_txt in p.name.lower()]
        for p in sorted(products, key=lambda x: x.pid):
            self.product_Table.insert(
                {"pid": p.pid, "name": p.name, "cat": p.cat, "sup": p.sup, "price": p.price, "qty": p.qty, "status": p.status}
            )

    def show_cart(self) -> None:
        self.CartTable.clear()
        for ci in self.cart_list:
            self.CartTable.insert(
                {"pid": ci.pid, "pname": ci.pname, "price": ci.price, "qty": ci.qty, "stock": ci.stock, "amount": ci.amount}
            )

    def search(self) -> None:
        self.show()

    def update_date_time(self) -> None:
        self.lbl_clock.config(text=_now_str())

    def get_input(self, num: Union[int, str]) -> None:
        s = self.var_cal_input.get()
        s += str(num)
        self.var_cal_input.set(s)
        self.txt_cal_input.set(s)

    def perform_cal(self) -> None:
        expr = self.var_cal_input.get().strip()
        if not expr:
            return
        allowed = set("0123456789+-*/(). ")
        if any(ch not in allowed for ch in expr):
            raise ValueError("Invalid characters in calculator input")
        try:
            result = eval(expr, {"__builtins__": {}}, {})
        except Exception as e:
            raise ValueError("Invalid expression") from e
        self.var_cal_input.set(str(result))
        self.txt_cal_input.set(str(result))

    def update_stock_after_sale(self) -> None:
        for ci in self.cart_list:
            if ci.pid not in GLOBAL_DB.products:
                raise ValueError("Product not found during stock update")
            p = GLOBAL_DB.products[ci.pid]
            if ci.qty > p.qty:
                raise ValueError("Insufficient stock during stock update")
            p.qty -= ci.qty
            GLOBAL_DB.products[ci.pid] = p

    def finalize_sale(self) -> None:
        self.generate_bill()
        self.update_stock_after_sale()
        self.show()
        self.clear_cart()
        self.bill_update()


class IMS:
    def __init__(self, root: Any = None) -> None:
        self.root = root
        self.MenuLogo: Optional[PhotoImage] = None
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
        self.new_obj.fetch_cat_sup()
        return self.new_obj

    def sales(self) -> salesClass:
        self.new_win = Toplevel(self.root)
        self.new_obj = salesClass(self.new_win)
        self.new_obj.show()
        return self.new_obj

    def supplier(self) -> supplierClass:
        self.new_win = Toplevel(self.root)
        self.new_obj = supplierClass(self.new_win)
        return self.new_obj

    def update_content(self) -> None:
        self.lbl_clock.config(text=_now_str())
        self.lbl_category.config(text=str(len(GLOBAL_DB.categories)))
        self.lbl_supplier.config(text=str(len(GLOBAL_DB.suppliers)))
        self.lbl_employee.config(text=str(len(GLOBAL_DB.employees)))
        self.lbl_product.config(text=str(len(GLOBAL_DB.products)))
        self.lbl_sales.config(text=str(len(GLOBAL_DB.sales)))