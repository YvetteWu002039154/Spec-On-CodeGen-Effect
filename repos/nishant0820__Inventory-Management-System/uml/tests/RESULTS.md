# Conformance results — `Inventory-Management-System` **UML track**

Reference: origin app `Inventory-Management-System-main/` (seven entity modules) ·
Suite: `uml/tests/test_conformance.py` (10 structural facts, see
[CONTRACT.md](CONTRACT.md)) · pytest 9 / Python 3.12.

## Matrix (P = pass, F = fail)

| Fact | uml/cla | uml/gpt | uml/dee | uml/gem |
|---|---|---|---|---|
| U1 composition targets present     | P | P | P | P |
| U2 IMS navigation set              | P | P | P | P |
| U3 IMS update_content              | P | P | P | F |
| U4 categoryClass methods           | P | P | P | F |
| U5 supplierClass methods           | P | P | P | F |
| U6 employeeClass methods           | P | P | P | F |
| U7 productClass methods            | P | P | P | F |
| U8 salesClass methods              | P | P | P | F |
| U9 billClass full 18-method set    | F | F | F | F |
| U10 billClass calculator trio      | P | P | P | F |
| **Pass / 10** | 9 | 9 | 9 | 2 |
| **Score** | 0.900 | 0.900 | 0.900 | 0.200 |

Run summary: **29 passed, 11 failed, 0 N/A.**

## Interpretation

The method-set facts now require a **real (non-stub) body**: a method present
only as `pass` / `...` / `return None` / `raise NotImplementedError` is judged
(statically, from source) as *not* implemented and fails the set. This separates
generations that reproduced the diagram's *operations* from those that emitted a
name-only **skeleton**.

- **`uml/gemini` is a skeleton.** Nearly every entity- and bill-class method is a
  bare `pass`, so it fails U3–U10; only the `IMS` composition wiring and its five
  navigation methods (U1–U2), which carry real bodies, survive. Under the old
  name-only check this scored a false **1.000** — the exact failure mode this
  change corrects.
- **U9 fails for all four.** Every generation stubs at least one of `billClass`'s
  18 drawn operations: `uml/claude` leaves `bill_top`/`bill_middle`/`bill_bottom`
  as `pass`, `uml/gpt` leaves `bill_bottom`/`bill_middle` as a bare `return`,
  `uml/deepseek` stubs those three plus `get_data_cart`, and `uml/gemini` stubs
  the whole class.
- **`uml/cla`/`uml/gpt`/`uml/dee` otherwise conform** — the category, supplier,
  employee, product, sales surfaces and the `billClass` calculator trio
  (`get_input`/`perform_cal`/`clear_cal`) are all really implemented.

Superset checks still tolerate extra members not on the diagram (e.g.
`uml/claude`/`uml/deepseek`'s `IMS.billing()`, `deepseek`'s `IMS.open_window` and
`billClass.calculate_net`) as additions rather than violations.

- **No N/A** — every generation defines all seven classes the diagram names.

## Reproduce

```bash
cd nishant0820__Inventory-Management-System/uml/tests
python3 -m pytest -p no:warnings -q   # full matrix
```
