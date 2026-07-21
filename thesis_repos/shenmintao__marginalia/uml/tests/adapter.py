import ast
import inspect
import textwrap
import re

_TYPING_NOISE = {
    "Optional", "Union", "List", "Dict", "Set", "Tuple", "Sequence", "Mapped",
    "Any", "NoneType", "None", "Annotated", "ClassVar", "Final", "datetime",
}


class Unsupported(Exception):
    """Raised when an implementation does not expose a structure under test."""


def _module_classes(modules):
    names = {m.__name__ for m in modules}
    for m in modules:
        for obj in vars(m).values():
            if inspect.isclass(obj) and getattr(obj, "__module__", None) in names:
                yield obj


def _annotation_names(ann):
    """The set of type *names* an annotation references.

    Robust to both stringized annotations (PEP 563 / ``from __future__ import
    annotations``) and real typing objects (SQLAlchemy leaves ``Mapped[T]``
    intact on ``__annotations__``): every identifier appearing in the
    annotation's source/repr is collected, then typing noise is filtered by the
    caller.
    """
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", str(ann)))


def _func_node(func):
    """The AST FunctionDef/AsyncFunctionDef for `func`, or None if unavailable.

    Source is parsed, never run; a callable whose source can't be recovered
    (builtins, C-level, dynamically built) yields None -> given the benefit of
    the doubt (treated as *not* a stub).
    """
    try:
        src = textwrap.dedent(inspect.getsource(func))
        node = ast.parse(src).body[0]
    except (OSError, TypeError, SyntaxError, IndexError):
        return None
    return node if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else None


def _is_stub(func):
    """True if the method's body is a trivial placeholder, not an implementation.

    Judged statically from source: `pass`, a bare `...`/docstring, `return None`,
    or `raise NotImplementedError`.
    """
    node = _func_node(func)
    if node is None:
        return False
    body = node.body
    # drop a leading docstring
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    if not body:
        return True
    if len(body) != 1:
        return False
    stmt = body[0]
    if isinstance(stmt, ast.Pass):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
        return True  # bare `...` or a stray literal
    if isinstance(stmt, ast.Return) and (
            stmt.value is None
            or (isinstance(stmt.value, ast.Constant) and stmt.value.value is None)):
        return True
    if isinstance(stmt, ast.Raise):
        exc = stmt.exc
        name = (exc.id if isinstance(exc, ast.Name)
                else exc.func.id if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name)
                else None)
        if name in {"NotImplementedError", "NotImplemented"}:
            return True
    return False


class Implementation:
    def __init__(self, ident, modules):
        self.ident = ident
        self.modules = list(modules)
        self._by_name = {}
        for c in _module_classes(self.modules):
            self._by_name.setdefault(c.__name__, c)

    def _class(self, name):
        return self._by_name.get(name)

    def _require(self, name):
        c = self._class(name)
        if c is None:
            raise Unsupported(f"no {name} class")
        return c

    # -- inheritance convergence -------------------------------------------
    def common_ancestor_names(self, names):
        """Names of the non-``object`` classes that are a base of *every*
        listed entity that the implementation defines.

        Realizes the shared ``Base`` / ``IdMixin`` superclasses the diagram
        lists as standalone member-holding classes. Raises Unsupported (→ FAIL) if fewer than two of
        the listed entities are present.
        """
        present = [self._class(n) for n in names]
        present = [c for c in present if c is not None]
        if len(present) < 2:
            raise Unsupported(f"fewer than two of {names} defined")
        common = None
        for c in present:
            anc = {k.__name__ for k in c.__mro__[1:] if k is not object}
            common = anc if common is None else (common & anc)
        return frozenset(common or ())

    def subclass_link(self, child, parent):
        c = self._require(child)
        p = self._require(parent)
        return issubclass(c, p) and c is not p

    # -- members under a class ---------------------------------------------
    def _all_annotations(self, cls):
        out = {}
        for k in reversed(cls.__mro__):
            out.update(getattr(k, "__annotations__", {}) or {})
        return out

    def members(self, cls_name):
        """Declared attribute names (MRO-walked ``__annotations__`` plus any
        instrumented/class attributes) of ``cls_name``."""
        c = self._require(cls_name)
        out = set(self._all_annotations(c).keys())
        for n in dir(c):
            if not n.startswith("__"):
                out.add(n)
        return frozenset(out)

    def methods(self, cls_name):
        """Public (non-dunder) callable attribute names on ``cls_name``. A stub-bodied method (`pass` / `...` / `return None` / `raise
        NotImplementedError`) is excluded, so it counts as *not* implemented.
        """
        c = self._require(cls_name)
        out = set()
        for n in dir(c):
            if n.startswith("_"):
                continue
            obj = getattr(c, n, None)
            if callable(obj) and not _is_stub(obj):
                out.add(n)
        return frozenset(out)

    # -- member types (association-like) -----------------------------------
    def attr_refs(self, cls_name, attr):
        """Type names referenced by ``cls_name.attr``'s annotation (MRO-walked,
        ``Mapped[...]`` unwrapped, typing noise stripped)."""
        c = self._require(cls_name)
        ann = self._all_annotations(c)
        if attr not in ann:
            raise Unsupported(f"{cls_name} has no annotated attribute {attr!r}")
        return frozenset(_annotation_names(ann[attr]) - _TYPING_NOISE)
