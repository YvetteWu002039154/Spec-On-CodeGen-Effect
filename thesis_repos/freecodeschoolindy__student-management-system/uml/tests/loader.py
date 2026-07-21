import importlib
import importlib.util
import os
import sys
import types

_HERE = os.path.dirname(os.path.abspath(__file__))
_UML = os.path.dirname(_HERE)                        # .../<repo>/uml
_REPO = os.path.dirname(_UML)                        # .../<repo>
_REF = os.path.join(_REPO, "student-management-system-main")

SOURCE = "uml"
MODELS = ("claude", "gpt", "deepseek", "gemini")

# app label -> dotted module path; these cover every class the diagram draws
# that the contract pins (AbstractTableMeta, User/CustomUserManager/UserProfile,
# Certificate, WaitlistEntry, Volunteer/VolunteerHours).
_REF_APPS = [
    ("Utils", "apps.utils"),
    ("Users", "apps.users"),
    ("Certificates", "apps.certificates"),
    ("Waitlist", "apps.waitlist"),
    ("Volunteers", "apps.volunteers"),
]

_django_ready = False


def gencode_paths():
    out = []
    for model in MODELS:
        p = os.path.join(_UML, "outputcode", model, "generated_code.py")
        if os.path.exists(p):
            out.append((f"{SOURCE}/{model}", p))
    return out


def _ensure_django():
    """Configure a minimal Django once (idempotent)."""
    global _django_ready
    if _django_ready:
        return
    import django
    from django.conf import settings
    if not settings.configured:
        if _REF not in sys.path:
            sys.path.insert(0, _REF)
        # The project's apps.py declare bare labels ('users' for apps.users);
        # supply AppConfigs with the correct dotted names.
        cfg = types.ModuleType("_ref_apps")
        from django.apps import AppConfig
        for name, path in _REF_APPS:
            setattr(cfg, name + "Config",
                    type(name + "Config", (AppConfig,), {"name": path}))
        sys.modules["_ref_apps"] = cfg
        settings.configure(
            DEBUG=True,
            DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3",
                                   "NAME": ":memory:"}},
            INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth"]
            + [f"_ref_apps.{n}Config" for n, _ in _REF_APPS],
            AUTH_USER_MODEL="users.User",
            DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
            USE_TZ=True,
        )
        django.setup()
    _django_ready = True


def load_gencodemodule(impl_id, path):
    """Load one generated_code.py under a unique module name. Raises on failure."""
    _ensure_django()  # so a Django-based generation at least has settings
    mod_name = "gen_" + impl_id.replace("/", "_")
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module
