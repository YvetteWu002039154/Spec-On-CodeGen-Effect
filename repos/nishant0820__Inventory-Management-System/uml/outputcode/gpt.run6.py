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

    def delete(self, start: int, end: Optional[int] = None) -> None:
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
        self._selection: Optional[int] = None

    def delete(self, start: int, end: Optional[int] = None) -> None:
        if end is None:
            if 0 <= start < len(self.items):
                del self.items[start]
                if self._selection == start:
                    self._selection = None
        else:
            if start < 0:
                start = 0
            if end >= len(self.items):
                end = len(self.items) - 1
            if start <= end and self.items:
                del self.items[start : end + 1]
                self._selection = None

    def insert(self, index: int, value: str) -> None:
        if index < 0 or index > len(self.items):
            self.items.append(value)
        else:
            self.items.insert(index, value)

    def curselection(self) -> Tuple[int, ...]:
        return () if self._selection is None else (self._selection,)

    def get(self, index: int) -> str:
        return self.items[index]

    def select_set(self, index: int) -> None:
        if 0 <= index < len(self.items):
            self._selection = index
        else:
            self._selection = None


class Treeview:
    def __init__(self) -> None:
        self._rows: List[Dict[str, Any]] = []
        self._selection: Optional[int] = None

    def insert(self, parent: str, index: str, values: Tuple[Any, ...]) -> str:
        row_id = str(len(self._rows))
        self._rows.append({"id": row_id, "values": values})
        return row_id

    def delete(self, item: str) -> None:
        idx = self._find_index(item)
        if idx is None:
            return
        del self._rows[idx]
        if self._selection == idx:
            self._selection = None

    def get_children(self) -> List[str]:
        return [r["id"] for r in self._rows]

    def item(self, item: str, option: str = "values") -> Any:
        idx = self._find_index(item)
        if idx is None:
            return None
        if option == "values":
            return self._rows[idx]["values"]
        return self._rows[idx].get(option)

    def selection(self) -> Tuple[str, ...]:
        if self._selection is None:
            return ()
        if 0 <= self._selection < len(self._rows):
            return (self._rows[self._selection]["id"],)
        return ()

    def selection_set(self, item: str) -> None:
        idx = self._find_index(item)
        self._selection = idx

    def clear(self) -> None:
        self._rows.clear()
        self._selection = None

    def _find_index(self, item: str) -> Optional[int]:
        for i, r in enumerate(self._rows):
            if r["id"] == item:
                return i
        return None


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


class Root:
    def __init__(self) -> None:
        self.title_text: str = ""

    def title(self, text: str) -> None:
        self.title_text = text


class _InMemoryDB:
    def __init__(self) -> None:
        self.categories: Dict[str, Dict[str, Any]] = {}
        self.suppliers: Dict[str, Dict[str, Any]] = {}
        self.employees: Dict[str, Dict[str, Any]] = {}
        self.products: Dict[str, Dict[str, Any]] = {}
        self.sales: Dict[str, Dict[str, Any]] = {}

    def reset(self) -> None:
        self.__init__()


_DB = _InMemoryDB()


def _now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _require_non_empty(value: str, field: str) -> None:
    if value is None or str(value).strip() == "":
        raise ValueError(f"{field} is required")


def _parse_int(value: str, field: str) -> int:
    _require_non_empty(value, field)
    try:
        iv = int(str(value).strip())
    except Exception as e:
        raise ValueError(f"{field} must be an integer") from e
    return iv


def _parse_float(value: str, field: str) -> float:
    _require_non_empty(value, field)
    try:
        fv = float(str(value).strip())
    except Exception as e:
        raise ValueError(f"{field} must be a number") from e
    return fv


def _normalize_key(value: str) -> str:
    return str(value).strip()


