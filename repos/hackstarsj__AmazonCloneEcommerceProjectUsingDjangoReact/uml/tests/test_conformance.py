import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from structure import Implementation                         # noqa: E402
from loader import gencode_paths, load_gencodemodules       # noqa: E402

_PARAMS = [ident for ident, _ in gencode_paths()]
_PATHS = dict(gencode_paths())
_cache = {}


def _impl(ident):
    if ident not in _cache:
        try:
            _cache[ident] = Implementation(
                ident, load_gencodemodules(ident, _PATHS[ident]))
        except Exception as exc:
            # A generation that does not load exposes no structure at all: build
            # an empty implementation so every behavior FAILS (this track never
            # skips / marks N/A -- a module that does not load is a failure).
            # Built here rather than pytest.fail()-ing: this runs inside the
            # `impl` fixture, and pytest.fail() in a FIXTURE is reported as an
            # <error>, not a <failure> -- mislabelling a model-side defect as a
            # harness bug. Failing in the test body keeps `error` meaning
            # "the harness/env broke", which is what the step3 scorer warns on.
            impl = Implementation(ident, [])
            impl._load_error = exc
            _cache[ident] = impl
    return _cache[ident]


@pytest.fixture(params=_PARAMS)
def impl(request):
    return _impl(request.param)


# ---------------------------------------------------------------------------
# Entities + defining fields (entity <name> { ... })
# ---------------------------------------------------------------------------
def test_users_entity_has_auth_fields(impl):
    # U1: userservices_users carries the auth fields `username` and `password`.
    assert impl.has_fields("users", "username", "password") is True


def test_products_entity_has_sku_name_price(impl):
    # U2: productservices_products carries `sku`, `name`, `initial_selling_price`.
    assert impl.has_fields("products", "sku", "name", "initial_selling_price") is True


def test_categories_entity_has_name(impl):
    # U3: productservices_categories carries `name`.
    assert impl.has_fields("categories", "name") is True


def test_warehouse_entity_has_name_status(impl):
    # U4: inventoryservices_warehouse carries `name` and `status`.
    assert impl.has_fields("warehouse", "name", "status") is True


def test_purchaseorder_entity_has_po_code_status(impl):
    # U5: orderservice_purchaseorder carries `po_code` and `status`.
    assert impl.has_fields("purchaseorder", "po_code", "status") is True


def test_salesorder_entity_has_so_code(impl):
    # U6: orderservice_salesorder carries `so_code`.
    assert impl.has_fields("salesorder", "so_code") is True


# ---------------------------------------------------------------------------
# Associations (A }o--|| B : fk)
# ---------------------------------------------------------------------------
def test_products_reference_category(impl):
    # U7: productservices_products --> productservices_categories (category_id).
    assert impl.references("products", "categories") is True


def test_purchaseorder_references_warehouse(impl):
    # U8: orderservice_purchaseorder --> inventoryservices_warehouse (warehouse_id).
    assert impl.references("purchaseorder", "warehouse") is True


def test_inventory_references_warehouse(impl):
    # U9: inventoryservices_inventory --> inventoryservices_warehouse (warehouse_id).
    assert impl.references("inventory", "warehouse") is True


def test_category_self_reference_parent(impl):
    # U10: productservices_categories --> productservices_categories (parent_id).
    assert impl.references("categories", "categories") is True
