import ast
import inspect
import re
import textwrap
import typing

_TYPING_NOISE = {
    "Optional", "Union", "List", "Dict", "Set", "Tuple", "Sequence",
    "Any", "NoneType", "None", "Annotated", "ClassVar", "Final",
}


def _module_classes(modules):
    names = {m.__name__ for m in modules}
    for m in modules:
        for obj in vars(m).values():
            if inspect.isclass(obj) and getattr(obj, "__module__", None) in names:
                yield obj


def _annotation_names(ann):
    """The set of type *names* an annotation references (Optional/containers unwrapped)."""
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


class Implementation:
    def __init__(self, ident, modules):
        self.ident = ident
        self.modules = list(modules)
        self._by_name = {}
        for c in _module_classes(self.modules):
            self._by_name.setdefault(c.__name__, c)

    def _class(self, name):
        return self._by_name.get(name)

    # -- inheritance links (--|>) ------------------------------------------
    
    def subclass_link(self, child, parent):
        """True iff `child` is a proper subclass of `parent` (both by name).

        False if either class is absent — a link the PUML draws but the
        generation does not realize is a failure, not a skip.
        """
        c = self._class(child)
        p = self._class(parent)
        if c is None or p is None:
            return False
        return issubclass(c, p) and c is not p

    def common_ancestor_names(self, names):
        """Names of the non-`object` classes that are a base of *every* listed entity.

        Realizes the shared `--|> Base` link. Empty (→ failure) unless **all**
        listed entities are defined and converge on a common base — a missing
        entity is a failure, not a skip.
        """
        present = [self._class(n) for n in names]
        if any(c is None for c in present):
            return frozenset()
        common = None
        for c in present:
            anc = {k.__name__ for k in c.__mro__[1:] if k is not object}
            common = anc if common is None else (common & anc)
        return frozenset(common or ())

    # -- association links (-->) -------------------------------------------
    
    def attr_refs(self, cls_name, attr):
        """Type names referenced by `cls_name.attr`'s annotation (MRO-walked).

        Empty (→ failure) if the class or the annotated attribute is absent.
        """
        c = self._class(cls_name)
        if c is None:
            return frozenset()
        for k in c.__mro__:
            ann = getattr(k, "__annotations__", {})
            if attr in ann:
                return frozenset(_annotation_names(ann[attr]) - _TYPING_NOISE)
        return frozenset()

    # -- methods under a class ---------------------------------------------
    
    def methods(self, cls_name):
        """Public (non-dunder) callable names on `cls_name` with a real body.

        Empty (→ failure) if the class is absent. A stub method (`pass` / `...` /
        `return None` / `raise NotImplementedError`) is excluded, so it counts as
        *not* implemented.
        """
        c = self._class(cls_name)
        if c is None:
            return frozenset()
        out = set()
        for n in dir(c):
            if n.startswith("_"):
                continue
            obj = getattr(c, n, None)
            if callable(obj) and not _is_stub(obj):
                out.add(n)
        return frozenset(out)


def _func_node(func):
    """The AST FunctionDef/AsyncFunctionDef for `func`, or None if not a def."""
    src = textwrap.dedent(inspect.getsource(func))
    node = ast.parse(src).body[0]
    return node if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else None


def _is_stub(func):
    """True if the method's body is trivial (a placeholder, not an implementation).

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
