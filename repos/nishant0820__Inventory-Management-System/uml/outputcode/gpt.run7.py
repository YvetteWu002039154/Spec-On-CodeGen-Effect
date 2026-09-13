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


class StringVar:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = "" if value is None else str(value)


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

    def insert(self, parent: str, index: Union[int, str], values: Tuple[Any, ...]) -> str:
        row_id = f"I{len(self._rows) + 1}"
        self._rows.append({"id": row_id, "values": tuple(values)})
        return row_id

    def get_children(self) -> List[str]:
        return [r["id"] for r in self._rows]

    def delete(self, item_id: str) -> None:
        for i, r in enumerate(self._rows):
            if r["id"] == item_id:
                del self._rows[i]
                break
        self._selection_index = None

    def item(self, item_id: str, option: str = "values") -> Any:
        for r in self._rows:
            if r["id"] == item_id:
                if option == "values":
                    return r["values"]
                return r
        return () if option == "values" else {}

    def selection(self) -> Tuple[str, ...]:
        if self._selection_index is None:
            return ()
        if 0 <= self._selection_index < len(self._rows):
            return (self._rows[self._selection_index]["id"],)
        return ()

    def selection_set(self, item_id: str) -> None:
        for i, r in enumerate(self._rows):
            if r["id"] == item_id:
                self._selection_index = i
                return
        self._selection_index = None

    def clear(self) -> None:
        self._rows.clear()
        self._selection_index = None

    def rows(self) -> List[Tuple[Any, ...]]:
        return [r["values"] for r in self._rows]


class Toplevel:
    def __init__(self, root: Any = None) -> None:
        self.root = root


class Root:
    def __init__(self) -> None:
        self.title_text: str = ""

    def title(self, text: str) -> None:
        self.title_text = text


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
    customer_name: str
    contact: str
    items: List[CartItem]
    bill_amount: float
    discount: float
    net_pay: float
    created_at: datetime.datetime
    bill_text: str


class InMemoryDB:
    def __init__(self) -> None:
        self.categories: Dict[str, CategoryRecord] = {}
        self.suppliers: Dict[str, SupplierRecord] = {}
        self.employees: Dict[str, EmployeeRecord] = {}
        self.products: Dict[str, ProductRecord] = {}
        self.invoices: Dict[str, InvoiceRecord] = {}
        self._invoice_counter = itertools.count(1)

    def next_invoice(self) -> str:
        return f"INV{next(self._invoice_counter):06d}"


_GLOBAL_DB = InMemoryDB()


