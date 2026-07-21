import inspect
import re
import typing

_TYPING_NOISE = {
    "Optional", "Union", "List", "Dict", "Set", "Tuple", "Sequence",
    "Any", "NoneType", "None", "Annotated", "ClassVar", "Final", "ForeignKey",
    "OneToOneField",
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

    def _require(self, name):
        c = self._class(name)
        if c is None:
            raise Unsupported(f"no {name} class")
        return c

    # -- inheritance (--|>) ----------------------------------------------
    def subclass_link(self, child, parent):
        c = self._require(child)
        p = self._require(parent)
        return issubclass(c, p) and c is not p

    # -- composition (--*) : User.objects is a CustomUserManager ---------
    def manager_class_name(self, cls_name="User", attr="objects"):
        c = self._require(cls_name)
        mgr = getattr(c, attr, None)
        if mgr is None:
            raise Unsupported(f"{cls_name} has no {attr!r}")
        return type(mgr).__name__

    # -- methods ----------------------------------------------------------
    def defined_methods(self, cls_name):
        c = self._require(cls_name)
        out = set()
        for n in dir(c):
            if n.startswith("__"):
                continue
            if inspect.isfunction(inspect.getattr_static(c, n, None)):
                out.add(n)
        return frozenset(out)

    def attribute_present(self, cls_name, name):
        """True iff `name` is a member of the class (method, property, field…)."""
        c = self._require(cls_name)
        if name in dir(c):
            return True
        raise Unsupported(f"{cls_name} has no member {name!r}")

    # -- declared attributes (class attr / annotation / __init__ param) ---
    def _declared(self, cls):
        names = set()
        for k in cls.__mro__:
            names |= {n for n in vars(k) if not n.startswith("__")}
            names |= set(getattr(k, "__annotations__", {}) or {})
            init = k.__dict__.get("__init__")
            if inspect.isfunction(init):
                try:
                    names |= {p for p in inspect.signature(init).parameters
                              if p not in ("self", "cls")}
                except (TypeError, ValueError):
                    pass
        # Django model fields (declared on the concrete model's _meta)
        meta = getattr(cls, "_meta", None)
        if meta is not None:
            try:
                names |= {f.name for f in meta.get_fields()}
            except Exception:
                pass
        return names

    def declares_all(self, cls_name, names):
        """Raises Unsupported (→ FAIL) if the class declares *none* of `names`; else True/False."""
        c = self._require(cls_name)
        decl = self._declared(c)
        names = set(names)
        if not (names & decl):
            raise Unsupported(f"{cls_name} declares none of {sorted(names)}")
        return names <= decl

    def class_attr_is_tuple(self, cls_name, attr):
        c = self._require(cls_name)
        val = getattr(c, attr, None)
        if val is None and attr not in dir(c):
            raise Unsupported(f"{cls_name} has no {attr!r}")
        return isinstance(val, tuple)

    # -- association (-->) : attribute type reference --------------------
    def attr_refs(self, cls_name, attr):
        """Type names referenced by `cls_name.attr` (Django related model,
        class annotation, or __init__ parameter annotation)."""
        c = self._require(cls_name)
        # Django relational field
        meta = getattr(c, "_meta", None)
        if meta is not None:
            try:
                f = meta.get_field(attr)
                rel = getattr(f, "related_model", None)
                if rel is not None:
                    return frozenset({rel.__name__})
            except Exception:
                pass
        # class-level annotation
        for k in c.__mro__:
            ann = getattr(k, "__annotations__", {}) or {}
            if attr in ann:
                names = _annotation_names(ann[attr]) - _TYPING_NOISE
                if names:
                    return frozenset(names)
        # __init__ parameter annotation
        init = getattr(c, "__init__", None)
        if inspect.isfunction(init):
            try:
                p = inspect.signature(init).parameters.get(attr)
            except (TypeError, ValueError):
                p = None
            if p is not None and p.annotation is not inspect.Parameter.empty:
                names = _annotation_names(p.annotation) - _TYPING_NOISE
                if names:
                    return frozenset(names)
        raise Unsupported(f"{cls_name}.{attr} has no resolvable type reference")