class category:
    class categoryClass:
        CategoryTable: Treeview
        im1: Union[None, PhotoImage]
        im2: Union[None, PhotoImage]
        lbl_im1: Label
        lbl_im2: Label
        root: Any
        var_cat_id: StringVar
        var_name: StringVar

        def __init__(self, root: Any = None) -> None:
            self.root = root
            self.CategoryTable = Treeview()
            self.im1 = None
            self.im2 = None
            self.lbl_im1 = Label()
            self.lbl_im2 = Label()
            self.var_cat_id = StringVar()
            self.var_name = StringVar()

        def add(self) -> None:
            cat_id = _normalize_key(self.var_cat_id.get())
            name = _normalize_key(self.var_name.get())
            _require_non_empty(cat_id, "Category ID")
            _require_non_empty(name, "Category Name")
            if cat_id in _DB.categories:
                raise ValueError("Category ID already exists")
            _DB.categories[cat_id] = {"cat_id": cat_id, "name": name}
            self.show()

        def clear(self) -> None:
            self.var_cat_id.set("")
            self.var_name.set("")
            self.CategoryTable.clear()

        def delete(self) -> None:
            cat_id = _normalize_key(self.var_cat_id.get())
            _require_non_empty(cat_id, "Category ID")
            if cat_id not in _DB.categories:
                raise ValueError("Category not found")
            for p in _DB.products.values():
                if p.get("cat") == cat_id:
                    raise ValueError("Cannot delete category referenced by products")
            del _DB.categories[cat_id]
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
            for cat_id in sorted(_DB.categories.keys()):
                c = _DB.categories[cat_id]
                self.CategoryTable.insert("", "end", (c["cat_id"], c["name"]))


class supplier:
    class supplierClass:
        SupplierTable: Treeview
        root: Any
        txt_desc: Text
        var_contact: StringVar
        var_name: StringVar
        var_searchby: StringVar
        var_searchtxt: StringVar
        var_sup_invoice: StringVar

        def __init__(self, root: Any = None) -> None:
            self.root = root
            self.SupplierTable = Treeview()
            self.txt_desc = Text()
            self.var_contact = StringVar()
            self.var_name = StringVar()
            self.var_searchby = StringVar()
            self.var_searchtxt = StringVar()
            self.var_sup_invoice = StringVar()

        def add(self) -> None:
            sup_invoice = _normalize_key(self.var_sup_invoice.get())
            name = _normalize_key(self.var_name.get())
            contact = _normalize_key(self.var_contact.get())
            desc = self.txt_desc.get().strip()
            _require_non_empty(sup_invoice, "Supplier Invoice")
            _require_non_empty(name, "Supplier Name")
            _require_non_empty(contact, "Supplier Contact")
            if sup_invoice in _DB.suppliers:
                raise ValueError("Supplier invoice already exists")
            _DB.suppliers[sup_invoice] = {
                "sup_invoice": sup_invoice,
                "name": name,
                "contact": contact,
                "desc": desc,
            }
            self.show()

        def clear(self) -> None:
            self.var_sup_invoice.set("")
            self.var_name.set("")
            self.var_contact.set("")
            self.var_searchby.set("")
            self.var_searchtxt.set("")
            self.txt_desc.delete()
            self.SupplierTable.clear()

        def delete(self) -> None:
            sup_invoice = _normalize_key(self.var_sup_invoice.get())
            _require_non_empty(sup_invoice, "Supplier Invoice")
            if sup_invoice not in _DB.suppliers:
                raise ValueError("Supplier not found")
            for p in _DB.products.values():
                if p.get("sup") == sup_invoice:
                    raise ValueError("Cannot delete supplier referenced by products")
            del _DB.suppliers[sup_invoice]
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
            self.txt_desc.delete()
            self.txt_desc.insert("1.0", str(values[3]))

        def search(self) -> None:
            by = _normalize_key(self.var_searchby.get()).lower()
            txt = _normalize_key(self.var_searchtxt.get()).lower()
            if by not in {"sup_invoice", "name", "contact"}:
                raise ValueError("Invalid search field")
            self.SupplierTable.clear()
            for s in _DB.suppliers.values():
                val = str(s.get(by, "")).lower()
                if txt in val:
                    self.SupplierTable.insert("", "end", (s["sup_invoice"], s["name"], s["contact"], s["desc"]))

        def show(self) -> None:
            self.SupplierTable.clear()
            for sup_invoice in sorted(_DB.suppliers.keys()):
                s = _DB.suppliers[sup_invoice]
                self.SupplierTable.insert("", "end", (s["sup_invoice"], s["name"], s["contact"], s["desc"]))

        def update(self) -> None:
            sup_invoice = _normalize_key(self.var_sup_invoice.get())
            _require_non_empty(sup_invoice, "Supplier Invoice")
            if sup_invoice not in _DB.suppliers:
                raise ValueError("Supplier not found")
            name = _normalize_key(self.var_name.get())
            contact = _normalize_key(self.var_contact.get())
            desc = self.txt_desc.get().strip()
            _require_non_empty(name, "Supplier Name")
            _require_non_empty(contact, "Supplier Contact")
            _DB.suppliers[sup_invoice].update({"name": name, "contact": contact, "desc": desc})
            self.show()


