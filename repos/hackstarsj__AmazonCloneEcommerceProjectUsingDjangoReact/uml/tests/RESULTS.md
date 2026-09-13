# Conformance results — Amazon-clone backend **UML track**

Suite: `uml/tests/test_conformance.py` (10 structural facts, see
[CONTRACT.md](CONTRACT.md)).

## Matrix (P = pass, F = fail)

| Fact | uml/claude | uml/gpt | uml/deepseek | uml/gemini |
|---|---|---|---|---|
| U1 users has username+password | P | P | P | P |
| U2 products has sku+name+selling price | P | P | P | P |
| U3 categories has name | P | P | P | P |
| U4 warehouse has name+status | P | P | P | P |
| U5 purchaseorder has po_code+status | P | P | P | P |
| U6 salesorder has so_code | P | P | P | P |
| U7 products → categories | P | P | P | P |
| U8 purchaseorder → warehouse | P | P | P | P |
| U9 inventory → warehouse | P | P | P | P |
| U10 categories → categories (parent) | P | P | P | P |
| **Pass / 10** | 10 | 10 | 10 | 10 |
| **Score** | 1.000 | 1.000 | 1.000 | 1.000 |

Run summary: **40 passed, 0 failed, 0 skipped.**

## Interpretation

The ER structure is reproduced with **complete fidelity** by all four
generations at the pinned granularity. Every generation defines each of the six
entities under test, keeps their defining fields, and preserves the four
foreign-key associations — including the `categories.parent_id` **self-reference**
and the `so_code` field on `salesorder`. This mirrors the observation from the
repo's earlier combined suite that UML/ER structure survives transcription far
better than free-form behavior.

Notes on realization differences the adapter had to absorb (all resolved, none
caused a divergence):

- **uml/gpt, uml/gemini** put FK targets on class annotations
  (`category_id_id: productservices_categories`; gemini also adds a
  `category: 'productservices_categories'` forward reference).
- **uml/claude** (plain classes) and **uml/deepseek** (`class X(Model)`) put both
  fields and FK types on `__init__` parameters; deepseek uses a forward-ref
  string (`Optional['productservices_categories']`) that the adapter resolves.

## Reproduce

```bash
cd repos/hackstarsj__AmazonCloneEcommerceProjectUsingDjangoReact/uml/tests
python3 -m pytest -q
```
