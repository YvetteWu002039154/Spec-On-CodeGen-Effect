import ast
import importlib
import importlib.util
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_UML = os.path.dirname(_HERE)                        # .../<repo>/uml
_REPO = os.path.dirname(_UML)                        # .../<repo>

SOURCE = "uml"
MODELS = ("claude", "gpt", "deepseek", "gemini")

_django_ready = False


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


def _ensure_django():
    """Configure a minimal, self-contained Django once (idempotent).

    Reference-free: the ground truth is `description.txt`, so nothing here
    depends on the original repository. A Django-based generation gets enough
    scaffolding to import (its models are given an app label via
    `_register_django_app`); a plain-class generation is unaffected by this
    running.
    """
    global _django_ready
    if _django_ready:
        return
    import django
    from django.conf import settings
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3",
                                   "NAME": ":memory:"}},
            INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth",
                            "django.contrib.admin", "django.contrib.sessions",
                            "django.contrib.messages"],
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
            USE_TZ=True,
            SECRET_KEY="conformance-test-secret-key",
        )
        django.setup()
    _django_ready = True


def _register_django_app(label, path):
    """Give a standalone generation module its own Django app label so its
    `models.Model` subclasses resolve without an explicit app_label. No-op for
    plain-class generations (they simply never register any model)."""
    from django.apps import AppConfig, apps
    if label in apps.app_configs:
        return
    mod = types.ModuleType(label)
    mod.__path__ = [os.path.dirname(os.path.abspath(path))]
    conf = AppConfig(label, mod)
    conf.models = {}
    conf.apps = apps
    apps.app_configs[label] = conf
    apps.all_models.setdefault(label, {})
    apps.clear_cache()


def load_gencodemodule(impl_id, path):
    """Load one generated_code.py under a unique module name. Raises on failure."""
    _ensure_django()  # so a Django-based generation has settings + an app label
    mod_name = "gen_" + impl_id.replace("/", "_")
    _register_django_app(mod_name, path)
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    module.__package__ = mod_name
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


# ── multi-file / chatty generations ─────────────────────────────────────────
# A generation is normally ONE flat file, <model>.run<N>.py. A few generations
# were saved as an unpacked TREE (a directory of that same name) because the
# model ignored the "single file, no prose, no fences" instruction and returned
# several code blocks; step2's _strip_fences only removes an outer fence, so the
# saved text was not valid Python and something later split it into files.
#
# gencode_paths() used to see only the flat form, so those runs produced no
# result slot and were SILENTLY DROPPED from the N-run average (n_runs_averaged
# fell to 8 or 9). Dropping is the worst option: it is non-random -- a run
# disappears precisely when the model emitted an unusually structured answer --
# so the average is computed on a biased subset. These runs are now always
# scored. Recovery is attempted in a documented cascade, and when nothing is
# recoverable the raw text is loaded anyway so a genuinely broken generation
# scores as broken (0) instead of vanishing.

_TREE_ORIGINAL   = "generated_code(original).py"
_TREE_SKIP_DIRS  = {"__pycache__", ".ipynb_checkpoints"}


def _tree_parses(src):
    try:
        ast.parse(src)
        return True
    except SyntaxError:
        return False


def _tree_exec(impl_id, src, filename, suffix=""):
    """Exec one source text as a single synthetic module — the same semantics a
    flat generation gets. Compiled under `filename` so inspect.getsource() on the
    resulting methods still resolves."""
    import types as _types
    name = "gen_" + impl_id.replace("/", "_") + suffix
    module = _types.ModuleType(name)
    module.__file__ = filename
    module.__dict__["__name__"] = name
    sys.modules[name] = module
    exec(compile(src, filename, "exec"), module.__dict__)
    return [module]


def _tree_py_files(tree_dir):
    out = []
    for dirpath, dirnames, filenames in os.walk(tree_dir):
        dirnames[:] = [d for d in dirnames if d not in _TREE_SKIP_DIRS]
        for fn in sorted(filenames):
            if fn.endswith(".py") and fn != _TREE_ORIGINAL:
                out.append(os.path.join(dirpath, fn))
    return out


