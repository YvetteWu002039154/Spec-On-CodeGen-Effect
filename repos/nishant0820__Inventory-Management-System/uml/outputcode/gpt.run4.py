from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
import datetime
import math
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


class Toplevel:
    def __init__(self, root: Any = None) -> None:
        self.root = root


class Treeview:
    def __init__(self) -> None:
        self._rows: List[Dict[str, Any]] = []
        self._selected_index: Optional[int] = None

    def insert(self, values: Dict[str, Any]) -> None:
        self._rows.append(dict(values))

    def clear(self) -> None:
        self._rows.clear()
        self._selected_index = None

    def all(self) -> List[Dict[str, Any]]:
        return [dict(r) for r in self._rows]

    def select(self, index: int) -> None:
        if index < 0 or index >= len(self._rows):
            raise IndexError("Treeview selection index out of range")
        self._selected_index = index

    def selected(self) -> Optional[Dict[str, Any]]:
        if self._selected_index is None:
            return None
        return dict(self._rows[self._selected_index])


class Listbox:
    def __init__(self) -> None:
        self._items: List[str] = []
        self._selected_index: Optional[int] = None

    def insert(self, item: str) -> None:
        self._items.append(str(item))

    def clear(self) -> None:
        self._items.clear()
        self._selected_index = None

    def items(self) -> List[str]:
        return list(self._items)

    def select(self, index: int) -> None:
        if index < 0 or index >= len(self._items):
            raise IndexError("Listbox selection index out of range")
        self._selected_index = index

    def selected(self) -> Optional[str]:
        if self._selected_index is None:
            return None
        return self._items[self._selected_index]


class Text:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = str(value)

    def clear(self) -> None:
        self.value = ""


class Entry:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = str(value)

    def clear(self) -> None:
        self.value = ""


class StringVar:
    def __init__(self, value: str = "") -> None:
        self._value = str(value)

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = str(value)


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
    salary: str
    address: str


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
class BillRecord:
    invoice: str
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
        self.categories: Dict[str, CategoryRecord] = {}
        self.suppliers: Dict[str, SupplierRecord] = {}
        self.employees: Dict[str, EmployeeRecord] = {}
        self.products: Dict[str, ProductRecord] = {}
        self.sales: Dict[str, BillRecord] = {}

    def reset(self) -> None:
        self.categories.clear()
        self.suppliers.clear()
        self.employees.clear()
        self.products.clear()
        self.sales.clear()


class BaseManager:
    def __init__(self, root: Any = None, db: Optional[InMemoryDB] = None) -> None:
        self.root = root
        self._db = db if db is not None else InMemoryDB()

    @property
    def db(self) -> InMemoryDB:
        return self._db


class categoryClass(BaseManager):
    def __init__(self, root: Any = None, db: Optional[InMemoryDB] = None) -> None:
        super().__init__(root=root, db=db)
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
        if cat_id in self.db.categories:
            raise ValueError("Category ID already exists")
        self.db.categories[cat_id] = CategoryRecord(cat_id=cat_id, name=name)
        self.show()

    def clear(self) -> None:
        self.var_cat_id.set("")
        self.var_name.set("")
        self.CategoryTable.clear()

    def delete(self) -> None:
        cat_id = self.var_cat_id.get().strip()
        if not cat_id:
            raise ValueError("Category ID is required for delete")
        if cat_id not in self.db.categories:
            raise KeyError("Category not found")
        del self.db.categories[cat_id]
        self.show()

    def get_data(self, ev: Any) -> None:
        row = None
        if isinstance(ev, dict):
            row = ev
        elif hasattr(ev, "get") and callable(getattr(ev, "get")):
            try:
                row = ev.get()
            except Exception:
                row = None
        if row is None and isinstance(ev, int):
            self.CategoryTable.select(ev)
            row = self.CategoryTable.selected()
        if not isinstance(row, dict):
            raise ValueError("Invalid event data for get_data")
        self.var_cat_id.set(str(row.get("cat_id", "")))
        self.var_name.set(str(row.get("name", "")))

    def show(self) -> None:
        self.CategoryTable.clear()
        for rec in sorted(self.db.categories.values(), key=lambda r: r.cat_id):
            self.CategoryTable.insert({"cat_id": rec.cat_id, "name": rec.name})


