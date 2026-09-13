from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


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


class Treeview:
    def __init__(self) -> None:
        self._rows: List[Tuple[Any, ...]] = []
        self._selection_index: Optional[int] = None

    def insert(self, values: Tuple[Any, ...]) -> None:
        self._rows.append(values)

    def delete(self, index: int) -> None:
        if 0 <= index < len(self._rows):
            del self._rows[index]
            if self._selection_index == index:
                self._selection_index = None
            elif self._selection_index is not None and self._selection_index > index:
                self._selection_index -= 1

    def clear(self) -> None:
        self._rows.clear()
        self._selection_index = None

    def get_children(self) -> List[int]:
        return list(range(len(self._rows)))

    def item(self, index: int) -> Dict[str, Any]:
        return {"values": self._rows[index]}

    def selection_set(self, index: int) -> None:
        if 0 <= index < len(self._rows):
            self._selection_index = index
        else:
            self._selection_index = None

    def selection(self) -> List[int]:
        return [] if self._selection_index is None else [self._selection_index]

    def focus(self) -> Optional[int]:
        return self._selection_index

    def rows(self) -> List[Tuple[Any, ...]]:
        return list(self._rows)


class Listbox:
    def __init__(self) -> None:
        self._items: List[str] = []
        self._selection_index: Optional[int] = None

    def insert(self, item: str) -> None:
        self._items.append(item)

    def delete(self, index: int) -> None:
        if 0 <= index < len(self._items):
            del self._items[index]
            if self._selection_index == index:
                self._selection_index = None
            elif self._selection_index is not None and self._selection_index > index:
                self._selection_index -= 1

    def clear(self) -> None:
        self._items.clear()
        self._selection_index = None

    def get(self, index: int) -> str:
        return self._items[index]

    def size(self) -> int:
        return len(self._items)

    def selection_set(self, index: int) -> None:
        if 0 <= index < len(self._items):
            self._selection_index = index
        else:
            self._selection_index = None

    def curselection(self) -> Tuple[int, ...]:
        return tuple() if self._selection_index is None else (self._selection_index,)

    def items(self) -> List[str]:
        return list(self._items)


class Toplevel:
    def __init__(self, root: Any = None) -> None:
        self.root = root


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
    pass_: str
    utype: str
    address: str
    salary: str


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
    invoice: str
    customer_name: str
    contact: str
    items: List[CartItem]
    bill_amount: float
    discount: float
    net_pay: float
    created_at: str


class _InMemoryDB:
    def __init__(self) -> None:
        self.categories: Dict[str, Category] = {}
        self.suppliers: Dict[str, Supplier] = {}
        self.employees: Dict[str, Employee] = {}
        self.products: Dict[str, Product] = {}
        self.invoices: Dict[str, Invoice] = {}

    def next_invoice_id(self) -> str:
        base = datetime.now().strftime("%Y%m%d%H%M%S")
        suffix = 0
        inv = base
        while inv in self.invoices:
            suffix += 1
            inv = f"{base}{suffix:02d}"
        return inv


