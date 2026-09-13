import dataclasses
import inspect
import re
import typing

_TYPING_NOISE = {
    "Optional", "Union", "List", "Dict", "Set", "Tuple", "Sequence",
    "Any", "NoneType", "None", "Annotated", "ClassVar", "Final", "int",
    "str", "float", "bool", "bytes", "datetime", "date", "Decimal",
}

# Service prefixes stripped during entity-name normalization. Longest-first so
# e.g. ``inventoryservices`` is tried before any shorter accidental match.
_PREFIXES = ("inventoryservices", "productservices", "userservices",
             "orderservice", "django", "auth")


def _norm(name):
    """Normalize an entity/class name to a prefix-free, case-free token.

    ``userservices_users`` / ``UserservicesUsers`` / ``Users`` -> ``users``;
    ``orderservice_purchaseorder`` / ``OrderservicePurchaseOrder`` /
    ``PurchaseOrder`` -> ``purchaseorder``.
    """
    s = str(name).lower().replace("_", "")
    for pre in _PREFIXES:
        if s.startswith(pre) and len(s) > len(pre):
            return s[len(pre):]
    return s


def _module_classes(modules):
    names = {m.__name__ for m in modules}
    for m in modules:
        for obj in vars(m).values():
            if inspect.isclass(obj) and getattr(obj, "__module__", None) in names:
                yield obj


def _annotation_names(ann):
    """The set of type *names* an annotation references (containers unwrapped)."""
    names = set()
    if ann is None or ann is inspect.Parameter.empty:
        return names
    if isinstance(ann, str):
        names |= set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", ann))
        return names
    if isinstance(ann, typing.ForwardRef):
        names |= set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*",
                                ann.__forward_arg__))
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
        self._by_norm = {}
        for c in _module_classes(self.modules):
            self._by_norm.setdefault(_norm(c.__name__), c)

    # -- lookup ------------------------------------------------------------
    def _entity(self, name):
        return self._by_norm.get(_norm(name))

    # -- fields ------------------------------------------------------------
    def _django_fields(self, cls):
        """The Django model Field objects for `cls`, or () if it isn't one.

        `_meta.get_fields()` is the framework's own introspection API, so this
        sees real model fields (plain class-body assignments like
        ``warehouse = models.ForeignKey(...)``) that `__annotations__` never
        captures — Django fields aren't type-annotated."""
        meta = getattr(cls, "_meta", None)
        if meta is None:
            return ()
        try:
            return meta.get_fields()
        except Exception:
            return ()

    def _field_names(self, cls):
        names = set(getattr(cls, "__annotations__", {}).keys())
        if dataclasses.is_dataclass(cls):
            names |= {f.name for f in dataclasses.fields(cls)}
        try:
            sig = inspect.signature(cls.__init__)
            for p in sig.parameters.values():
                if p.name != "self" and p.kind in (
                        p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY):
                    names.add(p.name)
        except (TypeError, ValueError):
            pass
        names |= {f.name for f in self._django_fields(cls)}
        return names

    def has_fields(self, entity, *fields):
        """True iff the entity is defined and declares every named field.

        False (→ failure) if the entity is absent — a missing entity is a
        failure, not a skip.
        """
        cls = self._entity(entity)
        if cls is None:
            return False
        have = {f.lower() for f in self._field_names(cls)}
        return all(f.lower() in have for f in fields)

    # -- associations ------------------------------------------------------
    def _ref_norms(self, cls):
        """Normalized names of every entity this class points at: every type
        name mentioned in a class annotation or ``__init__`` param annotation,
        plus every Django relational field's `related_model` (FK/O2O/M2M —
        including a 'self' FK, which Django resolves to `cls` itself)."""
        anns = list(getattr(cls, "__annotations__", {}).values())
        try:
            sig = inspect.signature(cls.__init__)
            anns += [p.annotation for p in sig.parameters.values()
                     if p.annotation is not inspect.Parameter.empty]
        except (TypeError, ValueError):
            pass
        out = set()
        for a in anns:
            for nm in _annotation_names(a) - _TYPING_NOISE:
                out.add(_norm(nm))
        for f in self._django_fields(cls):
            related = getattr(f, "related_model", None)
            if related is not None and isinstance(related, type):
                out.add(_norm(related.__name__))
        return out

    def references(self, source, target):
        """True iff `source` is defined and has an attribute typed as `target`.

        False (→ failure) if the source entity is absent.
        """
        src = self._entity(source)
        if src is None:
            return False
        return _norm(target) in self._ref_norms(src)
