import ast
import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_NL = os.path.dirname(_HERE)                         # .../BismuthCloud__asimov/nl

SOURCE = "nl"
MODELS = ("claude", "gpt", "deepseek", "gemini")


def gencode_paths():
    out = []
    for model in MODELS:
        p = os.path.join(_NL, "outputcode", f"{model}.run{os.environ.get('RUN', '0')}.py")
        if os.path.exists(p):
            out.append((f"{SOURCE}/{model}", p))
    return out


def _dep_bindings(tree, dep):
    """Local names a file binds by importing package `dep` (top-level `dep` only).
    Handles `import dep`, `import dep.sub as x`, and `from dep[.sub] import a, b`.
    Returns the set of names those imports introduce into the module namespace."""
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


def dependency_used(path, dep):
    """Tier-A dependency check (fully static): does the generation both IMPORT the
    named package `dep` and REFERENCE what it imported at least once (not a dead
    import)? Parses the AST only — never imports the module — so it is independent
    of whether `dep` is installed and needs no stubbing."""
    tree = ast.parse(open(path).read())
    binds = _dep_bindings(tree, dep)
    if not binds:
        return False
    loaded = {n.id for n in ast.walk(tree)
              if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return bool(binds & loaded)


def load_gencodemodule(impl_id, path):
    # The test env installs the generations' third-party dependencies
    # (redis, opentelemetry, openai, anthropic), so the module imports directly.
    model = "gen_" + impl_id.replace("/", "_")
    spec = importlib.util.spec_from_file_location(model, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[model] = module
    spec.loader.exec_module(module)
    return module
