import contextlib
import inspect
import os
import sys
import sqlite3
import tempfile

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "adapter_harness")))
import faketk  # noqa: E402

BOGUS = "999999"


# ── Tk stand-ins ────────────────────────────────────────────────────────────

class _Var:
    def __init__(self, value=""):
        self._v = str(value)

    def get(self):
        return self._v

    def set(self, value):
        self._v = str(value)


class _Text:
    def __init__(self, value="parts"):
        self._v = value

    def get(self, *_a, **_k):
        return self._v


class _Msg:
    def __init__(self):
        self.errors, self.infos = [], []

    def showerror(self, *a, **_k):
        self.errors.append(a)

    def showwarning(self, *a, **_k):
        self.errors.append(a)

    def showinfo(self, *a, **_k):
        self.infos.append(a)

    def askyesno(self, *_a, **_k):
        return True

    def askquestion(self, *_a, **_k):
        return "yes"


class _Self:
    """Synthetic `self` for an unbound handler.

    `noops` are presentation-only methods the handler calls (refresh a tree,
    clear a form). `borrow` pulls real methods off the generation's own class and
    binds them here (e.g. claude.run3's get_entry_value). Anything undeclared
    raises AttributeError, so a stale driver fails loudly instead of passing
    quietly.
    """

    def __init__(self, cls=None, noops=(), borrow=(), **attrs):
        self.__dict__.update(attrs)
        self.__dict__["_noops"] = set(noops)
        for name in borrow:
            self.__dict__[name] = inspect.getattr_static(cls, name).__get__(self)

    def __getattr__(self, name):
        if name in self.__dict__.get("_noops", ()):
            return lambda *a, **k: None
        raise AttributeError(name)


@contextlib.contextmanager
def _in_dir(path):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


@contextlib.contextmanager
def _msgbox(module):
    rec = _Msg()
    had = hasattr(module, "messagebox")
    old = getattr(module, "messagebox", None)
    module.messagebox = rec
    try:
        yield rec
    finally:
        if had:
            module.messagebox = old
        else:
            try:
                del module.messagebox
            except AttributeError:
                pass


def _count(cwd, db, table):
    path = os.path.join(cwd, db)
    if not os.path.exists(path):
        return 0
    con = sqlite3.connect(path)
    try:
        return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except sqlite3.OperationalError:
        return 0
    finally:
        con.close()


def _first(cwd, db, table, col):
    path = os.path.join(cwd, db)
    if not os.path.exists(path):
        return None
    con = sqlite3.connect(path)
    try:
        row = con.execute(f"SELECT {col} FROM {table} LIMIT 1").fetchone()
        return None if row is None else str(row[0])
    except sqlite3.OperationalError:
        return None
    finally:
        con.close()


# ── generation spec ─────────────────────────────────────────────────────────

class Gen:
    """One generation's concrete driving recipe.

    bootstrap(m, cwd)          create that generation's schema
    add(m, cwd, ent, name, id) drive its real add path for entity `ent`
    delete(m, cwd, ent, key)   drive its real delete path
    key_col[ent]               column the delete path keys off
    """

    def __init__(self, db, tables, key_col, bootstrap, add, delete, note=""):
        self.db, self.tables, self.key_col = db, tables, key_col
        self.bootstrap, self.add, self.delete, self.note = bootstrap, add, delete, note


# ── executor: the 10 contract behaviours, identical for every generation ────