class employee:
    class employeeClass:
        EmployeeTable: Treeview
        root: Any
        txt_address: Text
        var_contact: StringVar
        var_dob: StringVar
        var_doj: StringVar
        var_email: StringVar
        var_emp_id: StringVar
        var_gender: StringVar
        var_name: StringVar
        var_pass: StringVar
        var_salary: StringVar
        var_searchby: StringVar
        var_searchtxt: StringVar
        var_utype: StringVar

        def __init__(self, root: Any = None) -> None:
            self.root = root
            self.EmployeeTable = Treeview()
            self.txt_address = Text()
            self.var_contact = StringVar()
            self.var_dob = StringVar()
            self.var_doj = StringVar()
            self.var_email = StringVar()
            self.var_emp_id = StringVar()
            self.var_gender = StringVar()
            self.var_name = StringVar()
            self.var_pass = StringVar()
            self.var_salary = StringVar()
            self.var_searchby = StringVar()
            self.var_searchtxt = StringVar()
            self.var_utype = StringVar()

        def add(self) -> None:
            emp_id = _normalize_key(self.var_emp_id.get())
            name = _normalize_key(self.var_name.get())
            email = _normalize_key(self.var_email.get())
            contact = _normalize_key(self.var_contact.get())
            gender = _normalize_key(self.var_gender.get())
            dob = _normalize_key(self.var_dob.get())
            doj = _normalize_key(self.var_doj.get())
            utype = _normalize_key(self.var_utype.get())
            password = self.var_pass.get()
            salary = _normalize_key(self.var_salary.get())
            address = self.txt_address.get().strip()

            _require_non_empty(emp_id, "Employee ID")
            _require_non_empty(name, "Employee Name")
            _require_non_empty(email, "Employee Email")
            _require_non_empty(contact, "Employee Contact")
            _require_non_empty(utype, "User Type")
            _require_non_empty(password, "Password")
            _require_non_empty(salary, "Salary")

            _ = _parse_float(salary, "Salary")

            if emp_id in _DB.employees:
                raise ValueError("Employee ID already exists")

            _DB.employees[emp_id] = {
                "emp_id": emp_id,
                "name": name,
                "email": email,
                "contact": contact,
                "gender": gender,
                "dob": dob,
                "doj": doj,
                "utype": utype,
                "pass": password,
                "salary": salary,
                "address": address,
            }
            self.show()

        def clear(self) -> None:
            self.var_emp_id.set("")
            self.var_name.set("")
            self.var_email.set("")
            self.var_contact.set("")
            self.var_gender.set("")
            self.var_dob.set("")
            self.var_doj.set("")
            self.var_utype.set("")
            self.var_pass.set("")
            self.var_salary.set("")
            self.var_searchby.set("")
            self.var_searchtxt.set("")
            self.txt_address.delete()
            self.EmployeeTable.clear()

        def delete(self) -> None:
            emp_id = _normalize_key(self.var_emp_id.get())
            _require_non_empty(emp_id, "Employee ID")
            if emp_id not in _DB.employees:
                raise ValueError("Employee not found")
            del _DB.employees[emp_id]
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
                contact,
                gender,
                dob,
                doj,
                utype,
                password,
                salary,
                address,
            ) = values
            self.var_emp_id.set(str(emp_id))
            self.var_name.set(str(name))
            self.var_email.set(str(email))
            self.var_contact.set(str(contact))
            self.var_gender.set(str(gender))
            self.var_dob.set(str(dob))
            self.var_doj.set(str(doj))
            self.var_utype.set(str(utype))
            self.var_pass.set(str(password))
            self.var_salary.set(str(salary))
            self.txt_address.delete()
            self.txt_address.insert("1.0", str(address))

        def search(self) -> None:
            by = _normalize_key(self.var_searchby.get()).lower()
            txt = _normalize_key(self.var_searchtxt.get()).lower()
            if by not in {"emp_id", "name", "email", "contact", "utype"}:
                raise ValueError("Invalid search field")
            self.EmployeeTable.clear()
            for e in _DB.employees.values():
                val = str(e.get(by, "")).lower()
                if txt in val:
                    self.EmployeeTable.insert(
                        "",
                        "end",
                        (
                            e["emp_id"],
                            e["name"],
                            e["email"],
                            e["contact"],
                            e["gender"],
                            e["dob"],
                            e["doj"],
                            e["utype"],
                            e["pass"],
                            e["salary"],
                            e["address"],
                        ),
                    )

        def show(self) -> None:
            self.EmployeeTable.clear()
            for emp_id in sorted(_DB.employees.keys()):
                e = _DB.employees[emp_id]
                self.EmployeeTable.insert(
                    "",
                    "end",
                    (
                        e["emp_id"],
                        e["name"],
                        e["email"],
                        e["contact"],
                        e["gender"],
                        e["dob"],
                        e["doj"],
                        e["utype"],
                        e["pass"],
                        e["salary"],
                        e["address"],
                    ),
                )

        def update(self) -> None:
            emp_id = _normalize_key(self.var_emp_id.get())
            _require_non_empty(emp_id, "Employee ID")
            if emp_id not in _DB.employees:
                raise ValueError("Employee not found")

            name = _normalize_key(self.var_name.get())
            email = _normalize_key(self.var_email.get())
            contact = _normalize_key(self.var_contact.get())
            gender = _normalize_key(self.var_gender.get())
            dob = _normalize_key(self.var_dob.get())
            doj = _normalize_key(self.var_doj.get())
            utype = _normalize_key(self.var_utype.get())
            password = self.var_pass.get()
            salary = _normalize_key(self.var_salary.get())
            address = self.txt_address.get().strip()

            _require_non_empty(name, "Employee Name")
            _require_non_empty(email, "Employee Email")
            _require_non_empty(contact, "Employee Contact")
            _require_non_empty(utype, "User Type")
            _require_non_empty(password, "Password")
            _require_non_empty(salary, "Salary")
            _ = _parse_float(salary, "Salary")

            _DB.employees[emp_id].update(
                {
                    "name": name,
                    "email": email,
                    "contact": contact,
                    "gender": gender,
                    "dob": dob,
                    "doj": doj,
                    "utype": utype,
                    "pass": password,
                    "salary": salary,
                    "address": address,
                }
            )
            self.show()


