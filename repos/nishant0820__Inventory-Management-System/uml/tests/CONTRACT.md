# Structural contract — `Inventory-Management-System` **UML track**

Reference: the origin app `Inventory-Management-System-main/` — the seven
per-entity modules the class diagram was extracted from (`dashboard.IMS`,
`billing.billClass`, `category.categoryClass`, `employee.employeeClass`,
`product.productClass`, `sales.salesClass`, `supplier.supplierClass`).

This contract is derived from the **UML class diagram**
(`uml/input/classes.puml`, a pyreverse extraction) and grounded in that origin
code. A class diagram records *structure*, not runtime behavior. For this
Tkinter app the diagram's structural content is:

1. **Class presence** — the seven boxes.
2. **Methods under a class** — the operations listed inside each box.
3. **Composition links** — `entityClass --* IMS : new_obj` (five of them).

The composition links carry no type annotation in the origin (`new_obj` is
assigned inside `IMS.category()` etc.), so each `--*` link is realized
structurally by **`IMS` defining a navigation method per composed entity**
(`category/employee/product/sales/supplier`, each of which opens the entity window
and stores it in `new_obj`). The diagram draws **no inheritance links** (`--|>`)
and **no annotated associations** (`-->`), so those are not pinned.

## Facts pinned

| # | Diagram fact | Origin evidence |
|---|---|---|
| U1 | `categoryClass/employeeClass/productClass/salesClass/supplierClass --* IMS : new_obj` | `dashboard.py::IMS.category/employee/product/sales/supplier` each do `self.new_obj = <Entity>Class(self.new_win)` |
| U2 | `IMS` navigation + `update_content()` — IMS navigation set | `dashboard.py::IMS` methods `category, employee, product, sales, supplier, update_content` |
| U3 | `IMS` navigation + `update_content()` — IMS refresh | `dashboard.py::IMS` methods `category, employee, product, sales, supplier, update_content` |
| U4 | `categoryClass` methods | `category.py`: `add, clear, delete, get_data, show` |
| U5 | `supplierClass` methods | `supplier.py`: `add, clear, delete, get_data, search, show, update` |
| U6 | `employeeClass` methods | `employee.py`: `add, clear, delete, get_data, search, show, update` |
| U7 | `productClass` methods | `product.py`: `add, clear, delete, fetch_cat_sup, get_data, search, show, update` (`fetch_cat_sup` loads the category/supplier combolists) |
| U8 | `salesClass` methods | `sales.py`: `clear, get_data, search, show` |
| U9 | `billClass` methods (18) — Full method set | `billing.py`: `add_update_cart, bill_bottom, bill_middle, bill_top, bill_update, clear_all, clear_cal, clear_cart, generate_bill, get_data, get_data_cart, get_input, perform_cal, print_bill, search, show, show_cart, update_date_time` |
| U10 | `billClass` methods (18) — Embedded calculator | `billing.py`: `add_update_cart, bill_bottom, bill_middle, bill_top, bill_update, clear_all, clear_cal, clear_cart, generate_bill, get_data, get_data_cart, get_input, perform_cal, print_bill, search, show, show_cart, update_date_time` |