class SpecDriver:
    def __init__(self, gen, module):
        self.g, self.m = gen, module

    def _fresh(self):
        cwd = tempfile.mkdtemp(prefix="ims_")
        if self.g.bootstrap:
            with _in_dir(cwd), _msgbox(self.m):
                self.g.bootstrap(self.m, cwd)
        return cwd

    def _add(self, cwd, ent, name, ident):
        with _in_dir(cwd), _msgbox(self.m):
            try:
                self.g.add(self.m, cwd, ent, name, ident)
            except Exception:  # noqa: BLE001 — a raise IS the rejection signal
                pass

    def _del(self, cwd, ent, key):
        with _in_dir(cwd), _msgbox(self.m):
            try:
                self.g.delete(self.m, cwd, ent, key)
            except Exception:  # noqa: BLE001
                pass

    def _n(self, cwd, ent):
        return _count(cwd, self.g.db, self.g.tables[ent])

    def _persists(self, ent):
        cwd = self._fresh()
        self._add(cwd, ent, "Books" if ent == "category" else "Acme", "101")
        return self._n(cwd, ent)

    def _blank(self, ent):
        cwd = self._fresh()
        self._add(cwd, ent, "", "")
        n = self._n(cwd, ent)
        return n == 0, n

    def _dup(self, ent):
        cwd = self._fresh()
        val = "Books" if ent == "category" else "Acme"
        self._add(cwd, ent, val, "101")
        self._add(cwd, ent, val, "102")
        return self._n(cwd, ent)

    def _del_removes(self, ent):
        cwd = self._fresh()
        self._add(cwd, ent, "Books" if ent == "category" else "Acme", "101")
        if self._n(cwd, ent) != 1:
            return -1
        key = _first(cwd, self.g.db, self.g.tables[ent], self.g.key_col[ent])
        self._del(cwd, ent, key)
        return self._n(cwd, ent)

    def _del_unknown(self, ent):
        cwd = self._fresh()
        self._add(cwd, ent, "Books" if ent == "category" else "Acme", "101")
        self._del(cwd, ent, BOGUS)
        return self._n(cwd, ent) == 1

    def category_add_persists(self):            return self._persists("category")
    def category_empty_name_rejected(self):     return self._blank("category")
    def category_duplicate_rejected(self):      return self._dup("category")
    def category_delete_removes(self):          return self._del_removes("category")
    def category_delete_unknown_rejected(self): return self._del_unknown("category")

    def supplier_add_persists(self):            return self._persists("supplier")
    def supplier_missing_invoice_rejected(self):return self._blank("supplier")
    def supplier_duplicate_rejected(self):      return self._dup("supplier")
    def supplier_delete_removes(self):          return self._del_removes("supplier")
    def supplier_delete_unknown_rejected(self): return self._del_unknown("supplier")


# ── deepseek run3: logic lives in Button command= closures ─────────────────

def _deepseek_run3():
    """generic_crud_window builds the form and hands add/delete to Buttons.
    Driven by capturing those callbacks — see adapter_harness/faketk.py."""
    COLS = {"category": ["id", "name"],
            "supplier": ["id", "name", "contact", "email", "address"]}
    TABLE = {"category": "categories", "supplier": "suppliers"}

    def _open(m, conn, ent):
        faketk.install(m)
        faketk.reset()
        app = _Self(noops=("clear_content",), conn=conn, _children=[])
        m.InventoryManagementSystem.generic_crud_window(
            app, "W", TABLE[ent], COLS[ent])
        return dict(faketk.buttons())

    def bootstrap(m, _cwd):
        faketk.install(m)
        m.setup_database()

    def add(m, cwd, ent, name, ident):
        import sqlite3 as _s
        conn = _s.connect(os.path.join(cwd, m.DB_NAME))
        try:
            btns = _open(m, conn, ent)
            cells = faketk.closure_of(btns["Add"])
            fields = [c for c in COLS[ent] if c != "id"]
            for i, col in enumerate(fields):
                cells["entries"][col].insert(0, name if i == 0 else (ident or "x"))
            btns["Add"]()
        finally:
            conn.close()

    def delete(m, cwd, ent, key):
        import sqlite3 as _s
        conn = _s.connect(os.path.join(cwd, m.DB_NAME))
        try:
            btns = _open(m, conn, ent)
            cells = faketk.closure_of(btns["Delete"])
            tree = cells.get("tree")
            if tree is not None and getattr(tree, "_rows", None):
                # delete_record reads the id from the selected tree row
                tree._rows = {k: v for k, v in tree._rows.items() if str(v[0]) == str(key)}
            btns["Delete"]()
        finally:
            conn.close()

    return Gen(db="inventory.db",
               tables={"category": "categories", "supplier": "suppliers"},
               key_col={"category": "id", "supplier": "id"},
               bootstrap=bootstrap, add=add, delete=delete)