class product:
    class productClass:
        ProductTable: Treeview
        cat_list: list
        root: Any
        sup_list: list
        var_cat: StringVar
        var_name: StringVar
        var_pid: StringVar
        var_price: StringVar
        var_qty: StringVar
        var_searchby: StringVar
        var_searchtxt: StringVar
        var_status: StringVar
        var_sup: StringVar

        def __init__(self, root: Any = None) -> None:
            self.root = root
            self.ProductTable = Treeview()
            self.cat_list = []
            self.sup_list = []
            self.var_cat = StringVar()
            self.var_name = StringVar()
            self.var_pid = StringVar()
            self.var_price = StringVar()
            self.var_qty = StringVar()
            self.var_searchby = StringVar()
            self.var_searchtxt = StringVar()
            self.var_status = StringVar()
            self.var_sup = StringVar()
            self.fetch_cat_sup()

        def fetch_cat_sup(self) -> None:
            self.cat_list = sorted(_DB.categories.keys())
            self.sup_list = sorted(_DB.suppliers.keys())

        def add(self) -> None:
            pid = _normalize_key(self.var_pid.get())
            name = _normalize_key(self.var_name.get())
            cat = _normalize_key(self.var_cat.get())
            sup = _normalize_key(self.var_sup.get())
            price_s = _normalize_key(self.var_price.get())
            qty_s = _normalize_key(self.var_qty.get())
            status = _normalize_key(self.var_status.get())

            _require_non_empty(pid, "Product ID")
            _require_non_empty(name, "Product Name")
            _require_non_empty(cat, "Category")
            _require_non_empty(sup, "Supplier")
            _require_non_empty(price_s, "Price")
            _require_non_empty(qty_s, "Quantity")
            _require_non_empty(status, "Status")

            if pid in _DB.products:
                raise ValueError("Product ID already exists")
            if cat not in _DB.categories:
                raise ValueError("Category not found")
            if sup not in _DB.suppliers:
                raise ValueError("Supplier not found")

            price = _parse_float(price_s, "Price")
            qty = _parse_int(qty_s, "Quantity")
            if price < 0:
                raise ValueError("Price cannot be negative")
            if qty < 0:
                raise ValueError("Quantity cannot be negative")

            _DB.products[pid] = {
                "pid": pid,
                "name": name,
                "cat": cat,
                "sup": sup,
                "price": float(price),
                "qty": int(qty),
                "status": status,
            }
            self.fetch_cat_sup()
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
            pid = _normalize_key(self.var_pid.get())
            _require_non_empty(pid, "Product ID")
            if pid not in _DB.products:
                raise ValueError("Product not found")
            del _DB.products[pid]
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
            by = _normalize_key(self.var_searchby.get()).lower()
            txt = _normalize_key(self.var_searchtxt.get()).lower()
            if by not in {"pid", "name", "cat", "sup", "status"}:
                raise ValueError("Invalid search field")
            self.ProductTable.clear()
            for p in _DB.products.values():
                val = str(p.get(by, "")).lower()
                if txt in val:
                    self.ProductTable.insert(
                        "",
                        "end",
                        (p["pid"], p["name"], p["cat"], p["sup"], p["price"], p["qty"], p["status"]),
                    )

        def show(self) -> None:
            self.ProductTable.clear()
            for pid in sorted(_DB.products.keys()):
                p = _DB.products[pid]
                self.ProductTable.insert(
                    "",
                    "end",
                    (p["pid"], p["name"], p["cat"], p["sup"], p["price"], p["qty"], p["status"]),
                )

        def update(self) -> None:
            pid = _normalize_key(self.var_pid.get())
            _require_non_empty(pid, "Product ID")
            if pid not in _DB.products:
                raise ValueError("Product not found")

            name = _normalize_key(self.var_name.get())
            cat = _normalize_key(self.var_cat.get())
            sup = _normalize_key(self.var_sup.get())
            price_s = _normalize_key(self.var_price.get())
            qty_s = _normalize_key(self.var_qty.get())
            status = _normalize_key(self.var_status.get())

            _require_non_empty(name, "Product Name")
            _require_non_empty(cat, "Category")
            _require_non_empty(sup, "Supplier")
            _require_non_empty(price_s, "Price")
            _require_non_empty(qty_s, "Quantity")
            _require_non_empty(status, "Status")

            if cat not in _DB.categories:
                raise ValueError("Category not found")
            if sup not in _DB.suppliers:
                raise ValueError("Supplier not found")

            price = _parse_float(price_s, "Price")
            qty = _parse_int(qty_s, "Quantity")
            if price < 0:
                raise ValueError("Price cannot be negative")
            if qty < 0:
                raise ValueError("Quantity cannot be negative")

            _DB.products[pid].update(
                {"name": name, "cat": cat, "sup": sup, "price": float(price), "qty": int(qty), "status": status}
            )
            self.fetch_cat_sup()
            self.show()


