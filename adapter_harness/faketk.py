"""A tkinter stand-in that constructs without a display and captures callbacks.

Why this exists
---------------
Several generations put their persistence logic in a *closure* attached to a
widget rather than in a method::

    def generic_crud_window(self, title, table, columns, ...):
        window = tk.Toplevel(self)              # needs a window server
        ...
        def add_record():                       # not an attribute of anything
            self.conn.execute(sql, values)
        tk.Button(btn_frame, text="Add", command=add_record)

`inspect.getattr_static` cannot reach `add_record` — it is not on any class — so
such a generation looks undrivable and would be scored 0 for a reason that is
about the harness, not the code.

But the callback is not hidden: it is *handed to a widget*. Swap tkinter for the
stubs below and the fake `Button` records its ``command=``. Calling the real
method then yields the real callback, and ``callback.__closure__`` exposes the
free variables it reads (the ``entries`` dict of fake Entry widgets, the table
name, the selection var), so a driver can seed inputs and invoke the generation's
own handler. No display, no Xvfb, cross-platform.

This does NOT make driving generic: a driver still names the method, its
arguments and the button label. It only removes the toolkit as an obstacle.

Usage
-----
    from faketk import install, buttons, closure_of, reset

    tkmod, ttkmod, msg = install(module)   # swap module.tk / .ttk / .messagebox
    reset()
    module.SomeApp.build_window(self_stub, "Title", "categories", ["id", "name"])
    add = dict(buttons())["Add"]
    cells = closure_of(add)
    cells["entries"]["name"].insert(0, "Books")
    add()

`install` only replaces attributes the module actually has, and returns the
message recorder so a driver can tell an accepted operation (showinfo) from a
rejected one (showerror) — the CONTRACT.md rejection signal.
"""

import types

END = "end"

_registry: dict = {}


def reset() -> dict:
    """Forget widgets captured so far. Call before driving each window."""
    _registry.clear()
    return _registry


def buttons():
    """[(text, command), ...] for every Button built since the last reset()."""
    return _registry.get("buttons", [])


def entries():
    """Every Entry built since the last reset(), in construction order."""
    return _registry.get("entries", [])


def closure_of(fn) -> dict:
    """{free variable name: value} for a captured callback.

    This is how a driver reaches the widgets a closure reads without having to
    guess construction order.
    """
    if not getattr(fn, "__closure__", None):
        return {}
    return dict(zip(fn.__code__.co_freevars,
                    [c.cell_contents for c in fn.__closure__]))


# ── widgets ─────────────────────────────────────────────────────────────────

class _W:
    """Generic widget. Unknown attributes are no-ops, so layout/styling calls
    (pack/grid/place/configure/bind/...) succeed without being enumerated."""

    def __init__(self, master=None, **kw):
        self._kw = kw
        self._children = []
        kids = getattr(master, "_children", None)
        if isinstance(kids, list):
            kids.append(self)
        _registry.setdefault("all", []).append(self)

    def __getattr__(self, name):
        return lambda *a, **k: None


class Misc(_W): pass
class Tk(_W): pass
class Toplevel(_W): pass
class Frame(_W): pass
class LabelFrame(_W): pass
class Label(_W): pass
class Canvas(_W): pass
class Scrollbar(_W): pass
class Menu(_W): pass
class Checkbutton(_W): pass
class Radiobutton(_W): pass
class Listbox(_W): pass


class Entry(_W):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._v = ""
        _registry.setdefault("entries", []).append(self)

    def get(self):
        return self._v

    def insert(self, _index, value):
        self._v = str(value)

    def delete(self, *_a, **_k):
        self._v = ""


class Text(_W):
    """tk.Text reads with .get('1.0', END) and is isinstance-checked by some
    generations, so it must be a distinct class from Entry."""

    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._v = ""

    def get(self, *_a, **_k):
        return self._v

    def insert(self, *a, **_k):
        self._v = str(a[-1]) if a else ""

    def delete(self, *_a, **_k):
        self._v = ""


class Button(_W):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        _registry.setdefault("buttons", []).append(
            (str(kw.get("text", "")), kw.get("command")))


