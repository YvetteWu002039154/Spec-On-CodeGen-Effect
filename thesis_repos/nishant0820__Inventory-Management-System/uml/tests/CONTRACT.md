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

## Diagram fact → origin grounding

| Diagram fact | Origin evidence |
|---|---|
| `categoryClass/employeeClass/productClass/salesClass/supplierClass --* IMS : new_obj` | `dashboard.py::IMS.category/employee/product/sales/supplier` each do `self.new_obj = <Entity>Class(self.new_win)` |
| `IMS` navigation + `update_content()` | `dashboard.py::IMS` methods `category, employee, product, sales, supplier, update_content` |
| `categoryClass` methods | `category.py`: `add, clear, delete, get_data, show` |
| `supplierClass` methods | `supplier.py`: `add, clear, delete, get_data, search, show, update` |
| `employeeClass` methods | `employee.py`: `add, clear, delete, get_data, search, show, update` |
| `productClass` methods | `product.py`: `add, clear, delete, fetch_cat_sup, get_data, search, show, update` (`fetch_cat_sup` loads the category/supplier combolists) |
| `salesClass` methods | `sales.py`: `clear, get_data, search, show` |
| `billClass` methods (18) | `billing.py`: `add_update_cart, bill_bottom, bill_middle, bill_top, bill_update, clear_all, clear_cal, clear_cart, generate_bill, get_data, get_data_cart, get_input, perform_cal, print_bill, search, show, show_cart, update_date_time` |

## Facts pinned

### Composition (`--* : new_obj`)
- **U1. Composition targets present.** All five composed entity classes
  (`categoryClass`, `employeeClass`, `productClass`, `salesClass`,
  `supplierClass`) are defined.
- **U2. IMS navigation set.** `IMS` realizes the five `--*` links via the
  navigation methods `{category, employee, product, sales, supplier}`.
- **U3. IMS refresh.** `IMS` carries the dashboard method `update_content`.

### Methods under each entity box
- **U4. categoryClass.** Carries `{add, clear, delete, get_data, show}`.
- **U5. supplierClass.** Carries `{add, clear, delete, get_data, search, show, update}`.
- **U6. employeeClass.** Carries `{add, clear, delete, get_data, search, show, update}`.
- **U7. productClass.** Carries `{add, clear, delete, fetch_cat_sup, get_data,
  search, show, update}` (`fetch_cat_sup` is distinctive to product).
- **U8. salesClass.** Carries `{clear, get_data, search, show}`.

### billClass (the largest box)
- **U9. Full method set.** `billClass` carries its full 18-method operation set
  (see the grounding table).
- **U10. Embedded calculator.** `billClass` exposes the numeric-calculator trio
  `{get_input, perform_cal, clear_cal}` — the on-screen keypad distinctive to the
  billing screen.

All method checks are **superset** checks (`expected ⊆ defined`), so a generation
may add extra methods without penalty; only a *missing* listed method fails.

## Harness

The pinned surface is the **structure the class diagram draws** — class presence,
the method set under each box, and the five `entityClass --* IMS` composition
links (realized by `IMS`'s per-entity navigation methods) — asserted by
**reflection on the loaded classes** (class presence, method names), never by
executing behavior. A pinned method must be a **real (non-stub) implementation**: a body that is only `pass` / `...` / `return None` / `raise NotImplementedError` is judged statically (from source, never executed) as *not* implemented and fails the method set. A class a generation omits is a **FAILURE**, as is a class
present but missing a listed method. This track does not skip / mark N/A. Subjects are the
4 UML generations (`uml/outputcode/{claude,gpt,deepseek,gemini}`); the origin the
diagram was extracted from grounds the facts above but is not itself a test
subject.

## Portability

Class *definition* never touches the display or third-party image libraries
(those are used only inside `__init__`/handler bodies), so importing is
side-effect-free; `tkinter` (stdlib) stays real, and any missing heavy
third-party top (e.g. `PIL`) is resolved to a permissive stub. `_REF` is put on
`sys.path` so `dashboard.py`'s sibling imports resolve. Every module execs far
enough to *define* its classes with only the standard library required.
