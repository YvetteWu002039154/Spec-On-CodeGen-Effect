import asyncio
import enum

from _dbharness import fresh_db_dsn, LoopSafePool

# --- small shared observation helpers ---------------------------------------

TENANT = "t1"


def _run(coro):
    """Drive an async generation's coroutine to completion."""
    return asyncio.run(coro)


def _token(status):
    """Normalise a status value (enum or str) to a lowercase token."""
    if isinstance(status, enum.Enum):
        return str(status.value).lower()
    return str(status).lower()


# ============================================================================
# One driver per generation. `m` is that generation's loaded module.
# ============================================================================

class ClaudeDriver:
    model = "claude"

    def __init__(self, m):
        self.m = m

    def _toolset(self):
        return self.m.TodoToolset()

    def add_task_is_observable(self):
        ts = self._toolset()
        created = _run(ts.add_task(title="Alpha", tenant_id=TENANT))
        ids = {t.id for t in _run(ts.list_tasks(tenant_id=TENANT))}
        return created.id in ids

    def list_all_count(self, n):
        ts = self._toolset()
        for i in range(n):
            _run(ts.add_task(title=f"T{i}", tenant_id=TENANT))
        return len(_run(ts.list_tasks(tenant_id=TENANT)))

    def update_status_observed(self):
        ts = self._toolset()
        created = _run(ts.add_task(title="Beta", tenant_id=TENANT))
        updated = _run(ts.update_task_status(
            task_id=created.id, status=self.m.TaskStatus.IN_PROGRESS, tenant_id=TENANT))
        return _token(updated.status)

    def delete_removes_task(self):
        ts = self._toolset()
        created = _run(ts.add_task(title="Gamma", tenant_id=TENANT))
        _run(ts.delete_task(task_id=created.id, tenant_id=TENANT))
        ids = {t.id for t in _run(ts.list_tasks(tenant_id=TENANT))}
        return created.id not in ids

    def child_links_to_parent(self):
        ts = self._toolset()
        parent = _run(ts.add_task(title="Parent", tenant_id=TENANT))
        child = _run(ts.create_child_task(
            parent_id=parent.id, title="Child", tenant_id=TENANT))
        return child.parent_id == parent.id

    def link_dependency_recorded(self):
        ts = self._toolset()
        a = _run(ts.add_task(title="Dep", tenant_id=TENANT))
        b = _run(ts.add_task(title="Main", tenant_id=TENANT))
        # N6 observes the *effect*: linking b→a (a incomplete) records a
        # dependency that moves b from ready to blocked. (Return-value agnostic.)
        before = b.id in {t.id for t in _run(ts.list_ready_tasks(tenant_id=TENANT))}
        _run(ts.link_dependency(task_id=b.id, depends_on_task_id=a.id, tenant_id=TENANT))
        after = b.id in {t.id for t in _run(ts.list_ready_tasks(tenant_id=TENANT))}
        return before and not after

    def ready_reflects_dependency(self):
        ts = self._toolset()
        a = _run(ts.add_task(title="Prereq", tenant_id=TENANT))
        b = _run(ts.add_task(title="Blocked", tenant_id=TENANT))
        _run(ts.link_dependency(task_id=b.id, depends_on_task_id=a.id, tenant_id=TENANT))
        before = b.id in {t.id for t in _run(ts.list_ready_tasks(tenant_id=TENANT))}
        _run(ts.update_task_status(
            task_id=a.id, status=self.m.TaskStatus.COMPLETED, tenant_id=TENANT))
        after = b.id in {t.id for t in _run(ts.list_ready_tasks(tenant_id=TENANT))}
        return before, after

    def bulk_write_creates(self, n):
        ts = self._toolset()
        items = [self.m.Task(title=f"B{i}") for i in range(n)]
        saved = _run(ts.bulk_write_tasks(tasks=items, tenant_id=TENANT))
        return len(list(saved))

    def hierarchical_nests_child(self):
        ts = self._toolset()
        parent = _run(ts.add_task(title="Root", tenant_id=TENANT))
        _run(ts.create_child_task(parent_id=parent.id, title="Leaf", tenant_id=TENANT))
        flat = len(_run(ts.list_tasks(tenant_id=TENANT, hierarchical=False)))
        top = len(_run(ts.list_tasks(tenant_id=TENANT, hierarchical=True)))
        return flat, top


