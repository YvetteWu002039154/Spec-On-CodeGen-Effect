import ast
import contextlib
import importlib.util
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_NL = os.path.dirname(_HERE)                         # .../nishant0820__.../nl

SOURCE = "nl"
MODELS = ("claude", "gpt", "deepseek", "gemini")


def gencode_paths():
    out = []
    for model in MODELS:
        p = os.path.join(_NL, "outputcode", f"{model}.run0.py")
        if os.path.exists(p):
            out.append((f"{SOURCE}/{model}", p))
    return out


@contextlib.contextmanager
def _scratch_cwd():
    """Run inside a throwaway dir so any import-time DB/file creation in the
    generated code lands there, not in the repo tree."""
    prev = os.getcwd()
    tmp = tempfile.mkdtemp(prefix="ims_import_")
    os.chdir(tmp)
    try:
        yield
    finally:
        os.chdir(prev)


def _load_path(mod_name, path):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    with _scratch_cwd():
        spec.loader.exec_module(module)
    return module


def load_gencodemodule(impl_id, path):
    """Load one generated_code.py under a unique module name. Raises on failure."""
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
