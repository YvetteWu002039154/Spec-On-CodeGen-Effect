import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loader import dependency_used, gencode_paths, run_probes  # noqa: E402

_RESULTS = {ident: run_probes(ident, path) for ident, path in gencode_paths()}


@pytest.fixture(params=sorted(_RESULTS))
def results(request):
    return _RESULTS[request.param]


def _value(results, name):
    outcome = results.get(name) or {}
    assert outcome.get("status") == "ok", \
        outcome.get("error") or results.get("__load__", {}).get("error") or "not run"
    return outcome["value"]


# ---------------------------------------------------------------------------
# Product listing & catalog
# ---------------------------------------------------------------------------
def test_product_can_be_listed(results):
    assert _value(results, "N1_product_listing") >= 1


def test_product_has_selling_price(results):
    assert abs(_value(results, "N2_product_price") - 49.50) < 0.01


def test_product_links_to_category(results):
    assert _value(results, "N3_product_category_link") is True


# ---------------------------------------------------------------------------
# Shopping cart
# ---------------------------------------------------------------------------
def test_cart_totals_its_lines(results):
    v = _value(results, "N4_cart_total")
    assert abs(v["total"] - v["expected"]) < 0.01


# ---------------------------------------------------------------------------
# Inventory management
# ---------------------------------------------------------------------------
def test_inventory_tracks_quantity(results):
    assert _value(results, "N5_inventory_quantity") is True


# ---------------------------------------------------------------------------
# Order management
# ---------------------------------------------------------------------------
def test_order_has_status(results):
    v = _value(results, "N6_order_status")
    assert isinstance(v, str) and v != ""


def test_purchase_order_references_supplier(results):
    assert _value(results, "N7_purchase_order_supplier") is True


# ---------------------------------------------------------------------------
# Warehouse management
# ---------------------------------------------------------------------------
def test_warehouse_can_be_created(results):
    assert _value(results, "N8_warehouse_named") is True


# ---------------------------------------------------------------------------
# User authentication
# ---------------------------------------------------------------------------
def test_user_password_is_hashed(results):
    v = _value(results, "N9_password_hashed")
    assert v["differs"] is True and v["verifies"] is True


# ---------------------------------------------------------------------------
# Dependency usage — the description names django; does the generation
# import and use it, or hand-roll a substitute? Static (AST) check — see
# loader.dependency_used and CONTRACT.md § "Dependency usage".
# ---------------------------------------------------------------------------
_PATHS = dict(gencode_paths())


@pytest.fixture(params=sorted(_PATHS))
def ident(request):
    return request.param


# One test per named dependency rather than a @parametrize: parametrize ids
# append "-<dep>" inside the brackets, which breaks the canonical
# test_xxx[nl/<model>] id shape the step3 scorer parses.
def _assert_dependency_used(ident, dep):
    assert dependency_used(_PATHS[ident], dep), (
        f"{ident} does not import and use '{dep}' — the description names it, "
        f"so a hand-rolled substitute does not use the dependency"
    )


def test_uses_named_dependency_django(ident):
    _assert_dependency_used(ident, "django")
