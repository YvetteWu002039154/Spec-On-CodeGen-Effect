import ast
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_NL = os.path.dirname(_HERE)                         # .../nl

SOURCE = "nl"
MODELS = ("claude", "gpt", "deepseek", "gemini")

_MARKER = "@@PROBES@@"


def gencode_paths():
    # A generation delivered as a single file loads from its generated_code.py;
    # one delivered as a full multi-app Django project (deepseek) loads from its
    # project directory (see _load_project).
    out = []
    for model in MODELS:
        single = os.path.join(_NL, "outputcode", f"{model}.run0.py")
        d = os.path.join(_NL, "outputcode", f"{model}.run0")  # multi-file project
        out.append((f"{SOURCE}/{model}", single if os.path.exists(single) else d))
    return out


def run_probes(impl_id, path):
    """Run one generation's probes in an isolated subprocess; return its results.

    A dict ``{probe_name: {"status": ok|error, ...}}`` plus a ``"__load__"``
    entry describing whether the module + DB set-up succeeded.
    """
    proc = subprocess.run(
        [sys.executable, os.path.abspath(__file__), impl_id, path],
        capture_output=True, text=True, timeout=300)
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith(_MARKER):
            return json.loads(line[len(_MARKER):])
    return {"__load__": {"status": "error",
                         "error": "no probe output\n"
                                  + proc.stdout[-1500:] + "\n" + proc.stderr[-1500:]}}


# ---------------------------------------------------------------------------
# subprocess worker
# ---------------------------------------------------------------------------
def _load_generation(path):
    """Exec one single-file generation under module name 'generated_code'."""
    import importlib.util
    import django
    from django.conf import settings

    spec = importlib.util.spec_from_file_location("generated_code", path)
    module = importlib.util.module_from_spec(spec)
    module.__path__ = []  # act like a package so it can be an app root
    sys.modules["generated_code"] = module

    if not settings.configured:
        settings.configure(
            DEBUG=True, SECRET_KEY="x",
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3",
                                   "NAME": ":memory:"}},
            # Full contrib set: a generation may register with admin.site or
            # touch sessions/messages/staticfiles at import time.
            INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth",
                            "django.contrib.admin", "django.contrib.sessions",
                            "django.contrib.messages", "django.contrib.staticfiles",
                            "generated_code"],
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
            STATIC_URL="/static/", USE_TZ=True,
        )
    django.setup()

    spec.loader.exec_module(module)
    return module


def _load_project(project_dir):
    """Load a generation delivered as a full Django project"""
    import django
    sys.path.insert(0, project_dir)
    os.chdir(project_dir)
    # The settings package is the one dir that carries a settings.py.
    settings_pkg = next(
        name for name in os.listdir(project_dir)
        if os.path.exists(os.path.join(project_dir, name, "settings.py")))
    os.environ["DJANGO_SETTINGS_MODULE"] = f"{settings_pkg}.settings"
    from django.conf import settings
    settings.DATABASES["default"]["NAME"] = ":memory:"  # accessing it loads settings
    django.setup()
    return None  # driver imports models directly from the app packages


def _load(path):
    """Dispatch on delivery shape: a directory is a project, a file is single."""
    if os.path.isdir(path):
        return _load_project(path)
    import tempfile
    os.chdir(tempfile.mkdtemp(prefix="nl_amazon_"))
    return _load_generation(path)


def _setup_db():
    """Build a schema for the loaded app in the in-memory DB. Additionally
    create a table for every registered model via the schema editor.
    """
    from django.apps import apps
    from django.core.management import call_command
    from django.db import connection
    call_command("migrate", run_syncdb=True, verbosity=0, interactive=False)
    existing = set(connection.introspection.table_names())
    with connection.schema_editor() as editor:
        for model in apps.get_models():
            if model._meta.db_table in existing:
                continue
            try:
                editor.create_model(model)
            except Exception:  # noqa: BLE001 - m2m/through quirks; best effort
                pass


def _worker(impl_id, path):
    results = {}
    try:
        module = _load(path)
    except Exception as exc:  # noqa: BLE001
        import traceback
        results["__load__"] = {"status": "error",
                               "error": f"{type(exc).__name__}: {exc}",
                               "trace": traceback.format_exc()[-1200:]}
        print(_MARKER + json.dumps(results))
        return
    try:
        _setup_db()
        db_ok = True
        db_err = ""
    except Exception as exc:  # noqa: BLE001
        db_ok = False
        db_err = f"{type(exc).__name__}: {exc}"
    results["__load__"] = {"status": "ok", "db_ok": db_ok, "db_err": db_err}

    from adapter import build_driver, BEHAVIORS
    model = impl_id.split("/")[-1]
    driver = build_driver(model, module)
    for pname, method in BEHAVIORS:
        try:
            val = getattr(driver, method)()
            results[pname] = {"status": "ok", "value": val}
        except Exception as exc:  # noqa: BLE001
            results[pname] = {"status": "error",
                              "error": f"{type(exc).__name__}: {exc}"}
    print(_MARKER + json.dumps(results, default=str))


if __name__ == "__main__":
    sys.path.insert(0, _HERE)
    _worker(sys.argv[1], sys.argv[2])


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
