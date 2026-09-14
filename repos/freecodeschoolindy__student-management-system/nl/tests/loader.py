import ast
import importlib.util
import os
import sys
import types

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "adapter_harness")))
import permissive_stubs  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_NL = os.path.dirname(_HERE)                         # .../<repo>/nl

SOURCE = "nl"
MODELS = ("claude", "gpt", "deepseek", "gemini")

# Optional third-party tops a generation might import. Any NOT importable on the
# host is stubbed; the rest (incl. django, when installed) are left real.
_OPTIONAL_TOPS = {
    "django", "rest_framework", "corsheaders", "oauth2_provider",
    "social_django", "debug_toolbar", "pydantic", "fastapi", "flask",
    "sqlalchemy", "bcrypt", "passlib", "jose", "dotenv",
}


_MISSING = permissive_stubs.missing_tops(_OPTIONAL_TOPS)


def gencode_paths():
    out = []
    for model in MODELS:
        p = os.path.join(_NL, "outputcode", f"{model}.run0.py")
        if os.path.exists(p):
            out.append((f"{SOURCE}/{model}", p))
    return out


# --- minimal Django, enough that a Django-based generation actually runs ----
# Started as bare contenttypes+auth ("so a Django-based generation fails
# cleanly"); a generation that does ordinary `admin.site.register(...)` /
# extends `UserAdmin` needs the admin/sessions/messages apps installed too, or
# it dies at import with `LookupError: No installed app with label 'admin'`
# before any behaviour is exercised. This is standard Django project
# scaffolding, not a change to any generation's code — the same fairness
# category as the psycopg2 UUID adapter registered for vstorm.
_django_ready = False


def _maybe_configure_django():
    global _django_ready
    if _django_ready or "django" in _MISSING:
        return
    try:
        import django
        from django.conf import settings
        if not settings.configured:
            settings.configure(
                DEBUG=True,
                DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3",
                                       "NAME": ":memory:"}},
                INSTALLED_APPS=["django.contrib.contenttypes",
                                "django.contrib.auth",
                                "django.contrib.admin",
                                "django.contrib.sessions",
                                "django.contrib.messages"],
                DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
                USE_TZ=True,
            )
            django.setup()
        _django_ready = True
    except Exception:
        # If Django cannot be configured, a Django-based generation will simply
        # raise on import and be recorded as a skip.
        pass


def _register_django_app(label, path):
    """Give a standalone generation module its own Django app label, so its
    `models.Model` subclasses (and anything referencing them, e.g. admin
    registration) resolve instead of raising `LookupError` / `RuntimeError:
    Model class ... doesn't declare an explicit app_label`."""
    import types
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


def _create_tables_for(module, label):
    """Create a real SQLite table for every `models.Model` subclass the
    generation defines, so ORM calls (`.objects.create/.get/.filter`) work
    without hand-written migrations. Infrastructure only — no generation
    content is touched. Best-effort: a model that fails to create (e.g. an
    unsupported field) is skipped, not fatal."""
    try:
        from django.db import models as dj_models, connection
    except Exception:
        return
    seen = []
    for name in dir(module):
        try:
            val = getattr(module, name)
        except Exception:
            continue
        if (isinstance(val, type) and issubclass(val, dj_models.Model)
                and val.__module__ == module.__name__ and not val._meta.abstract):
            seen.append(val)
    with connection.schema_editor() as editor:
        for model in seen:
            try:
                editor.create_model(model)
            except Exception:
                pass


def _load_path(mod_name, path):
    permissive_stubs.install(_MISSING)
    _maybe_configure_django()
    if _django_ready:
        _register_django_app(mod_name, path)
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    if _django_ready:
        _create_tables_for(module, mod_name)
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
