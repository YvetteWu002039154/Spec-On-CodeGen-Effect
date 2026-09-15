import re

# ── vocabulary matchers used by test_conformance.py ─────────────────────────
# The contract pins that a system DISTINGUISHES these states, not the exact
# spelling, so each is a set of accepted tokens.
SUCCESS_TOKENS = {"success", "succeeded", "successful", "ok", "completed", "done"}
FAILURE_TOKENS = {"failure", "failed", "error", "errored"}
RETRY_TOKENS = {"retry", "retried", "retrying", "retries", "retry_count",
                "retry_counter", "attempts"}
_STATUS_TOKENS = {"status", "state", "health", "is_healthy", "online", "alive"}
_HEARTBEAT_TOKENS = {"heartbeat", "last_heartbeat", "last_seen", "last_ping",
                     "updated_at", "seen_at"}


def _has_token(names, tokens):
    """True if any name contains any of the accepted tokens."""
    return any(t in str(n).lower() for n in (names or ()) for t in tokens)


def _has_status(names):
    return _has_token(names, _STATUS_TOKENS)


def _has_heartbeat(names):
    return _has_token(names, _HEARTBEAT_TOKENS)


def _has_retry_field(names):
    return _has_token(names, RETRY_TOKENS)


_STATE_LITERAL = re.compile(
    r"""(?:status|state)\s*[:=]=?\s*['"]([A-Za-z_-]+)['"]""")


def _enum_tokens(enum_cls):
    out = set()
    for member in enum_cls:
        out.add(str(member.name).lower())
        v = getattr(member, "value", None)
        if isinstance(v, str):
            out.add(v.lower())
    return out


def _source_tokens(module):
    """Vocabulary for a generation that declares none: every literal assigned to
    a `status`/`state` in its own source."""
    import inspect
    try:
        src = inspect.getsource(module)
    except Exception:                                    # noqa: BLE001
        src = open(module.__file__).read()
    return {m.lower() for m in _STATE_LITERAL.findall(src)}


def _fields(cls):
    """Declared field names: dataclass annotations, pydantic fields, or the
    SQLAlchemy column set."""
    names = set(getattr(cls, "__annotations__", {}) or {})
    names |= set(getattr(cls, "model_fields", {}) or {})
    table = getattr(cls, "__table__", None)
    if table is not None:
        names |= {c.name for c in table.columns}
    names |= {k for k in vars(cls) if not k.startswith("_")}
    return {str(n).lower() for n in names}


class _Base:
    def __init__(self, module):
        self.m = module

    def orphan_capability(self):
        return any(callable(getattr(self.m, n, None)) or
                   any(callable(getattr(c, n, None))
                       for c in vars(self.m).values() if isinstance(c, type))
                   for n in self.ORPHAN)

    def migration_runner(self):
        return any(callable(getattr(self.m, n, None)) or
                   any(callable(getattr(c, n, None))
                       for c in vars(self.m).values() if isinstance(c, type))
                   for n in self.MIGRATE)


class ClaudeDriver(_Base):
    ORPHAN = ("detect_orphans", "get_orphan_tasks", "is_orphan")
    MIGRATE = ("run_migrations", "migrate", "_register_migrations")

    def task_state_tokens(self):
        return _enum_tokens(self.m.TaskState)

    def retry_counter_fields(self):
        return _fields(self.m.TaskResult)

    def daily_stats_count_fields(self):
        return _fields(self.m.DailyTaskStats)

    def stats_success_increment(self):
        s = self.m.DailyTaskStats(date="2024-01-01", task_name="t")
        before = s.succeeded
        s.update(self.m.TaskState.SUCCESS)
        return before, s.succeeded

    def worker_health_fields(self):
        return _fields(self.m.WorkerInfo)

    def disconnect_removes_idempotent(self):
        """This generation names it remove_connection(), not disconnect()."""
        mgr = self.m.WebSocketManager()
        conn = self.m.WebSocketConnection("c1")
        try:
            mgr.add_connection(conn)
            mgr.remove_connection("c1")
            mgr.remove_connection("c1")               # second call must be a no-op
            return mgr.connection_count() == 0
        except Exception:                                # noqa: BLE001
            return False


