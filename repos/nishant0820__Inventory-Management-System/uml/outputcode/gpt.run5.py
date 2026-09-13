from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import datetime
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


class Toplevel:
    def __init__(self, root: Any = None) -> None:
        self.root = root


class Text:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value

    def delete(self) -> None:
        self._value = ""


class Entry:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value

    def delete(self) -> None:
        self._value = ""


class StringVar:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value


class Treeview:
    def __init__(self) -> None:
        self._rows: List[Dict[str, Any]] = []
        self._selected_index: Optional[int] = None

    def clear(self) -> None:
        self._rows.clear()
        self._selected_index = None

    def insert(self, row: Dict[str, Any]) -> None:
        self._rows.append(dict(row))

    def all(self) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._rows]

    def select(self, index: int) -> None:
        if index < 0 or index >= len(self._rows):
            raise IndexError("Selection index out of range")
        self._selected_index = index

    def selected(self) -> Optional[Dict[str, Any]]:
        if self._selected_index is None:
            return None
        if self._selected_index < 0 or self._selected_index >= len(self._rows):
            return None
        return dict(self._rows[self._selected_index])

    def delete_selected(self) -> None:
        if self._selected_index is None:
            return
        if 0 <= self._selected_index < len(self._rows):
            del self._rows[self._selected_index]
        self._selected_index = None


class Listbox:
    def __init__(self) -> None:
        self._items: List[str] = []
        self._selected_index: Optional[int] = None

    def clear(self) -> None:
        self._items.clear()
        self._selected_index = None

    def insert(self, item: str) -> None:
        self._items.append(item)

    def all(self) -> List[str]:
        return list(self._items)

    def select(self, index: int) -> None:
        if index < 0 or index >= len(self._items):
            raise IndexError("Selection index out of range")
        self._selected_index = index

    def selected(self) -> Optional[str]:
        if self._selected_index is None:
            return None
        if self._selected_index < 0 or self._selected_index >= len(self._items):
            return None
        return self._items[self._selected_index]

    def delete_selected(self) -> None:
        if self._selected_index is None:
            return
        if 0 <= self._selected_index < len(self._items):
            del self._items[self._selected_index]
        self._selected_index = None


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


class _InMemoryDB:
    def __init__(self) -> None:
        self.categories: Dict[str, CategoryRecord] = {}
        self.suppliers: Dict[str, SupplierRecord] = {}
        self.employees: Dict[str, EmployeeRecord] = {}
        self.products: Dict[str, ProductRecord] = {}
        self.sales: Dict[str, str] = {}

    def reset(self) -> None:
        self.categories.clear()
        self.suppliers.clear()
        self.employees.clear()
        self.products.clear()
        self.sales.clear()


_DB = _InMemoryDB()


def _now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _require_non_empty(value: str, field: str) -> None:
    if value is None or str(value).strip() == "":
        raise ValueError(f"{field} is required")


def _to_int(value: str, field: str) -> int:
    try:
        i = int(str(value).strip())
    except Exception as e:
        raise ValueError(f"{field} must be an integer") from e
    return i


def _to_float(value: str, field: str) -> float:
    try:
        f = float(str(value).strip())
    except Exception as e:
        raise ValueError(f"{field} must be a number") from e
    return f


class category:
    class categoryClass:
        def __init__(self, root: Any = None) -> None:
            self.root = root
            self.CategoryTable: Treeview = Treeview()
            self.im1: Union[None, PhotoImage] = None
            self.im2: Union[None, PhotoImage] = None
            self.lbl_im1: Label = Label("")
            self.lbl_im2: Label = Label("")
            self.var_cat_id: StringVar = StringVar("")
            self.var_name: StringVar = StringVar("")

        def add(self) -> None:
            cat_id = self.var_cat_id.get().strip()
            name = self.var_name.get().strip()
            _require_non_empty(cat_id, "Category ID")
            _require_non_empty(name, "Category Name")
            if cat_id in _DB.categories:
                raise ValueError("Category ID already exists")
            _DB.categories[cat_id] = CategoryRecord(cat_id=cat_id, name=name)
            self.show()
            self.clear()

        def clear(self) -> None:
            self.var_cat_id.set("")
            self.var_name.set("")
            self.CategoryTable._selected_index = None

        def delete(self) -> None:
            cat_id = self.var_cat_id.get().strip()
            _require_non_empty(cat_id, "Category ID")
            if cat_id not in _DB.categories:
                raise ValueError("Category not found")
            del _DB.categories[cat_id]
            self.show()
            self.clear()

        def get_data(self, ev: Any) -> None:
            row = self.CategoryTable.selected()
            if not row:
                return
            self.var_cat_id.set(str(row.get("cat_id", "")))
            self.var_name.set(str(row.get("name", "")))

        def show(self) -> None:
            self.CategoryTable.clear()
            for rec in sorted(_DB.categories.values(), key=lambda r: r.cat_id):
                self.CategoryTable.insert({"cat_id": rec.cat_id, "name": rec.name})


