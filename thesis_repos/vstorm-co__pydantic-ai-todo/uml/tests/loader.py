import importlib.util
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_UML = os.path.dirname(_HERE)                         # .../vstorm-co__pydantic-ai-todo/uml

SOURCE = "uml"
MODELS = ("claude", "gpt", "deepseek", "gemini")

# heavy/optional tops stubbed for portability (never stdlib, never pydantic)
_STUB_TOPS = {
    "pydantic_ai", "asyncpg", "redis", "aioredis", "psycopg2", "aiohttp",
    "sqlalchemy",
}


def gencode_paths():
    out = []
    for model in MODELS:
        p = os.path.join(_UML, "outputcode", model, "generated_code.py")
        if os.path.exists(p):
            out.append((f"{SOURCE}/{model}", p))
    return out


# --- permissive stub system --------------------------------------------------
_perm_cache = {}


def _dunder(name):
    return isinstance(name, str) and name.startswith("__") and name.endswith("__")


class _PermMeta(type):
    def __getattr__(cls, name):
        # Never fabricate dunders (e.g. __dataclass_fields__): a truthy fake
        # would make `@dataclass` treat a stubbed base as a dataclass base and
        # iterate its "fields" forever (__getitem__ returns self, never raising).
        if _dunder(name):
            raise AttributeError(name)
        return _perm(name)

    def __getitem__(cls, item):
        return cls

    def __call__(cls, *a, **k):
        return object.__new__(cls)


def _perm_getattr(self, n):
    if _dunder(n):
        raise AttributeError(n)
    return _perm(n)


def _perm(name="Perm"):
    if name not in _perm_cache:
        _perm_cache[name] = _PermMeta(name, (object,), {
            "__init__": lambda self, *a, **k: None,
            "__getattr__": _perm_getattr,
            "__getitem__": lambda self, i: self,
            "__call__": lambda self, *a, **k: None,
            "__mro_entries__": lambda self, bases: (),
        })
    return _perm_cache[name]


class _PermissiveModule(types.ModuleType):
    def __getattr__(self, name):
        return _perm(name)


class _StubFinder:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in _STUB_TOPS:
            return importlib.util.spec_from_loader(name, self)
        return None

    def create_module(self, spec):
        m = _PermissiveModule(spec.name)
        m.__path__ = []
        return m

    def exec_module(self, module):
        pass


def _install_stubs():
    if not any(isinstance(f, _StubFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _StubFinder())
    for name in list(sys.modules):
        if name.split(".")[0] in _STUB_TOPS:
            del sys.modules[name]


def _load_path(mod_name, path):
    _install_stubs()
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def load_gencodemodule(impl_id, path):
    return _load_path("gen_" + impl_id.replace("/", "_"), path)
