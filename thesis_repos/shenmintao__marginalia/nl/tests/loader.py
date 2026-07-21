import importlib
import importlib.util
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_NL = os.path.dirname(_HERE)                          # .../shenmintao__marginalia/nl

SOURCE = "nl"
MODELS = ("claude", "gpt", "deepseek", "gemini")

# Heavy ML tops that are ALWAYS stubbed, even when installed. Importing the real
# `sentence_transformers` pulls in `transformers`/`torch`, whose initialization
# both is slow and — in some environments — crashes during collection (e.g. a
# torch `custom_op` registration raising `TypeError` from `inspect`). The
# generations reach these behind a `try/except ImportError` guard, which would
# NOT catch such a non-ImportError crash — so forcing the stub keeps the module
# loadable and grading deterministic regardless of whether the host has torch.
# Every other optional top the generations reference is left real: they all
# guard those imports, so a missing package simply flips a `HAS_*` flag.
_ALWAYS_STUB = {"sentence_transformers", "transformers", "torch"}

_MISSING = _ALWAYS_STUB


def gencode_paths():
    out = []
    for model in MODELS:
        p = os.path.join(_NL, "outputcode", model, "generated_code.py")
        if os.path.exists(p):
            out.append((f"{SOURCE}/{model}", p))
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
            "__mro_entries__": lambda self, bases: (),
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
