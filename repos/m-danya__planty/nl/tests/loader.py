import importlib.util
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "adapter_harness")))
import permissive_stubs  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_NL = os.path.dirname(_HERE)                         # .../m-danya__planty/nl

SOURCE = "nl"
MODELS = ("claude", "gpt", "deepseek", "gemini")

# Optional third-party tops a generation *might* import; stubbed only if missing.
_OPTIONAL_TOPS = {
    "pydantic", "dateutil", "sqlalchemy", "fastapi", "pydantic_settings",
    "email_validator", "dotenv",
}


_MISSING = permissive_stubs.missing_tops(_OPTIONAL_TOPS)


def gencode_paths():
    out = []
    for model in MODELS:
        p = os.path.join(_NL, "outputcode", f"{model}.run0.py")
        if os.path.exists(p):
            out.append((f"{SOURCE}/{model}", p))
    return out


def _load_path(mod_name, path):
    permissive_stubs.install(_MISSING)
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def load_gencodemodule(impl_id, path):
    return _load_path("gen_" + impl_id.replace("/", "_"), path)
