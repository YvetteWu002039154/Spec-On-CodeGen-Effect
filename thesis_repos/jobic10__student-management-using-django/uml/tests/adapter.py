import ast
import inspect
import textwrap
import re
import typing

_NOISE = {
    "Optional", "Union", "List", "Dict", "Set", "Tuple", "Sequence", "Any",
    "NoneType", "None", "Annotated", "ClassVar", "Final", "bytes", "str",
    "int", "float", "bool", "date", "datetime",
    # Django / model-field wrapper names that are *not* association targets
    "ForeignKey", "OneToOneField", "ManyToManyField", "CharField", "TextField",
    "DateField", "DateTimeField", "BooleanField", "SmallIntegerField",
    "FloatField", "EmailField", "ImageField", "IntegerField",
}


class Unsupported(Exception):
    """Raised when an implementation does not expose a structure under test."""


def _module_classes(modules):
    names = {m.__name__ for m in modules}
    for m in modules:
        for obj in vars(m).values():
            if inspect.isclass(obj) and getattr(obj, "__module__", None) in names:
                yield obj


def _ann_names(ann):
    """The set of type *names* an annotation references (strings/containers unwrapped)."""
    names = set()
    if ann is None or ann is inspect.Parameter.empty:
        return names
    if isinstance(ann, str):
        return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", ann))
    if isinstance(ann, type):
        names.add(ann.__name__)
        return names
    origin = typing.get_origin(ann)
    if origin is not None:
        for arg in typing.get_args(ann):
            names |= _ann_names(arg)
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

    # -- attribute / field presence ---------------------------------------
    def _django_field_names(self, c):
        meta = getattr(c, "_meta", None)
        if meta is None:
            return set()
        try:
            return {f.name for f in meta.get_fields()}
        except Exception:
            return set()

    def _has_attr(self, c, attr):
        if hasattr(c, attr):
            return True
        for k in getattr(c, "__mro__", [c]):
            if attr in getattr(k, "__annotations__", {}):
                return True
        return attr in self._django_field_names(c)

    def has_attr(self, cls_name, attr):
        """True iff `cls_name` defines a class-level attribute/field `attr`.
        Absent → Unsupported (→ FAIL); the diagram lists it, so an omission fails."""
        c = self._require(cls_name)
        if self._has_attr(c, attr):
            return True
        raise Unsupported(f"{cls_name} has no attribute {attr!r}")

    # -- methods under a class --------------------------------------------
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

    # -- the composition link (CustomUserManager --* CustomUser : objects) -
    def objects_is_manager(self, user="CustomUser", manager="CustomUserManager"):
        """True iff `user`.objects is (an instance of) `manager`."""
        u = self._require(user)
        mgr_cls = self._require(manager)
        obj = getattr(u, "objects", None)
        if obj is None:
            raise Unsupported(f"{user} has no objects manager")
        if isinstance(obj, mgr_cls) or type(obj) is mgr_cls:
            return True
        # Django may wrap the manager; fall back to a name/subclass check.
        return type(obj).__name__ == manager or issubclass(type(obj), mgr_cls)

    # -- association target types (A --> B : attr) ------------------------
    def attr_refs(self, cls_name, attr):
        """Type names referenced by `cls_name.attr` (Django related_model,
        property return annotation, __init__ param annotation, or class
        annotation — whichever resolves first). Raises Unsupported (→ FAIL) if the
        attribute is absent or its target type cannot be recovered."""
        c = self._require(cls_name)
        names = set()

        # 1) Django relational field -> related_model
        meta = getattr(c, "_meta", None)
        if meta is not None:
            try:
                f = meta.get_field(attr)
                rm = getattr(f, "related_model", None)
                if rm is not None:
                    names.add(rm.__name__)
            except Exception:
                pass

        # 2) property getter return annotation
        if not names:
            static = inspect.getattr_static(c, attr, None)
            if isinstance(static, property) and static.fget is not None:
                names |= _ann_names(static.fget.__annotations__.get("return"))

        # 3) __init__ parameter annotation matching the attribute name
        if not names:
            try:
                for pname, p in inspect.signature(c.__init__).parameters.items():
                    if pname == attr:
                        names |= _ann_names(p.annotation)
            except (TypeError, ValueError):
                pass

        # 4) class-level annotation (drops field-wrapper / typing noise)
        if not names:
            for k in getattr(c, "__mro__", [c]):
                ann = getattr(k, "__annotations__", {})
                if attr in ann:
                    names |= _ann_names(ann[attr])
                    break

        names -= _NOISE
        if not names:
            if not self._has_attr(c, attr):
                raise Unsupported(f"{cls_name} has no attribute {attr!r}")
            raise Unsupported(f"cannot resolve target type of {cls_name}.{attr}")
        return frozenset(names)