class StringVar:
    def __init__(self, master=None, value="", name=None):
        self._v = "" if value is None else str(value)

    def get(self):
        return self._v

    def set(self, value):
        self._v = "" if value is None else str(value)


class IntVar(StringVar): pass
class DoubleVar(StringVar): pass
class BooleanVar(StringVar): pass


class Combobox(_W):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._v = ""

    def get(self):
        return self._v

    def set(self, value):
        self._v = str(value)


class Treeview(_W):
    def __init__(self, master=None, **kw):
        super().__init__(master, **kw)
        self._rows = {}

    def insert(self, _parent, _index, values=(), **_k):
        iid = f"I{len(self._rows)}"
        self._rows[iid] = tuple(values)
        return iid

    def get_children(self, *_a):
        return list(self._rows)

    def delete(self, *iids):
        for i in iids:
            self._rows.pop(i, None)

    def selection(self):
        return list(self._rows)[:1]

    def item(self, iid, option=None, **kw):
        """Real ttk semantics: item(iid) -> the full option dict, but
        item(iid, 'values') -> that option's value directly. Generations index
        the result as `tree.item(sel, 'values')[0]`, so returning a dict in the
        second form silently breaks them."""
        row = self._rows.get(iid, ())
        if kw.get("values") is not None:
            self._rows[iid] = tuple(kw["values"])
            return None
        opts = {"values": row, "text": "", "tags": ()}
        if option is None:
            return opts
        return opts.get(str(option).lstrip("-"), ())

    def focus(self, *_a):
        return next(iter(self._rows), "")


class MessageRecorder:
    """messagebox stand-in. Without this a rejection path opens a real dialog
    and blocks forever. Records the CONTRACT.md accept/reject signal."""

    def __init__(self):
        self.errors = []
        self.infos = []

    def showerror(self, *a, **_k):
        self.errors.append(a)

    def showwarning(self, *a, **_k):
        self.errors.append(a)

    def showinfo(self, *a, **_k):
        self.infos.append(a)

    def askyesno(self, *_a, **_k):
        return True

    def askokcancel(self, *_a, **_k):
        return True

    def askquestion(self, *_a, **_k):
        return "yes"


_CONSTANTS = ("BOTH", "X", "Y", "LEFT", "RIGHT", "TOP", "BOTTOM", "W", "E", "N", "S",
              "NE", "NW", "SE", "SW", "CENTER", "VERTICAL", "HORIZONTAL", "NONE",
              "SINGLE", "BROWSE", "EXTENDED", "RIDGE", "FLAT", "GROOVE", "SUNKEN",
              "RAISED", "SOLID", "NORMAL", "DISABLED", "ACTIVE", "INSERT")

_TK_NAMES = ("Tk", "Toplevel", "Frame", "LabelFrame", "Label", "Entry", "Text",
             "Button", "Canvas", "Scrollbar", "Menu", "Checkbutton", "Radiobutton",
             "Listbox", "StringVar", "IntVar", "DoubleVar", "BooleanVar", "Misc")

_TTK_NAMES = ("Treeview", "Combobox", "Frame", "Label", "Button", "Entry",
              "Scrollbar", "Notebook", "Style", "LabelFrame")


def _make_modules():
    tk = types.ModuleType("faketk.tk")
    for n in _TK_NAMES:
        setattr(tk, n, globals()[n])
    tk.END = END
    for c in _CONSTANTS:
        setattr(tk, c, c.lower())

    ttk = types.ModuleType("faketk.ttk")
    for n in _TTK_NAMES:
        setattr(ttk, n, globals().get(n, _W))
    return tk, ttk


def install(module):
    """Point `module` at the stubs. Returns (tk, ttk, message_recorder).

    Only attributes the module already has are replaced, so a generation that
    imported `tkinter as tk` but never `ttk` is left alone.
    """
    tk, ttk = _make_modules()
    msg = MessageRecorder()
    if hasattr(module, "tk"):
        module.tk = tk
    if hasattr(module, "tkinter"):
        module.tkinter = tk
    if hasattr(module, "ttk"):
        module.ttk = ttk
    if hasattr(module, "messagebox"):
        module.messagebox = msg
    return tk, ttk, msg
