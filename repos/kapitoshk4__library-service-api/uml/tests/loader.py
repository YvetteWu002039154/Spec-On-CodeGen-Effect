import functools
import tempfile
import importlib
import importlib.util
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_UML = os.path.dirname(_HERE)                        # .../kapitoshk4__.../uml
_REPO = os.path.dirname(_UML)                        # .../kapitoshk4__library-service-api

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
            # Saved as a directory. Kept so the run is never skipped silently --
            # load_gencodemodules raises and the run scores 0.
            out.append((f"{SOURCE}/{model}", stem))
    return out


def _ensure_django():
    """Configure a minimal, self-contained Django once (idempotent).

    Reference-free: nothing here depends on the original repository. A
    Django-based generation FKs to the default `auth.User` and gets an app
    label via `_register_django_app`; plain-class generations are unaffected.
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
    label = "genu_" + impl_id.replace("/", "_")
    _register_django_app(label, path)
    spec = importlib.util.spec_from_file_location(label, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[label] = module
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
