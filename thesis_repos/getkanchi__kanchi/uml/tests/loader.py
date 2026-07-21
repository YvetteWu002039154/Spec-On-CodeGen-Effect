import contextlib
import importlib.util
import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_UML = os.path.dirname(_HERE)                        # .../getkanchi__kanchi/uml

SOURCE = "uml"
MODELS = ("claude", "gpt", "deepseek", "gemini")


def gencode_paths():
    out = []
    for model in MODELS:
        p = os.path.join(_UML, "outputcode", model, "generated_code.py")
        if os.path.exists(p):
            out.append((f"{SOURCE}/{model}", p))
    return out


@contextlib.contextmanager
def _in_tmp_cwd():
    """Exec a generation with cwd in a throwaway dir: some modules create a
    SQLite file (e.g. `kanchi.db`) at import, which must not pollute the tests
    directory."""
    prev = os.getcwd()
    tmp = tempfile.mkdtemp(prefix="kanchi_uml_load_")
    os.chdir(tmp)
    try:
        yield
    finally:
        os.chdir(prev)


def load_gencodemodule(impl_id, path):
    mod_name = "gen_" + impl_id.replace("/", "_")
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    with _in_tmp_cwd():
        spec.loader.exec_module(module)
    return module
