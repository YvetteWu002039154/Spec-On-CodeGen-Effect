import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _dbharness import LoopSafePool, fresh_db_dsn  # noqa: E402

TENANT = "default"


def _run(coro):
    return asyncio.run(coro)


class ClaudeDriver:
    """Async toolset; the generation ships an InMemoryStorage, so use it."""

    def __init__(self, module):
        self.m = module

    def _kit(self):
        kit = self.m.TodoToolset(storage=self.m.InMemoryStorage())
        _run(kit.initialize())
        return kit

    def add_task_is_observable(self):
        kit = self._kit()
        _run(kit.add_task("a"))
        return len(_run(kit.list_tasks())) == 1

    def list_all_count(self, n):
        kit = self._kit()
        for i in range(n):
            _run(kit.add_task(f"t{i}"))
        return len(_run(kit.list_tasks()))

    def update_status_observed(self):
        kit = self._kit()
        t = _run(kit.add_task("a"))
        _run(kit.update_task_status(t.id, self.m.TaskStatus.IN_PROGRESS))
        st = _run(kit.get_task(t.id)).status
        return str(getattr(st, "value", st))

    def delete_removes_task(self):
        kit = self._kit()
        t = _run(kit.add_task("a"))
        _run(kit.delete_task(t.id))
        return len(_run(kit.list_tasks())) == 0

    def child_links_to_parent(self):
        kit = self._kit()
        p = _run(kit.add_task("p"))
        c = _run(kit.create_child_task(p.id, "c"))
        return c.parent_id == p.id

    def link_dependency_recorded(self):
        kit = self._kit()
        a = _run(kit.add_task("a"))
        b = _run(kit.add_task("b"))
        _run(kit.link_dependency(b.id, a.id))
        return True

    def ready_reflects_dependency(self):
        kit = self._kit()
        a = _run(kit.add_task("a"))
        b = _run(kit.add_task("b"))
        _run(kit.link_dependency(b.id, a.id))
        before = any(t.id == b.id for t in _run(kit.list_ready_tasks()))
        _run(kit.update_task_status(a.id, self.m.TaskStatus.COMPLETED))
        after = any(t.id == b.id for t in _run(kit.list_ready_tasks()))
        return before, after

    def bulk_write_creates(self, n):
        kit = self._kit()
        _run(kit.bulk_write_tasks([self.m.Task(title=f"b{i}") for i in range(n)]))
        return len(_run(kit.list_tasks()))

    def hierarchical_nests_child(self):
        kit = self._kit()
        p = _run(kit.add_task("p"))
        _run(kit.create_child_task(p.id, "c"))
        flat = len(_run(kit.list_tasks()))
        top = len(_run(kit.list_tasks(hierarchical=True)))
        return flat, top


