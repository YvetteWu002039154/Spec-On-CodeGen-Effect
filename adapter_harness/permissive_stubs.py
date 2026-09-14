"""Import-time stubs for optional third-party tops a generation may reference.

Why this exists
---------------
A generation is scored on the behaviour it implements, not on which packages
happen to be installed on the grading host. Several generations import an
optional top (`dateutil`, `sqlalchemy`, `rich`, ...) at module level and then
never touch it on the path the suite exercises. Without a stub the module fails
to import and every test fails for a reason that is about the environment, not
the code.

`_PermissiveModule` answers any attribute with a `_perm` class that accepts any
construction, subscript, call or subclassing. That is enough for a module-level
`class Foo(Base)` / `x: SomeType` / decorator to survive import. It deliberately
does NOT make the dependency work: a generation that relies on real behaviour
from a stubbed top still fails its tests, which is the correct outcome.

Policy stays with the caller
----------------------------
This module holds only the machinery. WHICH tops get stubbed is a per-repo
judgement and stays in each loader.py:

  * most repos stub only tops that are genuinely absent --
    `missing_tops(_OPTIONAL_TOPS)`;
  * marginalia stubs heavy ML tops (`torch` & co) even when installed, because
    importing them for real is slow and can crash during collection -- it passes
    its own fixed set.

Usage
-----
    import permissive_stubs

    _MISSING = permissive_stubs.missing_tops(_OPTIONAL_TOPS)   # or a fixed set
    ...
    def _load_path(mod_name, path):
        permissive_stubs.install(_MISSING)
        ...
"""
import importlib.util
import sys
import types

_perm_cache = {}


class _PermMeta(type):
    def __getattr__(cls, name):
        return _perm(name)

    def __getitem__(cls, item):
        return cls

    def __call__(cls, *a, **k):
        return object.__new__(cls)


def _perm(name="Perm"):
    if name not in _perm_cache:
        _perm_cache[name] = _PermMeta(name, (object,), {
            "__init__": lambda self, *a, **k: None,
            "__getattr__": lambda self, n: _perm(n),
            "__getitem__": lambda self, i: self,
            "__call__": lambda self, *a, **k: None,
            "__mro_entries__": lambda self, bases: (),
        })
    return _perm_cache[name]


class _PermissiveModule(types.ModuleType):
    def __getattr__(self, name):
        return _perm(name)


# Union of every set handed to install(). A suite runs one repo per process, so
# in practice this is exactly that repo's set; keeping it a union means a second
# install() in one process adds to the stubbed tops rather than being silently
# dropped by the "already installed" check below.
_MISSING = set()


class _StubFinder:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in _MISSING:
            return importlib.util.spec_from_loader(name, self)
        return None

    def create_module(self, spec):
        m = _PermissiveModule(spec.name)
        m.__path__ = []
        return m

    def exec_module(self, module):
        pass


def missing_tops(optional_tops):
    """Which of `optional_tops` are not importable here.

    A top whose spec lookup raises is treated as missing too: a package that
    explodes on inspection is no more usable than an absent one.
    """
    missing = set()
    for top in optional_tops:
        try:
            if importlib.util.find_spec(top) is None:
                missing.add(top)
        except Exception:
            missing.add(top)
    return missing


def install(missing):
    """Register the stub finder for `missing`. Idempotent; no-op if empty."""
    _MISSING.update(missing)
    if _MISSING and not any(isinstance(f, _StubFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _StubFinder())