class supplierClass(BaseManager):
    def __init__(self, root: Any = None, db: Optional[InMemoryDB] = None) -> None:
        super().__init__(root=root, db=db)
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
        self.SupplierTable.clear()

    def delete(self) -> None:
        sup_invoice = self.var_sup_invoice.get().strip()
        if not sup_invoice:
            raise ValueError("Supplier invoice is required for delete")
        if sup_invoice not in self.db.suppliers:
            raise KeyError("Supplier not found")
        del self.db.suppliers[sup_invoice]
        self.show()

    def get_data(self, ev: Any) -> None:
        row = None
        if isinstance(ev, dict):
            row = ev
        elif isinstance(ev, int):
            self.SupplierTable.select(ev)
            row = self.SupplierTable.selected()
        if not isinstance(row, dict):
            raise ValueError("Invalid event data for get_data")
        self.var_sup_invoice.set(str(row.get("sup_invoice", "")))
        self.var_name.set(str(row.get("name", "")))
        self.var_contact.set(str(row.get("contact", "")))
        self.txt_desc.set(str(row.get("desc", "")))

    def search(self) -> None:
        by = self.var_searchby.get().strip()
        txt = self.var_searchtxt.get().strip().lower()
        if not by:
            raise ValueError("Search by is required")
        if by not in {"sup_invoice", "name", "contact"}:
            raise ValueError("Invalid search field")
        self.SupplierTable.clear()
        for rec in self.db.suppliers.values():
            val = getattr(rec, by)
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
        if not sup_invoice:
            raise ValueError("Supplier invoice is required for update")
        if sup_invoice not in self.db.suppliers:
            raise KeyError("Supplier not found")
        name = self.var_name.get().strip()
        contact = self.var_contact.get().strip()
        desc = self.txt_desc.get().strip()
        if not name:
            raise ValueError("Supplier name is required")
        self.db.suppliers[sup_invoice] = SupplierRecord(
            sup_invoice=sup_invoice, name=name, contact=contact, desc=desc
        )
        self.show()


class employeeClass(BaseManager):
    def __init__(self, root: Any = None, db: Optional[InMemoryDB] = None) -> None:
        super().__init__(root=root, db=db)
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
        salary = self.var_salary.get().strip()
        address = self.txt_address.get().strip()

        if not emp_id:
            raise ValueError("Employee ID is required")
        if not name:
            raise ValueError("Employee name is required")
        if emp_id in self.db.employees:
            raise ValueError("Employee ID already exists")

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
            salary=salary,
            address=address,
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
        self.EmployeeTable.clear()

    def delete(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        if not emp_id:
            raise ValueError("Employee ID is required for delete")
        if emp_id not in self.db.employees:
            raise KeyError("Employee not found")
        del self.db.employees[emp_id]
        self.show()

    def get_data(self, ev: Any) -> None:
        row = None
        if isinstance(ev, dict):
            row = ev
        elif isinstance(ev, int):
            self.EmployeeTable.select(ev)
            row = self.EmployeeTable.selected()
        if not isinstance(row, dict):
            raise ValueError("Invalid event data for get_data")
        self.var_emp_id.set(str(row.get("emp_id", "")))
        self.var_name.set(str(row.get("name", "")))
        self.var_email.set(str(row.get("email", "")))
        self.var_gender.set(str(row.get("gender", "")))
        self.var_contact.set(str(row.get("contact", "")))
        self.var_dob.set(str(row.get("dob", "")))
        self.var_doj.set(str(row.get("doj", "")))
        self.var_pass.set(str(row.get("pass", row.get("pass_", ""))))
        self.var_utype.set(str(row.get("utype", "")))
        self.var_salary.set(str(row.get("salary", "")))
        self.txt_address.set(str(row.get("address", "")))

    def search(self) -> None:
        by = self.var_searchby.get().strip()
        txt = self.var_searchtxt.get().strip().lower()
        if not by:
            raise ValueError("Search by is required")
        if by not in {"emp_id", "name", "email", "contact", "utype"}:
            raise ValueError("Invalid search field")
        self.EmployeeTable.clear()
        for rec in self.db.employees.values():
            val = getattr(rec, by if by != "pass" else "pass_")
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
                        "pass_": rec.pass_,
                        "utype": rec.utype,
                        "salary": rec.salary,
                        "address": rec.address,
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
                    "pass_": rec.pass_,
                    "utype": rec.utype,
                    "salary": rec.salary,
                    "address": rec.address,
                }
            )

    def update(self) -> None:
        emp_id = self.var_emp_id.get().strip()
        if not emp_id:
            raise ValueError("Employee ID is required for update")
        if emp_id not in self.db.employees:
            raise KeyError("Employee not found")

        name = self.var_name.get().strip()
        if not name:
            raise ValueError("Employee name is required")

        self.db.employees[emp_id] = EmployeeRecord(
            emp_id=emp_id,
            name=name,
            email=self.var_email.get().strip(),
            gender=self.var_gender.get().strip(),
            contact=self.var_contact.get().strip(),
            dob=self.var_dob.get().strip(),
            doj=self.var_doj.get().strip(),
            pass_=self.var_pass.get(),
            utype=self.var_utype.get().strip(),
            salary=self.var_salary.get().strip(),
            address=self.txt_address.get().strip(),
        )
        self.show()


