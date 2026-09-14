import functools
import tempfile
import importlib
import importlib.util
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_UML = os.path.dirname(_HERE)                        # .../shenmintao__marginalia/uml

SOURCE = "uml"
MODELS = ("claude", "gpt", "deepseek", "gemini")

# Optional third-party tops a generation *might* import. Anything NOT importable
# on the host is stubbed; sqlalchemy (installed here) is deliberately left real.
_OPTIONAL_TOPS = {
    "sqlalchemy", "pydantic", "sqlmodel", "alembic",
}


def _missing_tops():
    missing = set()
    for top in _OPTIONAL_TOPS:
        try:
            if importlib.util.find_spec(top) is None:
                missing.add(top)
        except Exception:
            missing.add(top)
    return missing


_MISSING = _missing_tops()


def gencode_paths():
    out = []
    for model in MODELS:
        stem = os.path.join(_UML, "outputcode",
                            f"{model}.run{os.environ.get('RUN', '0')}")
        if os.path.exists(stem + ".py"):
            out.append((f"{SOURCE}/{model}", stem + ".py"))
        elif os.path.isdir(stem):
            out.append((f"{SOURCE}/{model}", stem))   # multi-file generation
    return out


# --- permissive stub system (only for missing optional tops) -----------------
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
            # a permissive *instance* used as a class base contributes its perm
            # class as a real base, so an inheritance link survives stubbing.
            "__mro_entries__": lambda self, bases: (type(self),),
        })
    return _perm_cache[name]


class _PermissiveModule(types.ModuleType):
    def __getattr__(self, name):
        return _perm(name)


class _StubFinder:
    def find_spec(self, name, path=None, target=None):
        if _MISSING and name.split(".")[0] in _MISSING:
            return importlib.util.spec_from_loader(name, self)
        return None

    def create_module(self, spec):
        m = _PermissiveModule(spec.name)
        m.__path__ = []
        return m

    def exec_module(self, module):
        pass


def _install_stubs():
    if _MISSING and not any(isinstance(f, _StubFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _StubFinder())


def _load_path(mod_name, path):
    _install_stubs()
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def load_gencodemodule(impl_id, path):
    return _load_path("gen_" + impl_id.replace("/", "_"), path)


def load_gencodemodules(impl_id, path):
    """Modules of one implementation. Every generation in this repo is a flat
    single file; structure.Implementation takes a list.

    A directory here would mean a generation was saved as an unpacked tree. That
    does not occur in this repo, but it must never be skipped silently: a run
    that vanishes is dropped from the N-run average precisely when the model
    emitted an unusually structured answer, which biases the mean. Raise instead
    -- test_conformance catches it and the run scores 0."""
    if os.path.isdir(path):
        raise RuntimeError(
            f"{impl_id}: generation saved as a directory ({path}); this repo "
            f"expects flat single-file generations")
    return [load_gencodemodule(impl_id, path)]


# ---------------------------------------------------------------------------
# Execute generations with cwd in a throwaway directory
# ---------------------------------------------------------------------------
# A generation may touch RELATIVE paths at import time. The concrete case: a
# pydantic `Settings` with `env_file = ".env"` — which the class diagram itself
# pins — instantiated at module level. Run from the repo root it reads the
# project's own .env, whose unrelated keys (API tokens) pydantic rejects, so the
# module fails to import and every structural test fails. Run from anywhere else
# it loads fine. That makes the SCORE a property of the directory pytest was
# launched from rather than of the generation.
#
# The NL loaders have chdir'd into a temp dir since a generation created
# `kanchi.db` in the tests directory; this brings the UML side in line.
def _with_tmp_cwd(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        prev = os.getcwd()
        tmp = tempfile.mkdtemp(prefix="uml_load_")
        os.chdir(tmp)
        try:
            return fn(*args, **kwargs)
        finally:
            os.chdir(prev)
    return wrapper


load_gencodemodules = _with_tmp_cwd(load_gencodemodules)
