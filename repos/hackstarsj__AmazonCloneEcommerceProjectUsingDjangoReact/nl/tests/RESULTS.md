# Conformance results — Amazon-clone backend **NL track**

Subjects: the 4 NL generations, each generation
that exists is driven by its own explicit driver in `adapter.py`.

| behavior (contract) | claude | gpt | deepseek | gemini |
|---|---|---|---|---|
| N1  product listing | pass | pass | pass | pass |
| N2  product selling price | pass | pass | pass | pass |
| N3  product↔category link | pass | pass | pass | pass |
| N4  cart totals its lines | pass | pass | **FAIL** | **FAIL** |
| N5  inventory quantity | pass | pass | pass | pass |
| N6  order has status | pass | pass | pass | pass |
| N7  purchase order → supplier | pass | pass | pass | pass |
| N8  warehouse created by name | pass | pass | pass | pass |
| N9  password hashed | pass | pass | pass | pass |
| **Pass / 9** | **9** | **9** | 8 | 8 |

**Totals:** 34 passed, 2 failed.

## The failures

Both failures are the same genuine capability gap: **no cart-total accessor.**

- **deepseek / N4** — deepseek has **no `Cart` model** at all.
- **gemini / N4** — gemini's `Cart` exposes `add_item` and `checkout` but **no
  total/subtotal accessor** on the model. The driver calls `Cart.get_total()` →
  `AttributeError`, so N4 fails.

## Reproduce

```bash
cd repos/hackstarsj__AmazonCloneEcommerceProjectUsingDjangoReact/nl/tests
python3 -m pytest -q
```

## Dependency usage

Complementary to the behavior matrix above: does each generation **import
and use the package(s) the description names** (static AST check,
`loader.dependency_used`), or hand-roll a substitute? `pass` = imports and
references the package · `FAIL` = does not use it (absent, or a dead import).

| dependency | claude | gpt | deepseek | gemini |
|---|---|---|---|---|
| `django` | pass | pass | pass | pass |

All four build on Django. deepseek is delivered as a full multi-app Django project (a directory), so the check scans every `.py` file in it; the single-file generations import `django` directly.