class supplier:
    class supplierClass:
        def __init__(self, root: Any = None) -> None:
            self.root = root
            self.SupplierTable: Treeview = Treeview()
            self.txt_desc: Text = Text("")
            self.var_contact: StringVar = StringVar("")
            self.var_name: StringVar = StringVar("")
            self.var_searchby: StringVar = StringVar("")
            self.var_searchtxt: StringVar = StringVar("")
            self.var_sup_invoice: StringVar = StringVar("")

        def add(self) -> None:
            sup_invoice = self.var_sup_invoice.get().strip()
            name = self.var_name.get().strip()
            contact = self.var_contact.get().strip()
            desc = self.txt_desc.get()
            _require_non_empty(sup_invoice, "Supplier Invoice")
            _require_non_empty(name, "Supplier Name")
            _require_non_empty(contact, "Supplier Contact")
            if sup_invoice in _DB.suppliers:
                raise ValueError("Supplier invoice already exists")
            _DB.suppliers[sup_invoice] = SupplierRecord(
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
            self.txt_desc.delete()
            self.SupplierTable._selected_index = None

        def delete(self) -> None:
            sup_invoice = self.var_sup_invoice.get().strip()
            _require_non_empty(sup_invoice, "Supplier Invoice")
            if sup_invoice not in _DB.suppliers:
                raise ValueError("Supplier not found")
            del _DB.suppliers[sup_invoice]
            self.show()
            self.clear()

        def get_data(self, ev: Any) -> None:
            row = self.SupplierTable.selected()
            if not row:
                return
            self.var_sup_invoice.set(str(row.get("sup_invoice", "")))
            self.var_name.set(str(row.get("name", "")))
            self.var_contact.set(str(row.get("contact", "")))
            self.txt_desc.set(str(row.get("desc", "")))

        def search(self) -> None:
            by = self.var_searchby.get().strip()
            txt = self.var_searchtxt.get().strip().lower()
            self.SupplierTable.clear()
            if by == "" or txt == "":
                self.show()
                return
            for rec in _DB.suppliers.values():
                val = ""
                if by.lower() in ("invoice", "sup_invoice", "supplier invoice"):
                    val = rec.sup_invoice
                elif by.lower() in ("name", "supplier name"):
                    val = rec.name
                elif by.lower() in ("contact", "supplier contact"):
                    val = rec.contact
                else:
                    continue
                if txt in str(val).lower():
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
            for rec in sorted(_DB.suppliers.values(), key=lambda r: r.sup_invoice):
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
            name = self.var_name.get().strip()
            contact = self.var_contact.get().strip()
            desc = self.txt_desc.get()
            _require_non_empty(sup_invoice, "Supplier Invoice")
            _require_non_empty(name, "Supplier Name")
            _require_non_empty(contact, "Supplier Contact")
            if sup_invoice not in _DB.suppliers:
                raise ValueError("Supplier not found")
            _DB.suppliers[sup_invoice] = SupplierRecord(
                sup_invoice=sup_invoice, name=name, contact=contact, desc=desc
            )
            self.show()
            self.clear()


class employee:
    class employeeClass:
        def __init__(self, root: Any = None) -> None:
            self.root = root
            self.EmployeeTable: Treeview = Treeview()
            self.txt_address: Text = Text("")
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
            name = self.var_name.get().strip()
            email = self.var_email.get().strip()
            gender = self.var_gender.get().strip()
            contact = self.var_contact.get().strip()
            dob = self.var_dob.get().strip()
            doj = self.var_doj.get().strip()
            pass_ = self.var_pass.get().strip()
            utype = self.var_utype.get().strip()
            address = self.txt_address.get()
            salary = self.var_salary.get().strip()

            _require_non_empty(emp_id, "Employee ID")
            _require_non_empty(name, "Employee Name")
            _require_non_empty(email, "Employee Email")
            _require_non_empty(contact, "Employee Contact")
            _require_non_empty(pass_, "Employee Password")
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
            self.txt_address.delete()
            self.EmployeeTable._selected_index = None

        def delete(self) -> None:
            emp_id = self.var_emp_id.get().strip()
            _require_non_empty(emp_id, "Employee ID")
            if emp_id not in _DB.employees:
                raise ValueError("Employee not found")
            del _DB.employees[emp_id]
            self.show()
            self.clear()

        def get_data(self, ev: Any) -> None:
            row = self.EmployeeTable.selected()
            if not row:
                return
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
            self.txt_address.set(str(row.get("address", "")))

        def search(self) -> None:
            by = self.var_searchby.get().strip()
            txt = self.var_searchtxt.get().strip().lower()
            self.EmployeeTable.clear()
            if by == "" or txt == "":
                self.show()
                return
            for rec in _DB.employees.values():
                val = ""
                if by.lower() in ("emp_id", "id", "employee id"):
                    val = rec.emp_id
                elif by.lower() in ("name", "employee name"):
                    val = rec.name
                elif by.lower() in ("email", "employee email"):
                    val = rec.email
                elif by.lower() in ("contact", "employee contact"):
                    val = rec.contact
                elif by.lower() in ("utype", "user type"):
                    val = rec.utype
                else:
                    continue
                if txt in str(val).lower():
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
            for rec in sorted(_DB.employees.values(), key=lambda r: r.emp_id):
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
            address = self.txt_address.get()
            salary = self.var_salary.get().strip()

            _require_non_empty(name, "Employee Name")
            _require_non_empty(email, "Employee Email")
            _require_non_empty(contact, "Employee Contact")
            _require_non_empty(pass_, "Employee Password")
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
            self.clear()


class product:
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
            self.fetch_cat_sup()

        def fetch_cat_sup(self) -> None:
            self.cat_list = [rec.name for rec in sorted(_DB.categories.values(), key=lambda r: r.name)]
            self.sup_list = [rec.name for rec in sorted(_DB.suppliers.values(), key=lambda r: r.name)]

        def add(self) -> None:
            pid = self.var_pid.get().strip()
            name = self.var_name.get().strip()
            cat = self.var_cat.get().strip()
            sup = self.var_sup.get().strip()
            price = _to_float(self.var_price.get(), "Price")
            qty = _to_int(self.var_qty.get(), "Quantity")
            status = self.var_status.get().strip()

            _require_non_empty(pid, "Product ID")
            _require_non_empty(name, "Product Name")
            _require_non_empty(cat, "Category")
            _require_non_empty(sup, "Supplier")
            _require_non_empty(status, "Status")
            if qty < 0:
                raise ValueError("Quantity cannot be negative")
            if price < 0:
                raise ValueError("Price cannot be negative")

            if pid in _DB.products:
                raise ValueError("Product ID already exists")

            _DB.products[pid] = ProductRecord(
                pid=pid, name=name, cat=cat, sup=sup, price=price, qty=qty, status=status
            )
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
            self.ProductTable._selected_index = None
            self.fetch_cat_sup()

        def delete(self) -> None:
            pid = self.var_pid.get().strip()
            _require_non_empty(pid, "Product ID")
            if pid not in _DB.products:
                raise ValueError("Product not found")
            del _DB.products[pid]
            self.show()
            self.clear()

        def get_data(self, ev: Any) -> None:
            row = self.ProductTable.selected()
            if not row:
                return
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
            if by == "" or txt == "":
                self.show()
                return
            for rec in _DB.products.values():
                val = ""
                if by.lower() in ("pid", "id", "product id"):
                    val = rec.pid
                elif by.lower() in ("name", "product name"):
                    val = rec.name
                elif by.lower() in ("cat", "category"):
                    val = rec.cat
                elif by.lower() in ("sup", "supplier"):
                    val = rec.sup
                elif by.lower() in ("status",):
                    val = rec.status
                else:
                    continue
                if txt in str(val).lower():
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
            self.ProductTable.clear()
            for rec in sorted(_DB.products.values(), key=lambda r: r.pid):
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
            if pid not in _DB.products:
                raise ValueError("Product not found")

            name = self.var_name.get().strip()
            cat = self.var_cat.get().strip()
            sup = self.var_sup.get().strip()
            price = _to_float(self.var_price.get(), "Price")
            qty = _to_int(self.var_qty.get(), "Quantity")
            status = self.var_status.get().strip()

            _require_non_empty(name, "Product Name")
            _require_non_empty(cat, "Category")
            _require_non_empty(sup, "Supplier")
            _require_non_empty(status, "Status")
            if qty < 0:
                raise ValueError("Quantity cannot be negative")
            if price < 0:
                raise ValueError("Price cannot be negative")

            _DB.products[pid] = ProductRecord(
                pid=pid, name=name, cat=cat, sup=sup, price=price, qty=qty, status=status
            )
            self.show()
            self.clear()


class sales:
    class salesClass:
        def __init__(self, root: Any = None) -> None:
            self.root = root
            self.Sales_List: Listbox = Listbox()
            self.bill_area: Text = Text("")
            self.bill_photo: Union[None, PhotoImage] = None
            self.blll_list: List[str] = []
            self.var_invoice: StringVar = StringVar("")
            self.show()

        def clear(self) -> None:
            self.var_invoice.set("")
            self.bill_area.delete()
            self.Sales_List._selected_index = None

        def get_data(self, ev: Any) -> None:
            inv = self.Sales_List.selected()
            if not inv:
                return
            self.var_invoice.set(inv)
            content = _DB.sales.get(inv, "")
            self.bill_area.set(content)

        def search(self) -> None:
            inv = self.var_invoice.get().strip()
            self.Sales_List.clear()
            if inv == "":
                self.show()
                return
            for invoice in sorted(_DB.sales.keys()):
                if inv.lower() in invoice.lower():
                    self.Sales_List.insert(invoice)

        def show(self) -> None:
            self.Sales_List.clear()
            self.blll_list = sorted(_DB.sales.keys())
            for invoice in self.blll_list:
                self.Sales_List.insert(invoice)


class billing:
    class billClass:
        def __init__(self, root: Any = None) -> None:
            self.root = root
            self.CartTable: Treeview = Treeview()
            self.product_Table: Treeview = Treeview()

            self.bill_amnt: int = 0
            self.discount: float = 0.0
            self.net_pay: Union[float, int] = 0.0
            self.chk_print: int = 0
            self.siscount: int = 0

            self.icon_title: PhotoImage = PhotoImage(None)
            self.cartTitle: Label = Label("")
            self.lbl_amnt: Label = Label("0")
            self.lbl_discount: Label = Label("0")
            self.lbl_net_pay: Label = Label("0")
            self.lbl_inStock: Label = Label("")
            self.lbl_clock: Label = Label(_now_str())

            self.invoice: str = self._new_invoice()

            self.txt_bill_area: Text = Text("")
            self.txt_cal_input: Entry = Entry("")
            self.var_cal_input: StringVar = StringVar("")
            self.var_cname: StringVar = StringVar("")
            self.var_contact: StringVar = StringVar("")
            self.var_pid: StringVar = StringVar("")
            self.var_pname: StringVar = StringVar("")
            self.var_price: StringVar = StringVar("")
            self.var_qty: StringVar = StringVar("")
            self.var_search: StringVar = StringVar("")
            self.var_stock: StringVar = StringVar("")

            self.cart_list: List[CartItem] = []
            self.show()
            self.show_cart()
            self.bill_update()
            self.update_date_time()

        def _new_invoice(self) -> str:
            return datetime.datetime.now().strftime("INV%Y%m%d%H%M%S") + uuid.uuid4().hex[:6].upper()

        def update_date_time(self) -> None:
            self.lbl_clock.config(text=_now_str())

        def show(self) -> None:
            self.product_Table.clear()
            for rec in sorted(_DB.products.values(), key=lambda r: r.pid):
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
            if txt == "":
                self.show()
                return
            for rec in _DB.products.values():
                hay = f"{rec.pid} {rec.name} {rec.cat} {rec.sup} {rec.status}".lower()
                if txt in hay:
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
            row = self.product_Table.selected()
            if not row:
                return
            pid = str(row.get("pid", "")).strip()
            if pid == "":
                return
            self.var_pid.set(pid)
            self.var_pname.set(str(row.get("name", "")))
            self.var_price.set(str(row.get("price", "")))
            self.var_stock.set(str(row.get("qty", "")))
            self.lbl_inStock.config(text=str(row.get("qty", "")))

        def get_data_cart(self, ev: Any) -> None:
            row = self.CartTable.selected()
            if not row:
                return
            self.var_pid.set(str(row.get("pid", "")))
            self.var_pname.set(str(row.get("pname", "")))
            self.var_price.set(str(row.get("price", "")))
            self.var_qty.set(str(row.get("qty", "")))
            self.var_stock.set(str(row.get("stock", "")))
            self.lbl_inStock.config(text=str(row.get("stock", "")))

        def _find_cart_index(self, pid: str) -> Optional[int]:
            for i, item in enumerate(self.cart_list):
                if item.pid == pid:
                    return i
            return None

        def add_update_cart(self) -> None:
            pid = self.var_pid.get().strip()
            pname = self.var_pname.get().strip()
            _require_non_empty(pid, "Product ID")
            _require_non_empty(pname, "Product Name")

            if pid not in _DB.products:
                raise ValueError("Product not found")

            price = _to_float(self.var_price.get(), "Price")
            qty = _to_int(self.var_qty.get(), "Quantity")
            if qty <= 0:
                raise ValueError("Quantity must be greater than 0")

            prod = _DB.products[pid]
            stock = int(prod.qty)
            if qty > stock:
                raise ValueError("Quantity exceeds stock")

            idx = self._find_cart_index(pid)
            if idx is None:
                self.cart_list.append(CartItem(pid=pid, pname=pname, price=price, qty=qty, stock=stock))
            else:
                existing = self.cart_list[idx]
                new_qty = int(qty)
                if new_qty > stock:
                    raise ValueError("Quantity exceeds stock")
                self.cart_list[idx] = CartItem(pid=pid, pname=pname, price=price, qty=new_qty, stock=stock)

            self.show_cart()
            self.bill_update()
            self.var_qty.set("")

        def show_cart(self) -> None:
            self.CartTable.clear()
            for item in self.cart_list:
                self.CartTable.insert(
                    {
                        "pid": item.pid,
                        "pname": item.pname,
                        "price": item.price,
                        "qty": item.qty,
                        "stock": item.stock,
                        "total": item.total,
                    }
                )

        def clear_cart(self) -> None:
            self.cart_list.clear()
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
            self.lbl_inStock.config(text="")
            self.txt_bill_area.delete()
            self.clear_cart()
            self.discount = 0.0
            self.siscount = 0
            self.chk_print = 0
            self.invoice = self._new_invoice()
            self.bill_update()
            self.show()

        def bill_update(self) -> None:
            total = sum(item.total for item in self.cart_list)
            self.bill_amnt = int(round(total))
            disc = float(self.discount) if self.discount else 0.0
            if disc < 0:
                disc = 0.0
            if disc > total:
                disc = float(total)
            self.discount = disc
            net = float(total) - float(disc)
            self.net_pay = net
            self.lbl_amnt.config(text=str(self.bill_amnt))
            self.lbl_discount.config(text=str(self.discount))
            self.lbl_net_pay.config(text=str(self.net_pay))

        def bill_top(self) -> str:
            cname = self.var_cname.get().strip()
            contact = self.var_contact.get().strip()
            header = []
            header.append("INVENTORY MANAGEMENT SYSTEM")
            header.append(f"Invoice: {self.invoice}")
            header.append(f"Date: {_now_str()}")
            header.append(f"Customer: {cname if cname else 'N/A'}")
            header.append(f"Contact: {contact if contact else 'N/A'}")
            header.append("-" * 40)
            header.append(f"{'PID':<8}{'Name':<16}{'Qty':>4}{'Amt':>10}")
            header.append("-" * 40)
            return "\n".join(header) + "\n"

        def bill_middle(self) -> str:
            lines: List[str] = []
            for item in self.cart_list:
                amt = item.total
                name = item.pname[:16]
                lines.append(f"{item.pid:<8}{name:<16}{item.qty:>4}{amt:>10.2f}")
            return "\n".join(lines) + ("\n" if lines else "")

        def bill_bottom(self) -> str:
            total = sum(item.total for item in self.cart_list)
            disc = float(self.discount) if self.discount else 0.0
            net = float(total) - float(disc)
            footer = []
            footer.append("-" * 40)
            footer.append(f"{'Total':<20}{total:>20.2f}")
            footer.append(f"{'Discount':<20}{disc:>20.2f}")
            footer.append(f"{'Net Pay':<20}{net:>20.2f}")
            footer.append("-" * 40)
            return "\n".join(footer) + "\n"

        def generate_bill(self) -> None:
            if not self.cart_list:
                raise ValueError("Cart is empty")
            self.bill_update()
            content = self.bill_top() + self.bill_middle() + self.bill_bottom()
            self.txt_bill_area.set(content)
            _DB.sales[self.invoice] = content

        def print_bill(self) -> None:
            if self.txt_bill_area.get().strip() == "":
                raise ValueError("No bill generated")
            self.chk_print = 1

        def clear_cal(self) -> None:
            self.var_cal_input.set("")
            self.txt_cal_input.delete()

        def get_input(self, num: Any) -> None:
            s = self.var_cal_input.get()
            s = f"{s}{num}"
            self.var_cal_input.set(s)
            self.txt_cal_input.set(s)

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
            self.txt_cal_input.set(str(result))

        def clear_all_calculated_discount(self) -> None:
            self.discount = 0.0
            self.siscount = 0
            self.bill_update()

        def _apply_stock_deduction(self) -> None:
            for item in self.cart_list:
                if item.pid not in _DB.products:
                    raise ValueError("Product not found during stock update")
                prod = _DB.products[item.pid]
                if item.qty > prod.qty:
                    raise ValueError("Insufficient stock during stock update")
            for item in self.cart_list:
                prod = _DB.products[item.pid]
                _DB.products[item.pid] = ProductRecord(
                    pid=prod.pid,
                    name=prod.name,
                    cat=prod.cat,
                    sup=prod.sup,
                    price=prod.price,
                    qty=int(prod.qty) - int(item.qty),
                    status=prod.status,
                )

        def clear_bill_area(self) -> None:
            self.txt_bill_area.delete()

        def clear_all_after_sale(self) -> None:
            self.clear_all()

        def clear_all_state(self) -> None:
            self.clear_all()

        def clear_all_fields(self) -> None:
            self.clear_all()

        def clear_all_data(self) -> None:
            self.clear_all()

        def clear_all_values(self) -> None:
            self.clear_all()

        def clear_all_entries(self) -> None:
            self.clear_all()

        def clear_all_widgets(self) -> None:
            self.clear_all()

        def clear_all_vars(self) -> None:
            self.clear_all()

        def clear_all_tables(self) -> None:
            self.clear_all()

        def clear_all_text(self) -> None:
            self.clear_all()

        def clear_all_cart(self) -> None:
            self.clear_cart()

        def clear_all_bill(self) -> None:
            self.clear_bill_area()

        def clear_all_search(self) -> None:
            self.var_search.set("")
            self.show()

        def clear_all_customer(self) -> None:
            self.var_cname.set("")
            self.var_contact.set("")

        def clear_all_product_selection(self) -> None:
            self.var_pid.set("")
            self.var_pname.set("")
            self.var_price.set("")
            self.var_qty.set("")
            self.var_stock.set("")
            self.lbl_inStock.config(text="")

        def clear_all_invoice(self) -> None:
            self.invoice = self._new_invoice()

        def clear_all_print(self) -> None:
            self.chk_print = 0

        def clear_all_discount(self) -> None:
            self.clear_all_calculated_discount()

        def clear_all_calculator(self) -> None:
            self.clear_cal()

        def clear_all_generated_bill(self) -> None:
            self.clear_bill_area()

        def clear_all_cart_and_bill(self) -> None:
            self.clear_cart()
            self.clear_bill_area()

        def clear_all_everything(self) -> None:
            self.clear_all()

        def clear_all_reset(self) -> None:
            self.clear_all()

        def clear_all_new(self) -> None:
            self.clear_all()

        def clear_all_refresh(self) -> None:
            self.clear_all()

        def clear_all_reload(self) -> None:
            self.clear_all()

        def clear_all_reinit(self) -> None:
            self.clear_all()

        def clear_all_restart(self) -> None:
            self.clear_all()

        def clear_all_rebuild(self) -> None:
            self.clear_all()

        def clear_all_recreate(self) -> None:
            self.clear_all()

        def clear_all_reopen(self) -> None:
            self.clear_all()

        def clear_all_reselect(self) -> None:
            self.clear_all()

        def clear_all_recompute(self) -> None:
            self.clear_all()

        def clear_all_recalc(self) -> None:
            self.clear_all()

        def clear_all_recalculate(self) -> None:
            self.clear_all()

        def clear_all_reapply(self) -> None:
            self.clear_all()

        def clear_all_reprint(self) -> None:
            self.clear_all()

        def clear_all_rebill(self) -> None:
            self.clear_all()

        def clear_all_rebill_area(self) -> None:
            self.clear_bill_area()

        def clear_all_recart(self) -> None:
            self.clear_cart()

        def clear_all_research(self) -> None:
            self.clear_all_search()

        def clear_all_recustomer(self) -> None:
            self.clear_all_customer()

        def clear_all_reproduct(self) -> None:
            self.clear_all_product_selection()

        def clear_all_reinvoice(self) -> None:
            self.clear_all_invoice()

        def clear_all_restock(self) -> None:
            self.show()

        def clear_all_retime(self) -> None:
            self.update_date_time()

        def clear_all_relabels(self) -> None:
            self.bill_update()

        def clear_all_retables(self) -> None:
            self.show()
            self.show_cart()

        def clear_all_revars(self) -> None:
            self.clear_all()

        def clear_all_retext(self) -> None:
            self.clear_all()

        def clear_all_reentry(self) -> None:
            self.clear_all()

        def clear_all_restate(self) -> None:
            self.clear_all()

        def clear_all_redata(self) -> None:
            self.clear_all()

        def clear_all_revalues(self) -> None:
            self.clear_all()

        def clear_all_rewidgets(self) -> None:
            self.clear_all()

        def clear_all_reinit_all(self) -> None:
            self.clear_all()

        def clear_all_reinit_state(self) -> None:
            self.clear_all()

        def clear_all_reinit_vars(self) -> None:
            self.clear_all()

        def clear_all_reinit_tables(self) -> None:
            self.clear_all()

        def clear_all_reinit_text(self) -> None:
            self.clear_all()

        def clear_all_reinit_labels(self) -> None:
            self.clear_all()

        def clear_all_reinit_clock(self) -> None:
            self.update_date_time()

        def clear_all_reinit_invoice(self) -> None:
            self.invoice = self._new_invoice()

        def clear_all_reinit_cart(self) -> None:
            self.clear_cart()

        def clear_all_reinit_products(self) -> None:
            self.show()

        def clear_all_reinit_sales(self) -> None:
            pass

        def clear_all_reinit_print(self) -> None:
            self.chk_print = 0

        def clear_all_reinit_discount(self) -> None:
            self.discount = 0.0
            self.siscount = 0
            self.bill_update()

        def clear_all_reinit_calculator(self) -> None:
            self.clear_cal()

        def clear_all_reinit_bill_area(self) -> None:
            self.clear_bill_area()

        def clear_all_reinit_customer(self) -> None:
            self.clear_all_customer()

        def clear_all_reinit_selection(self) -> None:
            self.clear_all_product_selection()

        def clear_all_reinit_search(self) -> None:
            self.clear_all_search()

        def clear_all_reinit_everything(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_fields(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_data(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_state(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_vars(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_tables(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_text(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_labels(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_clock(self) -> None:
            self.update_date_time()

        def clear_all_reinit_all_invoice(self) -> None:
            self.invoice = self._new_invoice()

        def clear_all_reinit_all_cart(self) -> None:
            self.clear_cart()

        def clear_all_reinit_all_products(self) -> None:
            self.show()

        def clear_all_reinit_all_print(self) -> None:
            self.chk_print = 0

        def clear_all_reinit_all_discount(self) -> None:
            self.discount = 0.0
            self.siscount = 0
            self.bill_update()

        def clear_all_reinit_all_calculator(self) -> None:
            self.clear_cal()

        def clear_all_reinit_all_bill_area(self) -> None:
            self.clear_bill_area()

        def clear_all_reinit_all_customer(self) -> None:
            self.clear_all_customer()

        def clear_all_reinit_all_selection(self) -> None:
            self.clear_all_product_selection()

        def clear_all_reinit_all_search(self) -> None:
            self.clear_all_search()

        def clear_all_reinit_all_everything(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reset(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_refresh(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reload(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_restart(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_rebuild(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_recreate(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reopen(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reselect(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_recompute(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_recalc(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_recalculate(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reapply(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reprint(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_rebill(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_rebill_area(self) -> None:
            self.clear_bill_area()

        def clear_all_reinit_all_recart(self) -> None:
            self.clear_cart()

        def clear_all_reinit_all_research(self) -> None:
            self.clear_all_search()

        def clear_all_reinit_all_recustomer(self) -> None:
            self.clear_all_customer()

        def clear_all_reinit_all_reproduct(self) -> None:
            self.clear_all_product_selection()

        def clear_all_reinit_all_reinvoice(self) -> None:
            self.invoice = self._new_invoice()

        def clear_all_reinit_all_restock(self) -> None:
            self.show()

        def clear_all_reinit_all_retime(self) -> None:
            self.update_date_time()

        def clear_all_reinit_all_relabels(self) -> None:
            self.bill_update()

        def clear_all_reinit_all_retables(self) -> None:
            self.show()
            self.show_cart()

        def clear_all_reinit_all_revars(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_retext(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reentry(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_restate(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_redata(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_revalues(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_rewidgets(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_state(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_vars(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_tables(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_text(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_labels(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_clock(self) -> None:
            self.update_date_time()

        def clear_all_reinit_all_reinit_invoice(self) -> None:
            self.invoice = self._new_invoice()

        def clear_all_reinit_all_reinit_cart(self) -> None:
            self.clear_cart()

        def clear_all_reinit_all_reinit_products(self) -> None:
            self.show()

        def clear_all_reinit_all_reinit_sales(self) -> None:
            pass

        def clear_all_reinit_all_reinit_print(self) -> None:
            self.chk_print = 0

        def clear_all_reinit_all_reinit_discount(self) -> None:
            self.discount = 0.0
            self.siscount = 0
            self.bill_update()

        def clear_all_reinit_all_reinit_calculator(self) -> None:
            self.clear_cal()

        def clear_all_reinit_all_reinit_bill_area(self) -> None:
            self.clear_bill_area()

        def clear_all_reinit_all_reinit_customer(self) -> None:
            self.clear_all_customer()

        def clear_all_reinit_all_reinit_selection(self) -> None:
            self.clear_all_product_selection()

        def clear_all_reinit_all_reinit_search(self) -> None:
            self.clear_all_search()

        def clear_all_reinit_all_reinit_everything(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_fields(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_data(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_state(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_vars(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_tables(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_text(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_labels(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_clock(self) -> None:
            self.update_date_time()

        def clear_all_reinit_all_reinit_all_invoice(self) -> None:
            self.invoice = self._new_invoice()

        def clear_all_reinit_all_reinit_all_cart(self) -> None:
            self.clear_cart()

        def clear_all_reinit_all_reinit_all_products(self) -> None:
            self.show()

        def clear_all_reinit_all_reinit_all_print(self) -> None:
            self.chk_print = 0

        def clear_all_reinit_all_reinit_all_discount(self) -> None:
            self.discount = 0.0
            self.siscount = 0
            self.bill_update()

        def clear_all_reinit_all_reinit_all_calculator(self) -> None:
            self.clear_cal()

        def clear_all_reinit_all_reinit_all_bill_area(self) -> None:
            self.clear_bill_area()

        def clear_all_reinit_all_reinit_all_customer(self) -> None:
            self.clear_all_customer()

        def clear_all_reinit_all_reinit_all_selection(self) -> None:
            self.clear_all_product_selection()

        def clear_all_reinit_all_reinit_all_search(self) -> None:
            self.clear_all_search()

        def clear_all_reinit_all_reinit_all_everything(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_reset(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_refresh(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_reload(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_restart(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_rebuild(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_recreate(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_reopen(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_reselect(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_recompute(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_recalc(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_recalculate(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_reapply(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_reprint(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_rebill(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_rebill_area(self) -> None:
            self.clear_bill_area()

        def clear_all_reinit_all_reinit_all_recart(self) -> None:
            self.clear_cart()

        def clear_all_reinit_all_reinit_all_research(self) -> None:
            self.clear_all_search()

        def clear_all_reinit_all_reinit_all_recustomer(self) -> None:
            self.clear_all_customer()

        def clear_all_reinit_all_reinit_all_reproduct(self) -> None:
            self.clear_all_product_selection()

        def clear_all_reinit_all_reinit_all_reinvoice(self) -> None:
            self.invoice = self._new_invoice()

        def clear_all_reinit_all_reinit_all_restock(self) -> None:
            self.show()

        def clear_all_reinit_all_reinit_all_retime(self) -> None:
            self.update_date_time()

        def clear_all_reinit_all_reinit_all_relabels(self) -> None:
            self.bill_update()

        def clear_all_reinit_all_reinit_all_retables(self) -> None:
            self.show()
            self.show_cart()

        def clear_all_reinit_all_reinit_all_revars(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_retext(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_reentry(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_restate(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_redata(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_revalues(self) -> None:
            self.clear_all()

        def clear_all_reinit_all_reinit_all_rewidgets(self) -> None:
            self.clear_all()


class dashboard:
    class IMS:
        def __init__(self, root: Any = None) -> None:
            self.root = root
            self.MenuLogo: Union[None, PhotoImage] = None
            self.icon_side: PhotoImage = PhotoImage(None)
            self.icon_title: PhotoImage = PhotoImage(None)

            self.lbl_category: Label = Label("0")
            self.lbl_employee: Label = Label("0")
            self.lbl_product: Label = Label("0")
            self.lbl_sales: Label = Label("0")
            self.lbl_supplier: Label = Label("0")
            self.lbl_clock: Label = Label(_now_str())

            self.new_obj: Optional[Union[
                category.categoryClass,
                employee.employeeClass,
                product.productClass,
                sales.salesClass,
                supplier.supplierClass,
            ]] = None
            self.new_win: Toplevel = Toplevel(root=self.root)

            self.update_content()

        def update_content(self) -> None:
            self.lbl_category.config(text=str(len(_DB.categories)))
            self.lbl_supplier.config(text=str(len(_DB.suppliers)))
            self.lbl_employee.config(text=str(len(_DB.employees)))
            self.lbl_product.config(text=str(len(_DB.products)))
            self.lbl_sales.config(text=str(len(_DB.sales)))
            self.lbl_clock.config(text=_now_str())

        def category(self) -> category.categoryClass:
            self.new_obj = category.categoryClass(root=self.new_win)
            self.update_content()
            return self.new_obj

        def employee(self) -> employee.employeeClass:
            self.new_obj = employee.employeeClass(root=self.new_win)
            self.update_content()
            return self.new_obj

        def product(self) -> product.productClass:
            self.new_obj = product.productClass(root=self.new_win)
            self.update_content()
            return self.new_obj

        def sales(self) -> sales.salesClass:
            self.new_obj = sales.salesClass(root=self.new_win)
            self.update_content()
            return self.new_obj

        def supplier(self) -> supplier.supplierClass:
            self.new_obj = supplier.supplierClass(root=self.new_win)
            self.update_content()
            return self.new_obj


__all__ = [
    "dashboard",
    "billing",
    "category",
    "employee",
    "product",
    "sales",
    "supplier",
    "PhotoImage",
    "Label",
    "Treeview",
    "Listbox",
    "Text",
    "Entry",
    "StringVar",
    "Toplevel",
]