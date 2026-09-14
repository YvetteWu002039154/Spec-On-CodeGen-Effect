import importlib
import importlib.util
import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "adapter_harness")))
import permissive_stubs  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_NL = os.path.dirname(_HERE)                          # .../shenmintao__marginalia/nl

SOURCE = "nl"
MODELS = ("claude", "gpt", "deepseek", "gemini")

# Heavy ML tops that are ALWAYS stubbed, even when installed. Importing the real
# `sentence_transformers` pulls in `transformers`/`torch`, whose initialization
# both is slow and — in some environments — crashes during collection (e.g. a
# torch `custom_op` registration raising `TypeError` from `inspect`). The
# generations reach these behind a `try/except ImportError` guard, which would
# NOT catch such a non-ImportError crash — so forcing the stub keeps the module
# loadable and grading deterministic regardless of whether the host has torch.
# Every other optional top the generations reference is left real: they all
# guard those imports, so a missing package simply flips a `HAS_*` flag.
_ALWAYS_STUB = {"sentence_transformers", "transformers", "torch"}

_MISSING = _ALWAYS_STUB


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
