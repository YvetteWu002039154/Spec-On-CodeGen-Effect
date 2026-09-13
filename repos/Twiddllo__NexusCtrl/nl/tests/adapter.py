"""Per-model behavioral drivers for `NexusCtrl` NL track.

One driver per model, written by reading that model's run0 source. The four
generations disagree about where each capability lives:

  claude    AgentMetricsCollector.collect()/.get_processes()/.kill_process();
            history is ServerConnection.metrics_history, filled by polling.
            Tasks: TaskManager.create_task(title, description, priority).
  gpt       the Agent is FED its data — report_metrics(cpu, ram, net) and
            report_processes(list) — so it never observes the host. Tasks:
            TaskManager.create_task(title, priority).
  deepseek  Agent.collect_metrics()/.get_processes()/.kill_process(); history is
            MetricsHistory.add()/.get_history(). Tasks live in a cmd.Cmd shell
            (NexusCtrlServer.do_add_task) keyed in self.tasks.
  gemini    Agent returns HARDCODED metrics and a _mock_processes dict; tasks are
            plain Task dataclasses held per Server.

N2/N3 deliberately fail a generation whose agent fabricates its readings: the
contract pins self-collection against the live host, so a fed (gpt) or
hardcoded (gemini) record is a behavioral failure, not a driver gap.

Return shapes match test_conformance.py's asserts.
"""

import os


def _dims(field_names):
    """Which of cpu / ram / network a metrics record covers.

    The dimension is named differently per generation — network appears as
    `net_bytes_sent`, `net_sent`, `network_kbps` — so each alias is listed
    explicitly rather than matched on the bare word.
    """
    text = " ".join(str(f).lower() for f in field_names)
    found = set()
    for dim, aliases in (("cpu", ("cpu",)),
                         ("ram", ("ram", "mem")),
                         ("network", ("network", "net_", "net "))):
        if any(a in text for a in aliases):
            found.add(dim)
    return found


def _tokens(enum_cls):
    """Lowercase vocabulary of an enum, by value and by member name."""
    out = set()
    for member in enum_cls:
        out.add(str(member.name).lower())
        v = getattr(member, "value", None)
        if isinstance(v, str):
            out.add(v.lower())
    return out


class ClaudeDriver:
    def __init__(self, module):
        self.m = module

    def history_length_after(self, n):
        conn = self.m.ServerConnection(
            self.m.ServerConfig(server_id="s1", name="s", host="127.0.0.1", port=9000))
        col = self.m.AgentMetricsCollector()
        for _ in range(n):
            conn.metrics_history.append(col.collect())
        return len(conn.get_metrics_history())

    def metrics(self):
        rec = self.m.AgentMetricsCollector().collect()
        return {"dims": _dims(vars(rec)), "ram_percent": float(rec.ram_percent)}

    def process_pids(self):
        return {p.pid for p in self.m.AgentMetricsCollector().get_processes()}

    def has_background_service(self):
        return callable(getattr(self.m.Agent, "start", None))

    def kill_missing_reports_failure(self):
        # kill_process -> (ok, message)
        ok, _msg = self.m.AgentMetricsCollector().kill_process(9999999)
        return ok is False

    def create_task_exists(self, priority):
        tm = self.m.TaskManager(storage_path=os.devnull)
        t = tm.create_task("t", "d", self.m.TaskPriority[priority.upper()])
        return tm.get_task(t.task_id) is not None

    def tracked_task_count(self, n):
        tm = self.m.TaskManager(storage_path=os.devnull)
        for i in range(n):
            tm.create_task(f"t{i}", "d", self.m.TaskPriority.MEDIUM)
        return len(tm.list_tasks())

    def priority_tokens(self):
        return _tokens(self.m.TaskPriority)

    def completion_token(self):
        tm = self.m.TaskManager(storage_path=os.devnull)
        t = tm.create_task("t", "d", self.m.TaskPriority.LOW)
        tm.complete_task(t.task_id)
        return str(tm.get_task(t.task_id).status.value).lower()

    def server_status_tokens(self):
        return _tokens(self.m.ServerStatus)


