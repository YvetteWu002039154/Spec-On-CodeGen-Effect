import enum
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


def _init_params(cls):
    try:
        params = list(inspect.signature(cls.__init__).parameters.values())
    except (TypeError, ValueError):
        return set()
    return {p.name for p in params
            if p.name != "self" and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)}


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

    # -- attributes --------------------------------------------------------
    def attributes(self, cls_name):
        """The set of attribute names a class *models*, from any of:

        Django model fields (`_meta`), class-level non-callable descriptors
        (fields / properties / ClassVars), `__init__` parameters, and
        class annotations. Covers both the Django reference and the
        plain-Python generations that assign attributes in `__init__`.
        """
        c = self._require(cls_name)
        names = set()
        meta = getattr(c, "_meta", None)
        if meta is not None and hasattr(meta, "get_fields"):
            try:
                names |= {f.name for f in meta.get_fields()}
            except Exception:
                pass
        for k in c.__mro__:
            for name, val in vars(k).items():
                if name.startswith("_"):
                    continue
                if inspect.isclass(val) or inspect.isfunction(val) \
                        or isinstance(val, (staticmethod, classmethod)):
                    continue
                names.add(name)
            names |= set(getattr(k, "__annotations__", {}).keys())
        names |= _init_params(c)
        return frozenset(names)

    # -- methods -----------------------------------------------------------
    def methods(self, cls_name):
        """Public (non-dunder) callable attribute names on the class. A stub-bodied method (`pass` / `...` / `return None` / `raise
        NotImplementedError`) is excluded, so it counts as *not* implemented.
        """
        c = self._require(cls_name)
        out = set()
        for n in dir(c):
            if n.startswith("_"):
                continue
            try:
                obj = getattr(c, n, None)
                if callable(obj) and not _is_stub(obj):
                    out.add(n)
            except Exception:
                continue
        return frozenset(out)

    # -- nested choice / enum classes --------------------------------------
    def nested_tokens(self, cls_name, nested_name):
        """Lowercased member name/value tokens of a nested choice/enum class."""
        c = self._require(cls_name)
        nested = getattr(c, nested_name, None)
        if not inspect.isclass(nested):
            raise Unsupported(f"{cls_name} has no nested {nested_name} class")
        toks = set()
        if issubclass(nested, enum.Enum):
            for m in nested:
                toks.add(str(m.name).lower())
                val = getattr(m, "value", None)
                if isinstance(val, str):
                    toks.add(val.lower())
        else:
            for name, val in vars(nested).items():
                if name.isupper() and isinstance(val, str):
                    toks.add(name.lower())
                    toks.add(val.lower())
        if not toks:
            raise Unsupported(f"{cls_name}.{nested_name} exposes no members")
        return frozenset(toks)

    # -- association: User.objects --* UserManager -------------------------
    def objects_manager_name(self):
        """Name of the class of `User.objects` (the `--* UserManager` link)."""
        user = self._require("User")
        obj = getattr(user, "objects", None)
        if obj is None:
            raise Unsupported("User has no `objects` attribute")
        if inspect.isclass(obj):
            return obj.__name__
        return type(obj).__name__
