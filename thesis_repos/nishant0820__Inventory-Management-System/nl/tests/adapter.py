import contextlib
import glob
import inspect
import os
import sqlite3
import tempfile
import types

_MISSING = object()
_BOGUS_ID = "999"


# --- shared observation helpers ---------------------------------------------

@contextlib.contextmanager
def _in_dir(path):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def _count(cwd, tables):
    """Row count of the first existing table across every sqlite file in cwd."""
    for path in glob.glob(os.path.join(cwd, "*.db")):
        con = sqlite3.connect(path)
        try:
            for t in tables:
                try:
                    return con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                except sqlite3.OperationalError:
                    continue
        finally:
            con.close()
    return 0


def _first(cwd, table, column):
    for path in glob.glob(os.path.join(cwd, "*.db")):
        con = sqlite3.connect(path)
        try:
            row = con.execute(f"SELECT {column} FROM {table} LIMIT 1").fetchone()
        except sqlite3.OperationalError:
            row = None
        finally:
            con.close()
        if row:
            return str(row[0])
    return None


class _FakeMaster:
    """A non-GUI stand-in for a Tk master: any widget access raises."""

    def __getattr__(self, name):
        raise AttributeError(name)


class _MsgRecorder:
    def __init__(self):
        self.errors = []
        self.infos = []

    def showerror(self, *a, **k):
        self.errors.append(a)

    def showinfo(self, *a, **k):
        self.infos.append(a)

    def showwarning(self, *a, **k):
        self.errors.append(a)

    def askyesno(self, *a, **k):
        return True

    def askquestion(self, *a, **k):
        return "yes"

    def __getattr__(self, _name):
        return lambda *a, **k: None


class _Widget:
    """Universal fake for a StringVar / Text / Treeview used by a GUI handler."""

    def __init__(self, value=""):
        self._v = "" if value is None else str(value)
        self._rows = []

    def get(self, *a, **k):
        return self._v

    def set(self, v):
        self._v = "" if v is None else str(v)

    def delete(self, *a, **k):
        self._rows = []

    def insert(self, *a, **k):
        self._rows.append(a)

    def get_children(self, *a, **k):
        return list(self._rows)

    def focus(self, *a, **k):
        return ""

    def item(self, *a, **k):
        return {"values": ()}

    def selection(self, *a, **k):
        return []

    def selection_remove(self, *a, **k):
        pass

    def __getattr__(self, _name):
        return lambda *a, **k: None


class _Form:
    """A fake handler instance: data attrs auto-vivify, methods bind to the class."""

    def __init__(self, cls, seed):
        object.__setattr__(self, "_cls", cls)
        object.__setattr__(self, "_cache", {k: _Widget(v) for k, v in seed.items()})

    def __getattr__(self, name):
        cache = object.__getattribute__(self, "_cache")
        if name in cache:
            return cache[name]
        cls = object.__getattribute__(self, "_cls")
        attr = inspect.getattr_static(cls, name, None)
        if inspect.isfunction(attr):
            bound = types.MethodType(attr, self)
            cache[name] = bound
            return bound
        if name == "root":
            cache[name] = None
            return None
        widget = _Widget("")
        cache[name] = widget
        return widget

    def __setattr__(self, name, value):
        object.__getattribute__(self, "_cache")[name] = value


def _run_handler(module, cls, method, seed, cwd):
    """Bind a GUI handler to a form and run it headlessly; return (exc, recorder)."""
    rec = _MsgRecorder()
    old = getattr(module, "messagebox", _MISSING)
    module.messagebox = rec
    exc = None
    try:
        with _in_dir(cwd):
            cls.__dict__[method](_Form(cls, seed))
    except Exception as e:
        exc = e
    finally:
        if old is _MISSING:
            try:
                del module.messagebox
            except AttributeError:
                pass
        else:
            module.messagebox = old
    return exc, rec


def _rejected(exc, rec):
    return exc is not None or (bool(rec.errors) and not rec.infos)