class productClass(BaseManager):
    def __init__(self, root: Any = None, db: Optional[InMemoryDB] = None) -> None:
        super().__init__(root=root, db=db)
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
        self.cat_list = [rec.name for rec in self.db.categories.values()]
        self.sup_list = [rec.name for rec in self.db.suppliers.values()]

    def _parse_price(self, s: str) -> float:
        s = s.strip()
        if not s:
            raise ValueError("Price is required")
        try:
            v = float(s)
        except ValueError as e:
            raise ValueError("Invalid price") from e
        if not math.isfinite(v) or v < 0:
            raise ValueError("Invalid price")
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
            raise ValueError("Invalid quantity")
        return v

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
        if not name:
            raise ValueError("Product name is required")
        if pid in self.db.products:
            raise ValueError("Product ID already exists")

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
        self.ProductTable.clear()

    def delete(self) -> None:
        pid = self.var_pid.get().strip()
        if not pid:
            raise ValueError("Product ID is required for delete")
        if pid not in self.db.products:
            raise KeyError("Product not found")
        del self.db.products[pid]
        self.show()

    def get_data(self, ev: Any) -> None:
        row = None
        if isinstance(ev, dict):
            row = ev
        elif isinstance(ev, int):
            self.ProductTable.select(ev)
            row = self.ProductTable.selected()
        if not isinstance(row, dict):
            raise ValueError("Invalid event data for get_data")
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
        if not by:
            raise ValueError("Search by is required")
        if by not in {"pid", "name", "cat", "sup", "status"}:
            raise ValueError("Invalid search field")
        self.ProductTable.clear()
        for rec in self.db.products.values():
            val = getattr(rec, by)
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
        if not pid:
            raise ValueError("Product ID is required for update")
        if pid not in self.db.products:
            raise KeyError("Product not found")

        name = self.var_name.get().strip()
        if not name:
            raise ValueError("Product name is required")

        price = self._parse_price(self.var_price.get())
        qty = self._parse_qty(self.var_qty.get())

        self.db.products[pid] = ProductRecord(
            pid=pid,
            name=name,
            cat=self.var_cat.get().strip(),
            sup=self.var_sup.get().strip(),
            price=price,
            qty=qty,
            status=self.var_status.get().strip(),
        )
        self.show()


