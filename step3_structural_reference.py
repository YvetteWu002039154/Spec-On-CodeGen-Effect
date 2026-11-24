"""Step 3b-ref — Structural fidelity of the ORIGIN repos (reference ceiling).

Usage:
    python step3_structural_reference.py              # every configured repo
    python step3_structural_reference.py getkanchi__kanchi m-danya__planty

Runs each repo's UML structural suite (repos/<repo>/uml/tests) UNCHANGED against
the original source the class diagram was extracted from, scored under the impl
id `uml/original`. This answers "what does the suite give the ground truth?" — a
score below 1.0 is a suite/measurement artifact, not a model failure.

How: the tests dir is copied to a temp dir and its loader.py is replaced by a
reference loader that imports the origin modules named in REPOS below (taken
from the module qualifiers in uml/input/classes.puml). test_conformance.py and
structure.py are untouched, so the reference is scored by exactly the same
assertions as the generations.

Origin source is NOT kept: if repos/<repo>/<name>-main/ (gitignored) is absent,
it is downloaded at the pinned `commit` below — the last upstream commit before
the repo entered this study — and can be deleted again after the run.

Writes repos/<repo>/ref_fidelity_results.json (NOT results.json, which is owned
by the generation scorers). step5_build_db loads it into the
ref_fidelity_results table.
"""

import json
import os
import shutil
import sys
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

import requests

from step3_common import REPOS_DIR, aggregate, run_conformance_suite

IMPL_ID = "uml/original"
TIMEOUT = 300