class GptDriver:
    model = "gpt"

    def __init__(self, m):
        self.m = m

    def _toolset(self):
        return self.m.TodoToolset(self.m.InMemoryTaskStorage())

    def add_task_is_observable(self):
        ts = self._toolset()
        created = ts.add_task(TENANT, "Alpha")
        ids = {t.id for t in ts.list_all_tasks(TENANT, hierarchical=False)}
        return created.id in ids

    def list_all_count(self, n):
        ts = self._toolset()
        for i in range(n):
            ts.add_task(TENANT, f"T{i}")
        return len(ts.list_all_tasks(TENANT, hierarchical=False))

    def update_status_observed(self):
        ts = self._toolset()
        created = ts.add_task(TENANT, "Beta")
        updated = ts.update_task_status_by_id(
            TENANT, created.id, self.m.TaskStatus.IN_PROGRESS)
        return _token(updated.status)

    def delete_removes_task(self):
        ts = self._toolset()
        created = ts.add_task(TENANT, "Gamma")
        ts.delete_task_by_id(TENANT, created.id)
        ids = {t.id for t in ts.list_all_tasks(TENANT, hierarchical=False)}
        return created.id not in ids

    def child_links_to_parent(self):
        ts = self._toolset()
        parent = ts.add_task(TENANT, "Parent")
        child = ts.create_child_task(TENANT, parent.id, "Child")
        return child.parent_id == parent.id

    def link_dependency_recorded(self):
        ts = self._toolset()
        a = ts.add_task(TENANT, "Dep")
        b = ts.add_task(TENANT, "Main")
        before = b.id in {t.id for t in ts.list_tasks_ready_to_work_on(TENANT)}
        ts.link_tasks_with_dependency(TENANT, b.id, a.id)
        after = b.id in {t.id for t in ts.list_tasks_ready_to_work_on(TENANT)}
        return before and not after

    def ready_reflects_dependency(self):
        ts = self._toolset()
        a = ts.add_task(TENANT, "Prereq")
        b = ts.add_task(TENANT, "Blocked")
        ts.link_tasks_with_dependency(TENANT, b.id, a.id)
        before = b.id in {t.id for t in ts.list_tasks_ready_to_work_on(TENANT)}
        ts.update_task_status_by_id(TENANT, a.id, self.m.TaskStatus.DONE)
        after = b.id in {t.id for t in ts.list_tasks_ready_to_work_on(TENANT)}
        return before, after

    def bulk_write_creates(self, n):
        ts = self._toolset()
        items = [{"title": f"B{i}"} for i in range(n)]
        saved = ts.bulk_write_tasks(TENANT, items)
        return len(list(saved))

    def hierarchical_nests_child(self):
        ts = self._toolset()
        parent = ts.add_task(TENANT, "Root")
        ts.create_child_task(TENANT, parent.id, "Leaf")
        flat = len(ts.list_all_tasks(TENANT, hierarchical=False))
        top = len(ts.list_all_tasks(TENANT, hierarchical=True))
        return flat, top


class DeepseekDriver:
    model = "deepseek"

    def __init__(self, m):
        self.m = m

    def _toolset(self):
        # deepseek exposes only an asyncpg-pool backend; drive it against a
        # fresh ephemeral database with a loop-safe pool + initialised schema.
        ts = self.m.TodoToolset(TENANT, LoopSafePool(fresh_db_dsn()))
        _run(ts.initialize_schema())
        return ts

    def add_task_is_observable(self):
        ts = self._toolset()
        created = _run(ts.add_task(self.m.TaskCreate(title="Alpha")))
        ids = {t.id for t in _run(ts.list_tasks())}
        return created.id in ids

    def list_all_count(self, n):
        ts = self._toolset()
        for i in range(n):
            _run(ts.add_task(self.m.TaskCreate(title=f"T{i}")))
        return len(_run(ts.list_tasks()))

    def update_status_observed(self):
        ts = self._toolset()
        created = _run(ts.add_task(self.m.TaskCreate(title="Beta")))
        updated = _run(ts.update_task_status(created.id, self.m.TaskStatus.IN_PROGRESS))
        return _token(updated.status)

    def delete_removes_task(self):
        ts = self._toolset()
        created = _run(ts.add_task(self.m.TaskCreate(title="Gamma")))
        _run(ts.delete_task(created.id))
        ids = {t.id for t in _run(ts.list_tasks())}
        return created.id not in ids

    def child_links_to_parent(self):
        ts = self._toolset()
        parent = _run(ts.add_task(self.m.TaskCreate(title="Parent")))
        child = _run(ts.create_child_task(parent.id, self.m.TaskCreate(title="Child")))
        return child.parent_id == parent.id

    def link_dependency_recorded(self):
        ts = self._toolset()
        a = _run(ts.add_task(self.m.TaskCreate(title="Dep")))
        b = _run(ts.add_task(self.m.TaskCreate(title="Main")))
        before = b.id in {t.id for t in _run(ts.list_ready_tasks())}
        _run(ts.link_tasks(b.id, a.id))
        after = b.id in {t.id for t in _run(ts.list_ready_tasks())}
        return before and not after

    def ready_reflects_dependency(self):
        ts = self._toolset()
        a = _run(ts.add_task(self.m.TaskCreate(title="Prereq")))
        b = _run(ts.add_task(self.m.TaskCreate(title="Blocked")))
        _run(ts.link_tasks(b.id, a.id))
        before = b.id in {t.id for t in _run(ts.list_ready_tasks())}
        _run(ts.update_task_status(a.id, self.m.TaskStatus.COMPLETED))
        after = b.id in {t.id for t in _run(ts.list_ready_tasks())}
        return before, after

    def bulk_write_creates(self, n):
        ts = self._toolset()
        items = [self.m.BulkTaskItem(title=f"B{i}") for i in range(n)]
        saved = _run(ts.bulk_write_tasks(items))
        return len(list(saved))

    def hierarchical_nests_child(self):
        ts = self._toolset()
        parent = _run(ts.add_task(self.m.TaskCreate(title="Root")))
        _run(ts.create_child_task(parent.id, self.m.TaskCreate(title="Leaf")))
        flat = len(_run(ts.list_tasks(hierarchical=False)))
        top = len(_run(ts.list_tasks(hierarchical=True)))
        return flat, top

    def persists_despite_marshal_bug(self):
        """Diagnostic for the blocked-vs-wrong distinction. deepseek's single
        defect is `Task.model_validate(row)` on an asyncpg Record (it needs
        `dict(row)`), which raises on every read/write return path. This confirms
        the INSERT itself still persists a row — so the nine behaviour FAILs
        cascade from one marshalling bug, not nine independent errors.
        Returns (rows_persisted, marshal_raised)."""
        import asyncpg
        dsn = fresh_db_dsn()
        ts = self.m.TodoToolset(TENANT, LoopSafePool(dsn))
        _run(ts.initialize_schema())
        raised = False
        try:
            _run(ts.add_task(self.m.TaskCreate(title="probe")))
        except Exception:
            raised = True

        async def _count():
            conn = await asyncpg.connect(dsn=dsn)
            try:
                return await conn.fetchval("SELECT count(*) FROM tasks")
            finally:
                await conn.close()

        return _run(_count()), raised