_GLOBAL_DB = _InMemoryDB()


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
        if not cat_id or not name:
            raise ValueError("Category ID and Name are required")
        if cat_id in _GLOBAL_DB.categories:
            raise ValueError("Category ID already exists")
        _GLOBAL_DB.categories[cat_id] = Category(cat_id=cat_id, name=name)
        self.show()
        self.clear()

    def clear(self) -> None:
        self.var_cat_id.set("")
        self.var_name.set("")

    def delete(self) -> None:
        cat_id = self.var_cat_id.get().strip()
        if not cat_id:
            raise ValueError("Category ID is required for delete")
        if cat_id not in _GLOBAL_DB.categories:
            raise ValueError("Category not found")
        del _GLOBAL_DB.categories[cat_id]
        self.show()
        self.clear()

    def get_data(self, ev: Any) -> None:
        index = self.CategoryTable.focus()
        if index is None:
            return
        values = self.CategoryTable.item(index).get("values", ())
        if len(values) >= 2:
            self.var_cat_id.set(str(values[0]))
            self.var_name.set(str(values[1]))

    def show(self) -> None:
        self.CategoryTable.clear()
        for cat in sorted(_GLOBAL_DB.categories.values(), key=lambda c: c.cat_id):
            self.CategoryTable.insert((cat.cat_id, cat.name))


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
        if not sup_invoice or not name:
            raise ValueError("Supplier Invoice and Name are required")
        if sup_invoice in _GLOBAL_DB.suppliers:
            raise ValueError("Supplier Invoice already exists")
        _GLOBAL_DB.suppliers[sup_invoice] = Supplier(
            sup_invoice=sup_invoice, name=name, contact=contact, desc=desc
        )
        self.show()
        self.clear()

    def clear(self) -> None:
        self.var_sup_invoice.set("")
        self.var_name.set("")
        self.var_contact.set("")
        self.txt_desc.delete()

    def delete(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        if not sup_invoice:
            raise ValueError("Supplier Invoice is required for delete")
        if sup_invoice not in _GLOBAL_DB.suppliers:
            raise ValueError("Supplier not found")
        del _GLOBAL_DB.suppliers[sup_invoice]
        self.show()
        self.clear()

    def get_data(self, ev: Any) -> None:
        index = self.SupplierTable.focus()
        if index is None:
            return
        values = self.SupplierTable.item(index).get("values", ())
        if len(values) >= 4:
            self.var_sup_invoice.set(str(values[0]))
            self.var_name.set(str(values[1]))
            self.var_contact.set(str(values[2]))
            self.txt_desc.delete()
            self.txt_desc.insert("1.0", str(values[3]))

    def search(self) -> None:
        by = self.var_searchby.get().strip().lower()
        txt = self.var_searchtxt.get().strip().lower()
        self.SupplierTable.clear()
        suppliers = list(_GLOBAL_DB.suppliers.values())
        if txt:
            if by in ("invoice", "sup_invoice", "id"):
                suppliers = [s for s in suppliers if txt in s.sup_invoice.lower()]
            elif by in ("name",):
                suppliers = [s for s in suppliers if txt in s.name.lower()]
            elif by in ("contact",):
                suppliers = [s for s in suppliers if txt in s.contact.lower()]
            else:
                suppliers = [
                    s
                    for s in suppliers
                    if txt in s.sup_invoice.lower()
                    or txt in s.name.lower()
                    or txt in s.contact.lower()
                    or txt in s.desc.lower()
                ]
        for s in sorted(suppliers, key=lambda x: x.sup_invoice):
            self.SupplierTable.insert((s.sup_invoice, s.name, s.contact, s.desc))

    def show(self) -> None:
        self.SupplierTable.clear()
        for s in sorted(_GLOBAL_DB.suppliers.values(), key=lambda x: x.sup_invoice):
            self.SupplierTable.insert((s.sup_invoice, s.name, s.contact, s.desc))

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
        _GLOBAL_DB.suppliers[sup_invoice] = Supplier(
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
        name = self.var_name.get().strip()
        email = self.var_email.get().strip()
        gender = self.var_gender.get().strip()
        contact = self.var_contact.get().strip()
        dob = self.var_dob.get().strip()
        doj = self.var_doj.get().strip()
        pass_ = self.var_pass.get()
        utype = self.var_utype.get().strip()
        address = self.txt_address.get().strip()
        salary = self.var_salary.get().strip()
        if not emp_id or not name:
            raise ValueError("Employee ID and Name are required")
        if emp_id in _GLOBAL_DB.employees:
            raise ValueError("Employee ID already exists")
        _GLOBAL_DB.employees[emp_id] = Employee(
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

    def delete(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        if not emp_id:
            raise ValueError("Employee ID is required for delete")
        if emp_id not in _GLOBAL_DB.employees:
            raise ValueError("Employee not found")
        del _GLOBAL_DB.employees[emp_id]
        self.show()
        self.clear()

    def get_data(self, ev: Any) -> None:
        index = self.EmployeeTable.focus()
        if index is None:
            return
        values = self.EmployeeTable.item(index).get("values", ())
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
            self.txt_address.delete()
            self.txt_address.insert("1.0", str(values[9]))
            self.var_salary.set(str(values[10]))

    def search(self) -> None:
        by = self.var_searchby.get().strip().lower()
        txt = self.var_searchtxt.get().strip().lower()
        self.EmployeeTable.clear()
        employees = list(_GLOBAL_DB.employees.values())
        if txt:
            if by in ("id", "emp_id", "employee id"):
                employees = [e for e in employees if txt in e.emp_id.lower()]
            elif by in ("name",):
                employees = [e for e in employees if txt in e.name.lower()]
            elif by in ("email",):
                employees = [e for e in employees if txt in e.email.lower()]
            elif by in ("contact",):
                employees = [e for e in employees if txt in e.contact.lower()]
            elif by in ("utype", "type"):
                employees = [e for e in employees if txt in e.utype.lower()]
            else:
                employees = [
                    e
                    for e in employees
                    if txt in e.emp_id.lower()
                    or txt in e.name.lower()
                    or txt in e.email.lower()
                    or txt in e.contact.lower()
                    or txt in e.utype.lower()
                ]
        for e in sorted(employees, key=lambda x: x.emp_id):
            self.EmployeeTable.insert(
                (
                    e.emp_id,
                    e.name,
                    e.email,
                    e.gender,
                    e.contact,
                    e.dob,
                    e.doj,
                    e.pass_,
                    e.utype,
                    e.address,
                    e.salary,
                )
            )

    def show(self) -> None:
        self.EmployeeTable.clear()
        for e in sorted(_GLOBAL_DB.employees.values(), key=lambda x: x.emp_id):
            self.EmployeeTable.insert(
                (
                    e.emp_id,
                    e.name,
                    e.email,
                    e.gender,
                    e.contact,
                    e.dob,
                    e.doj,
                    e.pass_,
                    e.utype,
                    e.address,
                    e.salary,
                )
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
        _GLOBAL_DB.employees[emp_id] = Employee(
            emp_id=emp_id,
            name=name,
            email=self.var_email.get().strip(),
            gender=self.var_gender.get().strip(),
            contact=self.var_contact.get().strip(),
            dob=self.var_dob.get().strip(),
            doj=self.var_doj.get().strip(),
            pass_=self.var_pass.get(),
            utype=self.var_utype.get().strip(),
            address=self.txt_address.get().strip(),
            salary=self.var_salary.get().strip(),
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

    def fetch_cat_sup(self) -> None:
        self.cat_list = [c.name for c in _GLOBAL_DB.categories.values()]
        self.sup_list = [s.name for s in _GLOBAL_DB.suppliers.values()]

    def _parse_price_qty(self) -> Tuple[float, int]:
        price_s = self.var_price.get().strip()
        qty_s = self.var_qty.get().strip()
        if not price_s:
            raise ValueError("Price is required")
        if not qty_s:
            raise ValueError("Quantity is required")
        try:
            price = float(price_s)
        except ValueError as e:
            raise ValueError("Invalid price") from e
        try:
            qty = int(float(qty_s))
        except ValueError as e:
            raise ValueError("Invalid quantity") from e
        if price < 0:
            raise ValueError("Price cannot be negative")
        if qty < 0:
            raise ValueError("Quantity cannot be negative")
        return price, qty

    def add(self) -> None:
        pid = self.var_pid.get().strip()
        name = self.var_name.get().strip()
        cat = self.var_cat.get().strip()
        sup = self.var_sup.get().strip()
        status = self.var_status.get().strip() or "Active"
        if not pid or not name:
            raise ValueError("Product ID and Name are required")
        if pid in _GLOBAL_DB.products:
            raise ValueError("Product ID already exists")
        price, qty = self._parse_price_qty()
        _GLOBAL_DB.products[pid] = Product(
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

    def delete(self) -> None:
        pid = self.var_pid.get().strip()
        if not pid:
            raise ValueError("Product ID is required for delete")
        if pid not in _GLOBAL_DB.products:
            raise ValueError("Product not found")
        del _GLOBAL_DB.products[pid]
        self.show()
        self.clear()

    def get_data(self, ev: Any) -> None:
        index = self.ProductTable.focus()
        if index is None:
            return
        values = self.ProductTable.item(index).get("values", ())
        if len(values) >= 7:
            self.var_pid.set(str(values[0]))
            self.var_name.set(str(values[1]))
            self.var_cat.set(str(values[2]))
            self.var_sup.set(str(values[3]))
            self.var_price.set(str(values[4]))
            self.var_qty.set(str(values[5]))
            self.var_status.set(str(values[6]))

    def search(self) -> None:
        by = self.var_searchby.get().strip().lower()
        txt = self.var_searchtxt.get().strip().lower()
        self.ProductTable.clear()
        products = list(_GLOBAL_DB.products.values())
        if txt:
            if by in ("id", "pid", "product id"):
                products = [p for p in products if txt in p.pid.lower()]
            elif by in ("name",):
                products = [p for p in products if txt in p.name.lower()]
            elif by in ("category", "cat"):
                products = [p for p in products if txt in p.cat.lower()]
            elif by in ("supplier", "sup"):
                products = [p for p in products if txt in p.sup.lower()]
            elif by in ("status",):
                products = [p for p in products if txt in p.status.lower()]
            else:
                products = [
                    p
                    for p in products
                    if txt in p.pid.lower()
                    or txt in p.name.lower()
                    or txt in p.cat.lower()
                    or txt in p.sup.lower()
                    or txt in p.status.lower()
                ]
        for p in sorted(products, key=lambda x: x.pid):
            self.ProductTable.insert((p.pid, p.name, p.cat, p.sup, p.price, p.qty, p.status))

    def show(self) -> None:
        self.ProductTable.clear()
        for p in sorted(_GLOBAL_DB.products.values(), key=lambda x: x.pid):
            self.ProductTable.insert((p.pid, p.name, p.cat, p.sup, p.price, p.qty, p.status))

    def update(self) -> None:
        pid = self.var_pid.get().strip()
        if not pid:
            raise ValueError("Product ID is required for update")
        if pid not in _GLOBAL_DB.products:
            raise ValueError("Product not found")
        name = self.var_name.get().strip()
        if not name:
            raise ValueError("Product Name is required")
        price, qty = self._parse_price_qty()
        _GLOBAL_DB.products[pid] = Product(
            pid=pid,
            name=name,
            cat=self.var_cat.get().strip(),
            sup=self.var_sup.get().strip(),
            price=price,
            qty=qty,
            status=self.var_status.get().strip() or "Active",
        )
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
        self.bill_area.delete()

    def get_data(self, ev: Any) -> None:
        sel = self.Sales_List.curselection()
        if not sel:
            return
        invoice_id = self.Sales_List.get(sel[0])
        self.var_invoice.set(invoice_id)
        inv = _GLOBAL_DB.invoices.get(invoice_id)
        self.bill_area.delete()
        if inv is not None:
            self.bill_area.insert("1.0", _format_invoice_text(inv))

    def search(self) -> None:
        txt = self.var_invoice.get().strip().lower()
        self.Sales_List.clear()
        invoices = list(_GLOBAL_DB.invoices.values())
        if txt:
            invoices = [i for i in invoices if txt in i.invoice.lower()]
        for inv in sorted(invoices, key=lambda x: x.invoice):
            self.Sales_List.insert(inv.invoice)
        self.blll_list = [inv.invoice for inv in sorted(invoices, key=lambda x: x.invoice)]

    def show(self) -> None:
        self.Sales_List.clear()
        invoices = sorted(_GLOBAL_DB.invoices.values(), key=lambda x: x.invoice)
        for inv in invoices:
            self.Sales_List.insert(inv.invoice)
        self.blll_list = [inv.invoice for inv in invoices]


def _format_invoice_text(inv: Invoice) -> str:
    lines: List[str] = []
    lines.append(f"INVOICE: {inv.invoice}")
    lines.append(f"DATE: {inv.created_at}")
    lines.append(f"CUSTOMER: {inv.customer_name}")
    lines.append(f"CONTACT: {inv.contact}")
    lines.append("")
    lines.append("ITEMS:")
    lines.append("PID\tNAME\tPRICE\tQTY\tAMOUNT")
    for it in inv.items:
        lines.append(f"{it.pid}\t{it.pname}\t{it.price:.2f}\t{it.qty}\t{it.amount:.2f}")
    lines.append("")
    lines.append(f"BILL AMOUNT: {inv.bill_amount:.2f}")
    lines.append(f"DISCOUNT: {inv.discount:.2f}")
    lines.append(f"NET PAY: {inv.net_pay:.2f}")
    return "\n".join(lines)


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
        self.invoice: Optional[str] = None
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
        self.var_cal_input: StringVar = StringVar()
        self.var_cname: StringVar = StringVar()
        self.var_contact: StringVar = StringVar()
        self.var_pid: StringVar = StringVar()
        self.var_pname: StringVar = StringVar()
        self.var_price: StringVar = StringVar()
        self.var_qty: StringVar = StringVar()
        self.var_search: StringVar = StringVar()
        self.var_stock: StringVar = StringVar()

    def bill_top(self) -> None:
        self.txt_bill_area.delete()
        inv = self.invoice or ""
        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.txt_bill_area.insert("1.0", f"INVOICE: {inv}\nDATE: {dt}\n")
        self.txt_bill_area.insert("end", f"CUSTOMER: {self.var_cname.get()}\nCONTACT: {self.var_contact.get()}\n\n")
        self.txt_bill_area.insert("end", "PID\tNAME\tPRICE\tQTY\tAMOUNT\n")

    def bill_middle(self) -> None:
        for it in self.cart_list:
            self.txt_bill_area.insert(
                "end",
                f"{it.pid}\t{it.pname}\t{it.price:.2f}\t{it.qty}\t{it.amount:.2f}\n",
            )

    def bill_bottom(self) -> None:
        self.bill_update()
        self.txt_bill_area.insert("end", "\n")
        self.txt_bill_area.insert("end", f"BILL AMOUNT: {float(self.bill_amnt):.2f}\n")
        self.txt_bill_area.insert("end", f"DISCOUNT: {float(self.discount):.2f}\n")
        self.txt_bill_area.insert("end", f"NET PAY: {float(self.net_pay):.2f}\n")

    def bill_update(self) -> None:
        total = sum(it.amount for it in self.cart_list)
        self.bill_amnt = int(round(total))
        self.discount = float(self.siscount) if self.siscount else float(self.discount or 0.0)
        net = total - float(self.discount)
        if net < 0:
            net = 0.0
        self.net_pay = net
        self.lbl_amnt.config(text=str(self.bill_amnt))
        self.lbl_discount.config(text=f"{float(self.discount):.2f}")
        self.lbl_net_pay.config(text=f"{float(self.net_pay):.2f}")

    def clear_all(self) -> None:
        self.clear_cart()
        self.var_cname.set("")
        self.var_contact.set("")
        self.var_search.set("")
        self.var_pid.set("")
        self.var_pname.set("")
        self.var_price.set("")
        self.var_qty.set("")
        self.var_stock.set("")
        self.discount = 0.0
        self.siscount = 0
        self.bill_amnt = 0
        self.net_pay = 0.0
        self.invoice = None
        self.txt_bill_area.delete()
        self.clear_cal()

    def clear_cal(self) -> None:
        self.var_cal_input.set("")
        self.txt_cal_input.delete()

    def clear_cart(self) -> None:
        self.cart_list.clear()
        self.CartTable.clear()
        self.bill_update()

    def show(self) -> None:
        self.product_Table.clear()
        for p in sorted(_GLOBAL_DB.products.values(), key=lambda x: x.pid):
            self.product_Table.insert((p.pid, p.name, p.price, p.qty, p.status, p.cat, p.sup))

    def search(self) -> None:
        txt = self.var_search.get().strip().lower()
        self.product_Table.clear()
        products = list(_GLOBAL_DB.products.values())
        if txt:
            products = [p for p in products if txt in p.pid.lower() or txt in p.name.lower()]
        for p in sorted(products, key=lambda x: x.pid):
            self.product_Table.insert((p.pid, p.name, p.price, p.qty, p.status, p.cat, p.sup))

    def get_data(self, ev: Any) -> None:
        index = self.product_Table.focus()
        if index is None:
            return
        values = self.product_Table.item(index).get("values", ())
        if len(values) >= 4:
            self.var_pid.set(str(values[0]))
            self.var_pname.set(str(values[1]))
            self.var_price.set(str(values[2]))
            self.var_stock.set(str(values[3]))
            self.lbl_inStock.config(text=str(values[3]))

    def show_cart(self) -> None:
        self.CartTable.clear()
        for it in self.cart_list:
            self.CartTable.insert((it.pid, it.pname, it.price, it.qty, it.amount))
        self.bill_update()

    def get_data_cart(self, ev: Any) -> None:
        index = self.CartTable.focus()
        if index is None:
            return
        values = self.CartTable.item(index).get("values", ())
        if len(values) >= 4:
            self.var_pid.set(str(values[0]))
            self.var_pname.set(str(values[1]))
            self.var_price.set(str(values[2]))
            self.var_qty.set(str(values[3]))

    def add_update_cart(self) -> None:
        pid = self.var_pid.get().strip()
        if not pid:
            raise ValueError("Select a product")
        if pid not in _GLOBAL_DB.products:
            raise ValueError("Product not found")
        p = _GLOBAL_DB.products[pid]
        qty_s = self.var_qty.get().strip()
        if not qty_s:
            raise ValueError("Quantity is required")
        try:
            qty = int(float(qty_s))
        except ValueError as e:
            raise ValueError("Invalid quantity") from e
        if qty <= 0:
            raise ValueError("Quantity must be greater than zero")
        if qty > p.qty:
            raise ValueError("Insufficient stock")

        existing = next((it for it in self.cart_list if it.pid == pid), None)
        if existing is None:
            self.cart_list.append(
                CartItem(pid=p.pid, pname=p.name, price=float(p.price), qty=qty, stock=int(p.qty))
            )
        else:
            new_qty = existing.qty + qty
            if new_qty > p.qty:
                raise ValueError("Insufficient stock")
            existing.qty = new_qty
            existing.stock = int(p.qty)
            existing.price = float(p.price)
            existing.pname = p.name
        self.show_cart()
        self.var_qty.set("")

    def generate_bill(self) -> None:
        if not self.cart_list:
            raise ValueError("Cart is empty")
        cname = self.var_cname.get().strip()
        contact = self.var_contact.get().strip()
        if not cname:
            raise ValueError("Customer name is required")
        if self.invoice is None:
            self.invoice = _GLOBAL_DB.next_invoice_id()

        self.bill_update()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = sum(it.amount for it in self.cart_list)
        disc = float(self.discount)
        net = float(self.net_pay)

        for it in self.cart_list:
            prod = _GLOBAL_DB.products.get(it.pid)
            if prod is None:
                raise ValueError("Product not found during billing")
            if it.qty > prod.qty:
                raise ValueError("Insufficient stock during billing")
        for it in self.cart_list:
            prod = _GLOBAL_DB.products[it.pid]
            prod.qty -= it.qty
            _GLOBAL_DB.products[it.pid] = prod

        inv = Invoice(
            invoice=self.invoice,
            customer_name=cname,
            contact=contact,
            items=[CartItem(pid=i.pid, pname=i.pname, price=i.price, qty=i.qty, stock=i.stock) for i in self.cart_list],
            bill_amount=float(total),
            discount=disc,
            net_pay=net,
            created_at=created_at,
        )
        _GLOBAL_DB.invoices[inv.invoice] = inv

        self.txt_bill_area.delete()
        self.bill_top()
        self.bill_middle()
        self.bill_bottom()
        self.chk_print = 1

    def print_bill(self) -> None:
        if not self.chk_print or not self.invoice:
            raise ValueError("No bill generated to print")
        self.chk_print = 2

    def update_date_time(self) -> None:
        self.lbl_clock.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def get_input(self, num: Union[int, str]) -> None:
        s = self.var_cal_input.get()
        s += str(num)
        self.var_cal_input.set(s)
        self.txt_cal_input.delete()
        self.txt_cal_input.insert(0, s)

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
        self.var_cal_input.set(str(result))
        self.txt_cal_input.delete()
        self.txt_cal_input.insert(0, str(result))

    def clear_cal(self) -> None:
        self.var_cal_input.set("")
        self.txt_cal_input.delete()

    def update_content(self) -> None:
        self.show()
        self.show_cart()
        self.update_date_time()


class IMS:
    def __init__(self, root: Any = None) -> None:
        self.root = root
        self.MenuLogo: Union[None, PhotoImage] = None
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
        self.lbl_clock.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.lbl_category.config(text=str(len(_GLOBAL_DB.categories)))
        self.lbl_supplier.config(text=str(len(_GLOBAL_DB.suppliers)))
        self.lbl_employee.config(text=str(len(_GLOBAL_DB.employees)))
        self.lbl_product.config(text=str(len(_GLOBAL_DB.products)))
        self.lbl_sales.config(text=str(len(_GLOBAL_DB.invoices)))


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
    "Treeview",
    "Listbox",
    "Toplevel",
]