# ── claude: Tk frames; handler reads a per-run field store, deletes by rowid ─

def _claude(cls_prefix, store, cat_id_key, sup_fields, cat_fields, boot, borrow=()):
    CAT = f"{cls_prefix}Category{'Frame' if cls_prefix == '' else ''}"

    def bootstrap(m, _cwd):
        getattr(m, boot)()

    def _drive(m, ent, method, fields, noops):
        cls = getattr(m, ("CategoryFrame" if ent == "category" else "SupplierFrame")
                      if cls_prefix == "F" else
                      ("CategoryWindow" if ent == "category" else "SupplierWindow"))
        fn = inspect.getattr_static(cls, method)
        this = _Self(cls=cls, noops=noops, borrow=borrow, **{store: fields})
        fn(this)

    def add(m, _cwd, ent, name, ident):
        if ent == "category":
            fields = {k: _Var(name if k == "name" else (ident if k == cat_id_key else "d"))
                      for k in cat_fields}
            _drive(m, ent, "add_category", fields, ("clear_form", "load_data", "load_categories"))
        else:
            fields = {k: _Var(name if k == "name" else (ident if k.endswith("_id") else "x"))
                      for k in sup_fields}
            _drive(m, ent, "add_supplier", fields, ("clear_form", "load_data", "load_suppliers"))

    def delete(m, _cwd, ent, key):
        cls = getattr(m, ("CategoryFrame" if ent == "category" else "SupplierFrame")
                      if cls_prefix == "F" else
                      ("CategoryWindow" if ent == "category" else "SupplierWindow"))
        method = "delete_category" if ent == "category" else "delete_supplier"
        fn = inspect.getattr_static(cls, method)
        this = _Self(cls=cls, noops=("clear_form", "load_data", "load_categories", "load_suppliers"),
                     selected_id=key)
        fn(this)

    return Gen(db="inventory.db",
               tables={"category": "categories", "supplier": "suppliers"},
               key_col={"category": "id", "supplier": "id"},
               bootstrap=bootstrap, add=add, delete=delete)


# ── gemini: origin-style var_* handlers, own ims.db ─────────────────────────

def _gemini(cat_cls, sup_cls, boot):
    def bootstrap(m, _cwd):
        getattr(m, boot)()

    def add(m, _cwd, ent, name, ident):
        if ent == "category":
            cls = getattr(m, cat_cls)
            this = _Self(cls=cls, noops=("show", "clear"), root=object(),
                         var_name=_Var(name), var_cat_id=_Var(""))
        else:
            cls = getattr(m, sup_cls)
            this = _Self(cls=cls, noops=("show", "clear"), root=object(),
                         var_sup_invoice=_Var(ident), var_name=_Var(name),
                         var_contact=_Var("555000"), txt_desc=_Text("parts"))
        inspect.getattr_static(cls, "add")(this)

    def delete(m, _cwd, ent, key):
        if ent == "category":
            cls = getattr(m, cat_cls)
            this = _Self(cls=cls, noops=("show", "clear"), root=object(),
                         var_cat_id=_Var(key), var_name=_Var(""))
        else:
            cls = getattr(m, sup_cls)
            this = _Self(cls=cls, noops=("show", "clear"), root=object(),
                         var_sup_invoice=_Var(key), var_name=_Var(""),
                         var_contact=_Var(""), txt_desc=_Text(""))
        inspect.getattr_static(cls, "delete")(this)

    return Gen(db="ims.db",
               tables={"category": "category", "supplier": "supplier"},
               key_col={"category": "cid", "supplier": "invoice"},
               bootstrap=bootstrap, add=add, delete=delete)


# ── gpt: layered repositories, GUI-free ─────────────────────────────────────

