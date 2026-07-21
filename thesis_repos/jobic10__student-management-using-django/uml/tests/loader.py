import importlib
import importlib.util
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_UML = os.path.dirname(_HERE)                        # .../<repo>/uml
_REPO = os.path.dirname(_UML)                        # .../<repo>
_REF = os.path.join(_REPO, "student-management-using-django-main")

SOURCE = "uml"
MODELS = ("claude", "gpt", "deepseek", "gemini")

_django_ready = False


def gencode_paths():
    out = []
    for model in MODELS:
        p = os.path.join(_UML, "outputcode", model, "generated_code.py")
        if os.path.exists(p):
            out.append((f"{SOURCE}/{model}", p))
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
        setattr(cfg, "MainAppConfig",
                type("MainAppConfig", (AppConfig,), {"name": "main_app"}))
        sys.modules["_ref_apps"] = cfg
        settings.configure(
            DEBUG=True,
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3",
                                   "NAME": ":memory:"}},
            INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth",
                            "_ref_apps.MainAppConfig"],
            AUTH_USER_MODEL="main_app.CustomUser",
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
            USE_TZ=True,
        )
        django.setup()
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
    label = "gima_" + impl_id.replace("/", "_")
    _register_django_app(label, path)
    spec = importlib.util.spec_from_file_location(label, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[label] = module
    spec.loader.exec_module(module)
    return module
