import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_NL = os.path.dirname(_HERE)                         # .../Twiddllo__NexusCtrl/nl

SOURCE = "nl"
MODELS = ("claude", "gpt", "deepseek", "gemini")


def gencode_paths():
    out = []
    for model in MODELS:
        p = os.path.join(_NL, "outputcode", f"{model}.run{os.environ.get('RUN', '0')}.py")
        if os.path.exists(p):
            out.append((f"{SOURCE}/{model}", p))
    return out

def load_gencodemodule(impl_id, path):
    model = "gen_" + impl_id.replace("/", "_")
    spec = importlib.util.spec_from_file_location(model, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[model] = module
    spec.loader.exec_module(module)
    return module
