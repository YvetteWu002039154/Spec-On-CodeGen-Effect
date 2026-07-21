import asyncio
import dataclasses
import inspect
import os
import tempfile

# Task-state / statistics vocabulary tokens (grounded in the origin
# `TaskDailyStatsDB` columns {succeeded, failed, retried, revoked, pending}).
SUCCESS_TOKENS = ("success", "succeed", "succeeded", "successful")
FAILURE_TOKENS = ("failure", "failed", "fail")
RETRY_TOKENS = ("retry", "retried", "retries")
_STATUS_TOKENS = ("status", "state")
_HEARTBEAT_TOKENS = ("heartbeat", "last_seen", "lastseen", "last_heartbeat", "seen")


# --- small shared observation helpers ---------------------------------------

def _has_token(values, group):
    """True if any of `group`'s stems appears in any of `values` (substring,
    lowercased). Used to check a vocabulary/field set for a concept regardless
    of the exact word a generation chose (`success` vs `succeeded`)."""
    return any(stem in str(v).lower() for v in values for stem in group)


def _has_retry_field(fields):
    """True if a field records a retry count (`retries` / `retry_count` / …)."""
    return _has_token(fields, RETRY_TOKENS)


def _has_status(fields):
    """True if a field records a worker's status/state."""
    return _has_token(fields, _STATUS_TOKENS)


def _has_heartbeat(fields):
    """True if a field records a worker's heartbeat / last-seen time."""
    return _has_token(fields, _HEARTBEAT_TOKENS)


def _enum_tokens(enum_cls):
    """Member names and values of an enum, lowercased."""
    tokens = set()
    for member in enum_cls:
        tokens.add(str(member.name).lower())
        tokens.add(str(getattr(member, "value", member.name)).lower())
    return tokens


def _dataclass_field_names(cls):
    return {f.name.lower() for f in dataclasses.fields(cls)}


def _column_names(model):
    """Column names of a SQLAlchemy ORM model, lowercased."""
    return {c.name.lower() for c in model.__table__.columns}

def _tmp_db():
    """Throwaway sqlite path for a generation that persists to disk."""
    return os.path.join(tempfile.mkdtemp(prefix="kanchi_nl_"), "kanchi.db")


def _enum_or_empty(module, *names):
    """Tokens of the first enum among `names` a generation defines, or an empty
    set when it exposes no enumerable state vocabulary — so N1 fails *cleanly*
    (a genuine shape divergence) instead of raising AttributeError."""
    for n in names:
        enum_cls = getattr(module, n, None)
        if enum_cls is not None:
            try:
                return _enum_tokens(enum_cls)
            except TypeError:
                pass
    return set()


