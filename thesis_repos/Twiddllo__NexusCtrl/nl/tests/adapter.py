import dataclasses
import datetime
import os
import tempfile

# --- small shared observation helpers ---------------------------------------

def _dims(record):
    """Which metric dimensions (cpu / ram / network) a produced record exposes."""
    if isinstance(record, dict):
        keys = [str(k).lower() for k in record]
    elif dataclasses.is_dataclass(record):
        keys = [f.name.lower() for f in dataclasses.fields(record)]
    else:
        keys = [a.lower() for a in dir(record) if not a.startswith("_")]
    dims = set()
    if any("cpu" in k for k in keys):
        dims.add("cpu")
    if any("ram" in k or "mem" in k for k in keys):
        dims.add("ram")
    if any("net" in k for k in keys):
        dims.add("network")
    return dims


def _enum_tokens(enum_cls):
    """Member names and values of an enum, lowercased."""
    tokens = set()
    for member in enum_cls:
        tokens.add(str(member.name).lower())
        tokens.add(str(member.value).lower())
    return tokens


def _tmp_file():
    """Throwaway path for a component that persists to disk."""
    return os.path.join(tempfile.mkdtemp(prefix="nexus_"), "store.json")


_BOGUS_PID = 2_147_483_647


# ============================================================================
# One driver per generation. `m` is that generation's loaded module.
# ============================================================================

class ClaudeDriver:
    model = "claude"

    def __init__(self, m):
        self.m = m

    def history_length_after(self, n):
        mgr = self.m.ServerManager(storage_path=_tmp_file())
        cfg = mgr.add_server("srv", "127.0.0.1", 9)
        conn = mgr.get_connection(cfg.server_id)
        for _ in range(n):
            conn.fetch_metrics()
        return len(conn.get_metrics_history())

    def metrics(self):
        rec = self.m.AgentMetricsCollector().collect()
        return {"dims": _dims(rec), "ram_percent": rec.ram_percent}

    def process_pids(self):
        return {p.pid for p in self.m.AgentMetricsCollector().get_processes()}

    def has_background_service(self):
        return callable(getattr(self.m.Agent, "start", None))

    def kill_missing_reports_failure(self):
        ok, _msg = self.m.AgentMetricsCollector().kill_process(_BOGUS_PID)
        return ok is False

    def create_task_exists(self, priority="critical"):
        mgr = self.m.TaskManager(storage_path=_tmp_file())
        task = mgr.create_task("t", "d", self.m.TaskPriority(priority))
        return mgr.get_task(task.task_id) is not None

    def tracked_task_count(self, k):
        mgr = self.m.TaskManager(storage_path=_tmp_file())
        for i in range(k):
            mgr.create_task(f"t{i}", "d", self.m.TaskPriority.HIGH)
        return len(mgr.list_tasks())

    def priority_tokens(self):
        return _enum_tokens(self.m.TaskPriority)

    def completion_token(self):
        mgr = self.m.TaskManager(storage_path=_tmp_file())
        task = mgr.create_task("t", "d", self.m.TaskPriority.HIGH)
        mgr.complete_task(task.task_id)
        return mgr.get_task(task.task_id).status.value

    def server_status_tokens(self):
        return _enum_tokens(self.m.ServerStatus)


class GptDriver:
    model = "gpt"

    def __init__(self, m):
        self.m = m

    def history_length_after(self, n):
        history = self.m.PerformanceHistory()
        for _ in range(n):
            snapshot = self.m.MetricsSnapshot(
                timestamp=datetime.datetime.now(),
                cpu_percent=1.0, ram_percent=2.0, network_kbps=3.0)
            history.add_snapshot(snapshot)
        return len(history.get_all())

    def metrics(self):
        rec = self.m.Agent("agent-1").get_latest_metrics()
        ram = rec.ram_percent if rec is not None else None
        return {"dims": _dims(rec), "ram_percent": ram}

    def process_pids(self):
        agent = self.m.Agent("agent-1")
        return {p.pid for p in agent.list_processes()}

    def has_background_service(self):
        return callable(getattr(self.m.Agent, "start", None))

    def kill_missing_reports_failure(self):
        return self.m.Agent("agent-1").kill_process(_BOGUS_PID) is False

    def create_task_exists(self, priority="critical"):
        mgr = self.m.TaskManager()
        task = mgr.create_task("t", self.m.TaskPriority(priority))
        return mgr.get_task(task.task_id) is not None

    def tracked_task_count(self, k):
        mgr = self.m.TaskManager()
        for i in range(k):
            mgr.create_task(f"t{i}", self.m.TaskPriority.HIGH)
        return len(mgr.list_tasks())

    def priority_tokens(self):
        return _enum_tokens(self.m.TaskPriority)

    def completion_token(self):
        mgr = self.m.TaskManager()
        task = mgr.create_task("t", self.m.TaskPriority.HIGH)
        mgr.complete_task(task.task_id)
        return mgr.get_task(task.task_id).status.value

    def server_status_tokens(self):
        return _enum_tokens(self.m.ServerStatus)