# root:    directory (relative to the origin checkout) put on sys.path
# modules: modules imported from root — the ones classes.puml draws classes from
# django:  local app labels to install + AUTH_USER_MODEL, as in the origin settings
REPOS = {
    "BismuthCloud__asimov": {
        "github": "BismuthCloud/asimov", "commit": "fb9ad6c895e978bca53cdd52660826a394c8e83d",
        "src": "asimov-main", "root": ".",
        "modules": ["asimov.asimov_base", "asimov.constants",
                    "asimov.executors.executor", "asimov.graph",
                    "asimov.graph.agent_directed_flow", "asimov.graph.tasks"],
    },
    "Twiddllo__NexusCtrl": {
        "github": "Twiddllo/NexusCtrl", "commit": "2d29c139ff8eaa735df59745c7a30e9c7a9fba88",
        "src": "NexusCtrl-main", "root": "backend", "modules": ["app"],
    },
    "ecopque__new_banking_system": {
        "github": "ecopque/new_banking_system", "commit": "62e0a6b43932687562676ac69be8ef91e5665ca3",
        "src": "new_banking_system-main", "root": ".", "modules": ["main"],
    },
    "freecodeschoolindy__student-management-system": {
        "github": "freecodeschoolindy/student-management-system", "commit": "92bad4b6200217c4364d94a471b9ad0098d5222e",
        "src": "student-management-system-main", "root": ".",
        "modules": ["apps.certificates.models", "apps.lectures.models",
                    "apps.projects.models", "apps.submissions.models",
                    "apps.users.models", "apps.utils.models",
                    "apps.volunteers.models", "apps.waitlist.models"],
        "django": {"apps": ["apps.utils", "apps.users", "apps.certificates",
                            "apps.waitlist", "apps.lectures", "apps.projects",
                            "apps.submissions", "apps.volunteers"],
                   "auth_user_model": "users.User",
                   # apps.py says name='users' — valid only on the Django the
                   # project pinned (no AppConfig auto-detection). Rebuild the
                   # old behaviour: AppConfig(name=<dotted>, label=<last part>).
                   "synth_appconfig": True},
    },
    "getkanchi__kanchi": {
        "github": "getkanchi/kanchi", "commit": "ecc07bba728b0a344eece436af70ef36bd0ac989",
        # agent/ is its own import root (`from models import ...`)
        "src": "kanchi-main", "root": "agent",
        "modules": ["database", "connection_manager", "event_handler", "monitor",
                    "services.actions.base", "services.actions.retry_action",
                    "services.actions.slack_action"],
    },
    "hackstarsj__AmazonCloneEcommerceProjectUsingDjangoReact": {
        "github": "hackstarsj/AmazonCloneEcommerceProjectUsingDjangoReact", "commit": "dc979933a7c531dbb9b9522d0295a472a01070b7",
        "src": "AmazonCloneEcommerceProjectUsingDjangoReact-main",
        "root": "Backend/EcommerceInventory",
        "modules": ["UserServices.models", "ProductServices.models",
                    "OrderService.models", "InventoryServices.models"],
        "django": {"apps": ["UserServices", "ProductServices", "OrderService",
                            "InventoryServices"],
                   "auth_user_model": "UserServices.Users"},
    },
    "jobic10__student-management-using-django": {
        "github": "jobic10/student-management-using-django", "commit": "066dcaeffc52fe52e9279d93e2a00c15909544ae",
        "src": "student-management-using-django-main", "root": ".",
        "modules": ["main_app.models"],
        "django": {"apps": ["main_app.apps.MainAppConfig"],
                   "auth_user_model": "main_app.CustomUser"},
    },
    "kapitoshk4__library-service-api": {
        "github": "kapitoshk4/library-service-api", "commit": "e9b2a7238b7e3156244e7417aa3a438152b47672",
        "src": "library-service-api-main", "root": ".",
        "modules": ["books.models", "borrowings.models", "payments.models",
                    "users.models"],
        "django": {"apps": ["books", "users", "borrowings", "payments"],
                   "auth_user_model": "users.User"},
    },
    "m-danya__planty": {
        "github": "m-danya/planty", "commit": "70c78b749fa2c87d9d015251d82bdea95daeebc2",
        "src": "planty-main", "root": ".",
        "modules": ["planty.domain.task", "planty.infrastructure.models",
                    "planty.infrastructure.repositories", "planty.application.uow"],
        # models.UserModel subclasses fastapi-users' SQLAlchemyBaseUserTableUUID,
        # which supplies the PK — a stub can't stand in. Real pinned packages
        # (uv.lock) are pip-installed into <checkout>/.ref_deps on download and
        # appended to sys.path, so anything already installed still wins.
        "extra_sys_path": [".ref_deps"],
        "ref_deps": ["fastapi-users==14.0.0", "fastapi-users-db-sqlalchemy==6.0.1"],
        # planty.config.Settings has required fields read from env at import;
        # dummy values (env_prefix="PLANTY_") — nothing connects to anything.
        "env": {"PLANTY_MODE": "TEST", "PLANTY_DB_TYPE": "sqlite", "PLANTY_DB_HOST": "x", "PLANTY_DB_PORT": "1",
                "PLANTY_DB_USER": "x", "PLANTY_DB_NAME": "x", "PLANTY_DB_PASS": "x",
                "PLANTY_TEST_DB_HOST": "x", "PLANTY_TEST_DB_PORT": "1", "PLANTY_TEST_DB_USER": "x",
                "PLANTY_TEST_DB_NAME": "x", "PLANTY_TEST_DB_PASS": "x", "PLANTY_AWS_URL": "x",
                "PLANTY_AWS_SECRET_ACCESS_KEY": "x", "PLANTY_AWS_ACCESS_KEY_ID": "x",
                "PLANTY_AWS_ATTACHMENTS_BUCKET": "x", "PLANTY_AUTH_SECRET": "x"},
    },
    "nishant0820__Inventory-Management-System": {
        "github": "nishant0820/Inventory-Management-System", "commit": "4c57b985f4de15ab017f21d6cef16920e8c09363",
        "src": "Inventory-Management-System-main", "root": ".",
        "modules": ["billing", "category", "dashboard", "employee", "product",
                    "sales", "supplier"],
    },
    # shenmintao__marginalia: upstream deleted (GitHub 404, not in Software
    # Heritage) and no local copy survives — no reference possible.
    "vstorm-co__pydantic-ai-todo": {
        "github": "vstorm-co/pydantic-ai-todo", "commit": "ae513666650c27828278a789e5bdd482b4ae0470",
        "src": "pydantic-ai-todo-main", "root": ".",
        "modules": ["pydantic_ai_todo.capability", "pydantic_ai_todo.events",
                    "pydantic_ai_todo.storage", "pydantic_ai_todo.types"],
        # __init__ calls importlib.metadata.version("pydantic-ai-todo")
        "fake_dists": {"pydantic-ai-todo": "0.2.6"},
    },
}


