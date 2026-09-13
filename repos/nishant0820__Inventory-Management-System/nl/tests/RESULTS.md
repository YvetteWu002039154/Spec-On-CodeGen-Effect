# Conformance results — `Inventory-Management-System` **NL track**

Subjects: the 4 NL generations (no reference in this track) · Suite:
`nl/tests/test_conformance.py` (10 behaviors, see [CONTRACT.md](CONTRACT.md)) ·
pytest / Python 3.12.

`pass` = behavior matches the contract · `FAIL` = capability wrong **or not
exposed as a drivable persistence path**. This suite does **not** skip / mark
N/A: a generation that only exposes its behavior through a live `Tk` window
(claude) or through nested local closures (deepseek) is driven through its real
entry point and fails.

## Matrix

| behavior (contract) | nl/claude | nl/gpt | nl/deepseek | nl/gemini |
|---|---|---|---|---|
| C1 category add persists            | FAIL | pass     | FAIL | pass |
| C2 empty name rejected              | FAIL | pass     | FAIL | pass |
| C3 duplicate rejected               | FAIL | pass     | FAIL | pass |
| C4 delete removes                   | FAIL | pass     | FAIL | pass |
| C5 delete-unknown rejected          | FAIL | **FAIL** | FAIL | pass |
| S1 supplier add persists            | FAIL | pass     | FAIL | pass |
| S2 missing invoice rejected         | FAIL | pass     | FAIL | pass |
| S3 duplicate rejected               | FAIL | pass     | FAIL | pass |
| S4 delete removes                   | FAIL | **FAIL** | FAIL | pass |
| S5 delete-unknown rejected          | FAIL | pass     | FAIL | pass |
| **pass / 10**                       | 0    | 8        | 0    | 10 |

Run summary: **18 passed, 22 failed** (0 skipped).

## Divergences (behavior present but wrong)

- **nl/gpt · C5** — `CategoryRepository.delete` runs `DELETE … WHERE cat_id=?`
  and returns silently; deleting an unknown id is a no-op, not a rejection (no
  exception, no error signal), so nothing distinguishes it from a real delete.
- **nl/gpt · S4** — `SupplierRepository.delete` cannot delete an existing
  supplier at all: gpt's own schema declares a `product`→`supplier` foreign key
  whose referenced column is not unique, so with FK enforcement on, `DELETE FROM
  supplier` raises `sqlite3.OperationalError: foreign key mismatch`. The record
  is never removed → the contract (delete removes) is violated. (Because *any*
  supplier delete raises, S5 "delete-unknown rejected" trivially passes — the
  raise is read as a rejection.)

## Capability not exposed (all FAIL)

- **nl/claude** — category/supplier persistence lives only on `tk.Toplevel`
  windows (`CategoryWindow.add_category` / `.delete_category`,
  `SupplierWindow.add_supplier` / `.delete_supplier`). The driver builds the real
  window, which requires a live display; headlessly it cannot be constructed, so
  no add/delete can be observed and every behavior FAILS.
- **nl/deepseek** — one monolithic `InventoryManagementApp` builds each entity
  window in `create_management_window` and defines its add/update/delete as
  **nested local closures**, not callable class methods; the wired
  `add_record`/`delete_record` were superseded and are dead. Driving the real
  `open_category_window` / `open_supplier_window` entry point exposes no callable
  add/delete, so every behavior FAILS.

## Interpretation

Only **nl/gemini** reproduces the origin's `var_`-driven GUI-handler shape
faithfully enough to pass all ten persistence behaviors. **nl/gpt**
re-architects into a clean repository layer that persists and validates adds well
(C1–C4, S1–S3) but drops two delete semantics — the unknown-id rejection (C5) and
a working supplier delete (S4, broken by its own FK schema). The other two
generations chose architectures — real-`Tk` windows (claude) and nested local
closures (deepseek) — that expose no drivable per-entity persistence handler, so
every behavior fails when driven through their real entry points.

## Reproduce

```bash
cd nishant0820__Inventory-Management-System/nl/tests
python3 -m pytest -q
```

## Dependency usage

Complementary to the behavior matrix above: does each generation **import
and use the package(s) the description names** (static AST check,
`loader.dependency_used`), or hand-roll a substitute? `pass` = imports and
references the package · `FAIL` = does not use it (absent, or a dead import).

| dependency | claude | gpt | deepseek | gemini |
|---|---|---|---|---|
| `tkinter` | pass | pass | pass | pass |
| `PIL` | pass | pass | pass | pass |
| `sqlite3` | pass | pass | pass | pass |

The description enumerates its stack explicitly and all four generations honor it: Tkinter for the GUI, Pillow (`PIL`) for images, and `sqlite3` for storage.
