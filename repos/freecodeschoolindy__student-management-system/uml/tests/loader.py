import functools
import tempfile
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
            # Saved as a directory. Kept so the run is never skipped silently --
            # load_gencodemodules raises and the run scores 0.
            out.append((f"{SOURCE}/{model}", stem))
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