def _tree_stub(paths):
    """Reuse whichever stub mechanism this repo's loader already defines."""
    fn = globals().get("_stub_missing")
    if fn is not None:
        fn(*paths)
        return
    fn = globals().get("_install_stubs")
    if fn is not None:
        fn()


def _tree_as_package(impl_id, tree_dir):
    """(b) The tree is a REAL package: fragments import each other properly.
    Import each module under its true dotted name so intra-package imports
    resolve and cross-module inheritance stays one class object. Returns the
    module list, or None if any fragment fails (then it was not a real package).
    sys.modules is rolled back: four models in one pytest process can each ship
    a top-level package of the same name."""
    import importlib
    src_dir = os.path.join(tree_dir, "src")
    roots = ([src_dir] if os.path.isdir(src_dir) else []) + [tree_dir]
    files = _tree_py_files(tree_dir)
    if not files:
        return None
    before = set(sys.modules)
    added = [r for r in roots if r not in sys.path]
    sys.path[:0] = added
    modules = []
    try:
        for path in sorted(files, key=lambda p: (p.count(os.sep),
                                                 os.path.basename(p) != "__init__.py")):
            root = src_dir if (os.path.isdir(src_dir) and
                               path.startswith(src_dir + os.sep)) else tree_dir
            rel = os.path.relpath(path, root)[:-3].split(os.sep)
            if rel[-1] == "__init__":
                rel = rel[:-1]
            if not rel or any(not part.isidentifier() for part in rel):
                return None
            modules.append(importlib.import_module(".".join(rel)))
    except Exception:                                       # noqa: BLE001
        return None
    finally:
        for r in added:
            try:
                sys.path.remove(r)
            except ValueError:
                pass
        for name in set(sys.modules) - before:
            sys.modules.pop(name, None)
    return modules or None


def _tree_after_last_fence(src):
    """(c) A chatty response whose FINAL block is the complete implementation
    (the models say so in prose: "let me provide the complete, single-file
    implementation"). Returns that region if it is valid Python."""
    if "```" not in src:
        return None
    tail = src.split("```")[-1].lstrip("\n \t")
    # Splitting on the fence marker leaves the info string ("python") as the
    # first line. ast.parse() accepts it -- a bare name is a valid expression --
    # so it must be removed explicitly or the module NameErrors at exec time,
    # and `from __future__` is no longer the first statement.
    first, _, rest = tail.partition("\n")
    if first.strip().lower() in ("python", "py", "python3"):
        tail = rest.lstrip("\n")
    return tail if tail.strip() and _tree_parses(tail) else None


def _load_tree(impl_id, tree_dir):
    orig_path = os.path.join(tree_dir, _TREE_ORIGINAL)
    orig = None
    if os.path.exists(orig_path):
        orig = open(orig_path, encoding="utf-8", errors="replace").read()

    _tree_stub(_tree_py_files(tree_dir) + ([orig_path] if orig is not None else []))

    # (a) the raw generation is already valid Python — score exactly it
    if orig is not None and _tree_parses(orig):
        _load_tree.recovery = "original"
        return _tree_exec(impl_id, orig, orig_path)

    # (b) a genuine multi-file package
    mods = _tree_as_package(impl_id, tree_dir)
    if mods:
        _load_tree.recovery = "package"
        return mods

    # (c) the final code block of a chatty response
    if orig is not None:
        tail = _tree_after_last_fence(orig)
        if tail is not None:
            _load_tree.recovery = "last-block"
            return _tree_exec(impl_id, tail, orig_path, "_tail")

    # (d) nothing recoverable: load the raw text so the generation is SCORED
    #     (it will fail to load and every structural check fails) rather than
    #     dropped from the average.
    _load_tree.recovery = "unrecoverable"
    return _tree_exec(impl_id, orig if orig is not None else "", orig_path)


def load_gencodemodules(impl_id, path):
    """Modules of one implementation: one for a flat file, one or more for a
    generation stored as a directory. structure.Implementation takes a list."""
    if os.path.isdir(path):
        return _load_tree(impl_id, path)
    return [load_gencodemodule(impl_id, path)]