class GptDriver(_Base):
    ORPHAN = ("detect_orphans", "orphans")
    MIGRATE = ("_apply_migrations", "migrate", "run_migrations")

    def _db(self):
        return self.m.Database(":memory:")

    def task_state_tokens(self):
        return _enum_tokens(self.m.TaskStatus)

    def retry_counter_fields(self):
        return _fields(self.m.TaskRecord)

    def daily_stats_count_fields(self):
        return _enum_tokens(self.m.TaskStatus) | {"count", "day", "name"}

    def stats_success_increment(self):
        repo = self.m.StatsRepository(self._db())
        day = "2024-01-01"
        def count():
            rows = repo.get_day(day) or []
            return sum(r["count"] if isinstance(r, dict) else r.count
                       for r in rows
                       if str(getattr(r, "status", r.get("status") if isinstance(r, dict) else "")
                              ).lower().endswith("success"))
        before = count()
        repo.increment(day, "t", self.m.TaskStatus.SUCCESS)
        return before, count()

    def worker_health_fields(self):
        return _fields(self.m.WorkerRecord)

    def disconnect_removes_idempotent(self):
        bus = self.m.EventBus()
        conn = object()
        try:
            bus.disconnect(conn)
            bus.disconnect(conn)
            return True
        except Exception:                                # noqa: BLE001
            return False


class _SqlAlchemyBase(_Base):
    """deepseek and gemini are both SQLAlchemy; give them a private in-memory
    engine so the counting path can actually run."""

    def _session(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        engine = create_engine("sqlite://")
        self.m.Base.metadata.create_all(engine)
        return sessionmaker(bind=engine)()

    def task_state_tokens(self):
        return _source_tokens(self.m)


class DeepseekDriver(_SqlAlchemyBase):
    ORPHAN = ("orphan_detector", "detect_orphans")
    MIGRATE = ("run_migrations", "migrate", "create_all")

    def retry_counter_fields(self):
        return _fields(self.m.TaskModel)

    def daily_stats_count_fields(self):
        return _fields(self.m.DailyStatsModel)

    def stats_success_increment(self):
        """update_daily_stats is an async CeleryMonitor method that awaits
        session.execute(), so it needs a real AsyncSession (aiosqlite), not the
        sync one the other behaviours use."""
        import asyncio
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        async def scenario():
            engine = create_async_engine("sqlite+aiosqlite://")
            async with engine.begin() as conn:
                await conn.run_sync(self.m.Base.metadata.create_all)
            maker = async_sessionmaker(engine, expire_on_commit=False)
            async with maker() as db:
                monitor = self.m.CeleryMonitor.__new__(self.m.CeleryMonitor)
                await self.m.CeleryMonitor.update_daily_stats(monitor, db, "SUCCESS")
                await db.commit()
                from sqlalchemy import select
                row = (await db.execute(select(self.m.DailyStatsModel))).scalars().first()
                return 0, ((row.succeeded or 0) if row else 0)

        return asyncio.run(scenario())

    def worker_health_fields(self):
        return _fields(self.m.WorkerModel)

    def disconnect_removes_idempotent(self):
        mgr = self.m.ConnectionManager()
        conn = object()
        try:
            mgr.disconnect(conn)
            mgr.disconnect(conn)
            return True
        except Exception:                                # noqa: BLE001
            return False

    def migration_runner(self):
        return callable(getattr(self.m.Base.metadata, "create_all", None))


class GeminiDriver(_SqlAlchemyBase):
    ORPHAN = ("detect_orphans", "background_health_and_orphan_checks")
    MIGRATE = ("run_migrations",)

    def retry_counter_fields(self):
        return _fields(self.m.TaskModel)

    def daily_stats_count_fields(self):
        return _fields(self.m.DailyStatisticModel)

    def stats_success_increment(self):
        """Driven on an EMPTY table, exactly as deepseek's equivalent is.

        Both generations declare default=0 columns and then create the day's row
        with only `date=` before doing `+= 1`. SQLAlchemy defaults do not
        materialise until flush, so the first task of any day raises
        `NoneType + int` in both. Seeding a zeroed row would hide that, and
        seeding for one generation but not the other would score them
        differently for the same defect — so neither is seeded."""
        db = self._session()
        row = db.query(self.m.DailyStatisticModel).first()
        before = (row.successful_tasks or 0) if row else 0
        self.m.StatsService(db).update_daily_stats("SUCCESS")
        db.commit()
        row = db.query(self.m.DailyStatisticModel).first()
        return before, ((row.successful_tasks or 0) if row else 0)

    def worker_health_fields(self):
        return _fields(self.m.WorkerModel)

    def disconnect_removes_idempotent(self):
        mgr = self.m.ConnectionManager()
        conn = object()
        try:
            mgr.disconnect(conn)
            mgr.disconnect(conn)
            return True
        except Exception:                                # noqa: BLE001
            return False


GENERATIONS = {
    "claude": ClaudeDriver,
    "gpt": GptDriver,
    "deepseek": DeepseekDriver,
    "gemini": GeminiDriver,
}


def build_driver(model, module):
    """One hand-written driver per model, written against that model's run0."""
    return GENERATIONS[model](module)
