import importlib.util
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_NL = os.path.dirname(_HERE)                         # .../kapitoshk4__.../nl
_REPO = os.path.dirname(_NL)                          # .../kapitoshk4__library-service-api
_REF = os.path.join(_REPO, "library-service-api-main")

SOURCE = "nl"
MODELS = ("claude", "gpt", "deepseek", "gemini")

# Some generations were later scaffolded into a full project and their single
# file renamed; fall back to the preserved "(original)" copy.
_FILE_CANDIDATES = ("generated_code.py", "generated_code(original).py")

_django_ready = False


def gencode_paths():
    out = []
    for model in MODELS:
        for fname in _FILE_CANDIDATES:
            p = os.path.join(_NL, "outputcode", model, fname)
            if os.path.exists(p):
                out.append((f"{SOURCE}/{model}", p))
                break
    return out


def _ensure_django():
    global _django_ready
    if _django_ready:
        return
    import django
    from django.conf import settings
    if not settings.configured:
        if _REF not in sys.path:
            sys.path.insert(0, _REF)
        cfg = types.ModuleType("_ref_apps")
        from django.apps import AppConfig
        for name, path in [("Books", "books"), ("Borrowings", "borrowings"),
                           ("Payments", "payments"), ("Users", "users")]:
            setattr(cfg, name + "Config",
                    type(name + "Config", (AppConfig,), {"name": path}))
        sys.modules["_ref_apps"] = cfg
        settings.configure(
            DEBUG=True,
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3",
                                   "NAME": ":memory:"}},
            INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth",
                            "django.contrib.admin.apps.SimpleAdminConfig",
                            "django.contrib.sessions", "django.contrib.messages",
                            "rest_framework",
                            "_ref_apps.BooksConfig", "_ref_apps.BorrowingsConfig",
                            "_ref_apps.PaymentsConfig", "_ref_apps.UsersConfig"],
            AUTH_USER_MODEL="users.User",
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


def load_gencodemodule(impl_id, path):
    _ensure_django()
    label = "genl_" + impl_id.replace("/", "_")
    _register_django_app(label, path)
    spec = importlib.util.spec_from_file_location(label, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[label] = module
    spec.loader.exec_module(module)
    return module
