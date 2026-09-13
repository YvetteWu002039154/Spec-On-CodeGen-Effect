"""Per-(model, run) drivers for the variance pilot — nishant0820__Inventory-Management-System.

Extends the main study's drivers to runs 1-3. Run 0 is NOT redefined here: it is
imported from repos/nishant0820__Inventory-Management-System/nl/tests/adapter.py, so the
generation the main study scores and the generation the pilot calls "run 0" are
driven by literally the same code. Everything else — Gen, SpecDriver, the Tk
stand-ins, the per-architecture builders — is imported from there too, so there
is one implementation and the pilot cannot drift from the instrument it is
supposed to be validating.

Only the run1-3 recipes are new. A regeneration is a different program: see the
drift table in the main adapter's docstring.
"""

import importlib.util
import os
import re
import sys

_MAIN_TESTS = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "repos", "nishant0820__Inventory-Management-System", "nl", "tests"))


def _load_main_adapter():
    """Load the repo's adapter.py by PATH, under a repo-unique module name.

    Deliberately not `sys.path.insert(_MAIN_TESTS); import adapter`:

      * that puts the repo's tests dir ahead of this one on sys.path, so
        `from loader import ...` in test_conformance.py would silently resolve
        to the repo's loader.py instead of the copy next to this file;
      * `import adapter` caches under the bare name "adapter", so loading two
        repos' pilots in one process would hand the second repo the first
        repo's drivers — silently, whenever the two happen to define the same
        names.

    Loading by path under a unique name avoids both.
    """
    name = "main_adapter_" + re.sub(r"\W", "_", "nishant0820__Inventory-Management-System")
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, os.path.join(_MAIN_TESTS, "adapter.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


_main = _load_main_adapter()

# machinery + builders — one implementation, defined in the main adapter
Gen = _main.Gen
SpecDriver = _main.SpecDriver
_claude = _main._claude
_deepseek_db = _main._deepseek_db
_deepseek_run3 = _main._deepseek_run3
_gemini = _main._gemini
_gpt = _main._gpt
_RUN0 = _main.GENERATIONS


GENERATIONS = {(m, 0): g for m, g in _RUN0.items()}
GENERATIONS.update({
    ("claude", 1): _claude("F", "vars", "category_id",
                           ("name", "supplier_id", "contact", "email", "phone", "address",
                            "company", "product_type"),
                           ("name", "category_id", "description"), "create_database"),
    ("claude", 2): _claude("F", "entries", "category_id",
                           ("name", "supplier_id", "email", "phone", "address", "company",
                            "description"),
                           ("name", "category_id", "description"), "create_database"),
    ("claude", 3): _claude("F", "entries", "cat_id",
                           ("name", "supplier_id", "email", "phone", "address", "company",
                            "product_type"),
                           ("name", "cat_id", "description"), "init_db",
                           borrow=("get_entry_value",)),
    ("gpt", 1): _gpt("Database",
                     {"category": "categories", "supplier": "suppliers"},
                     {"category": "id", "supplier": "id"},
                     cat_add=lambda m, db, n, i: m.CategoryRepository(db).add(n, "d"),
                     sup_add=lambda m, db, n, i: m.SupplierRepository(db).add(
                         n, "a@b.c", "555000", "addr", "co"),
                     cat_del=lambda m, db, k: m.CategoryRepository(db).delete(k),
                     sup_del=lambda m, db, k: m.SupplierRepository(db).delete(k)),
    ("gpt", 2): _gpt("Database",
                     {"category": "categories", "supplier": "suppliers"},
                     {"category": "name", "supplier": "sup_id"},
                     cat_add=lambda m, db, n, i: m.CategoryRepository(db).add(
                         m.Category(name=n, description="d")),
                     sup_add=lambda m, db, n, i: m.SupplierRepository(db).add(
                         m.Supplier(sup_id=i, name=n, email="a@b.c", phone="555000",
                                    address="addr")),
                     cat_del=lambda m, db, k: m.CategoryRepository(db).delete(k),
                     sup_del=lambda m, db, k: m.SupplierRepository(db).delete(k)),
    ("gpt", 3): _gpt("Database",
                     {"category": "categories", "supplier": "suppliers"},
                     {"category": "id", "supplier": "id"},
                     cat_add=lambda m, db, n, i: m.CategoryRepository(db).add(n, "d"),
                     sup_add=lambda m, db, n, i: m.SupplierRepository(db).add(
                         n, "a@b.c", "555000", "co", "addr"),
                     cat_del=lambda m, db, k: m.CategoryRepository(db).delete(k),
                     sup_del=lambda m, db, k: m.SupplierRepository(db).delete(k)),
    ("deepseek", 1): _deepseek_db(
        "Database",
        cat_add=lambda m, db, n, i: db.insert_category(m.Category(name=n)),
        sup_add=lambda m, db, n, i: db.insert_supplier(
            m.Supplier(name=n, contact="555000", email="a@b.c", address="addr", gst="g")),
        cat_del=lambda m, db, k: db.delete_category(int(k)),
        sup_del=lambda m, db, k: db.delete_supplier(int(k))),
    ("deepseek", 2): _deepseek_db(
        "DatabaseManager",
        cat_add=lambda m, db, n, i: db.insert_category(n),
        sup_add=lambda m, db, n, i: db.insert_supplier((n, "555000", "a@b.c", "addr")),
        cat_del=lambda m, db, k: db.delete_category(int(k)),
        sup_del=lambda m, db, k: db.delete_supplier(int(k))),
    ("deepseek", 3): _deepseek_run3(),
    ("gemini", 1): _gemini("CategoryClass", "SupplierClass", "create_database"),
    ("gemini", 2): _gemini("CategoryClass", "SupplierClass", "setup_database"),
    ("gemini", 3): _gemini("Category", "Supplier", "create_db"),
})


def build_driver(model, module):
    """Dispatch on (model, RUN) — a regeneration is a different program."""
    run = int(os.environ.get("RUN", "0"))
    try:
        gen = GENERATIONS[(model, run)]
    except KeyError:
        raise KeyError(f"no hand-written driver for {model}.run{run}") from None
    return SpecDriver(gen, module)
