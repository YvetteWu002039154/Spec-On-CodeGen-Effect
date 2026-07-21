# Structural contract — Amazon-clone backend **UML track**

This contract is derived from the **ER diagram** (`uml/input/classes.puml`, "32
entities … transcribed from ER_Diagram.png"), grounded in the origin Django
project it was transcribed from (`Backend/EcommerceInventory`). An ER diagram
records *structure*, not runtime behavior, so the pinned facts are the three
things the diagram actually draws:

1. **Entities** — a table/model exists (`entity <name> { … }`).
2. **Fields** — the columns declared under an entity.
3. **Associations** — the foreign-key links (`A → B : fk`) between entities.

## Diagram fact → origin grounding

| Diagram fact | Origin evidence |
|---|---|
| `userservices_users` has `username`, `password` | `UserServices/models.py::Users` — `username=CharField(unique=True)`, `password=CharField(max_length=255)` |
| `productservices_products` has `sku`, `name`, `initial_selling_price` | `ProductServices/models.py::Products` — those three fields |
| `productservices_categories` has `name` | `ProductServices/models.py::Categories.name` (+ `defaultkey()=='name'`) |
| `inventoryservices_warehouse` has `name`, `status` | `InventoryServices/models.py::Warehouse` — `name`, `status` |
| `orderservice_purchaseorder` has `po_code`, `status` | `OrderService/models.py::PurchaseOrder` — `po_code`, `status` |
| `orderservice_salesorder` has `so_code` | `OrderService/models.py::SalesOrder.so_code` |
| `products → categories : category_id` | `Products.category_id = ForeignKey(Categories)` |
| `purchaseorder → warehouse : warehouse_id` | `PurchaseOrder.warehouse_id = ForeignKey('InventoryServices.Warehouse')` |
| `inventory → warehouse : warehouse_id` | `Inventory.warehouse_id = ForeignKey(Warehouse)` |
| `categories → categories : parent_id` | `Categories.parent_id = ForeignKey('self')` |

## Facts pinned

### Entities + defining fields
- **U1. Users auth fields.** `userservices_users` exists and declares `username`
  and `password`.
- **U2. Products catalog fields.** `productservices_products` exists and declares
  `sku`, `name`, and `initial_selling_price`.
- **U3. Categories name.** `productservices_categories` exists and declares `name`.
- **U4. Warehouse fields.** `inventoryservices_warehouse` exists and declares
  `name` and `status`.
- **U5. PurchaseOrder fields.** `orderservice_purchaseorder` exists and declares
  `po_code` and `status`.
- **U6. SalesOrder code.** `orderservice_salesorder` exists and declares `so_code`.

### Associations (foreign keys)
- **U7. Product → Category.** `products` has an attribute typed as `categories`
  (`category_id`).
- **U8. PurchaseOrder → Warehouse.** `purchaseorder` has an attribute typed as
  `warehouse` (`warehouse_id`).
- **U9. Inventory → Warehouse.** `inventory` has an attribute typed as `warehouse`
  (`warehouse_id`).
- **U10. Category → Category (self).** `categories` has an attribute typed as
  `categories` (the `parent_id` self-reference — a distinctive structural link).

## Harness

The pinned surface is the **structure the ER diagram draws** — entities, their
fields, and the foreign-key associations between them — asserted by **reflection
on the loaded classes**, never by executing behavior. Entity names are compared
after normalization (the service prefix and case/underscores are stripped:
`userservices_users` ≡ `UserservicesUsers` ≡ `Users` → `users`), because the
generations name their classes differently (uml/gpt·deepseek·gemini: snake_case
`userservices_users`; uml/claude: CamelCase `UserservicesUsers`). Fields are
gathered from dataclass fields / annotations / `__init__` params; associations
from any attribute typed as the target class. Any fact the diagram specifies but a
generation does not implement — a missing entity, a dropped field or association —
is a **FAILURE**; no skip / N/A. Subjects are the 4 UML generations
(`uml/outputcode/{claude,gpt,deepseek,gemini}`).

## Portability

Each generation is a plain `@dataclass` / `__init__` module that needs no
framework — only the standard library is required to load and reflect on the
classes.
