import functools
import tempfile
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
        stem = os.path.join(_UML, "outputcode",
                            f"{model}.run{os.environ.get('RUN', '0')}")
        if os.path.exists(stem + ".py"):
            out.append((f"{SOURCE}/{model}", stem + ".py"))
        elif os.path.isdir(stem):
            # Saved as a directory. Kept so the run is never skipped silently --
            # load_gencodemodules raises and the run scores 0.
            out.append((f"{SOURCE}/{model}", stem))
    return out


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