class sales:
    class salesClass:
        Sales_List: Listbox
        bill_area: Text
        bill_photo: Union[None, PhotoImage]
        blll_list: list
        root: Any
        var_invoice: StringVar

        def __init__(self, root: Any = None) -> None:
            self.root = root
            self.Sales_List = Listbox()
            self.bill_area = Text()
            self.bill_photo = None
            self.blll_list = []
            self.var_invoice = StringVar()

        def clear(self) -> None:
            self.var_invoice.set("")
            self.bill_area.delete()
            self.Sales_List.delete(0, len(self.Sales_List.items) - 1 if self.Sales_List.items else 0)
            self.blll_list = []

        def get_data(self, ev: Any) -> None:
            sel = self.Sales_List.curselection()
            if not sel:
                return
            invoice = self.Sales_List.get(sel[0])
            self.var_invoice.set(invoice)
            rec = _DB.sales.get(invoice)
            self.bill_area.delete()
            if rec:
                self.bill_area.insert("1.0", rec.get("bill_text", ""))

        def search(self) -> None:
            invoice = _normalize_key(self.var_invoice.get())
            _require_non_empty(invoice, "Invoice")
            self.Sales_List.delete(0, len(self.Sales_List.items) - 1 if self.Sales_List.items else 0)
            self.blll_list = []
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


