import ast
import inspect
import textwrap


class Unsupported(Exception):
    """Raised when an implementation does not expose a structure under test."""


def _module_classes(modules):
    names = {m.__name__ for m in modules}
    for m in modules:
        for obj in vars(m).values():
            if inspect.isclass(obj) and getattr(obj, "__module__", None) in names:
                yield obj


# -- static "is this a real definition?" analysis (never executes code) -------
def _unwrap(attr):
    """Resolve a class attribute to its underlying function, or None."""
    if isinstance(attr, (staticmethod, classmethod)):
        return attr.__func__
    if isinstance(attr, property):
        return attr.fget
    if inspect.isfunction(attr):
        return attr
    return None


def _is_abstract(func):
    """True iff `func` is an @abstractmethod declaration (a legitimate stub on
    an abstract base, not a lazy placeholder)."""
    return bool(getattr(func, "__isabstractmethod__", False))


def _raises_not_implemented(node):
    exc = node.exc
    if isinstance(exc, ast.Call):
        exc = exc.func
    return isinstance(exc, ast.Name) and exc.id == "NotImplementedError"


def _is_stub(func):
    """Static: True iff `func`'s body is a trivial stub — empty, `pass`, `...`,
    docstring-only, or just `raise NotImplementedError`. Parses source; never
    runs the method. On unavailable source, gives the benefit of the doubt."""
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    except (OSError, TypeError, SyntaxError):
        return False
    fn = tree.body[0] if tree.body else None
    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    body = list(fn.body)
    # drop a leading docstring
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(getattr(body[0], "value", None), ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    if not body:
        return True
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)
                and stmt.value.value is Ellipsis):
            continue
        if isinstance(stmt, ast.Raise) and _raises_not_implemented(stmt):
            continue
        return False  # a statement that actually does something
    return True


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

    # -- inheritance links (--|>) ------------------------------------------
    def subclass_link(self, child, parent):
        """True iff `child` is a proper subclass of `parent` (both by name)."""
        c = self._require(child)
        p = self._require(parent)
        return issubclass(c, p) and c is not p

    # -- methods under a class ---------------------------------------------
    def methods(self, cls_name):
        """Public (non-dunder) callable attribute names on `cls_name`
        (MRO-walked, so inherited operations count)."""
        c = self._require(cls_name)
        out = set()
        for n in dir(c):
            if n.startswith("_"):
                continue
            try:
                if callable(inspect.getattr_static(c, n, None)):
                    out.add(n)
            except Exception:
                pass
        return frozenset(out)

    def has_method_set(self, cls_name, required):
        """True iff `cls_name` carries every name in `required` as a
        *substantive* operation: a real (non-stub) body, or an `@abstractmethod`
        declaration (the legitimate stub on an abstract base). MRO-walked, so an
        inherited real definition counts.

        The class must exist (else Unsupported → FAIL). A missing name, or one present only as a
        trivial stub (empty / `pass` / `...` / `raise NotImplementedError`), is a
        structural failure (returns False), also a FAIL — the diagram drew a real
        operation there.
        """
        c = self._require(cls_name)
        for name in required:
            func = _unwrap(inspect.getattr_static(c, name, None))
            if func is None:
                return False
            if _is_abstract(func):
                continue
            if _is_stub(func):
                return False
        return True

    def overrides_method_set(self, cls_name, required):
        """True iff `cls_name` **directly defines** (in its own body, not merely
        inherited) every name in `required`, each as a concrete, non-abstract,
        non-stub implementation. For specialization boxes whose diagram fact is
        an *override* — an inherited or still-abstract method does not satisfy
        it.
        """
        c = self._require(cls_name)
        own = vars(c)
        for name in required:
            if name not in own:
                return False
            func = _unwrap(own[name])
            if func is None or _is_abstract(func) or _is_stub(func):
                return False
        return True