class salesClass(BaseManager):
    def __init__(self, root: Any = None, db: Optional[InMemoryDB] = None) -> None:
        super().__init__(root=root, db=db)
        self.Sales_List: Listbox = Listbox()
        self.bill_area: Text = Text()
        self.bill_photo: Optional[PhotoImage] = None
        self.blll_list: List[str] = []
        self.var_invoice: StringVar = StringVar()

    def clear(self) -> None:
        self.var_invoice.set("")
        self.bill_area.clear()
        self.Sales_List.clear()
        self.blll_list = []

    def get_data(self, ev: Any) -> None:
        invoice: Optional[str] = None
        if isinstance(ev, str):
            invoice = ev
        elif isinstance(ev, int):
            self.Sales_List.select(ev)
            invoice = self.Sales_List.selected()
        elif isinstance(ev, dict):
            invoice = str(ev.get("invoice", "")).strip() or None
        if not invoice:
            raise ValueError("Invalid event data for get_data")
        self.var_invoice.set(invoice)
        rec = self.db.sales.get(invoice)
        if rec is None:
            raise KeyError("Invoice not found")
        self.bill_area.set(rec.text)

    def search(self) -> None:
        invoice = self.var_invoice.get().strip()
        self.Sales_List.clear()
        self.blll_list = []
        if not invoice:
            return
        for inv in sorted(self.db.sales.keys()):
            if invoice.lower() in inv.lower():
                self.Sales_List.insert(inv)
                self.blll_list.append(inv)

    def show(self) -> None:
        self.Sales_List.clear()
        self.blll_list = []
        for inv in sorted(self.db.sales.keys()):
            self.Sales_List.insert(inv)
            self.blll_list.append(inv)


