# Behavioral contract — Amazon-clone backend **NL track**

Reference: 
- **NL description** (`nl/input/description.txt`)
- **origin code** (`Backend/EcommerceInventory` Django models)

Behaviors are judged on observable capability/effect.


**Harness.** Each generation is a Django app that grabs the global Django
singletons, so its driver is built and run in its **own subprocess**
(`loader.py`) against a **real in-memory SQLite** schema (built for its models
via `migrate --run-syncdb` + the schema editor). The subprocess runs each
behavior method and prints the JSON outcomes; the suite reads them back and
asserts. Nothing is stubbed — Django is kept real so the behaviors actually run.

**Loading.** A generation delivered as a **single file** loads from its
`generated_code.py` (the pristine model output); the loader applies the Django
harness adaptation externally (registers the module as app `generated_code`,
configures a permissive Django before exec), so the generated file stays
pristine. A generation delivered as a **full multi-app project** (deepseek) loads from its own settings with the DB redirected to in-memory SQLite, and its driver imports models straight from the
app packages.


Each generation is driven by its own explicit driver (`adapter.py`) that names
the exact concrete classes and methods it uses. The driver attempts the real API and the resulting empty result / `AttributeError` / wrong value fails the test.

## Description feature → origin grounding

| Description feature | Origin evidence |
|---|---|
| "Product Listing and Search" | `ProductServices/models.py::Products` (name, sku, prices) |
| product pricing | `Products.initial_selling_price` (also `Inventory.sell_price`) |
| catalog / categories | `ProductServices/models.py::Categories`; `Products.category_id -> Categories` |
| "Shopping Cart Functionality" | cart totals items × price (a described capability; no single origin class — it is the React/checkout flow) |
| "Inventory Management System" | `InventoryServices/models.py::Inventory.quantity` / `InventoryLog` |
| "Order Management" / "Sales order" | `OrderService/models.py::SalesOrder.status` (status vocabulary) |
| "Purchase Order" + "Supplier" | `OrderService/models.py::PurchaseOrder.supplier_id -> Users` |
| "Warehouse Management" | `InventoryServices/models.py::Warehouse.name` (+ `defaultkey()=='name'`) |
| "User Authentication (Sign Up, Login, Logout)" | `UserServices/models.py::Users.save()` hashes via `make_password` |

## Behaviors pinned

### Product listing & catalog
- **N1. Product listing.** A product can be created and then listed (persisted
  and queryable through the ORM).
- **N2. Product price.** A product carries a selling price that reads back as the
  value it was created with.
- **N3. Product↔category link.** A product can be linked to a category and the
  foreign-key association persists (re-read from the DB).

### Shopping cart
- **N4. Cart total.** A shopping cart totals its lines: the reported total equals
  unit price × quantity.

### Inventory management
- **N5. Inventory quantity.** An inventory/stock record tracks a numeric stock
  quantity.

### Order management
- **N6. Order status.** An order can be created and exposes a (non-empty) status
  value.
- **N7. Purchase order → supplier.** A purchase order links to a supplier (or a
  user acting as supplier) and that link persists.

### Warehouse management
- **N8. Warehouse.** A warehouse can be created and identified by a name.

### User authentication
- **N9. Password hashing.** A user created through the app's user machinery
  stores its password **hashed** (differs from the plaintext) and the stored hash
  verifies against the raw password via Django's `check_password`.

## Availability note

`nl/outputcode/deepseek/` contains no canonical `generated_code.py` — that
generation's output was expanded into a full multi-app Django project.

## Dependency usage
The behaviors above are deliberately **dependency-agnostic** (the drivers
fake or stub external services), so a generation that reimplements a
dependency with a plain substitute still passes them. This section pins the
complementary axis — does a generation **import and use the package(s) the
description names**, rather than hand-roll a substitute?

> "Creating a fully functional Amazon clone using Django, complete with an inventory management system."

The check is **static** (`loader.dependency_used`, AST only — it never
imports the module, so it is independent of whether the package is installed).
A dependency passes when the file both **imports** the package *and*
**references** what it imported at least once (guarding against a dead
import). It is deliberately scoped to import-and-use, not correct-API
verification. A generation delivered as a full project directory passes if
any of its `.py` files imports-and-uses the package.

| # | Check | claude | gpt | deepseek | gemini |
|---|---|---|---|---|---|
| D1 | imports and uses `django` | pass | pass | pass | pass |

All four build on Django. deepseek is delivered as a full multi-app Django project (a directory), so the check scans every `.py` file in it; the single-file generations import `django` directly.