class GptDriver:
    """The agent does not observe anything: metrics and processes are reported
    INTO it. N2/N3 therefore fail on the contract's own terms."""

    def __init__(self, module):
        self.m = module

    def _agent(self):
        return self.m.Agent("a1")

    def history_length_after(self, n):
        a = self._agent()
        for i in range(n):
            a.report_metrics(1.0 * i, 2.0 * i, 3.0 * i)
        return len(a.get_performance_history())

    def metrics(self):
        a = self._agent()
        a.report_metrics(1.0, 2.0, 3.0)
        s = a.get_latest_metrics()
        return {"dims": {"cpu", "ram", "network"}, "ram_percent": float(s.ram_percent)}

    def process_pids(self):
        a = self._agent()
        a.report_processes([])
        return {p.pid for p in a.list_processes()}

    def has_background_service(self):
        return callable(getattr(self.m.Agent, "start", None))

    def kill_missing_reports_failure(self):
        return self._agent().kill_process(9999999) is False

    def create_task_exists(self, priority):
        tm = self.m.TaskManager()
        t = tm.create_task("t", self.m.TaskPriority[priority.upper()])
        return tm.get_task(t.task_id) is not None

    def tracked_task_count(self, n):
        tm = self.m.TaskManager()
        for i in range(n):
            tm.create_task(f"t{i}", self.m.TaskPriority.MEDIUM)
        return len(tm.list_tasks())

    def priority_tokens(self):
        return _tokens(self.m.TaskPriority)

    def completion_token(self):
        tm = self.m.TaskManager()
        t = tm.create_task("t", self.m.TaskPriority.LOW)
        tm.complete_task(t.task_id)
        return str(tm.get_task(t.task_id).status.value).lower()

    def server_status_tokens(self):
        return _tokens(self.m.ServerStatus)


class DeepseekDriver:
    """Agent self-collects; tasks live inside a cmd.Cmd shell."""

    def __init__(self, module):
        self.m = module

    def _agent(self):
        return self.m.Agent("127.0.0.1")

    def _shell(self):
        return self.m.NexusCtrlServer()

    def history_length_after(self, n):
        h = self.m.MetricsHistory()
        a = self._agent()
        for _ in range(n):
            h.add(a.collect_metrics())
        return len(h.get_history())

    def metrics(self):
        d = self._agent().collect_metrics()      # {"cpu","ram","net_sent","net_recv"}
        return {"dims": _dims(d), "ram_percent": float(d["ram"])}

    def process_pids(self):
        # get_processes() -> List[Tuple[int, str]]
        return {pid for pid, _name in self._agent().get_processes()}

    def has_background_service(self):
        return callable(getattr(self.m.Agent, "start", None))

    def kill_missing_reports_failure(self):
        return self._agent().kill_process(9999999) is False

    def create_task_exists(self, priority):
        sh = self._shell()
        sh.do_add_task(f"task {priority}")
        return len(sh.tasks) == 1

    def tracked_task_count(self, n):
        sh = self._shell()
        for i in range(n):
            sh.do_add_task(f"task{i} medium")
        return len(sh.tasks)

    def priority_tokens(self):
        return _tokens(self.m.TaskPriority)

    def completion_token(self):
        sh = self._shell()
        sh.do_add_task("task medium")
        tid = next(iter(sh.tasks))
        sh.do_update_task(f"{tid} completed")
        return str(sh.tasks[tid].status.value).lower()

    def server_status_tokens(self):
        """No ServerStatus enum here: state is the boolean ServerState.online,
        whose vocabulary is expressed by is_online() / set_offline()."""
        names = dir(self.m.ServerState)
        return {t for t in ("online", "offline")
                if any(t in n.lower() for n in names)}


class GeminiDriver:
    """Agent fabricates its readings (fixed numbers, _mock_processes), so N2/N3
    fail by contract. Tasks are dataclasses held on a Server."""

    def __init__(self, module):
        self.m = module

    def _agent(self):
        a = self.m.Agent("a1")
        a.start()
        return a

    def _server(self):
        return self.m.Server("s1", "srv", self._agent())

    def history_length_after(self, n):
        s = self._server()
        s.connect()                      # update_metrics raises while offline
        for _ in range(n):
            s.update_metrics()
        return len(s._metrics_history)

    def metrics(self):
        rec = self._agent().collect_metrics()
        return {"dims": _dims(vars(rec)), "ram_percent": float(rec.ram_percent)}

    def process_pids(self):
        return {p.pid for p in self._agent().get_processes()}

    def has_background_service(self):
        return callable(getattr(self.m.Agent, "start", None))

    def kill_missing_reports_failure(self):
        return self._agent().kill_process(9999999) is False

    def _task(self, i=0, priority="MEDIUM"):
        return self.m.Task(id=f"t{i}", title=f"t{i}", description="d",
                           priority=self.m.TaskPriority[priority],
                           status=self.m.TaskStatus.PENDING)

    def create_task_exists(self, priority):
        s = self._server()
        t = self._task(0, priority.upper())
        s.add_task(t)
        return len(s.get_tasks()) == 1

    def tracked_task_count(self, n):
        s = self._server()
        for i in range(n):
            s.add_task(self._task(i))
        return len(s.get_tasks())

    def priority_tokens(self):
        return _tokens(self.m.TaskPriority)

    def completion_token(self):
        return str(self.m.TaskStatus.COMPLETED.value).lower()

    def server_status_tokens(self):
        return _tokens(self.m.ServerStatus)


GENERATIONS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """One hand-written driver per model, written against that model's run0."""
    return GENERATIONS[model](module)