class GptDriver:
    """Fully synchronous, in-memory."""

    def __init__(self, module):
        self.m = module

    def _kit(self):
        return self.m.TodoToolset(storage=self.m.InMemoryTaskStorage())

    def add_task_is_observable(self):
        kit = self._kit()
        kit.add_task(TENANT, "a")
        return len(kit.list_all_tasks(TENANT, hierarchical=False)) == 1

    def list_all_count(self, n):
        kit = self._kit()
        for i in range(n):
            kit.add_task(TENANT, f"t{i}")
        return len(kit.list_all_tasks(TENANT, hierarchical=False))

    def update_status_observed(self):
        kit = self._kit()
        t = kit.add_task(TENANT, "a")
        kit.update_task_status_by_id(TENANT, t.id, self.m.TaskStatus.IN_PROGRESS)
        got = [x for x in kit.list_all_tasks(TENANT, hierarchical=False)
               if str(x.id) == str(t.id)][0]
        return str(getattr(got.status, "value", got.status))

    def delete_removes_task(self):
        kit = self._kit()
        t = kit.add_task(TENANT, "a")
        kit.delete_task_by_id(TENANT, t.id)
        return len(kit.list_all_tasks(TENANT, hierarchical=False)) == 0

    def child_links_to_parent(self):
        kit = self._kit()
        p = kit.add_task(TENANT, "p")
        c = kit.create_child_task(TENANT, p.id, "c")
        return c.parent_id == p.id

    def link_dependency_recorded(self):
        kit = self._kit()
        a = kit.add_task(TENANT, "a")
        b = kit.add_task(TENANT, "b")
        kit.link_tasks_with_dependency(TENANT, b.id, a.id)
        return True

    def ready_reflects_dependency(self):
        kit = self._kit()
        a = kit.add_task(TENANT, "a")
        b = kit.add_task(TENANT, "b")
        kit.link_tasks_with_dependency(TENANT, b.id, a.id)
        before = any(t.id == b.id for t in kit.list_tasks_ready_to_work_on(TENANT))
        kit.update_task_status_by_id(TENANT, a.id, self.m.TaskStatus.DONE)
        after = any(t.id == b.id for t in kit.list_tasks_ready_to_work_on(TENANT))
        return before, after

    def bulk_write_creates(self, n):
        kit = self._kit()
        kit.bulk_write_tasks(TENANT, [{"title": f"b{i}"} for i in range(n)])
        return len(kit.list_all_tasks(TENANT, hierarchical=False))

    def hierarchical_nests_child(self):
        kit = self._kit()
        p = kit.add_task(TENANT, "p")
        kit.create_child_task(TENANT, p.id, "c")
        flat = len(kit.list_all_tasks(TENANT, hierarchical=False))
        top = len(kit.list_all_tasks(TENANT, hierarchical=True))
        return flat, top


class DeepseekDriver:
    """asyncpg-only. Driven against a throwaway PostgreSQL.

    Scores 0: every behaviour fails for ONE root cause, not nine independent
    defects. The INSERT persists the row, then the generation's own return path
    calls Task.model_validate(asyncpg.Record); pydantic cannot read a Record as
    a mapping, so it raises "Field required" for id/tenant_id and the call never
    returns. Confirmed by driving the storage layer directly: the row is there.
    A blocking marshalling bug, not a harness limitation."""

    def __init__(self, module):
        self.m = module

    def _kit(self):
        kit = self.m.TodoToolset(TENANT, LoopSafePool(fresh_db_dsn()))
        _run(kit.initialize_schema())
        return kit

    def add_task_is_observable(self):
        kit = self._kit()
        _run(kit.add_task(self.m.TaskCreate(title="a")))
        return len(_run(kit.list_tasks())) == 1

    def list_all_count(self, n):
        kit = self._kit()
        for i in range(n):
            _run(kit.add_task(self.m.TaskCreate(title=f"t{i}")))
        return len(_run(kit.list_tasks()))

    def update_status_observed(self):
        kit = self._kit()
        t = _run(kit.add_task(self.m.TaskCreate(title="a")))
        tid = t["id"] if isinstance(t, dict) else t.id
        _run(kit.update_task_status(tid, "in_progress"))
        got = _run(kit.get_task(tid))
        st = got["status"] if isinstance(got, dict) else got.status
        return str(getattr(st, "value", st))

    def delete_removes_task(self):
        kit = self._kit()
        t = _run(kit.add_task(self.m.TaskCreate(title="a")))
        tid = t["id"] if isinstance(t, dict) else t.id
        _run(kit.delete_task(tid))
        return len(_run(kit.list_tasks())) == 0

    def child_links_to_parent(self):
        kit = self._kit()
        p = _run(kit.add_task(self.m.TaskCreate(title="p")))
        pid = p["id"] if isinstance(p, dict) else p.id
        c = _run(kit.create_child_task(pid, self.m.TaskCreate(title="c")))
        cp = c["parent_id"] if isinstance(c, dict) else c.parent_id
        return str(cp) == str(pid)

    def link_dependency_recorded(self):
        kit = self._kit()
        a = _run(kit.add_task(self.m.TaskCreate(title="a")))
        b = _run(kit.add_task(self.m.TaskCreate(title="b")))
        aid = a["id"] if isinstance(a, dict) else a.id
        bid = b["id"] if isinstance(b, dict) else b.id
        _run(kit.link_tasks(bid, aid))
        return True

    def ready_reflects_dependency(self):
        kit = self._kit()
        a = _run(kit.add_task(self.m.TaskCreate(title="a")))
        b = _run(kit.add_task(self.m.TaskCreate(title="b")))
        aid = a["id"] if isinstance(a, dict) else a.id
        bid = b["id"] if isinstance(b, dict) else b.id
        _run(kit.link_tasks(bid, aid))
        ready = lambda: {str(t["id"] if isinstance(t, dict) else t.id)
                         for t in _run(kit.list_ready_tasks())}
        before = str(bid) in ready()
        _run(kit.update_task_status(aid, "completed"))
        after = str(bid) in ready()
        return before, after

    def bulk_write_creates(self, n):
        kit = self._kit()
        _run(kit.bulk_write_tasks([self.m.TaskCreate(title=f"b{i}") for i in range(n)]))
        return len(_run(kit.list_tasks()))

    def hierarchical_nests_child(self):
        kit = self._kit()
        p = _run(kit.add_task(self.m.TaskCreate(title="p")))
        pid = p["id"] if isinstance(p, dict) else p.id
        _run(kit.create_child_task(pid, self.m.TaskCreate(title="c")))
        flat = len(_run(kit.list_tasks()))
        top = len(_run(kit.list_tasks(hierarchical=True)))
        return flat, top


