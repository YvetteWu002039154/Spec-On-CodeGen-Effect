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

from adapter import build_driver  # noqa: E402
from loader import dependency_used, gencode_paths, load_gencodemodule  # noqa: E402

_DRIVERS = {
    ident: build_driver(ident.split("/")[-1], load_gencodemodule(ident, path))
    for ident, path in gencode_paths()
}


@pytest.fixture(params=sorted(_DRIVERS))
def driver(request):
    return _DRIVERS[request.param]


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
_PATHS = dict(gencode_paths())


@pytest.fixture(params=sorted(_PATHS))
def ident(request):
    return request.param


NAMED_DEPENDENCIES = ('tkinter', 'PIL', 'sqlite3')


@pytest.mark.parametrize("dep", NAMED_DEPENDENCIES)
def test_uses_named_dependency(ident, dep):
    assert dependency_used(_PATHS[ident], dep), (
        f"{ident} does not import and use '{dep}' — the description names it, "
        f"so a hand-rolled substitute does not use the dependency"
    )