def _sync_orm_session(module):
    """A real in-memory SQLite session over a generation's SQLAlchemy `Base`
    (the NL loader imports the real ORM, so this drives actual persistence)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    engine = create_engine("sqlite://")
    module.Base.metadata.create_all(engine)
    return Session(engine)


class _SeededAsyncResult:
    def __init__(self, obj):
        self._obj = obj

    def scalars(self):
        return self

    def first(self):
        return self._obj


class _SeededAsyncSession:
    """Minimal async session that feeds a pre-seeded ORM row to a generation's
    async ``update_daily_stats`` so its *real* increment branch runs without
    standing up an aiosqlite engine. Every ``execute`` resolves to the seeded
    row (the "record already exists" path — N5 is about incrementing an existing
    daily record)."""

    def __init__(self, existing):
        self._existing = existing

    async def execute(self, *a, **k):
        return _SeededAsyncResult(self._existing)

    def add(self, obj):  # new-row path is unused: we seed an existing row
        pass

    async def flush(self):
        pass


# ============================================================================
# One driver per generation. `m` is that generation's loaded module.
# ============================================================================

class ClaudeDriver:
    model = "claude"

    def __init__(self, m):
        self.m = m

    def task_state_tokens(self):
        return _enum_tokens(self.m.TaskState)

    def retry_counter_fields(self):
        return _dataclass_field_names(self.m.TaskResult)

    def orphan_capability(self):
        detector = self.m.OrphanDetector(self.m.TaskStorage())
        task = self.m.TaskResult("t", "n", self.m.TaskState.FAILURE)
        return isinstance(detector.is_orphan(task), bool)

    def daily_stats_count_fields(self):
        return _dataclass_field_names(self.m.DailyTaskStats)

    def stats_success_increment(self):
        rec = self.m.DailyTaskStats(date="2024-01-01", task_name="t")
        before = rec.succeeded
        rec.update(self.m.TaskState.SUCCESS)
        return before, rec.succeeded

    def worker_health_fields(self):
        return _dataclass_field_names(self.m.WorkerInfo)

    def disconnect_removes_idempotent(self):
        # claude's registry is id-keyed: `remove_connection(connection_id)`,
        # backed by a dict `.pop(id, None)` — inherently idempotent.
        mgr = self.m.WebSocketManager()
        mgr.add_connection(self.m.WebSocketConnection("c1"))
        mgr.remove_connection("c1")
        removed = mgr.get_connection("c1") is None
        mgr.remove_connection("c1")           # idempotent: already gone
        mgr.remove_connection("nonexistent")  # idempotent: never registered
        return removed

    def migration_runner(self):
        self.m.MigrationManager().run_migrations()
        return True


class GptDriver:
    model = "gpt"

    def __init__(self, m):
        self.m = m

    def task_state_tokens(self):
        return _enum_tokens(self.m.TaskStatus)

    def retry_counter_fields(self):
        return _dataclass_field_names(self.m.TaskRecord)

    def orphan_capability(self):
        repo = self.m.TaskRepository(self.m.Database(_tmp_db()))
        return isinstance(repo.detect_orphans(), list)

    def daily_stats_count_fields(self):
        # gpt uses a *long* schema — one row per (day, name, status) — so the
        # success/failure vocabulary lives in the `status` values, not in wide
        # `succeeded`/`failed` columns.
        stats = self.m.StatsRepository(self.m.Database(_tmp_db()))
        stats.increment("2024-01-01", "t", self.m.TaskStatus.SUCCESS)
        stats.increment("2024-01-01", "t", self.m.TaskStatus.FAILURE)
        return {row["status"] for row in stats.get_day("2024-01-01")}

    def stats_success_increment(self):
        stats = self.m.StatsRepository(self.m.Database(_tmp_db()))
        stats.increment("2024-01-01", "t", self.m.TaskStatus.SUCCESS)
        row = next(r for r in stats.get_day("2024-01-01")
                   if r["status"] == self.m.TaskStatus.SUCCESS.value)
        return 0, row["count"]

    def worker_health_fields(self):
        return _dataclass_field_names(self.m.WorkerRecord)

    def disconnect_removes_idempotent(self):
        # gpt's `EventBus.disconnect` is a coroutine — must be awaited.
        async def go():
            bus = self.m.EventBus()
            ws = object()
            bus._clients.append(ws)
            await bus.disconnect(ws)
            removed = ws not in bus._clients
            await bus.disconnect(object())    # idempotent: not registered
            return removed
        return asyncio.run(go())

    def migration_runner(self):
        # gpt has no `MigrationManager`; auto-migration is `_apply_migrations`
        # on `Database`, run against a versioned `schema_migrations` table.
        db = self.m.Database(_tmp_db())
        db._apply_migrations()                # idempotent re-run
        return True


class DeepseekDriver:
    model = "deepseek"

    def __init__(self, m):
        self.m = m

    def task_state_tokens(self):
        # deepseek models task state as free strings (no enum), so there is no
        # enumerable vocabulary to inspect — N1 fails cleanly (genuine finding).
        return _enum_or_empty(self.m, "TaskState", "TaskStatus")

    def retry_counter_fields(self):
        return _column_names(self.m.TaskModel)

    def orphan_capability(self):
        # Contract N3 allows a dedicated detector; deepseek exposes the
        # `orphan_detector` coroutine (flags STARTED tasks whose worker went
        # offline as 'ORPHAN') rather than a `TaskModel.is_orphan` flag.
        return inspect.iscoroutinefunction(getattr(self.m, "orphan_detector", None))

    def daily_stats_count_fields(self):
        return _column_names(self.m.DailyStatsModel)

    def stats_success_increment(self):
        # deepseek accumulates via the async `CeleryMonitor.update_daily_stats`
        # (needs a session); drive its real increment branch on a seeded row.
        rec = self.m.DailyStatsModel()
        for f in ("total", "succeeded", "failed", "retried", "pending"):
            setattr(rec, f, 0)                # column defaults apply at flush
        session = _SeededAsyncSession(rec)
        # the method doesn't touch `self`; call it unbound with self=None.
        asyncio.run(self.m.CeleryMonitor.update_daily_stats(None, session, "SUCCESS"))
        return 0, rec.succeeded

    def worker_health_fields(self):
        return _column_names(self.m.WorkerModel)

    def disconnect_removes_idempotent(self):
        mgr = self.m.ConnectionManager()
        ws = object()
        mgr.active_connections.append(ws)
        mgr.disconnect(ws)
        removed = ws not in mgr.active_connections
        mgr.disconnect(object())
        return removed

    def migration_runner(self):
        # deepseek has no runner class; it auto-migrates by running
        # `alembic ... upgrade head` inside its FastAPI `lifespan` startup.
        # Confirm that upgrade call is wired.
        try:
            src = inspect.getsource(self.m.lifespan)
        except (OSError, TypeError):
            return False
        return "alembic" in src and "upgrade" in src


class GeminiDriver:
    model = "gemini"

    def __init__(self, m):
        self.m = m

    def task_state_tokens(self):
        # gemini also models task state as free strings (no enum) — N1 fails
        # cleanly rather than raising AttributeError.
        return _enum_or_empty(self.m, "TaskState", "TaskStatus")

    def retry_counter_fields(self):
        return _column_names(self.m.TaskModel)

    def orphan_capability(self):
        return "is_orphan" in _column_names(self.m.TaskModel)

    def daily_stats_count_fields(self):
        return _column_names(self.m.DailyStatisticModel)

    def stats_success_increment(self):
        # gemini's `StatsService.update_daily_stats` needs a real session; drive
        # it over an in-memory DB against an existing (flushed) daily record so
        # the success counter increment is observable.
        import datetime as _dt
        session = _sync_orm_session(self.m)
        try:
            seed = self.m.DailyStatisticModel(date=_dt.datetime.utcnow().date())
            session.add(seed)
            session.commit()                  # applies the default-0 counters
            before = seed.successful_tasks
            self.m.StatsService(session).update_daily_stats("SUCCESS")
            session.refresh(seed)
            return before, seed.successful_tasks
        finally:
            session.close()

    def worker_health_fields(self):
        return _column_names(self.m.WorkerModel)

    def disconnect_removes_idempotent(self):
        mgr = self.m.ConnectionManager()
        ws = object()
        mgr.active_connections.append(ws)
        mgr.disconnect(ws)
        removed = ws not in mgr.active_connections
        mgr.disconnect(object())
        return removed

    def migration_runner(self):
        self.m.AutoMigration.run_migrations()
        return True


DRIVERS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """Wrap a loaded generation module in its explicit driver."""
    return DRIVERS[model](module)
