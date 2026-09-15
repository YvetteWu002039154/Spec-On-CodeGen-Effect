# Structural contract — Amazon-clone backend **UML track**

This contract is derived from the **ER diagram** (`uml/input/classes.puml`, "32
entities … transcribed from ER_Diagram.png"), grounded in the origin Django
project it was transcribed from (`Backend/EcommerceInventory`). An ER diagram
records *structure*, not runtime behavior, so the pinned facts are the three
things the diagram actually draws:

1. **Entities** — a table/model exists (`entity <name> { … }`).
2. **Fields** — the columns declared under an entity.
3. **Associations** — the foreign-key links (`A → B : fk`) between entities.

## Facts pinned

| # | Diagram fact | Origin evidence |
|---|---|---|
| U1 | `userservices_users` has `username`, `password` | `UserServices/models.py::Users` — `username=CharField(unique=True)`, `password=CharField(max_length=255)` |
| U2 | `productservices_products` has `sku`, `name`, `initial_selling_price` | `ProductServices/models.py::Products` — those three fields |
| U3 | `productservices_categories` has `name` | `ProductServices/models.py::Categories.name` (+ `defaultkey()=='name'`) |
| U4 | `inventoryservices_warehouse` has `name`, `status` | `InventoryServices/models.py::Warehouse` — `name`, `status` |
| U5 | `orderservice_purchaseorder` has `po_code`, `status` | `OrderService/models.py::PurchaseOrder` — `po_code`, `status` |
| U6 | `orderservice_salesorder` has `so_code` | `OrderService/models.py::SalesOrder.so_code` |
| U7 | `products → categories : category_id` | `Products.category_id = ForeignKey(Categories)` |
| U8 | `purchaseorder → warehouse : warehouse_id` | `PurchaseOrder.warehouse_id = ForeignKey('InventoryServices.Warehouse')` |
| U9 | `inventory → warehouse : warehouse_id` | `Inventory.warehouse_id = ForeignKey(Warehouse)` |
| U10 | `categories → categories : parent_id` | `Categories.parent_id = ForeignKey('self')` |