class billClass(BaseManager):
    def __init__(self, root: Any = None, db: Optional[InMemoryDB] = None) -> None:
        super().__init__(root=root, db=db)
        self.CartTable: Treeview = Treeview()
        self.bill_amnt: int = 0
        self.cartTitle: Label = Label()
        self.cart_list: List[Dict[str, Any]] = []
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
        if not self.invoice:
            self.invoice = self._new_invoice()
        now = datetime.datetime.now()
        header = [
            "INVENTORY MANAGEMENT SYSTEM",
            f"Invoice: {self.invoice}",
            f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Customer: {self.var_cname.get().strip()}",
            f"Contact: {self.var_contact.get().strip()}",
            "-" * 40,
            f"{'PID':<8}{'Name':<16}{'Qty':>4}{'Price':>6}{'Total':>6}",
            "-" * 40,
        ]
        self.txt_bill_area.set("\n".join(header) + "\n")

    def bill_middle(self) -> None:
        lines: List[str] = []
        for item in self._cart_items():
            lines.append(
                f"{item.pid:<8}{item.pname[:16]:<16}{item.qty:>4}{item.price:>6.2f}{item.total:>6.2f}"
            )
        current = self.txt_bill_area.get()
        self.txt_bill_area.set(current + ("\n".join(lines) + ("\n" if lines else "")))

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

    def _new_invoice(self) -> str:
        return datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6].upper()

    def _cart_items(self) -> List[CartItem]:
        items: List[CartItem] = []
        for row in self.cart_list:
            items.append(
                CartItem(
                    pid=str(row["pid"]),
                    pname=str(row["pname"]),
                    price=float(row["price"]),
                    qty=int(row["qty"]),
                    stock=int(row.get("stock", row.get("in_stock", 0))),
                )
            )
        return items

    def show(self) -> None:
        self.product_Table.clear()
        for rec in sorted(self.db.products.values(), key=lambda r: r.pid):
            self.product_Table.insert(
                {
                    "pid": rec.pid,
                    "name": rec.name,
                    "price": rec.price,
                    "qty": rec.qty,
                    "status": rec.status,
                    "cat": rec.cat,
                    "sup": rec.sup,
                }
            )

    def search(self) -> None:
        txt = self.var_search.get().strip().lower()
        self.product_Table.clear()
        for rec in self.db.products.values():
            if (
                txt in rec.pid.lower()
                or txt in rec.name.lower()
                or txt in rec.cat.lower()
                or txt in rec.sup.lower()
                or txt in rec.status.lower()
            ):
                self.product_Table.insert(
                    {
                        "pid": rec.pid,
                        "name": rec.name,
                        "price": rec.price,
                        "qty": rec.qty,
                        "status": rec.status,
                        "cat": rec.cat,
                        "sup": rec.sup,
                    }
                )

    def get_data(self, ev: Any) -> None:
        row = None
        if isinstance(ev, dict):
            row = ev
        elif isinstance(ev, int):
            self.product_Table.select(ev)
            row = self.product_Table.selected()
        if not isinstance(row, dict):
            raise ValueError("Invalid event data for get_data")
        pid = str(row.get("pid", "")).strip()
        if not pid:
            raise ValueError("Product ID missing")
        rec = self.db.products.get(pid)
        if rec is None:
            raise KeyError("Product not found")
        self.var_pid.set(rec.pid)
        self.var_pname.set(rec.name)
        self.var_price.set(str(rec.price))
        self.var_stock.set(str(rec.qty))
        self.lbl_inStock.config(text=str(rec.qty))

    def get_data_cart(self, ev: Any) -> None:
        row = None
        if isinstance(ev, dict):
            row = ev
        elif isinstance(ev, int):
            self.CartTable.select(ev)
            row = self.CartTable.selected()
        if not isinstance(row, dict):
            raise ValueError("Invalid event data for get_data_cart")
        self.var_pid.set(str(row.get("pid", "")))
        self.var_pname.set(str(row.get("pname", "")))
        self.var_price.set(str(row.get("price", "")))
        self.var_qty.set(str(row.get("qty", "")))
        self.var_stock.set(str(row.get("stock", "")))

    def show_cart(self) -> None:
        self.CartTable.clear()
        for row in self.cart_list:
            self.CartTable.insert(
                {
                    "pid": row["pid"],
                    "pname": row["pname"],
                    "price": row["price"],
                    "qty": row["qty"],
                    "stock": row.get("stock", 0),
                    "total": float(row["price"]) * int(row["qty"]),
                }
            )

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
        self.var_stock.set("")
        self.var_search.set("")
        self.txt_bill_area.clear()
        self.invoice = ""
        self.chk_print = 0
        self.discount = 0.0
        self.siscount = 0
        self.bill_amnt = 0
        self.net_pay = 0.0
        self.clear_cart()
        self.show()
        self.update_date_time()

    def add_update_cart(self) -> None:
        pid = self.var_pid.get().strip()
        if not pid:
            raise ValueError("Select a product")
        rec = self.db.products.get(pid)
        if rec is None:
            raise KeyError("Product not found")

        try:
            qty = int(self.var_qty.get().strip())
        except ValueError as e:
            raise ValueError("Invalid quantity") from e
        if qty <= 0:
            raise ValueError("Quantity must be greater than 0")
        if qty > rec.qty:
            raise ValueError("Quantity exceeds stock")

        price = float(rec.price)
        pname = rec.name
        stock = int(rec.qty)

        existing_index: Optional[int] = None
        for i, row in enumerate(self.cart_list):
            if str(row.get("pid")) == pid:
                existing_index = i
                break

        if existing_index is None:
            self.cart_list.append(
                {"pid": pid, "pname": pname, "price": price, "qty": qty, "stock": stock}
            )
        else:
            self.cart_list[existing_index] = {
                "pid": pid,
                "pname": pname,
                "price": price,
                "qty": qty,
                "stock": stock,
            }

        self.show_cart()
        self.bill_update()

    def bill_update(self) -> None:
        total = 0.0
        for item in self._cart_items():
            total += item.total
        self.bill_amnt = int(round(total))
        self.discount = float(self.siscount) if isinstance(self.siscount, int) else float(self.discount)
        if self.discount < 0:
            self.discount = 0.0
        net = total - self.discount
        if net < 0:
            net = 0.0
        self.net_pay = net
        self.lbl_amnt.config(text=f"{total:.2f}")
        self.lbl_discount.config(text=f"{self.discount:.2f}")
        self.lbl_net_pay.config(text=f"{net:.2f}")
        self.cartTitle.config(text=f"Cart ({len(self.cart_list)})")

    def generate_bill(self) -> str:
        cname = self.var_cname.get().strip()
        contact = self.var_contact.get().strip()
        if not cname:
            raise ValueError("Customer name is required")
        if not contact:
            raise ValueError("Customer contact is required")
        if not self.cart_list:
            raise ValueError("Cart is empty")

        if not self.invoice:
            self.invoice = self._new_invoice()

        for item in self._cart_items():
            rec = self.db.products.get(item.pid)
            if rec is None:
                raise KeyError(f"Product not found: {item.pid}")
            if item.qty > rec.qty:
                raise ValueError(f"Insufficient stock for product {item.pid}")

        for item in self._cart_items():
            rec = self.db.products[item.pid]
            self.db.products[item.pid] = ProductRecord(
                pid=rec.pid,
                name=rec.name,
                cat=rec.cat,
                sup=rec.sup,
                price=rec.price,
                qty=int(rec.qty) - int(item.qty),
                status=rec.status,
            )

        self.txt_bill_area.clear()
        self.bill_top()
        self.bill_middle()
        self.bill_bottom()

        self.bill_update()
        created_at = datetime.datetime.now()
        text = self.txt_bill_area.get()
        bill = BillRecord(
            invoice=self.invoice,
            customer_name=cname,
            contact=contact,
            items=self._cart_items(),
            bill_amount=float(self.bill_amnt),
            discount=float(self.discount),
            net_pay=float(self.net_pay),
            created_at=created_at,
            text=text,
        )
        self.db.sales[self.invoice] = bill
        self.chk_print = 1
        self.show()
        return self.invoice

    def print_bill(self) -> str:
        if not self.chk_print or not self.invoice:
            raise ValueError("No bill generated to print")
        rec = self.db.sales.get(self.invoice)
        if rec is None:
            raise KeyError("Invoice not found")
        return rec.text

    def update_date_time(self) -> None:
        now = datetime.datetime.now()
        self.lbl_clock.config(text=now.strftime("%Y-%m-%d %H:%M:%S"))

    def get_input(self, num: Union[int, str]) -> None:
        s = self.var_cal_input.get()
        self.var_cal_input.set(s + str(num))
        self.txt_cal_input.set(self.var_cal_input.get())

    def clear_cal(self) -> None:
        self.var_cal_input.set("")
        self.txt_cal_input.clear()

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
        if isinstance(result, (int, float)):
            self.var_cal_input.set(str(result))
            self.txt_cal_input.set(str(result))
        else:
            raise ValueError("Invalid expression result")

    def clear_all_calculated_discount(self) -> None:
        self.siscount = 0
        self.discount = 0.0
        self.bill_update()


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
        self.new_win: Toplevel = Toplevel(root=self.root)

        self._db = InMemoryDB()
        self._category: Optional[categoryClass] = None
        self._employee: Optional[employeeClass] = None
        self._product: Optional[productClass] = None
        self._sales: Optional[salesClass] = None
        self._supplier: Optional[supplierClass] = None

        self.update_content()

    def category(self) -> categoryClass:
        self._category = categoryClass(root=self.new_win, db=self._db)
        self.new_obj = self._category
        self._category.show()
        self.update_content()
        return self._category

    def employee(self) -> employeeClass:
        self._employee = employeeClass(root=self.new_win, db=self._db)
        self.new_obj = self._employee
        self._employee.show()
        self.update_content()
        return self._employee

    def product(self) -> productClass:
        self._product = productClass(root=self.new_win, db=self._db)
        self.new_obj = self._product
        self._product.fetch_cat_sup()
        self._product.show()
        self.update_content()
        return self._product

    def sales(self) -> salesClass:
        self._sales = salesClass(root=self.new_win, db=self._db)
        self.new_obj = self._sales
        self._sales.show()
        self.update_content()
        return self._sales

    def supplier(self) -> supplierClass:
        self._supplier = supplierClass(root=self.new_win, db=self._db)
        self.new_obj = self._supplier
        self._supplier.show()
        self.update_content()
        return self._supplier

    def update_content(self) -> None:
        self.lbl_category.config(text=str(len(self._db.categories)))
        self.lbl_supplier.config(text=str(len(self._db.suppliers)))
        self.lbl_employee.config(text=str(len(self._db.employees)))
        self.lbl_product.config(text=str(len(self._db.products)))
        self.lbl_sales.config(text=str(len(self._db.sales)))
        self.lbl_clock.config(text=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


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
    "Toplevel",
    "Treeview",
    "Listbox",
    "Text",
    "Entry",
    "StringVar",
]