# The replacement loader. Reads its config from REF_CONFIG (JSON) so the file
# itself is identical for every repo.
REF_LOADER = r'''
import importlib, importlib.abc, importlib.util, json, os, sys, tempfile, types

_CFG = json.loads(os.environ["REF_CONFIG"])
STUBBED = set()


def gencode_paths():
    return [(_CFG["impl_id"], _CFG["root"])]


# -- permissive stubs for third-party packages the origin needs but this env
#    lacks. Appended LAST to sys.meta_path, so any real package wins. Same
#    semantics as the suites' own loaders: a stubbed name used as a base class
#    drops out of the bases (__mro_entries__ -> ()), so it can never cause a
#    metaclass conflict; local inheritance between origin classes is untouched.
class _Perm:
    def __init__(self, name="Perm"):
        self.__name__ = name
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return _Perm(name)
    def __call__(self, *a, **k):
        if len(a) == 1 and callable(a[0]) and not k:
            return a[0]                      # used as a bare decorator
        return _Perm(self.__name__ + "()")
    def __getitem__(self, item):
        return self
    def __mro_entries__(self, bases):
        return ()
    def __or__(self, o):
        return self
    __ror__ = __or__

class _PermModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return _Perm(name)

class _StubFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Stubs ONLY packages the origin source imports directly and this env
    lacks. Installed libraries' own optional `try: import x` probes are never
    answered (that would hand e.g. redis a fake `hiredis`)."""
    def __init__(self, allow):
        self.allow = allow
    def find_spec(self, name, path=None, target=None):
        hit = next((p for p in self.allow
                    if name == p or name.startswith(p + ".")), None)
        if hit is None:
            return None
        STUBBED.add(hit)
        return importlib.util.spec_from_loader(name, self, is_package=True)
    def create_module(self, spec):
        m = _PermModule(spec.name)
        m.__path__ = []
        return m
    def exec_module(self, module):
        pass


_SKIP_DIRS = {"node_modules", ".venv", "venv", "env", "site-packages", ".git",
              ".ref_deps"}

def _origin_missing_imports(root, local_tops):
    import ast
    tops = set()
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in _SKIP_DIRS]
        for fn in fns:
            if not fn.endswith(".py"):
                continue
            try:
                tree = ast.parse(open(os.path.join(dp, fn), encoding="utf-8").read())
            except (SyntaxError, UnicodeDecodeError, ValueError):
                continue
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    tops |= {a.name for a in n.names}
                elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                    tops.add(n.module)
    # smallest missing dotted prefix, e.g. `opentelemetry.instrumentation` when
    # opentelemetry is installed but its instrumentation extra is not
    missing = set()
    for dotted in tops:
        parts = dotted.split(".")
        if parts[0] in sys.stdlib_module_names or parts[0] in local_tops:
            continue
        for i in range(1, len(parts) + 1):
            prefix = ".".join(parts[:i])
            try:
                found = importlib.util.find_spec(prefix) is not None
            except Exception:
                found = False
            if not found:
                missing.add(prefix)
                break
    return missing


def _synth_appconfigs(app_paths, root):
    from django.apps import AppConfig
    mod = types.ModuleType("_ref_appconfigs")
    entries = []
    for i, name in enumerate(app_paths):
        cls = type(f"RefApp{i}", (AppConfig,), {
            "name": name, "label": name.rsplit(".", 1)[-1],
            "path": os.path.join(root, *name.split(".")),
            "default_auto_field": "django.db.models.AutoField",
        })
        setattr(mod, cls.__name__, cls)
        entries.append(f"_ref_appconfigs.{cls.__name__}")
    sys.modules["_ref_appconfigs"] = mod
    return entries


def _setup_django(dj):
    import django
    from django.conf import settings
    if settings.configured:
        return
    settings.configure(
        DEBUG=True,
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3",
                               "NAME": ":memory:"}},
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth",
                        "django.contrib.admin", "django.contrib.sessions",
                        "django.contrib.messages"]
                       + (_synth_appconfigs(dj["apps"], _CFG["root"])
                          if dj.get("synth_appconfig") else dj["apps"]),
        AUTH_USER_MODEL=dj["auth_user_model"],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        USE_TZ=True,
        SECRET_KEY="reference-structural-run",
    )
    django.setup()


def load_gencodemodules(impl_id, path):
    root = _CFG["root"]
    sys.path.insert(0, root)
    local_tops = {n.split(".")[0] for n in os.listdir(root)
                  if not n.startswith(".")} | \
                 {n[:-3] for n in os.listdir(root) if n.endswith(".py")}
    for extra in _CFG.get("extra_sys_path") or []:
        sys.path.append(os.path.join(root, extra))
    os.environ.update(_CFG.get("env") or {})
    if _CFG.get("fake_dists"):
        d = tempfile.mkdtemp(prefix="uml_ref_dists_")
        for dist, ver in _CFG["fake_dists"].items():
            info = os.path.join(d, dist.replace("-", "_") + "-" + ver + ".dist-info")
            os.makedirs(info)
            with open(os.path.join(info, "METADATA"), "w") as f:
                f.write(f"Metadata-Version: 2.1\nName: {dist}\nVersion: {ver}\n")
        sys.path.append(d)
    sys.meta_path.append(_StubFinder(_origin_missing_imports(root, local_tops)))
    prev = os.getcwd()
    os.chdir(tempfile.mkdtemp(prefix="uml_ref_"))   # never write into the repo
    try:
        if _CFG.get("django"):
            _setup_django(_CFG["django"])
        mods = [importlib.import_module(m) for m in _CFG["modules"]]
    finally:
        os.chdir(prev)
        if STUBBED:
            print(f"[reference] stubbed third-party: {sorted(STUBBED)}",
                  file=sys.stderr)
            with open(os.path.join(os.path.dirname(__file__), "_stubbed.json"), "w") as f:
                json.dump(sorted(STUBBED), f)
    return mods
'''


