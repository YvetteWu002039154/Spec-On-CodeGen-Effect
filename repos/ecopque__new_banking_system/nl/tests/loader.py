import ast
import importlib.util
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_NL = os.path.dirname(_HERE)                          # .../ecopque__.../nl

SOURCE = "nl"
MODELS = ("claude", "gpt", "deepseek", "gemini")

# Optional third-party tops a generation might import. Anything here that is not
# importable on the host is resolved to a permissive stub; stdlib is untouched.
_OPTIONAL_TOPS = {
    "pydantic", "pydantic_settings", "dateutil", "pytz", "tabulate", "rich",
    "colorama", "click",
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
        p = os.path.join(_NL, "outputcode", f"{model}.run{os.environ.get('RUN', '0')}.py")
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


def _load_path(mod_name, path):
    _install_stubs()
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def load_gencodemodule(impl_id, path):
    return _load_path("gen_" + impl_id.replace("/", "_"), path)


# ---------------------------------------------------------------------------
# Dependency usage — does a generation import and *use* a package the
# description names, rather than hand-roll a substitute? Fully static (AST):
# never imports the module, so it is independent of whether the package is
# installed. Mirrors the asimov NL track. See CONTRACT.md § "Dependency usage".
# ---------------------------------------------------------------------------
def _dep_bindings(tree, dep):
    """Local names a file binds by importing package `dep` (top-level `dep`
    only). Handles `import dep`, `import dep.sub as x`, and
    `from dep[.sub] import a, b`."""
    binds = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0] == dep:
                    binds.add(a.asname or a.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            if n.module.split(".")[0] == dep:
                for a in n.names:
                    binds.add(a.asname or a.name)
    return binds


def _file_dep_used(path, dep):
    tree = ast.parse(open(path).read())
    binds = _dep_bindings(tree, dep)
    if not binds:
        return False
    loaded = {n.id for n in ast.walk(tree)
              if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return bool(binds & loaded)


def dependency_used(path, dep):
    """Does the generation both IMPORT `dep` and REFERENCE what it imported at
    least once (not a dead import)? Parses the AST only — never imports the
    module — so it is independent of whether `dep` is installed. A generation
    delivered as a directory (a full project) passes if ANY of its `.py` files
    imports-and-uses `dep`."""
    if os.path.isdir(path):
        for root, _dirs, files in os.walk(path):
            for f in files:
                if f.endswith(".py") and _file_dep_used(os.path.join(root, f), dep):
                    return True
        return False
    return _file_dep_used(path, dep)
