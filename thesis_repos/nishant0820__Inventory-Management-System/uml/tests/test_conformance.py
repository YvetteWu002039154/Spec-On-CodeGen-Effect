"""Structure-conformance suite for `Inventory-Management-System` **UML track**.

One shared test body runs against the 4 UML generations, via the adapter.
Expected structure comes only from CONTRACT.md, derived from the class diagram
`uml/input/classes.puml` (a pyreverse extraction). For this Tkinter app the
diagram records **class presence** (seven boxes), **the method set under each
box**, and **composition links** (`entityClass --* IMS : new_obj`) realized by
`IMS`'s per-entity navigation methods — all checked by reflection on the loaded
classes, never by running behavior. Each test pins one fact (Un). A class a
generation omits is a FAILURE, as is a present class missing a listed method;
this track does not skip / mark N/A.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter import Implementation, Unsupported            # noqa: E402
from loader import gencode_paths, load_gencodemodule  # noqa: E402

_PARAMS = [ident for ident, _ in gencode_paths()]
_PATHS = dict(gencode_paths())
_cache = {}

# The five entity classes composed into IMS (the `--* : new_obj` links) …
_COMPOSED_ENTITIES = ("categoryClass", "employeeClass", "productClass",
                      "salesClass", "supplierClass")
# … realized by IMS defining one navigation method per composed entity.
_IMS_NAV = frozenset({"category", "employee", "product", "sales", "supplier"})

# Method sets each box carries in the diagram (grounded in the origin modules).
_CATEGORY_METHODS = frozenset({"add", "clear", "delete", "get_data", "show"})
_EMPLOYEE_METHODS = frozenset({"add", "clear", "delete", "get_data", "search",
                               "show", "update"})
_PRODUCT_METHODS = frozenset({"add", "clear", "delete", "fetch_cat_sup",
                              "get_data", "search", "show", "update"})
_SUPPLIER_METHODS = frozenset({"add", "clear", "delete", "get_data", "search",
                               "show", "update"})
_SALES_METHODS = frozenset({"clear", "get_data", "search", "show"})
# billClass carries the largest surface; these are its defining operations.
_BILL_CORE = frozenset({"add_update_cart", "generate_bill", "print_bill"})
_BILL_CALC = frozenset({"get_input", "perform_cal", "clear_cal"})
_BILL_FULL = frozenset({
    "add_update_cart", "bill_bottom", "bill_middle", "bill_top", "bill_update",
    "clear_all", "clear_cal", "clear_cart", "generate_bill", "get_data",
    "get_data_cart", "get_input", "perform_cal", "print_bill", "search",
    "show", "show_cart", "update_date_time",
})


def _impl(ident):
    if ident not in _cache:
        try:
            _cache[ident] = Implementation(
                ident, [load_gencodemodule(ident, _PATHS[ident])])
        except Exception as exc:
            # A generation that does not load exposes no structure at all: build
            # an empty implementation so every behavior FAILS (this track never
            # skips / marks N/A -- a module that does not load is a failure).
            impl = Implementation(ident, [])
            impl._load_error = exc
            _cache[ident] = impl
    return _cache[ident]


@pytest.fixture(params=_PARAMS)
def impl(request):
    return _impl(request.param)


def _guard(fn):
    try:
        return fn()
    except Unsupported as exc:
        pytest.fail(f"structure not present: {exc}")


# ---------------------------------------------------------------------------
# Composition links (entityClass --* IMS : new_obj)
# ---------------------------------------------------------------------------
def test_ims_composes_all_entities(impl):
    # U1: the five composed entity classes are all present (--* composition targets).
    assert impl.present(_COMPOSED_ENTITIES) == frozenset(_COMPOSED_ENTITIES)


def test_ims_navigation_methods(impl):
    # U2: IMS realizes the five --* links via a navigation method per entity
    #     (category/employee/product/sales/supplier).
    assert _IMS_NAV <= _guard(lambda: impl.methods("IMS"))


def test_ims_update_content(impl):
    # U3: IMS carries the dashboard refresh method update_content().
    assert "update_content" in _guard(lambda: impl.methods("IMS"))


# ---------------------------------------------------------------------------
# Methods under each entity box
# ---------------------------------------------------------------------------
def test_category_method_set(impl):
    # U4: categoryClass carries {add, clear, delete, get_data, show}.
    assert _CATEGORY_METHODS <= _guard(lambda: impl.methods("categoryClass"))


def test_supplier_method_set(impl):
    # U5: supplierClass carries {add, clear, delete, get_data, search, show, update}.
    assert _SUPPLIER_METHODS <= _guard(lambda: impl.methods("supplierClass"))


def test_employee_method_set(impl):
    # U6: employeeClass carries {add, clear, delete, get_data, search, show, update}.
    assert _EMPLOYEE_METHODS <= _guard(lambda: impl.methods("employeeClass"))


def test_product_method_set(impl):
    # U7: productClass carries {add, clear, delete, fetch_cat_sup, get_data,
    #     search, show, update} (fetch_cat_sup is distinctive to product).
    assert _PRODUCT_METHODS <= _guard(lambda: impl.methods("productClass"))


def test_sales_method_set(impl):
    # U8: salesClass carries {clear, get_data, search, show}.
    assert _SALES_METHODS <= _guard(lambda: impl.methods("salesClass"))


# ---------------------------------------------------------------------------
# billClass (the largest box)
# ---------------------------------------------------------------------------
def test_bill_full_method_set(impl):
    # U9: billClass carries its full 18-method operation set.
    assert _BILL_FULL <= _guard(lambda: impl.methods("billClass"))


def test_bill_calculator_methods(impl):
    # U10: billClass exposes the embedded numeric-calculator trio
    #      {get_input, perform_cal, clear_cal} (distinctive to billing).
    assert _BILL_CALC <= _guard(lambda: impl.methods("billClass"))
