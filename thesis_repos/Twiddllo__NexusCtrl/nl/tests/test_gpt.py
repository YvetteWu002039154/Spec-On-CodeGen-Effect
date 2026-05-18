import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../outputcode/gpt"))
sys.modules.pop("generated_code", None)
import generated_code as _m

# Resolve classes — gpt uses 'Priority' instead of 'TaskPriority'
ServerStatus             = getattr(_m, 'ServerStatus', None)
TaskStatus               = getattr(_m, 'TaskStatus', None)
TaskPriority             = getattr(_m, 'TaskPriority', None) or getattr(_m, 'Priority', None)
User                     = getattr(_m, 'User', None)
Project                  = getattr(_m, 'Project', None)
Server                   = getattr(_m, 'Server', None)
Task                     = getattr(_m, 'Task', None)
MetricSnapshot           = getattr(_m, 'MetricSnapshot', None) or getattr(_m, 'SystemMetrics', None)
MetricsConnectionManager = getattr(_m, 'MetricsConnectionManager', None)
UserRole                 = getattr(_m, 'UserRole', None)


def _has(cls, *names):
    dc = getattr(cls, '__dataclass_fields__', {})
    return any(hasattr(cls, n) or n in dc for n in names)


# T01 — ServerStatus has 'online' value
def test_T01_server_status_online_exists():
    assert ServerStatus is not None, "ServerStatus not defined"
    assert "online" in {s.value for s in ServerStatus}


# T02 — ServerStatus has 'offline' value
def test_T02_server_status_offline_exists():
    assert ServerStatus is not None, "ServerStatus not defined"
    assert "offline" in {s.value for s in ServerStatus}


# T03 — TaskStatus has a pending/todo and done/completed value
def test_T03_task_status_has_todo_and_done():
    assert TaskStatus is not None, "TaskStatus not defined"
    values = {s.value for s in TaskStatus}
    assert "todo" in values or "pending" in values
    assert "done" in values or "completed" in values


# T04 — TaskPriority has all four ground-truth levels
def test_T04_task_priority_has_all_levels():
    assert TaskPriority is not None, "TaskPriority not defined"
    values = {p.value for p in TaskPriority}
    assert "low" in values
    assert "medium" in values
    assert "high" in values
    assert "critical" in values


# T05 — User model has username and email
def test_T05_user_has_username_and_email():
    assert User is not None, "User not defined"
    assert _has(User, 'username', 'name')
    assert _has(User, 'email')


# T06 — User has hashed_password and is_active
def test_T06_user_has_password_and_active():
    assert User is not None, "User not defined"
    assert _has(User, 'hashed_password', 'password')
    assert _has(User, 'is_active', 'active')


# T07 — Project has name and owner_id
def test_T07_project_has_name_and_owner_id():
    assert Project is not None, "Project not defined"
    assert _has(Project, 'name')
    assert _has(Project, 'owner_id', 'owner')


# T08 — Server has hostname and status
def test_T08_server_has_hostname_and_status():
    assert Server is not None, "Server not defined"
    assert _has(Server, 'hostname', 'host', 'ip_address')
    assert _has(Server, 'status', 'online')


# T09 — Task has title and a project/server reference
def test_T09_task_has_title_and_project_id():
    assert Task is not None, "Task not defined"
    assert _has(Task, 'title', 'description')
    assert _has(Task, 'project_id', 'server_id', 'assigned_server')


# T10 — MetricSnapshot has cpu_percent
def test_T10_metric_snapshot_has_required_fields():
    assert MetricSnapshot is not None, "MetricSnapshot/SystemMetrics not defined"
    assert _has(MetricSnapshot, 'cpu_percent')


# T11 — MetricsConnectionManager can be instantiated
def test_T11_metrics_connection_manager_instantiates():
    assert MetricsConnectionManager is not None, "MetricsConnectionManager not defined"
    mgr = MetricsConnectionManager()
    assert mgr is not None


# T12 — UserRole has 'admin' value
def test_T12_user_role_has_admin():
    assert UserRole is not None, "UserRole not defined"
    values = {r.value for r in UserRole}
    assert "admin" in values
