# Behavioral contract — `Inventory-Management-System` **NL track**

Subjects: the 4 NL generations (`nl/outputcode/{claude,gpt,deepseek,gemini}`).
**No reference** is loaded in the NL track — expected behavior is derived by
comparing the **NL description** (`nl/input/description.txt`) with the **origin
code** (`Inventory-Management-System-main/`), then pinning the observable
persistence behaviors every reasonable implementation of that description would
expose.

The origin is a Tkinter desktop app; its behavior lives in the per-entity GUI
event handlers as SQLite operations that read `self.var_*` StringVars and
signal outcome through `messagebox.showinfo` (accepted) / `messagebox.showerror`
(rejected). The windowing, images, `Treeview` rendering and clock are
presentation plumbing and out of scope. Behaviors are asserted on the
**observable record count** (does the record exist afterwards?), never on a
return value. **Rejection** is any of: an exception, or an error dialog with no
success dialog.

Each generation is driven by its own explicit driver (`adapter.py`) that names
the concrete classes and methods that generation actually uses to add / delete a
Category and a Supplier. There is **no skip and no N/A**: a capability a
generation does not expose as a drivable persistence path is exercised through
its real entry point and the resulting empty / raising / wrong result is a
behavioral **FAILURE** (distinct only in cause from a capability that is present
but behaves wrong).

The pinned behaviors are the persistence semantics of the two simplest, FK-free
entities the description calls out — **Category** ("information about the
category of the product") and **Supplier** ("data regarding suppliers").

## Description feature → origin grounding

| Description feature | Origin evidence |
|---|---|
| "shows the information about the category of the product" | `category.py::categoryClass.add` inserts into `category(name)`; requires `name`; rejects duplicate `name` |
| category removal | `category.py::categoryClass.delete` deletes by `cid`; rejects empty / unknown id (via a `Select … where cid=?` existence check) |
| "data regarding suppliers" | `supplier.py::supplierClass.add` inserts into `supplier(invoice,name,contact,desc)`; requires `invoice`; rejects duplicate `invoice` |
| supplier removal | `supplier.py::supplierClass.delete` deletes by `invoice`; rejects empty / unknown id |
| database via sqlite3 | every handler `sqlite3.connect('ims.db')` — persistence is the observable effect |

## Behaviors pinned

### Category
- **C1. Add persists.** Adding a valid category persists exactly one record.
- **C2. Empty name rejected.** Adding a category with an empty **name** is
  rejected (nothing persisted).
- **C3. Duplicate rejected.** Adding a **duplicate** category is rejected (still
  one record).
- **C4. Delete removes.** Deleting an existing category removes it (count
  returns to zero).
- **C5. Delete unknown rejected.** Deleting a **non-existent** category is
  rejected.

### Supplier
- **S1. Add persists.** Adding a valid supplier persists exactly one record.
- **S2. Missing invoice rejected.** Adding a supplier without its **invoice/id**
  is rejected (nothing persisted).
- **S3. Duplicate rejected.** Adding a **duplicate** supplier (same invoice) is
  rejected (still one record).
- **S4. Delete removes.** Deleting an existing supplier removes it (count
  returns to zero).
- **S5. Delete unknown rejected.** Deleting a **non-existent** supplier is
  rejected.

## Notes for the adapter

- Each generation has one explicit driver naming the concrete API it uses:
  - **gpt** — a clean repository layer: `Database` + `CategoryRepository` /
    `SupplierRepository` over frozen `Category` / `Supplier` dataclasses.
  - **gemini** — origin-style `var_`-driven handlers `CategoryClass.add`/`.delete`
    and `SupplierClass.add`/`.delete`, invoked by binding the handler to a form
    object (StringVar / Text / Treeview fakes) with `messagebox` patched, in a
    private temp cwd that isolates the hard-coded `ims.db`.
  - **claude** — category/supplier persistence lives only on `tk.Toplevel`
    windows (`CategoryWindow.add_category`, `SupplierWindow.add_supplier`, ...);
    the driver builds the real window, which cannot be constructed headlessly.
  - **deepseek** — one monolithic `InventoryManagementApp` whose add/delete are
    nested local closures inside `create_management_window`; there is no callable
    per-entity handler, so the driver drives the real `open_category_window` /
    `open_supplier_window` entry point.
- The record count is read from the `category`/`supplier`/`categories`/`suppliers`
  table of the SQLite file the generation writes, or through its repository's
  `list_all()`. `delete_removes` first seeds a record and only reports 0 if that
  seed succeeded, so it can never pass by vacuously observing an empty store.
- The origin's `supplier.invoice` is an INTEGER primary key, so a numeric invoice
  is used throughout.
- A generation that exposes no drivable `Category`/`Supplier` handler — behavior
  living in `tk.Toplevel` window classes that read live widgets, or in handlers
  nested as local closures — is driven through its real entry point and **FAILS**
  (no display / no callable handler), never skipped.

## Dependency usage
The behaviors above are deliberately **dependency-agnostic** (the drivers
fake or stub external services), so a generation that reimplements a
dependency with a plain substitute still passes them. This section pins the
complementary axis — does a generation **import and use the package(s) the
description names**, rather than hand-roll a substitute?

> "uses tkinter modules for Graphical User Interface(GUI) ... manage images using pil ... database using sqlite3."

The check is **static** (`loader.dependency_used`, AST only — it never
imports the module, so it is independent of whether the package is installed).
A dependency passes when the file both **imports** the package *and*
**references** what it imported at least once (guarding against a dead
import). It is deliberately scoped to import-and-use, not correct-API
verification. A generation delivered as a full project directory passes if
any of its `.py` files imports-and-uses the package.

| # | Check | claude | gpt | deepseek | gemini |
|---|---|---|---|---|---|
| D1 | imports and uses `tkinter` | pass | pass | pass | pass |
| D2 | imports and uses `PIL` | pass | pass | pass | pass |
| D3 | imports and uses `sqlite3` | pass | pass | pass | pass |

The description enumerates its stack explicitly and all four generations honor it: Tkinter for the GUI, Pillow (`PIL`) for images, and `sqlite3` for storage.
