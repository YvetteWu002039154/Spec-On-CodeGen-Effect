# Behavioral contract — Amazon-clone backend **NL track**

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

## Dependency usage

> "Creating a fully functional Amazon clone using Django, complete with an inventory management system."

| # | Check | claude | gpt | deepseek | gemini |
|---|---|---|---|---|---|
| D1 | imports and uses `django` | pass | pass | pass | pass |