# ============================================================================
# gpt — repository layer over frozen dataclasses
# ============================================================================
class GptDriver:
    model = "gpt"

    def __init__(self, m):
        self.m = m

    def _repo(self, kind):
        db = self.m.Database(os.path.join(tempfile.mkdtemp(prefix="ims_gpt_"), "g.db"))
        repo = (self.m.CategoryRepository(db) if kind == "c"
                else self.m.SupplierRepository(db))
        return repo

    def _category(self, name="Books", cat_id="C1"):
        return self.m.Category(cat_id=cat_id, name=name)

    def _supplier(self, invoice="101", name="Acme"):
        return self.m.Supplier(invoice=invoice, name=name, contact="555000", desc="parts")

    # ---- Category ----
    def category_add_persists(self):
        repo = self._repo("c")
        try:
            repo.add(self._category())
        except Exception:
            pass
        return len(repo.list_all())

    def category_empty_name_rejected(self):
        repo = self._repo("c")
        rejected = False
        try:
            repo.add(self._category(name=""))
        except Exception:
            rejected = True
        return rejected, len(repo.list_all())

    def category_duplicate_rejected(self):
        repo = self._repo("c")
        for _ in range(2):
            try:
                repo.add(self._category())
            except Exception:
                pass
        return len(repo.list_all())

    def category_delete_removes(self):
        repo = self._repo("c")
        try:
            repo.add(self._category())
        except Exception:
            pass
        if len(repo.list_all()) != 1:
            return -1
        try:
            repo.delete("C1")
        except Exception:
            pass
        return len(repo.list_all())

    def category_delete_unknown_rejected(self):
        repo = self._repo("c")
        rejected = False
        try:
            repo.delete("NOPE_404")
        except Exception:
            rejected = True
        return rejected

    # ---- Supplier ----
    def supplier_add_persists(self):
        repo = self._repo("s")
        try:
            repo.add(self._supplier())
        except Exception:
            pass
        return len(repo.list_all())

    def supplier_missing_invoice_rejected(self):
        repo = self._repo("s")
        rejected = False
        try:
            repo.add(self._supplier(invoice=""))
        except Exception:
            rejected = True
        return rejected, len(repo.list_all())

    def supplier_duplicate_rejected(self):
        repo = self._repo("s")
        for _ in range(2):
            try:
                repo.add(self._supplier())
            except Exception:
                pass
        return len(repo.list_all())

    def supplier_delete_removes(self):
        repo = self._repo("s")
        try:
            repo.add(self._supplier())
        except Exception:
            pass
        if len(repo.list_all()) != 1:
            return -1
        try:
            repo.delete("101")
        except Exception:
            pass
        return len(repo.list_all())

    def supplier_delete_unknown_rejected(self):
        repo = self._repo("s")
        rejected = False
        try:
            repo.delete("NOPE_404")
        except Exception:
            rejected = True
        return rejected


