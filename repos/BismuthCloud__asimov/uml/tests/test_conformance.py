"""Structure-conformance suite for `asimov` (BismuthCloud) **UML track**.

One shared test body runs against the 4 UML generations, via the name-tolerant
reflection layer in structure.py (inspect/ast) — no per-model adapter is used or
needed on this track, since structure is read rather than exercised.
Expected structure comes only from CONTRACT.md, derived from the
class diagram `uml/input/classes.puml` (a pyreverse extraction of the origin
`asimov.graph` package). The diagram records three kinds of fact — inheritance
links (`--|>`), association links (`--* / --o : attr`), and methods under a
class — and each test pins one of them (Un). A class/attribute a generation
omits is a FAILURE, as is a present-but-wrong link/method; this track does not
skip / mark N/A.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from structure import Implementation, Unsupported            # noqa: E402
from loader import gencode_paths, load_gencodemodules        # noqa: E402

_PARAMS = [ident for ident, _ in gencode_paths()]
_PATHS = dict(gencode_paths())
_cache = {}

# Core Agent method set the diagram draws under `Agent`.
_AGENT_METHODS = frozenset({
    "add_node", "add_multiple_nodes", "run_task", "run_node",
    "compile_execution_plan",
})


def _impl(ident):
    if ident not in _cache:
        try:
            _cache[ident] = Implementation(
                ident, load_gencodemodules(ident, _PATHS[ident]))
        except Exception as exc:
            # A generation that does not load exposes no structure at all: build
            # an empty implementation so every behavior FAILS (this track never
            # skips / marks N/A -- a module that does not load is a failure).
            impl = Implementation(ident, [])
            impl._load_error = exc
            _cache[ident] = impl
    return _cache[ident]


@pytest.fixture(params=_PARAMS)
def impl(request):
    return _impl(request.param)


def _guard(fn):
    try:
        return fn()
    except Unsupported as exc:
        pytest.fail(f"structure not present: {exc}")


# ---------------------------------------------------------------------------
# Inheritance links (--|>)
# ---------------------------------------------------------------------------
def test_agent_module_specializes_base(impl):
    # U1: AgentModule --|> AsimovBase.
    assert _guard(lambda: impl.subclass_link("AgentModule", "AsimovBase")) is True


def test_agent_specializes_base(impl):
    # U2: Agent --|> AsimovBase.
    assert _guard(lambda: impl.subclass_link("Agent", "AsimovBase")) is True


def test_composite_specializes_agent_module(impl):
    # U3: CompositeModule --|> AgentModule.
    assert _guard(lambda: impl.subclass_link("CompositeModule", "AgentModule")) is True


def test_node_specializes_composite(impl):
    # U4: Node --|> CompositeModule.
    assert _guard(lambda: impl.subclass_link("Node", "CompositeModule")) is True


def test_flow_control_specializes_agent_module(impl):
    # U5: FlowControlModule --|> AgentModule.
    assert _guard(lambda: impl.subclass_link("FlowControlModule", "AgentModule")) is True


def test_task_specializes_base(impl):
    # U6: Task --|> AsimovBase.
    assert _guard(lambda: impl.subclass_link("Task", "AsimovBase")) is True


# ---------------------------------------------------------------------------
# Association links (--* / --o : attr)
# ---------------------------------------------------------------------------
def test_agent_module_type_refs_module_type(impl):
    # U7: AgentModule --* ModuleType (attribute `type`).
    assert "ModuleType" in _guard(lambda: impl.attr_refs("AgentModule", "type"))


def test_task_status_refs_task_status(impl):
    # U8: Task --o TaskStatus (attribute `status`).
    assert "TaskStatus" in _guard(lambda: impl.attr_refs("Task", "status"))


def test_composite_node_config_refs_node_config(impl):
    # U9: CompositeModule --* NodeConfig (attribute `node_config`).
    assert "NodeConfig" in _guard(lambda: impl.attr_refs("CompositeModule", "node_config"))


# ---------------------------------------------------------------------------
# Methods under a class
# ---------------------------------------------------------------------------
def test_agent_defines_core_method_set(impl):
    # U10: Agent carries the core graph-execution method set (add_node,
    # add_multiple_nodes, run_task, run_node, compile_execution_plan).
    assert _AGENT_METHODS <= _guard(lambda: impl.methods("Agent"))
