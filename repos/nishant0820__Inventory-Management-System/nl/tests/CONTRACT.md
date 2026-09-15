# Behavioral contract — `Inventory-Management-System` **NL track**

## Description features

| Description feature |
|---|
| "shows the information about the category of the product" |
| category removal |
| "data regarding suppliers" |
| supplier removal |
| database via sqlite3 |

## Behaviors pinned

| # | Group | Behavior |
|---|---|---|
| C1 | Category | **Add persists.** Adding a valid category persists exactly one record. |
| C2 | Category | **Empty name rejected.** Adding a category with an empty **name** is rejected (nothing persisted). |
| C3 | Category | **Duplicate rejected.** Adding a **duplicate** category is rejected (still one record). |
| C4 | Category | **Delete removes.** Deleting an existing category removes it (count returns to zero). |
| C5 | Category | **Delete unknown rejected.** Deleting a **non-existent** category is rejected. |
| S1 | Supplier | **Add persists.** Adding a valid supplier persists exactly one record. |
| S2 | Supplier | **Missing invoice rejected.** Adding a supplier without its **invoice/id** is rejected (nothing persisted). |
| S3 | Supplier | **Duplicate rejected.** Adding a **duplicate** supplier (same invoice) is rejected (still one record). |
| S4 | Supplier | **Delete removes.** Deleting an existing supplier removes it (count returns to zero). |
| S5 | Supplier | **Delete unknown rejected.** Deleting a **non-existent** supplier is rejected. |

## Dependency usage

> "uses tkinter modules for Graphical User Interface(GUI) ... manage images using
> pil ... database using sqlite3."

| # | Check |
|---|---|
| D1 | imports and uses `tkinter` |
| D2 | imports and uses `PIL` |
| D3 | imports and uses `sqlite3` |