class billing:
    @dataclass
    class _CartItem:
        pid: str
        pname: str
        price: float
        qty: int
        stock: int

        @property
        def amount(self) -> float:
            return float(self.price) * int(self.qty)

    class billClass:
        CartTable: Treeview
        bill_amnt: int
        cartTitle: Label
        cart_list: list
        chk_print: int
        discount: float
        icon_title: PhotoImage
        invoice: Any
        lbl_amnt: Label
        lbl_clock: Label
        lbl_discount: Label
        lbl_inStock: Label
        lbl_net_pay: Label
        net_pay: Union[float, int]
        product_Table: Treeview
        root: Any
        siscount: int
        txt_bill_area: Text
        txt_cal_input: Entry
        var_cal_input: StringVar
        var_cname: StringVar
        var_contact: StringVar
        var_pid: StringVar
        var_pname: StringVar
        var_price: StringVar
        var_qty: StringVar
        var_search: StringVar
        var_stock: StringVar

        _invoice_counter = itertools.count(1)

        def __init__(self, root: Any = None) -> None:
            self.root = root
            self.CartTable = Treeview()
            self.product_Table = Treeview()
            self.bill_amnt = 0
            self.net_pay = 0
            self.discount = 0.0
            self.siscount = 0
            self.chk_print = 0
            self.invoice = None
            self.icon_title = PhotoImage()
            self.cartTitle = Label()
            self.lbl_amnt = Label()
            self.lbl_clock = Label()
            self.lbl_discount = Label()
            self.lbl_inStock = Label()
            self.lbl_net_pay = Label()
            self.txt_bill_area = Text()
            self.txt_cal_input = Entry()
            self.var_cal_input = StringVar()
            self.var_cname = StringVar()
            self.var_contact = StringVar()
            self.var_pid = StringVar()
            self.var_pname = StringVar()
            self.var_price = StringVar()
            self.var_qty = StringVar()
            self.var_search = StringVar()
            self.var_stock = StringVar()
            self.cart_list: List[billing._CartItem] = []
            self.show()
            self.show_cart()
            self.update_date_time()

        def bill_top(self) -> None:
            cname = _normalize_key(self.var_cname.get())
            contact = _normalize_key(self.var_contact.get())
            if self.invoice is None:
                self.invoice = f"INV{next(self._invoice_counter):06d}"
            header = [
                "Inventory Management System - Invoice",
                f"Invoice: {self.invoice}",
                f"Date: {_now_str()}",
                f"Customer: {cname}",
                f"Contact: {contact}",
                "-" * 40,
                f"{'PID':<8}{'Name':<16}{'Qty':>5}{'Price':>8}{'Amt':>8}",
                "-" * 40,
            ]
            self.txt_bill_area.delete()
            self.txt_bill_area.insert("1.0", "\n".join(header) + "\n")

        def bill_middle(self) -> None:
            for item in self.cart_list:
                line = f"{item.pid:<8}{item.pname[:16]:<16}{item.qty:>5}{item.price:>8.2f}{item.amount:>8.2f}"
                self.txt_bill_area.insert("end", line + "\n")

        def bill_bottom(self) -> None:
            self.bill_update()
            footer = [
                "-" * 40,
                f"Bill Amount: {float(self.bill_amnt):.2f}",
                f"Discount: {float(self.discount):.2f}",
                f"Net Pay: {float(self.net_pay):.2f}",
                "-" * 40,
            ]
            self.txt_bill_area.insert("end", "\n".join(footer) + "\n")

        def bill_update(self) -> None:
            total = sum(ci.amount for ci in self.cart_list)
            self.bill_amnt = int(round(total))
            disc = float(self.discount) if self.discount is not None else 0.0
            if disc < 0:
                raise ValueError("Discount cannot be negative")
            net = total - disc
            if net < 0:
                net = 0.0
            self.net_pay = net
            self.lbl_amnt.config(text=str(float(total)))
            self.lbl_discount.config(text=str(float(disc)))
            self.lbl_net_pay.config(text=str(float(net)))

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
            self.chk_print = 0
            self.invoice = None
            self.txt_bill_area.delete()
            self.show()
            self.update_date_time()

        def clear_cal(self) -> None:
            self.var_cal_input.set("")
            self.txt_cal_input.delete(0, None)

        def clear_cart(self) -> None:
            self.cart_list = []
            self.CartTable.clear()
            self.bill_update()

        def show(self) -> None:
            self.product_Table.clear()
            for pid in sorted(_DB.products.keys()):
                p = _DB.products[pid]
                self.product_Table.insert(
                    "",
                    "end",
                    (p["pid"], p["name"], p["price"], p["qty"], p["status"], p["cat"], p["sup"]),
                )

        def search(self) -> None:
            txt = _normalize_key(self.var_search.get()).lower()
            self.product_Table.clear()
            for p in _DB.products.values():
                if txt in p["pid"].lower() or txt in p["name"].lower():
                    self.product_Table.insert(
                        "",
                        "end",
                        (p["pid"], p["name"], p["price"], p["qty"], p["status"], p["cat"], p["sup"]),
                    )

        def get_data(self, ev: Any) -> None:
            sel = self.product_Table.selection()
            if not sel:
                return
            values = self.product_Table.item(sel[0], "values")
            if not values:
                return
            pid, name, price, qty, status, cat, sup = values
            self.var_pid.set(str(pid))
            self.var_pname.set(str(name))
            self.var_price.set(str(price))
            self.var_stock.set(str(qty))
            self.lbl_inStock.config(text=str(qty))

        def show_cart(self) -> None:
            self.CartTable.clear()
            for ci in self.cart_list:
                self.CartTable.insert("", "end", (ci.pid, ci.pname, ci.price, ci.qty, ci.amount))
            self.bill_update()

        def get_data_cart(self, ev: Any) -> None:
            sel = self.CartTable.selection()
            if not sel:
                return
            values = self.CartTable.item(sel[0], "values")
            if not values:
                return
            pid, pname, price, qty, amt = values
            self.var_pid.set(str(pid))
            self.var_pname.set(str(pname))
            self.var_price.set(str(price))
            self.var_qty.set(str(qty))
            p = _DB.products.get(str(pid))
            if p:
                self.var_stock.set(str(p["qty"]))
                self.lbl_inStock.config(text=str(p["qty"]))

        def add_update_cart(self) -> None:
            pid = _normalize_key(self.var_pid.get())
            _require_non_empty(pid, "Product ID")
            if pid not in _DB.products:
                raise ValueError("Product not found")

            p = _DB.products[pid]
            pname = _normalize_key(self.var_pname.get()) or str(p["name"])
            price = _parse_float(self.var_price.get() or str(p["price"]), "Price")
            qty = _parse_int(self.var_qty.get(), "Quantity")
            if qty <= 0:
                raise ValueError("Quantity must be greater than zero")

            stock = int(p["qty"])
            if qty > stock:
                raise ValueError("Quantity exceeds stock")

            existing = next((ci for ci in self.cart_list if ci.pid == pid), None)
            if existing is None:
                self.cart_list.append(billing._CartItem(pid=pid, pname=pname, price=float(price), qty=int(qty), stock=stock))
            else:
                new_qty = existing.qty + int(qty)
                if new_qty > stock:
                    raise ValueError("Quantity exceeds stock")
                existing.qty = new_qty
                existing.price = float(price)
                existing.pname = pname
                existing.stock = stock

            self.show_cart()

        def generate_bill(self) -> None:
            if not self.cart_list:
                raise ValueError("Cart is empty")
            if self.invoice is None:
                self.invoice = f"INV{next(self._invoice_counter):06d}"
            self.bill_top()
            self.bill_middle()
            self.bill_bottom()
            self.chk_print = 1
            _DB.sales[self.invoice] = {
                "invoice": self.invoice,
                "created_at": _now_str(),
                "customer_name": _normalize_key(self.var_cname.get()),
                "customer_contact": _normalize_key(self.var_contact.get()),
                "bill_amount": float(sum(ci.amount for ci in self.cart_list)),
                "discount": float(self.discount),
                "net_pay": float(self.net_pay),
                "items": [
                    {"pid": ci.pid, "pname": ci.pname, "price": ci.price, "qty": ci.qty, "amount": ci.amount}
                    for ci in self.cart_list
                ],
                "bill_text": self.txt_bill_area.get(),
            }
            for ci in self.cart_list:
                _DB.products[ci.pid]["qty"] = int(_DB.products[ci.pid]["qty"]) - int(ci.qty)
            self.show()

        def print_bill(self) -> None:
            if not self.chk_print or self.invoice is None:
                raise ValueError("No bill generated to print")
            if self.invoice not in _DB.sales:
                raise ValueError("Invoice not found")
            self.chk_print = 2

        def update_date_time(self) -> None:
            self.lbl_clock.config(text=_now_str())

        def get_input(self, num: Union[int, str]) -> None:
            s = self.var_cal_input.get()
            s += str(num)
            self.var_cal_input.set(s)
            self.txt_cal_input.insert(0, self.var_cal_input.get())

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
                raise ValueError("Invalid expression") from e
            self.var_cal_input.set(str(result))
            self.txt_cal_input.delete(0, None)
            self.txt_cal_input.insert(0, str(result))


