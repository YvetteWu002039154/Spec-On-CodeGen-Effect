import importlib
import importlib.util
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_UML = os.path.dirname(_HERE)                        # .../m-danya__planty/uml

SOURCE = "uml"
MODELS = ("claude", "gpt", "deepseek", "gemini")

# Heavy third-party tops stubbed for portability (never stdlib, never pydantic).
# sqlalchemy is stubbed on purpose: it keeps the generations' ORM `*Model`
# classes from registering real tables (which would collide across the four
# modules loaded in one process).
_STUB_TOPS = {
    "sqlalchemy", "fastapi", "starlette", "jose", "jwt", "passlib", "bcrypt",
    "redis", "aioredis", "boto3", "botocore", "minio", "alembic", "celery",
    "httpx", "aiosqlite", "asyncpg", "dotenv", "pydantic_settings",
    "email_validator", "uvicorn", "cryptography", "dateutil", "anyio",
}


def gencode_paths():
    out = []
    for model in MODELS:
        p = os.path.join(_UML, "outputcode", model, "generated_code.py")
        if os.path.exists(p):
            out.append((f"{SOURCE}/{model}", p))
    return out


# --- permissive stub system (shared metaclass so stubs compose as bases) ------
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
            # A permissive *instance* used as a class base (e.g. the result of
            # `Base = declarative_base()`) contributes its perm class as a real
            # base, so a `--|> Base` link would survive stubbed loading instead
            # of collapsing to `object`.
            "__mro_entries__": lambda self, bases: (type(self),),
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
    # ensure stubbed tops resolve to the finder (drop any partial real imports)
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