class GeminiDriver:
    model = "gemini"

    def __init__(self, m):
        self.m = m

    def _toolset(self):
        # gemini exposes only a psycopg2/Postgres backend; drive it against a
        # fresh ephemeral database (its constructor runs CREATE TABLE).
        return self.m.TodoToolset(fresh_db_dsn())

    def add_task_is_observable(self):
        ts = self._toolset()
        created = ts.add_task(TENANT, "Alpha")
        ids = {t.id for t in ts.list_tasks(TENANT)}
        return created.id in ids

    def list_all_count(self, n):
        ts = self._toolset()
        for i in range(n):
            ts.add_task(TENANT, f"T{i}")
        return len(ts.list_tasks(TENANT))

    def update_status_observed(self):
        ts = self._toolset()
        created = ts.add_task(TENANT, "Beta")
        updated = ts.update_task_status(TENANT, created.id, self.m.TaskStatus.IN_PROGRESS)
        return _token(updated.status)

    def delete_removes_task(self):
        ts = self._toolset()
        created = ts.add_task(TENANT, "Gamma")
        ts.delete_task(TENANT, created.id)
        ids = {t.id for t in ts.list_tasks(TENANT)}
        return created.id not in ids

    def child_links_to_parent(self):
        ts = self._toolset()
        parent = ts.add_task(TENANT, "Parent")
        child = ts.create_child_task(TENANT, parent.id, "Child")
        return child.parent_id == parent.id

    def link_dependency_recorded(self):
        ts = self._toolset()
        a = ts.add_task(TENANT, "Dep")
        b = ts.add_task(TENANT, "Main")
        before = b.id in {t.id for t in ts.list_ready_tasks(TENANT)}
        ts.link_tasks(TENANT, b.id, a.id)
        after = b.id in {t.id for t in ts.list_ready_tasks(TENANT)}
        return before and not after

    def ready_reflects_dependency(self):
        ts = self._toolset()
        a = ts.add_task(TENANT, "Prereq")
        b = ts.add_task(TENANT, "Blocked")
        ts.link_tasks(TENANT, b.id, a.id)
        before = b.id in {t.id for t in ts.list_ready_tasks(TENANT)}
        ts.update_task_status(TENANT, a.id, self.m.TaskStatus.COMPLETED)
        after = b.id in {t.id for t in ts.list_ready_tasks(TENANT)}
        return before, after

    def bulk_write_creates(self, n):
        ts = self._toolset()
        items = [self.m.Task(tenant_id=TENANT, title=f"B{i}") for i in range(n)]
        saved = ts.bulk_write_tasks(TENANT, items)
        return len(list(saved))

    def hierarchical_nests_child(self):
        ts = self._toolset()
        parent = ts.add_task(TENANT, "Root")
        ts.create_child_task(TENANT, parent.id, "Leaf")
        flat = len(ts.list_tasks(TENANT, hierarchical=False))
        top = len(ts.list_tasks(TENANT, hierarchical=True))
        return flat, top


DRIVERS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """Wrap a loaded generation module in its explicit driver."""
    return DRIVERS[model](module)