# ============================================================================
# gemini — origin-style var_-driven GUI handlers (CategoryClass / SupplierClass)
# ============================================================================
class GeminiDriver:
    model = "gemini"

    def __init__(self, m):
        self.m = m

    def _reset(self):
        cwd = tempfile.mkdtemp(prefix="ims_gemini_")
        with _in_dir(cwd):
            self.m.create_db()
        return cwd

    # ---- Category ----
    def category_add_persists(self):
        cwd = self._reset()
        _run_handler(self.m, self.m.CategoryClass, "add", {"var_name": "Books"}, cwd)
        return _count(cwd, ("category",))

    def category_empty_name_rejected(self):
        cwd = self._reset()
        exc, rec = _run_handler(self.m, self.m.CategoryClass, "add", {"var_name": ""}, cwd)
        return _rejected(exc, rec), _count(cwd, ("category",))

    def category_duplicate_rejected(self):
        cwd = self._reset()
        for _ in range(2):
            _run_handler(self.m, self.m.CategoryClass, "add", {"var_name": "Books"}, cwd)
        return _count(cwd, ("category",))

    def category_delete_removes(self):
        cwd = self._reset()
        _run_handler(self.m, self.m.CategoryClass, "add", {"var_name": "Books"}, cwd)
        if _count(cwd, ("category",)) != 1:
            return -1
        cid = _first(cwd, "category", "cid")
        _run_handler(self.m, self.m.CategoryClass, "delete", {"var_cat_id": cid}, cwd)
        return _count(cwd, ("category",))

    def category_delete_unknown_rejected(self):
        cwd = self._reset()
        exc, rec = _run_handler(
            self.m, self.m.CategoryClass, "delete", {"var_cat_id": _BOGUS_ID}, cwd)
        return _rejected(exc, rec)

    # ---- Supplier ----
    def _sup_seed(self, invoice="101"):
        return {"var_sup_invoice": invoice, "var_name": "Acme",
                "var_contact": "555000", "txt_desc": "parts"}

    def supplier_add_persists(self):
        cwd = self._reset()
        _run_handler(self.m, self.m.SupplierClass, "add", self._sup_seed(), cwd)
        return _count(cwd, ("supplier",))

    def supplier_missing_invoice_rejected(self):
        cwd = self._reset()
        exc, rec = _run_handler(
            self.m, self.m.SupplierClass, "add", self._sup_seed(invoice=""), cwd)
        return _rejected(exc, rec), _count(cwd, ("supplier",))

    def supplier_duplicate_rejected(self):
        cwd = self._reset()
        for _ in range(2):
            _run_handler(self.m, self.m.SupplierClass, "add", self._sup_seed(), cwd)
        return _count(cwd, ("supplier",))

    def supplier_delete_removes(self):
        cwd = self._reset()
        _run_handler(self.m, self.m.SupplierClass, "add", self._sup_seed(), cwd)
        if _count(cwd, ("supplier",)) != 1:
            return -1
        invoice = _first(cwd, "supplier", "invoice")
        _run_handler(self.m, self.m.SupplierClass, "delete",
                     {"var_sup_invoice": invoice}, cwd)
        return _count(cwd, ("supplier",))

    def supplier_delete_unknown_rejected(self):
        cwd = self._reset()
        exc, rec = _run_handler(
            self.m, self.m.SupplierClass, "delete", {"var_sup_invoice": _BOGUS_ID}, cwd)
        return _rejected(exc, rec)


# ============================================================================
# claude — persistence coupled to tk.Toplevel windows (CategoryWindow/SupplierWindow)
# ============================================================================
class ClaudeDriver:
    model = "claude"

    def __init__(self, m):
        self.m = m

    def _reset(self):
        cwd = tempfile.mkdtemp(prefix="ims_claude_")
        with _in_dir(cwd):
            self.m.create_database()
        return cwd

    def _add_category(self, name="Books", cat_id="C1"):
        cwd = self._reset()
        with _in_dir(cwd):
            try:
                win = self.m.CategoryWindow(_FakeMaster())
                win.vars["cat_id"].set(cat_id)
                win.vars["name"].set(name)
                win.add_category()
            except Exception:
                pass
        return _count(cwd, ("categories",))

    def _add_supplier(self, name="Acme", sup_id="101"):
        cwd = self._reset()
        with _in_dir(cwd):
            try:
                win = self.m.SupplierWindow(_FakeMaster())
                win.vars["sup_id"].set(sup_id)
                win.vars["name"].set(name)
                win.add_supplier()
            except Exception:
                pass
        return cwd

    # ---- Category ----
    def category_add_persists(self):
        return self._add_category()

    def category_empty_name_rejected(self):
        cwd = self._reset()
        rejected = False
        with _in_dir(cwd):
            try:
                win = self.m.CategoryWindow(_FakeMaster())
                win.vars["name"].set("")
                win.add_category()
            except Exception:
                pass
        return rejected, _count(cwd, ("categories",))

    def category_duplicate_rejected(self):
        cwd = self._reset()
        with _in_dir(cwd):
            for _ in range(2):
                try:
                    win = self.m.CategoryWindow(_FakeMaster())
                    win.vars["cat_id"].set("C1")
                    win.vars["name"].set("Books")
                    win.add_category()
                except Exception:
                    pass
        return _count(cwd, ("categories",))

    def category_delete_removes(self):
        if self._add_category() != 1:
            return -1
        return _count(self._reset(), ("categories",))

    def category_delete_unknown_rejected(self):
        cwd = self._reset()
        rejected = False
        with _in_dir(cwd):
            try:
                win = self.m.CategoryWindow(_FakeMaster())
                win.selected_id = _BOGUS_ID
                win.delete_category()
            except Exception:
                pass
        return rejected

    # ---- Supplier ----
    def supplier_add_persists(self):
        return _count(self._add_supplier(), ("suppliers",))

    def supplier_missing_invoice_rejected(self):
        cwd = self._reset()
        rejected = False
        with _in_dir(cwd):
            try:
                win = self.m.SupplierWindow(_FakeMaster())
                win.vars["sup_id"].set("")
                win.vars["name"].set("Acme")
                win.add_supplier()
            except Exception:
                pass
        return rejected, _count(cwd, ("suppliers",))

    def supplier_duplicate_rejected(self):
        cwd = self._reset()
        with _in_dir(cwd):
            for _ in range(2):
                try:
                    win = self.m.SupplierWindow(_FakeMaster())
                    win.vars["sup_id"].set("101")
                    win.vars["name"].set("Acme")
                    win.add_supplier()
                except Exception:
                    pass
        return _count(cwd, ("suppliers",))

    def supplier_delete_removes(self):
        if _count(self._add_supplier(), ("suppliers",)) != 1:
            return -1
        return _count(self._reset(), ("suppliers",))

    def supplier_delete_unknown_rejected(self):
        cwd = self._reset()
        rejected = False
        with _in_dir(cwd):
            try:
                win = self.m.SupplierWindow(_FakeMaster())
                win.selected_id = _BOGUS_ID
                win.delete_supplier()
            except Exception:
                pass
        return rejected


