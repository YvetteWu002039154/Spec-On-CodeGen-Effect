import ast
import inspect
import textwrap
import re
import typing

_TYPING_NOISE = {
    "Optional", "Union", "List", "list", "Dict", "dict", "Set", "set",
    "Tuple", "tuple", "Sequence", "Any", "NoneType", "None", "Annotated",
    "ClassVar", "Final", "Literal",
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
    """The set of type *names* an annotation references (containers unwrapped)."""
    names = set()
    if ann is None:
        return names
    if isinstance(ann, str):
        names |= set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", ann))
        return names
    if isinstance(ann, type):
        names.add(ann.__name__)
        return names
    origin = typing.get_origin(ann)
    if origin is not None:
        for arg in typing.get_args(ann):
            names |= _annotation_names(arg)
    nm = getattr(ann, "__name__", None) or getattr(ann, "_name", None)
    if nm:
        names.add(str(nm))
    return names


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

    # -- composition/association links (--* : attr) ------------------------
    def attr_refs(self, cls_name, attr):
        """Type names referenced by `cls_name.attr`'s annotation (MRO-walked)."""
        c = self._require(cls_name)
        for k in c.__mro__:
            ann = getattr(k, "__annotations__", {})
            if attr in ann:
                return frozenset(_annotation_names(ann[attr]) - _TYPING_NOISE)
        raise Unsupported(f"{cls_name} has no annotated attribute {attr!r}")

    # -- attributes under a class ------------------------------------------
    def fields(self, cls_name):
        """The set of annotated attribute names on `cls_name` (MRO-walked).

        Covers dataclass / pydantic fields (both expose them via
        ``__annotations__``), plus pydantic's ``model_fields`` when present.
        """
        c = self._require(cls_name)
        out = set()
        for k in c.__mro__:
            out |= set(getattr(k, "__annotations__", {}).keys())
        mf = getattr(c, "model_fields", None)
        if isinstance(mf, dict):
            out |= set(mf.keys())
        out = {n for n in out if not n.startswith("_")}
        if not out:
            raise Unsupported(f"{cls_name} exposes no annotated fields")
        return frozenset(out)

    # -- methods under a class ---------------------------------------------
    def methods(self, cls_name):
        """Public (non-dunder) callable attribute names on `cls_name`. A stub-bodied method (`pass` / `...` / `return None` / `raise
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