class GeminiDriver:
    """psycopg2-only, synchronous. Driven against a fresh database."""

    def __init__(self, module):
        self.m = module

    def _kit(self):
        return self.m.TodoToolset(fresh_db_dsn())

    def add_task_is_observable(self):
        kit = self._kit()
        kit.add_task(TENANT, "a")
        return len(kit.list_tasks(TENANT)) == 1

    def list_all_count(self, n):
        kit = self._kit()
        for i in range(n):
            kit.add_task(TENANT, f"t{i}")
        return len(kit.list_tasks(TENANT))

    def update_status_observed(self):
        kit = self._kit()
        t = kit.add_task(TENANT, "a")
        kit.update_task_status(TENANT, t.id, self.m.TaskStatus.IN_PROGRESS)
        got = [x for x in kit.list_tasks(TENANT) if str(x.id) == str(t.id)][0]
        # this generation spells its states upper-case (IN_PROGRESS)
        return str(getattr(got.status, "value", got.status)).lower()

    def delete_removes_task(self):
        kit = self._kit()
        t = kit.add_task(TENANT, "a")
        kit.delete_task(TENANT, t.id)
        return len(kit.list_tasks(TENANT)) == 0

    def child_links_to_parent(self):
        kit = self._kit()
        p = kit.add_task(TENANT, "p")
        c = kit.create_child_task(TENANT, p.id, "c")
        return str(c.parent_id) == str(p.id)

    def link_dependency_recorded(self):
        kit = self._kit()
        a = kit.add_task(TENANT, "a")
        b = kit.add_task(TENANT, "b")
        kit.link_tasks(TENANT, b.id, a.id)
        return True

    def ready_reflects_dependency(self):
        kit = self._kit()
        a = kit.add_task(TENANT, "a")
        b = kit.add_task(TENANT, "b")
        kit.link_tasks(TENANT, b.id, a.id)
        ready = lambda: {str(t.id) for t in kit.list_ready_tasks(TENANT)}
        before = str(b.id) in ready()
        kit.update_task_status(TENANT, a.id, self.m.TaskStatus.COMPLETED)
        after = str(b.id) in ready()
        return before, after

    def bulk_write_creates(self, n):
        kit = self._kit()
        kit.bulk_write_tasks(TENANT, [self.m.Task(title=f"b{i}", tenant_id=TENANT) for i in range(n)])
        return len(kit.list_tasks(TENANT))

    def hierarchical_nests_child(self):
        kit = self._kit()
        p = kit.add_task(TENANT, "p")
        kit.create_child_task(TENANT, p.id, "c")
        flat = len(kit.list_tasks(TENANT))
        top = len(kit.list_tasks(TENANT, hierarchical=True))
        return flat, top


GENERATIONS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """One hand-written driver per model, written against that model's run0."""
    return GENERATIONS[model](module)