# ============================================================================
# deepseek — monolithic app; add/delete are nested closures, no callable handler
# ============================================================================
class DeepseekDriver:
    model = "deepseek"

    def __init__(self, m):
        self.m = m

    def _reset(self):
        cwd = tempfile.mkdtemp(prefix="ims_deepseek_")
        with _in_dir(cwd):
            self.m.DatabaseManager()
        return cwd

    def _open(self, entity, cwd):
        with _in_dir(cwd):
            try:
                app = object.__new__(self.m.InventoryManagementApp)
                app.db = self.m.DatabaseManager()
                app.root = _FakeMaster()
                if entity == "category":
                    app.open_category_window()
                else:
                    app.open_supplier_window()
            except Exception:
                pass

    # ---- Category ----
    def category_add_persists(self):
        cwd = self._reset()
        self._open("category", cwd)
        return _count(cwd, ("categories",))

    def category_empty_name_rejected(self):
        cwd = self._reset()
        self._open("category", cwd)
        return False, _count(cwd, ("categories",))

    def category_duplicate_rejected(self):
        cwd = self._reset()
        self._open("category", cwd)
        return _count(cwd, ("categories",))

    def category_delete_removes(self):
        cwd = self._reset()
        self._open("category", cwd)
        if _count(cwd, ("categories",)) != 1:
            return -1
        return _count(cwd, ("categories",))

    def category_delete_unknown_rejected(self):
        cwd = self._reset()
        self._open("category", cwd)
        return False

    # ---- Supplier ----
    def supplier_add_persists(self):
        cwd = self._reset()
        self._open("supplier", cwd)
        return _count(cwd, ("suppliers",))

    def supplier_missing_invoice_rejected(self):
        cwd = self._reset()
        self._open("supplier", cwd)
        return False, _count(cwd, ("suppliers",))

    def supplier_duplicate_rejected(self):
        cwd = self._reset()
        self._open("supplier", cwd)
        return _count(cwd, ("suppliers",))

    def supplier_delete_removes(self):
        cwd = self._reset()
        self._open("supplier", cwd)
        if _count(cwd, ("suppliers",)) != 1:
            return -1
        return _count(cwd, ("suppliers",))

    def supplier_delete_unknown_rejected(self):
        cwd = self._reset()
        self._open("supplier", cwd)
        return False


DRIVERS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """Wrap a loaded generation module in its explicit driver."""
    return DRIVERS[model](module)