class categoryClass:
    def __init__(self, root: Any = None) -> None:
        self.root = root
        self.CategoryTable: Treeview = Treeview()
        self.im1: Optional[PhotoImage] = None
        self.im2: Optional[PhotoImage] = None
        self.lbl_im1: Label = Label("")
        self.lbl_im2: Label = Label("")
        self.var_cat_id: StringVar = StringVar("")
        self.var_name: StringVar = StringVar("")

    def add(self) -> None:
        cat_id = self.var_cat_id.get().strip()
        name = self.var_name.get().strip()
        if not cat_id or not name:
            raise ValueError("Category ID and Name are required")
        if cat_id in _GLOBAL_DB.categories:
            raise ValueError("Category ID already exists")
        _GLOBAL_DB.categories[cat_id] = CategoryRecord(cat_id=cat_id, name=name)
        self.show()

    def clear(self) -> None:
        self.var_cat_id.set("")
        self.var_name.set("")
        self.CategoryTable.clear()

    def delete(self) -> None:
        cat_id = self.var_cat_id.get().strip()
        if not cat_id:
            sel = self.CategoryTable.selection()
            if sel:
                values = self.CategoryTable.item(sel[0], "values")
                if values:
                    cat_id = str(values[0])
        if not cat_id:
            raise ValueError("Category ID is required for delete")
        if cat_id not in _GLOBAL_DB.categories:
            raise ValueError("Category not found")
        del _GLOBAL_DB.categories[cat_id]
        self.show()

    def get_data(self, ev: Any) -> None:
        sel = self.CategoryTable.selection()
        if not sel:
            return
        values = self.CategoryTable.item(sel[0], "values")
        if not values:
            return
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
        desc = self.txt_desc.get().strip()
        if not sup_invoice or not name:
            raise ValueError("Supplier Invoice and Name are required")
        if sup_invoice in _GLOBAL_DB.suppliers:
            raise ValueError("Supplier Invoice already exists")
        _GLOBAL_DB.suppliers[sup_invoice] = SupplierRecord(
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
        if not sup_invoice:
            sel = self.SupplierTable.selection()
            if sel:
                values = self.SupplierTable.item(sel[0], "values")
                if values:
                    sup_invoice = str(values[0])
        if not sup_invoice:
            raise ValueError("Supplier Invoice is required for delete")
        if sup_invoice not in _GLOBAL_DB.suppliers:
            raise ValueError("Supplier not found")
        del _GLOBAL_DB.suppliers[sup_invoice]
        self.show()

    def get_data(self, ev: Any) -> None:
        sel = self.SupplierTable.selection()
        if not sel:
            return
        values = self.SupplierTable.item(sel[0], "values")
        if not values:
            return
        self.var_sup_invoice.set(str(values[0]))
        self.var_name.set(str(values[1]))
        self.var_contact.set(str(values[2]))
        self.txt_desc.delete("1.0", "end")
        self.txt_desc.insert("end", str(values[3]))

    def search(self) -> None:
        by = self.var_searchby.get().strip().lower()
        txt = self.var_searchtxt.get().strip().lower()
        self.SupplierTable.clear()
        records = list(_GLOBAL_DB.suppliers.values())
        if by and txt:
            if by not in {"invoice", "name", "contact"}:
                raise ValueError("Invalid searchby for supplier")
            def match(r: SupplierRecord) -> bool:
                if by == "invoice":
                    return txt in r.sup_invoice.lower()
                if by == "name":
                    return txt in r.name.lower()
                return txt in r.contact.lower()
            records = [r for r in records if match(r)]
        for r in sorted(records, key=lambda s: s.sup_invoice):
            self.SupplierTable.insert("", "end", (r.sup_invoice, r.name, r.contact, r.desc))

    def show(self) -> None:
        self.SupplierTable.clear()
        for r in sorted(_GLOBAL_DB.suppliers.values(), key=lambda s: s.sup_invoice):
            self.SupplierTable.insert("", "end", (r.sup_invoice, r.name, r.contact, r.desc))

    def update(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        if not sup_invoice:
            raise ValueError("Supplier Invoice is required for update")
        if sup_invoice not in _GLOBAL_DB.suppliers:
            raise ValueError("Supplier not found")
        name = self.var_name.get().strip()
        contact = self.var_contact.get().strip()
        desc = self.txt_desc.get().strip()
        if not name:
            raise ValueError("Supplier Name is required")
        _GLOBAL_DB.suppliers[sup_invoice] = SupplierRecord(
            sup_invoice=sup_invoice, name=name, contact=contact, desc=desc
        )
        self.show()


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
        address = self.txt_address.get().strip()
        salary = self.var_salary.get().strip()
        if not emp_id or not name:
            raise ValueError("Employee ID and Name are required")
        if emp_id in _GLOBAL_DB.employees:
            raise ValueError("Employee ID already exists")
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
        if not emp_id:
            sel = self.EmployeeTable.selection()
            if sel:
                values = self.EmployeeTable.item(sel[0], "values")
                if values:
                    emp_id = str(values[0])
        if not emp_id:
            raise ValueError("Employee ID is required for delete")
        if emp_id not in _GLOBAL_DB.employees:
            raise ValueError("Employee not found")
        del _GLOBAL_DB.employees[emp_id]
        self.show()

    def get_data(self, ev: Any) -> None:
        sel = self.EmployeeTable.selection()
        if not sel:
            return
        values = self.EmployeeTable.item(sel[0], "values")
        if not values:
            return
        (
            emp_id,
            name,
            email,
            gender,
            contact,
            dob,
            doj,
            pass_,
            utype,
            address,
            salary,
        ) = values
        self.var_emp_id.set(str(emp_id))
        self.var_name.set(str(name))
        self.var_email.set(str(email))
        self.var_gender.set(str(gender))
        self.var_contact.set(str(contact))
        self.var_dob.set(str(dob))
        self.var_doj.set(str(doj))
        self.var_pass.set(str(pass_))
        self.var_utype.set(str(utype))
        self.txt_address.delete("1.0", "end")
        self.txt_address.insert("end", str(address))
        self.var_salary.set(str(salary))

    def search(self) -> None:
        by = self.var_searchby.get().strip().lower()
        txt = self.var_searchtxt.get().strip().lower()
        self.EmployeeTable.clear()
        records = list(_GLOBAL_DB.employees.values())
        if by and txt:
            if by not in {"id", "name", "email", "contact", "utype"}:
                raise ValueError("Invalid searchby for employee")
            def match(r: EmployeeRecord) -> bool:
                if by == "id":
                    return txt in r.emp_id.lower()
                if by == "name":
                    return txt in r.name.lower()
                if by == "email":
                    return txt in r.email.lower()
                if by == "contact":
                    return txt in r.contact.lower()
                return txt in r.utype.lower()
            records = [r for r in records if match(r)]
        for r in sorted(records, key=lambda e: e.emp_id):
            self.EmployeeTable.insert(
                "",
                "end",
                (
                    r.emp_id,
                    r.name,
                    r.email,
                    r.gender,
                    r.contact,
                    r.dob,
                    r.doj,
                    r.pass_,
                    r.utype,
                    r.address,
                    r.salary,
                ),
            )

    def show(self) -> None:
        self.EmployeeTable.clear()
        for r in sorted(_GLOBAL_DB.employees.values(), key=lambda e: e.emp_id):
            self.EmployeeTable.insert(
                "",
                "end",
                (
                    r.emp_id,
                    r.name,
                    r.email,
                    r.gender,
                    r.contact,
                    r.dob,
                    r.doj,
                    r.pass_,
                    r.utype,
                    r.address,
                    r.salary,
                ),
            )

    def update(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        if not emp_id:
            raise ValueError("Employee ID is required for update")
        if emp_id not in _GLOBAL_DB.employees:
            raise ValueError("Employee not found")
        name = self.var_name.get().strip()
        if not name:
            raise ValueError("Employee Name is required")
        _GLOBAL_DB.employees[emp_id] = EmployeeRecord(
            emp_id=emp_id,
            name=name,
            email=self.var_email.get().strip(),
            gender=self.var_gender.get().strip(),
            contact=self.var_contact.get().strip(),
            dob=self.var_dob.get().strip(),
            doj=self.var_doj.get().strip(),
            pass_=self.var_pass.get().strip(),
            utype=self.var_utype.get().strip(),
            address=self.txt_address.get().strip(),
            salary=self.var_salary.get().strip(),
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
        self.fetch_cat_sup()

    def fetch_cat_sup(self) -> None:
        self.cat_list = [c.name for c in _GLOBAL_DB.categories.values()]
        self.sup_list = [s.name for s in _GLOBAL_DB.suppliers.values()]

    def _parse_price(self, s: str) -> float:
        s = s.strip()
        if not s:
            raise ValueError("Price is required")
        try:
            v = float(s)
        except ValueError as e:
            raise ValueError("Invalid price") from e
        if v < 0:
            raise ValueError("Price cannot be negative")
        return v

    def _parse_qty(self, s: str) -> int:
        s = s.strip()
        if not s:
            raise ValueError("Quantity is required")
        try:
            v = int(s)
        except ValueError as e:
            raise ValueError("Invalid quantity") from e
        if v < 0:
            raise ValueError("Quantity cannot be negative")
        return v

    def add(self) -> None:
        pid = self.var_pid.get().strip()
        name = self.var_name.get().strip()
        cat = self.var_cat.get().strip()
        sup = self.var_sup.get().strip()
        status = self.var_status.get().strip()
        price = self._parse_price(self.var_price.get())
        qty = self._parse_qty(self.var_qty.get())
        if not pid or not name:
            raise ValueError("Product ID and Name are required")
        if pid in _GLOBAL_DB.products:
            raise ValueError("Product ID already exists")
        _GLOBAL_DB.products[pid] = ProductRecord(
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
        if not pid:
            sel = self.ProductTable.selection()
            if sel:
                values = self.ProductTable.item(sel[0], "values")
                if values:
                    pid = str(values[0])
        if not pid:
            raise ValueError("Product ID is required for delete")
        if pid not in _GLOBAL_DB.products:
            raise ValueError("Product not found")
        del _GLOBAL_DB.products[pid]
        self.show()

    def get_data(self, ev: Any) -> None:
        sel = self.ProductTable.selection()
        if not sel:
            return
        values = self.ProductTable.item(sel[0], "values")
        if not values:
            return
        pid, name, cat, sup, price, qty, status = values
        self.var_pid.set(str(pid))
        self.var_name.set(str(name))
        self.var_cat.set(str(cat))
        self.var_sup.set(str(sup))
        self.var_price.set(str(price))
        self.var_qty.set(str(qty))
        self.var_status.set(str(status))

    def search(self) -> None:
        by = self.var_searchby.get().strip().lower()
        txt = self.var_searchtxt.get().strip().lower()
        self.ProductTable.clear()
        records = list(_GLOBAL_DB.products.values())
        if by and txt:
            if by not in {"id", "name", "category", "supplier", "status"}:
                raise ValueError("Invalid searchby for product")
            def match(r: ProductRecord) -> bool:
                if by == "id":
                    return txt in r.pid.lower()
                if by == "name":
                    return txt in r.name.lower()
                if by == "category":
                    return txt in r.cat.lower()
                if by == "supplier":
                    return txt in r.sup.lower()
                return txt in r.status.lower()
            records = [r for r in records if match(r)]
        for r in sorted(records, key=lambda p: p.pid):
            self.ProductTable.insert("", "end", (r.pid, r.name, r.cat, r.sup, r.price, r.qty, r.status))

    def show(self) -> None:
        self.ProductTable.clear()
        for r in sorted(_GLOBAL_DB.products.values(), key=lambda p: p.pid):
            self.ProductTable.insert("", "end", (r.pid, r.name, r.cat, r.sup, r.price, r.qty, r.status))

    def update(self) -> None:
        pid = self.var_pid.get().strip()
        if not pid:
            raise ValueError("Product ID is required for update")
        if pid not in _GLOBAL_DB.products:
            raise ValueError("Product not found")
        name = self.var_name.get().strip()
        if not name:
            raise ValueError("Product Name is required")
        price = self._parse_price(self.var_price.get())
        qty = self._parse_qty(self.var_qty.get())
        _GLOBAL_DB.products[pid] = ProductRecord(
            pid=pid,
            name=name,
            cat=self.var_cat.get().strip(),
            sup=self.var_sup.get().strip(),
            price=price,
            qty=qty,
            status=self.var_status.get().strip(),
        )
        self.show()


class salesClass:
    def __init__(self, root: Any = None) -> None:
        self.root = root
        self.Sales_List: Listbox = Listbox()
        self.bill_area: Text = Text("")
        self.bill_photo: Optional[PhotoImage] = None
        self.blll_list: List[str] = []
        self.var_invoice: StringVar = StringVar("")

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
        inv = _GLOBAL_DB.invoices.get(invoice)
        self.bill_area.delete("1.0", "end")
        if inv is not None:
            self.bill_area.insert("end", inv.bill_text)

    def search(self) -> None:
        invoice = self.var_invoice.get().strip()
        self.Sales_List.delete(0, len(self.Sales_List.items) - 1 if self.Sales_List.items else 0)
        self.blll_list = []
        if not invoice:
            self.show()
            return
        inv = _GLOBAL_DB.invoices.get(invoice)
        if inv is None:
            return
        self.Sales_List.insert("end", inv.invoice)
        self.blll_list = [inv.invoice]

    def show(self) -> None:
        self.Sales_List.delete(0, len(self.Sales_List.items) - 1 if self.Sales_List.items else 0)
        self.blll_list = []
        for inv_id in sorted(_GLOBAL_DB.invoices.keys()):
            self.Sales_List.insert("end", inv_id)
            self.blll_list.append(inv_id)


class billClass:
    def __init__(self, root: Any = None) -> None:
        self.root = root
        self.CartTable: Treeview = Treeview()
        self.product_Table: Treeview = Treeview()
        self.cartTitle: Label = Label("")
        self.icon_title: PhotoImage = PhotoImage()
        self.lbl_amnt: Label = Label("")
        self.lbl_clock: Label = Label("")
        self.lbl_discount: Label = Label("")
        self.lbl_inStock: Label = Label("")
        self.lbl_net_pay: Label = Label("")
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
        self.bill_amnt: int = 0
        self.discount: float = 0.0
        self.net_pay: Union[float, int] = 0
        self.chk_print: int = 0
        self.siscount: int = 0
        self.invoice: str = _GLOBAL_DB.next_invoice()
        self.show()
        self.show_cart()
        self.update_date_time()

    def bill_top(self) -> None:
        self.txt_bill_area.delete("1.0", "end")
        now = datetime.datetime.now()
        header = []
        header.append("INVENTORY MANAGEMENT SYSTEM\n")
        header.append(f"Invoice: {self.invoice}\n")
        header.append(f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
        header.append(f"Customer: {self.var_cname.get().strip()}\n")
        header.append(f"Contact: {self.var_contact.get().strip()}\n")
        header.append("-" * 40 + "\n")
        header.append("PID   Name                 Qty   Price   Total\n")
        header.append("-" * 40 + "\n")
        self.txt_bill_area.insert("end", "".join(header))

    def bill_middle(self) -> None:
        for item in self.cart_list:
            name = (item.pname[:18] + "..") if len(item.pname) > 20 else item.pname
            line = f"{item.pid:<5} {name:<20} {item.qty:<5} {item.price:<7.2f} {item.total:<7.2f}\n"
            self.txt_bill_area.insert("end", line)

    def bill_bottom(self) -> None:
        self.bill_update()
        footer = []
        footer.append("-" * 40 + "\n")
        footer.append(f"Bill Amount: {float(self.bill_amnt):.2f}\n")
        footer.append(f"Discount: {float(self.discount):.2f}\n")
        footer.append(f"Net Pay: {float(self.net_pay):.2f}\n")
        footer.append("-" * 40 + "\n")
        self.txt_bill_area.insert("end", "".join(footer))

    def bill_update(self) -> None:
        total = sum(i.total for i in self.cart_list)
        self.bill_amnt = int(round(total))
        disc = float(self.discount) if self.discount else 0.0
        if disc < 0:
            disc = 0.0
        if disc > total:
            disc = total
        self.discount = disc
        self.net_pay = float(total - disc)
        self.lbl_amnt.config(text=str(float(total)))
        self.lbl_discount.config(text=str(float(self.discount)))
        self.lbl_net_pay.config(text=str(float(self.net_pay)))

    def clear_all(self) -> None:
        self.clear_cart()
        self.var_cname.set("")
        self.var_contact.set("")
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_search.set("")
        self.var_stock.set("")
        self.discount = 0.0
        self.siscount = 0
        self.chk_print = 0
        self.invoice = _GLOBAL_DB.next_invoice()
        self.txt_bill_area.delete("1.0", "end")
        self.show()
        self.show_cart()
        self.update_date_time()

    def clear_cal(self) -> None:
        self.var_cal_input.set("")
        self.txt_cal_input.delete(0, None)

    def clear_cart(self) -> None:
        self.cart_list = []
        self.CartTable.clear()
        self.bill_update()

    def _parse_int(self, s: str, field: str) -> int:
        s = s.strip()
        if not s:
            raise ValueError(f"{field} is required")
        try:
            v = int(s)
        except ValueError as e:
            raise ValueError(f"Invalid {field}") from e
        return v

    def _parse_float(self, s: str, field: str) -> float:
        s = s.strip()
        if not s:
            raise ValueError(f"{field} is required")
        try:
            v = float(s)
        except ValueError as e:
            raise ValueError(f"Invalid {field}") from e
        return v

    def add_update_cart(self) -> None:
        pid = self.var_pid.get().strip()
        if not pid:
            raise ValueError("Product ID is required")
        if pid not in _GLOBAL_DB.products:
            raise ValueError("Product not found")
        prod = _GLOBAL_DB.products[pid]
        qty = self._parse_int(self.var_qty.get(), "Quantity")
        if qty <= 0:
            raise ValueError("Quantity must be greater than 0")
        if qty > prod.qty:
            raise ValueError("Quantity exceeds stock")
        price = self._parse_float(self.var_price.get() or str(prod.price), "Price")
        if price < 0:
            raise ValueError("Price cannot be negative")
        pname = self.var_pname.get().strip() or prod.name

        existing = next((c for c in self.cart_list if c.pid == pid), None)
        if existing is None:
            self.cart_list.append(CartItem(pid=pid, pname=pname, price=price, qty=qty, stock=prod.qty))
        else:
            new_qty = existing.qty + qty
            if new_qty > prod.qty:
                raise ValueError("Total quantity in cart exceeds stock")
            existing.qty = new_qty
            existing.price = price
            existing.pname = pname
            existing.stock = prod.qty

        self.var_stock.set(str(prod.qty))
        self.lbl_inStock.config(text=str(prod.qty))
        self.show_cart()
        self.bill_update()

    def generate_bill(self) -> None:
        cname = self.var_cname.get().strip()
        contact = self.var_contact.get().strip()
        if not cname:
            raise ValueError("Customer name is required")
        if not self.cart_list:
            raise ValueError("Cart is empty")
        self.bill_top()
        self.bill_middle()
        self.bill_bottom()
        self.bill_update()
        bill_text = self.txt_bill_area.get()
        inv = InvoiceRecord(
            invoice=self.invoice,
            customer_name=cname,
            contact=contact,
            items=[CartItem(**vars(i)) for i in self.cart_list],
            bill_amount=float(sum(i.total for i in self.cart_list)),
            discount=float(self.discount),
            net_pay=float(self.net_pay),
            created_at=datetime.datetime.now(),
            bill_text=bill_text,
        )
        _GLOBAL_DB.invoices[self.invoice] = inv
        self.chk_print = 1

    def print_bill(self) -> None:
        if self.invoice not in _GLOBAL_DB.invoices:
            raise ValueError("No generated bill to print")
        self.chk_print = 1

    def get_data(self, ev: Any) -> None:
        sel = self.product_Table.selection()
        if not sel:
            return
        values = self.product_Table.item(sel[0], "values")
        if not values:
            return
        pid, name, cat, sup, price, qty, status = values
        self.var_pid.set(str(pid))
        self.var_pname.set(str(name))
        self.var_price.set(str(price))
        self.var_stock.set(str(qty))
        self.lbl_inStock.config(text=str(qty))

    def get_data_cart(self, ev: Any) -> None:
        sel = self.CartTable.selection()
        if not sel:
            return
        values = self.CartTable.item(sel[0], "values")
        if not values:
            return
        pid, pname, price, qty, stock, total = values
        self.var_pid.set(str(pid))
        self.var_pname.set(str(pname))
        self.var_price.set(str(price))
        self.var_qty.set(str(qty))
        self.var_stock.set(str(stock))
        self.lbl_inStock.config(text=str(stock))

    def get_input(self, num: Union[int, str]) -> None:
        current = self.var_cal_input.get()
        self.var_cal_input.set(current + str(num))
        self.txt_cal_input.delete(0, None)
        self.txt_cal_input.insert(0, self.var_cal_input.get())

    def perform_cal(self) -> None:
        expr = self.var_cal_input.get().strip()
        if not expr:
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
        self.txt_cal_input.insert(0, self.var_cal_input.get())

    def search(self) -> None:
        txt = self.var_search.get().strip().lower()
        self.product_Table.clear()
        records = list(_GLOBAL_DB.products.values())
        if txt:
            records = [p for p in records if txt in p.pid.lower() or txt in p.name.lower()]
        for p in sorted(records, key=lambda r: r.pid):
            self.product_Table.insert("", "end", (p.pid, p.name, p.cat, p.sup, p.price, p.qty, p.status))

    def show(self) -> None:
        self.product_Table.clear()
        for p in sorted(_GLOBAL_DB.products.values(), key=lambda r: r.pid):
            self.product_Table.insert("", "end", (p.pid, p.name, p.cat, p.sup, p.price, p.qty, p.status))

    def show_cart(self) -> None:
        self.CartTable.clear()
        for c in self.cart_list:
            self.CartTable.insert("", "end", (c.pid, c.pname, c.price, c.qty, c.stock, c.total))

    def update_date_time(self) -> None:
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))


class IMS:
    def __init__(self, root: Any = None) -> None:
        self.root = root if root is not None else Root()
        self.MenuLogo: Optional[PhotoImage] = None
        self.icon_side: PhotoImage = PhotoImage()
        self.icon_title: PhotoImage = PhotoImage()
        self.lbl_category: Label = Label("")
        self.lbl_clock: Label = Label("")
        self.lbl_employee: Label = Label("")
        self.lbl_product: Label = Label("")
        self.lbl_sales: Label = Label("")
        self.lbl_supplier: Label = Label("")
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
        self.lbl_category.config(text=str(len(_GLOBAL_DB.categories)))
        self.lbl_supplier.config(text=str(len(_GLOBAL_DB.suppliers)))
        self.lbl_employee.config(text=str(len(_GLOBAL_DB.employees)))
        self.lbl_product.config(text=str(len(_GLOBAL_DB.products)))
        self.lbl_sales.config(text=str(len(_GLOBAL_DB.invoices)))
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))


__all__ = [
    "IMS",
    "billClass",
    "categoryClass",
    "employeeClass",
    "productClass",
    "salesClass",
    "supplierClass",
    "PhotoImage",
    "Label",
    "Entry",
    "Text",
    "StringVar",
    "Listbox",
    "Treeview",
    "Toplevel",
    "Root",
]