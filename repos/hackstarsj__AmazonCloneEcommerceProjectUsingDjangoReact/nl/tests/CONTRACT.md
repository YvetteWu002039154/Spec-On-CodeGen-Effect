# Behavioral contract — Amazon-clone backend **NL track**

## Description features

| Description feature |
|---|
| "Product Listing and Search" |
| product pricing |
| catalog / categories |
| "Shopping Cart Functionality" |
| "Inventory Management System" |
| "Order Management" / "Sales order" |
| "Purchase Order" + "Supplier" |
| "Warehouse Management" |
| "User Authentication (Sign Up, Login, Logout)" |

## Behaviors pinned

| # | Group | Behavior |
|---|---|---|
| N1 | Product listing & catalog | **Product listing.** A product can be created and then listed (persisted and queryable through the ORM). |
| N2 | Product listing & catalog | **Product price.** A product carries a selling price that reads back as the value it was created with. |
| N3 | Product listing & catalog | **Product↔category link.** A product can be linked to a category and the foreign-key association persists (re-read from the DB). |
| N4 | Shopping cart | **Cart total.** A shopping cart totals its lines: the reported total equals unit price × quantity. |
| N5 | Inventory management | **Inventory quantity.** An inventory/stock record tracks a numeric stock quantity. |
| N6 | Order management | **Order status.** An order can be created and exposes a (non-empty) status value. |
| N7 | Order management | **Purchase order → supplier.** A purchase order links to a supplier (or a user acting as supplier) and that link persists. |
| N8 | Warehouse management | **Warehouse.** A warehouse can be created and identified by a name. |
| N9 | User authentication | **Password hashing.** A user created through the app's user machinery stores its password **hashed** (differs from the plaintext) and the stored hash verifies against the raw password via Django's `check_password`. |

## Dependency usage

> "Creating a fully functional Amazon clone using Django, complete with an inventory management system."

| # | Check |
|---|---|
| D1 | imports and uses `django` |
