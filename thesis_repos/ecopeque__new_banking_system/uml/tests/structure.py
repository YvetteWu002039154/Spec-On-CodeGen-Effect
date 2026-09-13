import inspect
import re
import typing

_TYPING_NOISE = {
    "Optional", "Union", "List", "Dict", "Set", "Tuple", "Sequence",
    "Any", "NoneType", "None", "Annotated", "ClassVar", "Final", "Iterator",
    "Generator", "Type",
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

    # -- methods / properties under a class --------------------------------
    def member_names(self, cls_name):
        """Public (non-dunder) member names defined on the class or its MRO.

        Includes ``@property`` descriptors and plain methods alike — the diagram
        lists both `C003_balanceMTD` (a property) and `C001_depositMTD` (a
        method) as members "under" their class.
        """
        c = self._require(cls_name)
        out = set()
        for n in dir(c):
            if n.startswith("__"):
                continue
            out.add(n)
        return frozenset(out)

    def is_abstract_method(self, cls_name, method):
        """True iff `cls_name.method` is defined and marked abstract (MRO-walked)."""
        c = self._require(cls_name)
        for k in c.__mro__:
            if method in k.__dict__:
                return bool(getattr(k.__dict__[method], "__isabstractmethod__", False))
        return False

    # -- composition link (--*) --------------------------------------------
    def composes(self, owner_name, part_name):
        """True iff `owner` wires up an attribute typed as / built from `part`.

        Detected statically (no instantiation): the part class name appears in
        the owner's ``__init__`` code object (e.g. ``self.x = PartCls()``) or in
        a class/attribute annotation. Raises Unsupported (→ FAIL) if the *part* class is absent.
        """
        owner = self._require(owner_name)
        if self._class(part_name) is None:
            raise Unsupported(f"no {part_name} class")
        # names referenced in __init__ across the MRO (co_names holds globals +
        # attribute names used, without executing the code)
        refs = set()
        for k in owner.__mro__:
            init = k.__dict__.get("__init__")
            code = getattr(init, "__code__", None)
            if code is not None:
                refs |= set(code.co_names)
                for const in code.co_consts:  # nested comprehension/closure code
                    refs |= set(getattr(const, "co_names", ()))
        if part_name in refs:
            return True
        # fall back to class-level / attribute annotations
        for k in owner.__mro__:
            for ann in getattr(k, "__annotations__", {}).values():
                if part_name in _annotation_names(ann):
                    return True
        return False
