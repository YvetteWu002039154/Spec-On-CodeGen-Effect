"""Behavior-conformance suite for `Inventory-Management-System` NL track.

One driver per generation (see adapter.py) is built from its loaded module, and
one plain-assert test per contract behavior (Cn/Sn) runs against every driver.
There is no reference and no skip: a capability a generation does not expose as a
drivable persistence path FAILS. Success is the observable record count; a
rejection is an exception or an error dialog with no success dialog.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from adapter_per_run import build_driver  # noqa: E402
from loader import dependency_used, gencode_paths, load_gencodemodule  # noqa: E402

# Generations are loaded LAZILY, per driver, and an import-time crash is captured
# rather than raised. Loading all four eagerly here meant one generation that
# raises on import (e.g. a pydantic-v1 `Field(regex=...)` under pydantic v2) took
# down collection for the whole module, scoring every OTHER model 0-of-0 too.
# That is fatal when re-scoring across runs (Reports/variance_pilot/): a single
# bad generation would blank an entire run. Now an unloadable generation fails
# its own tests — which is the correct score for it — and leaves the rest intact.
_PATHS = dict(gencode_paths())
_CACHE = {}


class _Unloadable:
    def __init__(self, exc):
        self._exc = exc

    def __getattr__(self, name):
        raise self._exc


def _driver_for(ident):
    if ident not in _CACHE:
        try:
            module = load_gencodemodule(ident, _PATHS[ident])
        except Exception as exc:
            module = _Unloadable(exc)
        _CACHE[ident] = build_driver(ident.split("/")[-1], module)
    return _CACHE[ident]


@pytest.fixture(params=sorted(_PATHS))
def driver(request):
    return _driver_for(request.param)


# ---------------------------------------------------------------------------
# Category  (grounded in category.py::categoryClass.add / .delete)
# ---------------------------------------------------------------------------
def test_category_add_persists(driver):
    assert driver.category_add_persists() == 1


def test_category_empty_name_rejected(driver):
    rejected, count = driver.category_empty_name_rejected()
    assert rejected is True and count == 0


def test_category_duplicate_rejected(driver):
    assert driver.category_duplicate_rejected() == 1


def test_category_delete_removes(driver):
    assert driver.category_delete_removes() == 0


def test_category_delete_unknown_rejected(driver):
    assert driver.category_delete_unknown_rejected() is True


# ---------------------------------------------------------------------------
# Supplier  (grounded in supplier.py::supplierClass.add / .delete)
# ---------------------------------------------------------------------------
def test_supplier_add_persists(driver):
    assert driver.supplier_add_persists() == 1


def test_supplier_missing_invoice_rejected(driver):
    rejected, count = driver.supplier_missing_invoice_rejected()
    assert rejected is True and count == 0


def test_supplier_duplicate_rejected(driver):
    assert driver.supplier_duplicate_rejected() == 1


def test_supplier_delete_removes(driver):
    assert driver.supplier_delete_removes() == 0


def test_supplier_delete_unknown_rejected(driver):
    assert driver.supplier_delete_unknown_rejected() is True


# ---------------------------------------------------------------------------
# Dependency usage — the description names tkinter, PIL, sqlite3; does the generation
# import and use it, or hand-roll a substitute? Static (AST) check — see
# loader.dependency_used and CONTRACT.md § "Dependency usage".
# ---------------------------------------------------------------------------
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


def test_uses_named_dependency_tkinter(ident):
    _assert_dependency_used(ident, "tkinter")


def test_uses_named_dependency_pil(ident):
    _assert_dependency_used(ident, "PIL")


def test_uses_named_dependency_sqlite3(ident):
    _assert_dependency_used(ident, "sqlite3")