def download_origin(cfg: dict, dest: Path) -> None:
    """Fetch the pinned commit's archive from GitHub into `dest`."""
    url = f"https://github.com/{cfg['github']}/archive/{cfg['commit']}.zip"
    print(f"  downloading {url}")
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(BytesIO(r.content)) as zf:
        zf.extractall(tmp)
        (top,) = os.listdir(tmp)              # GitHub zips: one <repo>-<sha>/ dir
        shutil.move(os.path.join(tmp, top), dest)
    if cfg.get("ref_deps"):
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--target",
                        str(dest / ".ref_deps"), *cfg["ref_deps"]], check=True)


def score_reference(repo: str, cfg: dict) -> dict:
    repo_dir = REPOS_DIR / repo
    src = repo_dir / cfg["src"]
    if not src.is_dir():
        download_origin(cfg, src)
    pinned = cfg["commit"]

    with tempfile.TemporaryDirectory(prefix=f"ref_{repo}_") as tmp:
        tests = Path(tmp) / "tests"
        shutil.copytree(repo_dir / "uml" / "tests", tests,
                        ignore=shutil.ignore_patterns("__pycache__"))
        (tests / "loader.py").write_text(REF_LOADER)

        os.environ["REF_CONFIG"] = json.dumps({
            "impl_id": IMPL_ID,
            "root": str((src / cfg["root"]).resolve()),
            "modules": cfg["modules"],
            "django": cfg.get("django"),
            "env": cfg.get("env"),
            "fake_dists": cfg.get("fake_dists"),
            "extra_sys_path": cfg.get("extra_sys_path"),
        })
        try:
            tree = run_conformance_suite(tests, timeout=TIMEOUT)
        finally:
            del os.environ["REF_CONFIG"]
        stubbed_file = tests / "_stubbed.json"
        stubbed = json.loads(stubbed_file.read_text()) if stubbed_file.exists() else []

    if tree is None:
        return {"error": "pytest produced no report (timeout or crash)"}
    slot = aggregate(tree).get(IMPL_ID)
    if slot is None:
        return {"error": "no uml/original tests collected (collection error?)"}
    return {
        **slot,
        "pinned_commit": pinned,
        "stubbed_third_party": stubbed,
    }


def main() -> None:
    wanted = sys.argv[1:] or sorted(REPOS)
    summary = {}
    for repo in wanted:
        if repo not in REPOS:
            print(f"✗ {repo}: no reference config", file=sys.stderr)
            continue
        print(f"\n→ {repo}")
        res = score_reference(repo, REPOS[repo])
        summary[repo] = res
        if "error" in res:
            print(f"  ✗ {res['error']}")
            continue
        out = REPOS_DIR / repo / "ref_fidelity_results.json"
        out.write_text(json.dumps({IMPL_ID: res}, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        print(f"  {res['passed']}/{res['total']} passed  "
              f"rate={res['test_case_pass_rate']:.4f}  stubbed={res['stubbed_third_party']}")
        for name in res["failed_tests"]:
            print(f"    FAIL {name}")

    print("\n=== Reference structural fidelity (origin repos) ===")
    for repo, r in summary.items():
        if "error" in r:
            print(f"  {repo:<58} ERROR  {r['error']}")
        else:
            print(f"  {repo:<58} {r['passed']:>3}/{r['total']:<3} {r['test_case_pass_rate']:.4f}")


if __name__ == "__main__":
    main()