class dashboard:
    class IMS:
        MenuLogo: Union[None, PhotoImage]
        icon_side: PhotoImage
        icon_title: PhotoImage
        lbl_category: Label
        lbl_clock: Label
        lbl_employee: Label
        lbl_product: Label
        lbl_sales: Label
        lbl_supplier: Label
        new_obj: Any
        new_win: Toplevel
        root: Any

        def __init__(self, root: Any = None) -> None:
            self.root = root if root is not None else Root()
            self.MenuLogo = None
            self.icon_side = PhotoImage()
            self.icon_title = PhotoImage()
            self.lbl_category = Label()
            self.lbl_clock = Label()
            self.lbl_employee = Label()
            self.lbl_product = Label()
            self.lbl_sales = Label()
            self.lbl_supplier = Label()
            self.new_obj = None
            self.new_win = Toplevel(self.root)
            self.update_content()

        def category(self) -> category.categoryClass:
            self.new_win = Toplevel(self.root)
            self.new_obj = category.categoryClass(self.new_win)
            return self.new_obj

        def employee(self) -> employee.employeeClass:
            self.new_win = Toplevel(self.root)
            self.new_obj = employee.employeeClass(self.new_win)
            return self.new_obj

        def product(self) -> product.productClass:
            self.new_win = Toplevel(self.root)
            self.new_obj = product.productClass(self.new_win)
            return self.new_obj

        def sales(self) -> sales.salesClass:
            self.new_win = Toplevel(self.root)
            self.new_obj = sales.salesClass(self.new_win)
            return self.new_obj

        def supplier(self) -> supplier.supplierClass:
            self.new_win = Toplevel(self.root)
            self.new_obj = supplier.supplierClass(self.new_win)
            return self.new_obj

        def update_content(self) -> None:
            self.lbl_category.config(text=str(len(_DB.categories)))
            self.lbl_supplier.config(text=str(len(_DB.suppliers)))
            self.lbl_employee.config(text=str(len(_DB.employees)))
            self.lbl_product.config(text=str(len(_DB.products)))
            self.lbl_sales.config(text=str(len(_DB.sales)))
            self.lbl_clock.config(text=_now_str())