import sys, os, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../outputcode/gpt"))
from generated_code import (
    UserRole, ServerStatus, TaskStatus, TaskPriority,
    User, Project, Server, Task, MetricSnapshot,
    MetricsConnectionManager,
)


# T01 — ServerStatus has 'online' value
def test_T01_server_status_online_exists():
    values = {s.value for s in ServerStatus}
    assert "online" in values


# T02 — ServerStatus has 'offline' value
def test_T02_server_status_offline_exists():
    values = {s.value for s in ServerStatus}
    assert "offline" in values


# T03 — TaskStatus has 'todo' and 'done' values
def test_T03_task_status_has_todo_and_done():
    values = {s.value for s in TaskStatus}
    assert "todo" in values
    assert "done" in values


# T04 — TaskPriority has all four ground-truth levels
def test_T04_task_priority_has_all_levels():
    values = {p.value for p in TaskPriority}
    assert "low" in values
    assert "medium" in values
    assert "high" in values
    assert "critical" in values


# T05 — User model has username and email attributes
def test_T05_user_has_username_and_email():
    u = User(username="alice", email="alice@example.com", hashed_password="hashed")
    assert u.username == "alice"
    assert u.email == "alice@example.com"


# T06 — User has hashed_password and is_active
def test_T06_user_has_password_and_active():
    u = User(username="bob", email="bob@example.com", hashed_password="pw")
    assert hasattr(u, "hashed_password")
    assert hasattr(u, "is_active")


# T07 — Project has name and owner_id attributes
def test_T07_project_has_name_and_owner_id():
    p = Project(name="My Project", owner_id=1)
    assert p.name == "My Project"
    assert p.owner_id == 1


# T08 — Server has hostname and status attributes
def test_T08_server_has_hostname_and_status():
    s = Server(hostname="192.168.1.1", os_type="linux")
    assert s.hostname == "192.168.1.1"
    assert hasattr(s, "status")


# T09 — Task has title and project_id attributes
def test_T09_task_has_title_and_project_id():
    t = Task(title="Deploy", project_id=1)
    assert t.title == "Deploy"
    assert t.project_id == 1


# T10 — MetricSnapshot has server_id and cpu_percent
def test_T10_metric_snapshot_has_required_fields():
    m = MetricSnapshot(server_id=1)
    assert m.server_id == 1
    assert hasattr(m, "cpu_percent")


# T11 — MetricsConnectionManager can be instantiated
def test_T11_metrics_connection_manager_instantiates():
    mgr = MetricsConnectionManager()
    assert mgr is not None


# T12 — UserRole has 'admin' value
def test_T12_user_role_has_admin():
    values = {r.value for r in UserRole}
    assert "admin" in values