def _gpt(db_attr, tables, key_col, cat_add, sup_add, cat_del, sup_del):
    def _db(m, cwd):
        return m.Database(os.path.join(cwd, "app.db"))

    def add(m, cwd, ent, name, ident):
        db = _db(m, cwd)
        try:
            (cat_add if ent == "category" else sup_add)(m, db, name, ident)
        finally:
            db.close()

    def delete(m, cwd, ent, key):
        db = _db(m, cwd)
        try:
            (cat_del if ent == "category" else sup_del)(m, db, key)
        finally:
            db.close()

    return Gen(db="app.db", tables=tables, key_col=key_col,
               bootstrap=None, add=add, delete=delete)


# ── deepseek run0: one generic add_record on the app object ─────────────────

def _deepseek_run0():
    CAT_F, SUP_F = ("name", "description"), ("name", "contact", "email", "address")

    def _app(m, cwd):
        with _in_dir(cwd):
            return _Self(noops=("load_tree", "clear_entries"),
                         db=m.DatabaseManager("inventory.db"))

    def add(m, cwd, ent, name, _ident):
        fields = CAT_F if ent == "category" else SUP_F
        vals = [name] + ["x"] * (len(fields) - 1)
        app = _app(m, cwd)
        entries = {f: _Var(v) for f, v in zip(fields, vals)}
        table = "categories" if ent == "category" else "suppliers"
        fn = inspect.getattr_static(m.InventoryManagementApp, "add_record")
        try:
            fn(app, entries, table, list(fields), list(fields), None, _Var(""))
        finally:
            app.db.close()

    def delete(m, cwd, ent, key):
        app = _app(m, cwd)
        table = "categories" if ent == "category" else "suppliers"
        fn = inspect.getattr_static(m.InventoryManagementApp, "delete_record")
        try:
            fn(app, table, "id", None, _Var(key))
        finally:
            app.db.close()

    return Gen(db="inventory.db",
               tables={"category": "categories", "supplier": "suppliers"},
               key_col={"category": "id", "supplier": "id"},
               bootstrap=lambda m, _c: m.DatabaseManager("inventory.db").close(),
               add=add, delete=delete)


# ── deepseek run1/2: persistence methods live on the Database object ────────

def _deepseek_db(db_cls, cat_add, sup_add, cat_del, sup_del):
    def _db(m, cwd):
        with _in_dir(cwd):
            return getattr(m, db_cls)("inventory.db")

    def add(m, cwd, ent, name, ident):
        db = _db(m, cwd)
        (cat_add if ent == "category" else sup_add)(m, db, name, ident)

    def delete(m, cwd, ent, key):
        db = _db(m, cwd)
        (cat_del if ent == "category" else sup_del)(m, db, key)

    return Gen(db="inventory.db",
               tables={"category": "categories", "supplier": "suppliers"},
               key_col={"category": "id", "supplier": "id"},
               bootstrap=lambda m, _c: getattr(m, db_cls)("inventory.db"),
               add=add, delete=delete)


# ── the 4 run0 generations (the main study scores run0 only) ───────────────

GENERATIONS = {
    "claude": _claude("", "vars", "cat_id",
                           ("name", "sup_id", "contact", "email", "address", "company", "gst"),
                           ("name", "cat_id", "description"), "create_database"),
    "gpt": _gpt("Database",
                     {"category": "category", "supplier": "supplier"},
                     {"category": "cat_id", "supplier": "invoice"},
                     cat_add=lambda m, db, n, i: m.CategoryRepository(db).add(
                         m.Category(cat_id=i or "C1", name=n)),
                     sup_add=lambda m, db, n, i: m.SupplierRepository(db).add(
                         m.Supplier(invoice=i, name=n, contact="555000", desc="parts")),
                     cat_del=lambda m, db, k: m.CategoryRepository(db).delete(k),
                     sup_del=lambda m, db, k: m.SupplierRepository(db).delete(k)),
    "deepseek": _deepseek_run0(),
    "gemini": _gemini("CategoryClass", "SupplierClass", "create_db"),
}


def build_driver(model, module):
    """One hand-written driver per model, written against that model's run0."""
    return SpecDriver(GENERATIONS[model], module)
