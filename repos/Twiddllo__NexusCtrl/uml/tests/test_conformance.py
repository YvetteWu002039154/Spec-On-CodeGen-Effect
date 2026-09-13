import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from structure import Implementation
from loader import gencode_paths, load_gencodemodules

_PARAMS = [ident for ident, _ in gencode_paths()]
_PATHS = dict(gencode_paths())
_cache = {}

# The 6 ORM entities the diagram draws `--|> Base` from.
_ORM_ENTITIES = ("User", "Project", "Server", "Task", "MetricSnapshot", "AuditLog")

# The connection-management method set MetricsConnectionManager carries.
_MANAGER_METHODS = frozenset({
    "connect_client", "disconnect_client",
    "connect_agent", "disconnect_agent",
    "broadcast_to_clients",
})


def _impl(ident):
    if ident not in _cache:
        try:
            _cache[ident] = Implementation(
                ident, load_gencodemodules(ident, _PATHS[ident]))
        except Exception as exc:
            _cache[ident] = exc
    val = _cache[ident]
    if isinstance(val, Exception):
        # A generation whose module does not even load implements none of the
        # pinned structure -> failure (this track has no skip / N/A).
        pytest.fail(f"module did not load: {type(val).__name__}: {val}")
    return val


@pytest.fixture(params=_PARAMS)
def impl(request):
    return _impl(request.param)


# ---------------------------------------------------------------------------
# Inheritance links (--|>)
# ---------------------------------------------------------------------------
def test_orm_entities_share_common_base(impl):
    # U1: User/Project/Server/Task/MetricSnapshot/AuditLog all --|> a common Base.
    # Asserted on convergence (they share a base class), not its literal name,
    # since `class Base(...)` and `Base = declarative_base()` name it differently.
    assert impl.common_ancestor_names(_ORM_ENTITIES)


def test_task_create_specializes_task_base(impl):
    # U2: TaskCreate --|> TaskBase.
    assert impl.subclass_link("TaskCreate", "TaskBase") is True


def test_task_response_specializes_task_base(impl):
    # U3: TaskResponse --|> TaskBase.
    assert impl.subclass_link("TaskResponse", "TaskBase") is True


# ---------------------------------------------------------------------------
# Association links (--> : attr)
# ---------------------------------------------------------------------------
def test_task_base_priority_refs_task_priority(impl):
    # U4: TaskBase --> TaskPriority (attribute `priority`).
    assert "TaskPriority" in impl.attr_refs("TaskBase", "priority")


def test_task_base_status_refs_task_status(impl):
    # U5: TaskBase --> TaskStatus (attribute `status`).
    assert "TaskStatus" in impl.attr_refs("TaskBase", "status")


def test_token_response_user_refs_user_response(impl):
    # U6: TokenResponse --> UserResponse (attribute `user`).
    assert "UserResponse" in impl.attr_refs("TokenResponse", "user")


# ---------------------------------------------------------------------------
# Methods under a class
# ---------------------------------------------------------------------------
def test_manager_defines_full_method_set(impl):
    # U7: MetricsConnectionManager carries the full connection-management set.
    assert _MANAGER_METHODS <= impl.methods("MetricsConnectionManager")


def test_manager_client_connect_disconnect(impl):
    # U8: MetricsConnectionManager can connect and disconnect clients.
    m = impl.methods("MetricsConnectionManager")
    assert {"connect_client", "disconnect_client"} <= m


def test_manager_agent_connect_disconnect(impl):
    # U9: MetricsConnectionManager can connect and disconnect agents.
    m = impl.methods("MetricsConnectionManager")
    assert {"connect_agent", "disconnect_agent"} <= m


def test_manager_broadcasts_to_clients(impl):
    # U10: MetricsConnectionManager fans out via broadcast_to_clients (distinctive).
    assert "broadcast_to_clients" in impl.methods("MetricsConnectionManager")
