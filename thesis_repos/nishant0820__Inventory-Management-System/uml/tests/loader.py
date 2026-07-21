import contextlib
import importlib.util
import os
import sys
import tempfile
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_UML = os.path.dirname(_HERE)                        # .../nishant0820__.../uml

SOURCE = "uml"
MODELS = ("claude", "gpt", "deepseek", "gemini")

# Heavy third-party tops that some module may import at top level. Any that is
# genuinely missing on the host is stubbed; the rest (incl. PIL when present)
# stay real. Stdlib (tkinter, sqlite3, …) is never stubbed.
_OPTIONAL_TOPS = {
    "PIL", "numpy", "pandas", "reportlab", "dateutil", "cv2", "matplotlib",
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
        p = os.path.join(_UML, "outputcode", model, "generated_code.py")
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
            # A permissive instance used as a class base contributes a real base,
            # so an inheritance link survives stubbed loading instead of vanishing.
            "__mro_entries__": lambda self, bases: (type(self),),
        })
    return _perm_cache[name]


class _PermissiveModule(types.ModuleType):
    def __getattr__(self, name):
        return _perm(name)


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


def _install_stubs():
    if _MISSING and not any(isinstance(f, _StubFinder) for f in sys.meta_path):
        sys.meta_path.insert(0, _StubFinder())


@contextlib.contextmanager
def _scratch_cwd():
    """Import inside a throwaway dir so any stray import-time file creation lands
    there, not in the repo tree (structural loading should not persist anything)."""
    prev = os.getcwd()
    tmp = tempfile.mkdtemp(prefix="ims_uml_import_")
    os.chdir(tmp)
    try:
        yield
    finally:
        os.chdir(prev)


def _load_path(mod_name, path):
    _install_stubs()
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    with _scratch_cwd():
        spec.loader.exec_module(module)
    return module


def load_gencodemodule(impl_id, path):
    return _load_path("gen_" + impl_id.replace("/", "_"), path)
