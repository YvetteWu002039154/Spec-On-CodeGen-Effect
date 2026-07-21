import ast
import importlib.util
import os
import sys
from types import ModuleType

_HERE = os.path.dirname(os.path.abspath(__file__))
_UML = os.path.dirname(_HERE)                        # .../BismuthCloud__asimov/uml

SOURCE = "uml"
MODELS = ("claude", "gpt", "deepseek", "gemini")


def gencode_paths():
    out = []
    for model in MODELS:
        p = os.path.join(_UML, "outputcode", model, "generated_code.py")
        if os.path.exists(p):
            out.append((f"{SOURCE}/{model}", p))
    return out


# A module may import third-party packages that aren't installed. We stub ONLY
# the top-level packages a module imports directly and that are genuinely
# missing, so real packages — and their own optional-dependency probes — still
# behave normally. The finder is shared and accumulates names across loads.

class _Stub(ModuleType):
    """Permissive module: any attribute access, call, subscription, or use as a
    base class yields another _Stub, so import-time references never crash."""
    __path__ = []

    def __getattr__(self, name):
        return _Stub(name)

    def __call__(self, *a, **k):
        return _Stub(self.__name__)

    def __getitem__(self, item):
        return self

    def __mro_entries__(self, bases):
        return ()


class _StubFinder:
    allow = set()

    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in self.allow:
            return importlib.util.spec_from_loader(name, self)
        return None

    def create_module(self, spec):
        return _Stub(spec.name)

    def exec_module(self, module):
        pass


_STUB_FINDER = _StubFinder()


def _missing_direct_imports(path):
    try:
        tree = ast.parse(open(path).read())
    except SyntaxError:
        return set()
    tops = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            tops |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            tops.add(n.module.split(".")[0])
    missing = set()
    for t in tops - set(sys.stdlib_module_names):
        try:
            if importlib.util.find_spec(t) is None:
                missing.add(t)
        except Exception:
            missing.add(t)
    return missing


def _stub_missing(*paths):
    for p in paths:
        _STUB_FINDER.allow |= _missing_direct_imports(p)
    if _STUB_FINDER not in sys.meta_path:
        sys.meta_path.append(_STUB_FINDER)  # last: real packages win


def load_gencodemodule(impl_id, path):
    _stub_missing(path)
    model = "gen_" + impl_id.replace("/", "_")
    spec = importlib.util.spec_from_file_location(model, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[model] = module
    spec.loader.exec_module(module)
    return module
