import importlib.util
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_NL = os.path.dirname(_HERE)                         # .../kapitoshk4__.../nl
_REPO = os.path.dirname(_NL)                          # .../kapitoshk4__library-service-api

SOURCE = "nl"
MODELS = ("claude", "gpt", "deepseek", "gemini")

_django_ready = False


def gencode_paths():
    # Flat single-file generations live at outputcode/<model>.run0.py.
    # Some generations were later scaffolded into a full project (deepseek, gpt)
    # and kept as an outputcode/<model>/ directory; step3 loads the preserved
    # single-file "(original)" copy from inside that directory.
    out = []
    for model in MODELS:
        candidates = (
            os.path.join(_NL, "outputcode", f"{model}.run0.py"),
            os.path.join(_NL, "outputcode", f"{model}.run0",
                         "generated_code(original).py"),
        )
        for p in candidates:
            if os.path.exists(p):
                out.append((f"{SOURCE}/{model}", p))
                break
    return out


def _ensure_django():
    """Configure a minimal, self-contained Django once (idempotent).

    Reference-free: the ground truth is `description.txt`, so nothing here
    depends on the original repository. The Django-based generations (gpt,
    deepseek) FK to `settings.AUTH_USER_MODEL`, which is left as the default
    `auth.User`; each generation's own models get an app label via
    `_register_django_app`. The plain-Python (claude) and FastAPI (gemini)
    generations are unaffected by this running.
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
                            "django.contrib.admin.apps.SimpleAdminConfig",
                            "django.contrib.sessions", "django.contrib.messages",
                            "rest_framework"],
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
            USE_TZ=True,
            STRIPE_API_KEY="sk_test_dummy",
            SECRET_KEY="conformance-test-secret-key",
        )
        django.setup()
        # Compat shim: Django 6 renamed CheckConstraint(check=) -> condition=.
        try:
            from django.db.models import CheckConstraint
            _orig = CheckConstraint.__init__

            def _patched(self, *a, **k):
                if "check" in k and "condition" not in k:
                    k["condition"] = k.pop("check")
                return _orig(self, *a, **k)

            CheckConstraint.__init__ = _patched
        except Exception:
            pass
    _django_ready = True


def _register_django_app(label, file_path):
    from django.apps import AppConfig, apps
    if label in apps.app_configs:
        return
    mod = types.ModuleType(label)
    mod.__path__ = [os.path.dirname(os.path.abspath(file_path))]
    conf = AppConfig(label, mod)
    conf.models = {}
    conf.apps = apps
    apps.app_configs[label] = conf
    apps.all_models.setdefault(label, {})
    apps.clear_cache()


def _load_flat_file(label, path):
    spec = importlib.util.spec_from_file_location(label, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[label] = module
    spec.loader.exec_module(module)
    return module


def _load_scaffolded_package(label, pkg_dir):
    """Some `generated_code(original).py` flat dumps concatenate what was
    really a multi-file Django app (`# File: api/models.py`, `# File:
    api/admin.py`, ...) and keep each section's own `from .models import ...`
    — which only resolves inside a real package, not a flattened script, so
    the flat file raises `ImportError: attempted relative import with no
    known parent package`. A byte-identical, mechanically-split copy of the
    *same* generation is preserved alongside it as a real package (e.g.
    `api/`); importing that instead is infrastructure only — same content,
    correctly structured — not a change to the generation.

    Returns a single flat namespace merging every submodule's public names,
    matching the shape the flat file would have exposed if the relative
    imports had resolved.
    """
    import types

    # `label` is already registered as this generation's Django app (see
    # `_register_django_app`, called on the flat path before this runs).
    # Submodules must live under that same dotted name so Django's app-label
    # lookup (a prefix match on `__module__`) resolves them to it.
    flat = types.ModuleType(label)
    flat.__path__ = [pkg_dir]
    sys.modules[label] = flat
    for fname in sorted(os.listdir(pkg_dir)):
        if not fname.endswith(".py") or fname == "__init__.py":
            continue
        sub_name = f"{label}.{fname[:-3]}"
        spec = importlib.util.spec_from_file_location(sub_name, os.path.join(pkg_dir, fname))
        sub = importlib.util.module_from_spec(spec)
        sub.__package__ = label
        sys.modules[sub_name] = sub
        spec.loader.exec_module(sub)
        for name in dir(sub):
            if not name.startswith("_"):
                setattr(flat, name, getattr(sub, name))
    return flat


def load_gencodemodule(impl_id, path):
    _ensure_django()
    label = "genl_" + impl_id.replace("/", "_")
    _register_django_app(label, path)
    try:
        return _load_flat_file(label, path)
    except ImportError as exc:
        if "relative import" not in str(exc):
            raise
        pkg_dir = os.path.join(os.path.dirname(path), "api")
        if not os.path.isdir(pkg_dir):
            raise
        # The flat exec got partway through (e.g. defined Book/Borrowing/
        # Payment) before hitting the bad relative import, which left those
        # classes registered in Django's app registry. Undo that partial
        # registration before re-running the same app label via the package.
        from django.apps import apps
        apps.all_models[label] = {}
        apps.clear_cache()
        return _load_scaffolded_package(label, pkg_dir)
