# Behavioral contract — `Inventory-Management-System` **NL track**

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

## Dependency usage

> "uses tkinter modules for Graphical User Interface(GUI) ... manage images using
> pil ... database using sqlite3."

| # | Check | claude | gpt | deepseek | gemini |
|---|---|---|---|---|---|
| D1 | imports and uses `tkinter` | pass | pass | pass | pass |
| D2 | imports and uses `PIL` | pass | pass | pass | pass |
| D3 | imports and uses `sqlite3` | pass | pass | pass | pass |