class DeepseekDriver:
    model = "deepseek"

    def __init__(self, m):
        self.m = m

    def history_length_after(self, n):
        history = self.m.MetricsHistory()
        for _ in range(n):
            history.add({"cpu": 1.0, "ram": 2.0, "net_sent": 3.0, "net_recv": 4.0})
        return len(history.get_history())

    def metrics(self):
        rec = self.m.Agent("127.0.0.1").collect_metrics()
        return {"dims": _dims(rec), "ram_percent": rec["ram"]}

    def process_pids(self):
        return {pid for pid, _name in self.m.Agent("127.0.0.1").get_processes()}

    def has_background_service(self):
        return callable(getattr(self.m.Agent, "start", None))

    def kill_missing_reports_failure(self):
        return self.m.Agent("127.0.0.1").kill_process(_BOGUS_PID) is False

    def create_task_exists(self, priority="critical"):
        server = self.m.NexusCtrlServer()
        server.do_add_task(f"desc {priority}")
        return len(server.tasks) >= 1

    def tracked_task_count(self, k):
        server = self.m.NexusCtrlServer()
        for i in range(k):
            server.do_add_task(f"t{i} high")
        return len(server.tasks)

    def priority_tokens(self):
        return _enum_tokens(self.m.TaskPriority)

    def completion_token(self):
        server = self.m.NexusCtrlServer()
        server.do_add_task("desc high")
        tid = next(iter(server.tasks))
        server.do_update_task(f"{tid} completed")
        return server.tasks[tid].status.value

    def server_status_tokens(self):
        return _enum_tokens(self.m.ServerStatus)


class GeminiDriver:
    model = "gemini"

    def __init__(self, m):
        self.m = m

    def _server(self):
        agent = self.m.Agent("agent-1")
        return self.m.Server("srv-1", "srv", agent)

    def history_length_after(self, n):
        server = self._server()
        server.connect()
        for _ in range(n):
            server.update_metrics()
        return len(server.get_metrics_history())

    def metrics(self):
        agent = self.m.Agent("agent-1")
        agent.start()
        rec = agent.collect_metrics()
        return {"dims": _dims(rec), "ram_percent": rec.ram_percent}

    def process_pids(self):
        agent = self.m.Agent("agent-1")
        agent.start()
        return {p.pid for p in agent.get_processes()}

    def has_background_service(self):
        return callable(getattr(self.m.Agent, "start", None))

    def kill_missing_reports_failure(self):
        agent = self.m.Agent("agent-1")
        agent.start()
        return agent.kill_process(_BOGUS_PID) is False

    def create_task_exists(self, priority="critical"):
        server = self._server()
        task = self.m.Task(id="1", title="t", description="d",
                           priority=self.m.TaskPriority(priority))
        server.add_task(task)
        return any(t.id == task.id for t in server.get_tasks())

    def tracked_task_count(self, k):
        server = self._server()
        for i in range(k):
            server.add_task(self.m.Task(id=str(i), title=f"t{i}", description="d",
                                        priority=self.m.TaskPriority.HIGH))
        return len(server.get_tasks())

    def priority_tokens(self):
        return _enum_tokens(self.m.TaskPriority)

    def completion_token(self):
        server = self._server()
        task = self.m.Task(id="1", title="t", description="d",
                           priority=self.m.TaskPriority.HIGH)
        server.add_task(task)
        server.update_task_status(task.id, self.m.TaskStatus.COMPLETED)
        return next(t.status.value for t in server.get_tasks() if t.id == task.id)

    def server_status_tokens(self):
        return _enum_tokens(self.m.ServerStatus)


DRIVERS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """Wrap a loaded generation module in its explicit driver."""
    return DRIVERS[model](module)
