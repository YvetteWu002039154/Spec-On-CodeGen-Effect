from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union
from uuid import uuid4


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _dt_to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _iso_to_dt(s: Optional[str]) -> Optional[datetime]:
    if s is None:
        return None
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    STARTED = "STARTED"
    RETRY = "RETRY"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    REVOKED = "REVOKED"


class WorkerStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"


@dataclass(frozen=True)
class TaskEvent:
    task_id: str
    status: TaskStatus
    timestamp: datetime
    worker: Optional[str] = None
    name: Optional[str] = None
    args: Optional[str] = None
    kwargs: Optional[str] = None
    result: Optional[str] = None
    exception: Optional[str] = None
    traceback: Optional[str] = None
    retry_count: Optional[int] = None


@dataclass
class TaskRecord:
    task_id: str
    name: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    received_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    worker: Optional[str] = None
    args: Optional[str] = None
    kwargs: Optional[str] = None
    result: Optional[str] = None
    exception: Optional[str] = None
    traceback: Optional[str] = None
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    orphaned: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status.value,
            "created_at": _dt_to_iso(self.created_at),
            "updated_at": _dt_to_iso(self.updated_at),
            "received_at": _dt_to_iso(self.received_at),
            "started_at": _dt_to_iso(self.started_at),
            "finished_at": _dt_to_iso(self.finished_at),
            "worker": self.worker,
            "args": self.args,
            "kwargs": self.kwargs,
            "result": self.result,
            "exception": self.exception,
            "traceback": self.traceback,
            "retry_count": self.retry_count,
            "last_retry_at": _dt_to_iso(self.last_retry_at),
            "orphaned": self.orphaned,
        }


@dataclass
class WorkerRecord:
    worker: str
    status: WorkerStatus
    first_seen_at: datetime
    last_seen_at: datetime
    last_heartbeat_at: datetime
    active_tasks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker": self.worker,
            "status": self.status.value,
            "first_seen_at": _dt_to_iso(self.first_seen_at),
            "last_seen_at": _dt_to_iso(self.last_seen_at),
            "last_heartbeat_at": _dt_to_iso(self.last_heartbeat_at),
            "active_tasks": self.active_tasks,
        }


@dataclass(frozen=True)
class DailyStats:
    day: datetime
    total: int
    by_status: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "day": self.day.date().isoformat(),
            "total": self.total,
            "by_status": dict(self.by_status),
        }


@dataclass(frozen=True)
class TaskFilter:
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    statuses: Optional[Set[TaskStatus]] = None
    name: Optional[str] = None
    worker: Optional[str] = None
    full_text: Optional[str] = None

    def validate(self) -> None:
        if self.date_from and self.date_from.tzinfo is None:
            raise ValueError("date_from must be timezone-aware")
        if self.date_to and self.date_to.tzinfo is None:
            raise ValueError("date_to must be timezone-aware")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be <= date_to")


class Database:
    def __init__(self, path: str = ":memory:") -> None:
        self._path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self.migrate()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def migrate(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER NOT NULL
                )
                """
            )
            row = cur.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
            if row is None:
                cur.execute("INSERT INTO schema_version(version) VALUES (0)")
                self._conn.commit()

            version = int(cur.execute("SELECT version FROM schema_version LIMIT 1").fetchone()["version"])
            if version < 1:
                self._apply_migration_1(cur)
                cur.execute("UPDATE schema_version SET version = 1")
                self._conn.commit()

    def _apply_migration_1(self, cur: sqlite3.Cursor) -> None:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                received_at TEXT,
                started_at TEXT,
                finished_at TEXT,
                worker TEXT,
                args TEXT,
                kwargs TEXT,
                result TEXT,
                exception TEXT,
                traceback TEXT,
                retry_count INTEGER NOT NULL DEFAULT 0,
                last_retry_at TEXT,
                orphaned INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_name ON tasks(name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker)")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS task_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                worker TEXT,
                name TEXT,
                args TEXT,
                kwargs TEXT,
                result TEXT,
                exception TEXT,
                traceback TEXT,
                retry_count INTEGER,
                FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_task_events_task_id ON task_events(task_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_task_events_timestamp ON task_events(timestamp)")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS workers (
                worker TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                last_heartbeat_at TEXT NOT NULL,
                active_tasks INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_workers_last_heartbeat ON workers(last_heartbeat_at)")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_stats (
                day TEXT PRIMARY KEY,
                total INTEGER NOT NULL,
                by_status_json TEXT NOT NULL
            )
            """
        )

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        with self._lock:
            self._conn.execute(sql, params)
            self._conn.commit()

    def query(self, sql: str, params: Sequence[Any] = ()) -> List[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.fetchall()

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> Optional[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.fetchone()

    def transaction(self) -> sqlite3.Connection:
        return self._conn

    def lock(self) -> threading.RLock:
        return self._lock


class TaskRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert_task(self, record: TaskRecord) -> None:
        with self._db.lock():
            self._db.transaction().execute(
                """
                INSERT INTO tasks(
                    task_id, name, status, created_at, updated_at, received_at, started_at, finished_at,
                    worker, args, kwargs, result, exception, traceback, retry_count, last_retry_at, orphaned
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    name=excluded.name,
                    status=excluded.status,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at,
                    received_at=excluded.received_at,
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at,
                    worker=excluded.worker,
                    args=excluded.args,
                    kwargs=excluded.kwargs,
                    result=excluded.result,
                    exception=excluded.exception,
                    traceback=excluded.traceback,
                    retry_count=excluded.retry_count,
                    last_retry_at=excluded.last_retry_at,
                    orphaned=excluded.orphaned
                """,
                (
                    record.task_id,
                    record.name,
                    record.status.value,
                    _dt_to_iso(record.created_at),
                    _dt_to_iso(record.updated_at),
                    _dt_to_iso(record.received_at),
                    _dt_to_iso(record.started_at),
                    _dt_to_iso(record.finished_at),
                    record.worker,
                    record.args,
                    record.kwargs,
                    record.result,
                    record.exception,
                    record.traceback,
                    int(record.retry_count),
                    _dt_to_iso(record.last_retry_at),
                    1 if record.orphaned else 0,
                ),
            )
            self._db.transaction().commit()

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        row = self._db.query_one("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        if row is None:
            return None
        return self._row_to_task(row)

    def add_event(self, event: TaskEvent) -> None:
        with self._db.lock():
            self._db.transaction().execute(
                """
                INSERT INTO task_events(
                    task_id, status, timestamp, worker, name, args, kwargs, result, exception, traceback, retry_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.task_id,
                    event.status.value,
                    _dt_to_iso(event.timestamp),
                    event.worker,
                    event.name,
                    event.args,
                    event.kwargs,
                    event.result,
                    event.exception,
                    event.traceback,
                    event.retry_count,
                ),
            )
            self._db.transaction().commit()

    def list_events(self, task_id: str, limit: int = 1000) -> List[TaskEvent]:
        if limit <= 0:
            raise ValueError("limit must be > 0")
        rows = self._db.query(
            "SELECT * FROM task_events WHERE task_id = ? ORDER BY timestamp ASC, id ASC LIMIT ?",
            (task_id, limit),
        )
        out: List[TaskEvent] = []
        for r in rows:
            out.append(
                TaskEvent(
                    task_id=r["task_id"],
                    status=TaskStatus(r["status"]),
                    timestamp=_iso_to_dt(r["timestamp"]) or _utcnow(),
                    worker=r["worker"],
                    name=r["name"],
                    args=r["args"],
                    kwargs=r["kwargs"],
                    result=r["result"],
                    exception=r["exception"],
                    traceback=r["traceback"],
                    retry_count=r["retry_count"],
                )
            )
        return out

    def search_tasks(self, flt: TaskFilter, limit: int = 200, offset: int = 0) -> List[TaskRecord]:
        flt.validate()
        if limit <= 0 or limit > 1000:
            raise ValueError("limit must be in 1..1000")
        if offset < 0:
            raise ValueError("offset must be >= 0")

        where: List[str] = []
        params: List[Any] = []

        if flt.date_from is not None:
            where.append("created_at >= ?")
            params.append(_dt_to_iso(flt.date_from))
        if flt.date_to is not None:
            where.append("created_at <= ?")
            params.append(_dt_to_iso(flt.date_to))
        if flt.statuses:
            placeholders = ",".join(["?"] * len(flt.statuses))
            where.append(f"status IN ({placeholders})")
            params.extend([s.value for s in sorted(flt.statuses, key=lambda x: x.value)])
        if flt.name:
            where.append("name = ?")
            params.append(flt.name)
        if flt.worker:
            where.append("worker = ?")
            params.append(flt.worker)
        if flt.full_text:
            like = f"%{flt.full_text}%"
            where.append(
                "("
                "task_id LIKE ? OR name LIKE ? OR IFNULL(worker,'') LIKE ? OR "
                "IFNULL(args,'') LIKE ? OR IFNULL(kwargs,'') LIKE ? OR "
                "IFNULL(result,'') LIKE ? OR IFNULL(exception,'') LIKE ? OR IFNULL(traceback,'') LIKE ?"
                ")"
            )
            params.extend([like, like, like, like, like, like, like, like])

        sql = "SELECT * FROM tasks"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self._db.query(sql, params)
        return [self._row_to_task(r) for r in rows]

    def mark_orphaned(self, task_ids: Iterable[str], orphaned: bool) -> int:
        ids = list(dict.fromkeys(task_ids))
        if not ids:
            return 0
        placeholders = ",".join(["?"] * len(ids))
        with self._db.lock():
            cur = self._db.transaction().execute(
                f"UPDATE tasks SET orphaned = ?, updated_at = ? WHERE task_id IN ({placeholders})",
                (1 if orphaned else 0, _dt_to_iso(_utcnow()), *ids),
            )
            self._db.transaction().commit()
            return int(cur.rowcount)

    def _row_to_task(self, row: sqlite3.Row) -> TaskRecord:
        return TaskRecord(
            task_id=row["task_id"],
            name=row["name"],
            status=TaskStatus(row["status"]),
            created_at=_iso_to_dt(row["created_at"]) or _utcnow(),
            updated_at=_iso_to_dt(row["updated_at"]) or _utcnow(),
            received_at=_iso_to_dt(row["received_at"]),
            started_at=_iso_to_dt(row["started_at"]),
            finished_at=_iso_to_dt(row["finished_at"]),
            worker=row["worker"],
            args=row["args"],
            kwargs=row["kwargs"],
            result=row["result"],
            exception=row["exception"],
            traceback=row["traceback"],
            retry_count=int(row["retry_count"] or 0),
            last_retry_at=_iso_to_dt(row["last_retry_at"]),
            orphaned=bool(row["orphaned"]),
        )


class WorkerRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert_worker(self, record: WorkerRecord) -> None:
        with self._db.lock():
            self._db.transaction().execute(
                """
                INSERT INTO workers(worker, status, first_seen_at, last_seen_at, last_heartbeat_at, active_tasks)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(worker) DO UPDATE SET
                    status=excluded.status,
                    first_seen_at=MIN(workers.first_seen_at, excluded.first_seen_at),
                    last_seen_at=excluded.last_seen_at,
                    last_heartbeat_at=excluded.last_heartbeat_at,
                    active_tasks=excluded.active_tasks
                """,
                (
                    record.worker,
                    record.status.value,
                    _dt_to_iso(record.first_seen_at),
                    _dt_to_iso(record.last_seen_at),
                    _dt_to_iso(record.last_heartbeat_at),
                    int(record.active_tasks),
                ),
            )
            self._db.transaction().commit()

    def get_worker(self, worker: str) -> Optional[WorkerRecord]:
        row = self._db.query_one("SELECT * FROM workers WHERE worker = ?", (worker,))
        if row is None:
            return None
        return self._row_to_worker(row)

    def list_workers(self) -> List[WorkerRecord]:
        rows = self._db.query("SELECT * FROM workers ORDER BY worker ASC")
        return [self._row_to_worker(r) for r in rows]

    def _row_to_worker(self, row: sqlite3.Row) -> WorkerRecord:
        return WorkerRecord(
            worker=row["worker"],
            status=WorkerStatus(row["status"]),
            first_seen_at=_iso_to_dt(row["first_seen_at"]) or _utcnow(),
            last_seen_at=_iso_to_dt(row["last_seen_at"]) or _utcnow(),
            last_heartbeat_at=_iso_to_dt(row["last_heartbeat_at"]) or _utcnow(),
            active_tasks=int(row["active_tasks"] or 0),
        )


class StatsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert_daily_stats(self, stats: DailyStats) -> None:
        day_key = stats.day.date().isoformat()
        with self._db.lock():
            self._db.transaction().execute(
                """
                INSERT INTO daily_stats(day, total, by_status_json)
                VALUES (?, ?, ?)
                ON CONFLICT(day) DO UPDATE SET
                    total=excluded.total,
                    by_status_json=excluded.by_status_json
                """,
                (day_key, int(stats.total), json.dumps(stats.by_status, sort_keys=True)),
            )
            self._db.transaction().commit()

    def get_daily_stats(self, day: datetime) -> Optional[DailyStats]:
        day_key = day.date().isoformat()
        row = self._db.query_one("SELECT * FROM daily_stats WHERE day = ?", (day_key,))
        if row is None:
            return None
        by_status = json.loads(row["by_status_json"])
        dt = datetime.fromisoformat(row["day"]).replace(tzinfo=timezone.utc)
        return DailyStats(day=dt, total=int(row["total"]), by_status={str(k): int(v) for k, v in by_status.items()})

    def list_daily_stats(self, date_from: datetime, date_to: datetime) -> List[DailyStats]:
        if date_from.tzinfo is None or date_to.tzinfo is None:
            raise ValueError("date_from/date_to must be timezone-aware")
        if date_from > date_to:
            raise ValueError("date_from must be <= date_to")
        rows = self._db.query(
            "SELECT * FROM daily_stats WHERE day >= ? AND day <= ? ORDER BY day ASC",
            (date_from.date().isoformat(), date_to.date().isoformat()),
        )
        out: List[DailyStats] = []
        for r in rows:
            by_status = json.loads(r["by_status_json"])
            dt = datetime.fromisoformat(r["day"]).replace(tzinfo=timezone.utc)
            out.append(DailyStats(day=dt, total=int(r["total"]), by_status={str(k): int(v) for k, v in by_status.items()}))
        return out


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: Dict[str, "asyncio.Queue[Dict[str, Any]]"] = {}

    def subscribe(self) -> str:
        sid = uuid4().hex
        q: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        with self._lock:
            self._subscribers[sid] = q
        return sid

    def unsubscribe(self, subscription_id: str) -> None:
        with self._lock:
            self._subscribers.pop(subscription_id, None)

    async def next_event(self, subscription_id: str) -> Dict[str, Any]:
        with self._lock:
            q = self._subscribers.get(subscription_id)
        if q is None:
            raise KeyError("unknown subscription")
        return await q.get()

    def publish(self, event: Dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subscribers.values())
        for q in subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


class TaskService:
    TERMINAL: Set[TaskStatus] = {TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED}

    def __init__(self, tasks: TaskRepository, workers: WorkerRepository, stats: StatsRepository, bus: EventBus) -> None:
        self._tasks = tasks
        self._workers = workers
        self._stats = stats
        self._bus = bus

    def ingest_event(self, event: TaskEvent) -> TaskRecord:
        if not event.task_id:
            raise ValueError("task_id is required")
        if event.timestamp.tzinfo is None:
            raise ValueError("event.timestamp must be timezone-aware")

        existing = self._tasks.get_task(event.task_id)
        now = event.timestamp

        if existing is None:
            name = event.name or "unknown"
            record = TaskRecord(
                task_id=event.task_id,
                name=name,
                status=event.status,
                created_at=now,
                updated_at=now,
                worker=event.worker,
                args=event.args,
                kwargs=event.kwargs,
                result=event.result,
                exception=event.exception,
                traceback=event.traceback,
                retry_count=int(event.retry_count or 0),
                last_retry_at=now if event.status == TaskStatus.RETRY else None,
            )
        else:
            record = existing
            record.updated_at = max(record.updated_at, now)
            if event.name:
                record.name = event.name
            record.status = event.status
            if event.worker is not None:
                record.worker = event.worker
            if event.args is not None:
                record.args = event.args
            if event.kwargs is not None:
                record.kwargs = event.kwargs
            if event.result is not None:
                record.result = event.result
            if event.exception is not None:
                record.exception = event.exception
            if event.traceback is not None:
                record.traceback = event.traceback

            if event.status == TaskStatus.RECEIVED:
                record.received_at = record.received_at or now
            elif event.status == TaskStatus.STARTED:
                record.started_at = record.started_at or now
            elif event.status in self.TERMINAL:
                record.finished_at = record.finished_at or now
            elif event.status == TaskStatus.RETRY:
                record.retry_count = max(record.retry_count, int(event.retry_count or (record.retry_count + 1)))
                record.last_retry_at = now

        if record.status in self.TERMINAL:
            record.orphaned = False

        self._tasks.upsert_task(record)
        self._tasks.add_event(event)

        if event.worker:
            self._touch_worker(event.worker, now)

        self._bus.publish(
            {
                "type": "task_event",
                "task_id": event.task_id,
                "status": event.status.value,
                "timestamp": _dt_to_iso(event.timestamp),
                "worker": event.worker,
                "name": event.name,
                "retry_count": event.retry_count,
            }
        )
        return record

    def retry_task(self, task_id: str) -> TaskRecord:
        record = self._tasks.get_task(task_id)
        if record is None:
            raise KeyError("task not found")
        now = _utcnow()
        record.status = TaskStatus.RETRY
        record.updated_at = now
        record.retry_count += 1
        record.last_retry_at = now
        record.orphaned = False
        self._tasks.upsert_task(record)
        self._tasks.add_event(
            TaskEvent(
                task_id=task_id,
                status=TaskStatus.RETRY,
                timestamp=now,
                worker=record.worker,
                name=record.name,
                args=record.args,
                kwargs=record.kwargs,
                retry_count=record.retry_count,
            )
        )
        self._bus.publish(
            {
                "type": "task_retry",
                "task_id": task_id,
                "timestamp": _dt_to_iso(now),
                "retry_count": record.retry_count,
            }
        )
        return record

    def search_tasks(self, flt: TaskFilter, limit: int = 200, offset: int = 0) -> List[TaskRecord]:
        return self._tasks.search_tasks(flt, limit=limit, offset=offset)

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        return self._tasks.get_task(task_id)

    def get_task_history(self, task_id: str, limit: int = 1000) -> List[TaskEvent]:
        return self._tasks.list_events(task_id, limit=limit)

    def detect_orphans(self, stale_after: timedelta) -> int:
        if stale_after.total_seconds() <= 0:
            raise ValueError("stale_after must be > 0")
        cutoff = _utcnow() - stale_after
        flt = TaskFilter(
            date_from=None,
            date_to=None,
            statuses={TaskStatus.STARTED, TaskStatus.RECEIVED},
            name=None,
            worker=None,
            full_text=None,
        )
        candidates = self._tasks.search_tasks(flt, limit=1000, offset=0)
        stale_ids: List[str] = []
        for t in candidates:
            if t.finished_at is not None:
                continue
            if t.updated_at <= cutoff:
                stale_ids.append(t.task_id)
        updated = self._tasks.mark_orphaned(stale_ids, True)
        if updated:
            self._bus.publish(
                {
                    "type": "orphan_detection",
                    "timestamp": _dt_to_iso(_utcnow()),
                    "count": updated,
                }
            )
        return updated

    def compute_daily_stats(self, day: datetime) -> DailyStats:
        if day.tzinfo is None:
            raise ValueError("day must be timezone-aware")
        day_utc = day.astimezone(timezone.utc)
        start = datetime(day_utc.year, day_utc.month, day_utc.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1) - timedelta(microseconds=1)

        flt = TaskFilter(date_from=start, date_to=end)
        tasks = self._tasks.search_tasks(flt, limit=1000, offset=0)
        by_status: Dict[str, int] = {}
        for t in tasks:
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
        stats = DailyStats(day=start, total=len(tasks), by_status=by_status)
        self._stats.upsert_daily_stats(stats)
        self._bus.publish({"type": "daily_stats", "day": start.date().isoformat(), "total": stats.total, "by_status": by_status})
        return stats

    def _touch_worker(self, worker: str, ts: datetime) -> None:
        existing = self._workers.get_worker(worker)
        if existing is None:
            rec = WorkerRecord(
                worker=worker,
                status=WorkerStatus.ONLINE,
                first_seen_at=ts,
                last_seen_at=ts,
                last_heartbeat_at=ts,
                active_tasks=0,
            )
        else:
            rec = existing
            rec.last_seen_at = max(rec.last_seen_at, ts)
            rec.last_heartbeat_at = max(rec.last_heartbeat_at, ts)
            rec.status = WorkerStatus.ONLINE
        self._workers.upsert_worker(rec)
        self._bus.publish({"type": "worker_seen", "worker": worker, "timestamp": _dt_to_iso(ts)})


class WorkerHealthService:
    def __init__(self, workers: WorkerRepository, bus: EventBus) -> None:
        self._workers = workers
        self._bus = bus

    def heartbeat(self, worker: str, active_tasks: int = 0, timestamp: Optional[datetime] = None) -> WorkerRecord:
        if not worker:
            raise ValueError("worker is required")
        if active_tasks < 0:
            raise ValueError("active_tasks must be >= 0")
        ts = timestamp or _utcnow()
        if ts.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")

        existing = self._workers.get_worker(worker)
        if existing is None:
            rec = WorkerRecord(
                worker=worker,
                status=WorkerStatus.ONLINE,
                first_seen_at=ts,
                last_seen_at=ts,
                last_heartbeat_at=ts,
                active_tasks=active_tasks,
            )
        else:
            rec = existing
            rec.last_seen_at = max(rec.last_seen_at, ts)
            rec.last_heartbeat_at = max(rec.last_heartbeat_at, ts)
            rec.active_tasks = active_tasks
            rec.status = WorkerStatus.ONLINE
        self._workers.upsert_worker(rec)
        self._bus.publish({"type": "worker_heartbeat", "worker": worker, "timestamp": _dt_to_iso(ts), "active_tasks": active_tasks})
        return rec

    def evaluate_health(self, offline_after: timedelta, degraded_after: Optional[timedelta] = None) -> List[WorkerRecord]:
        if offline_after.total_seconds() <= 0:
            raise ValueError("offline_after must be > 0")
        if degraded_after is not None and degraded_after.total_seconds() <= 0:
            raise ValueError("degraded_after must be > 0")

        now = _utcnow()
        workers = self._workers.list_workers()
        changed: List[WorkerRecord] = []
        for w in workers:
            age = now - w.last_heartbeat_at
            new_status = w.status
            if age > offline_after:
                new_status = WorkerStatus.OFFLINE
            elif degraded_after is not None and age > degraded_after:
                new_status = WorkerStatus.DEGRADED
            else:
                new_status = WorkerStatus.ONLINE

            if new_status != w.status:
                w.status = new_status
                self._workers.upsert_worker(w)
                changed.append(w)
                self._bus.publish(
                    {
                        "type": "worker_status",
                        "worker": w.worker,
                        "status": w.status.value,
                        "timestamp": _dt_to_iso(now),
                    }
                )
        return changed


class WebSocketServer:
    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    async def stream(self) -> AsyncIterator[str]:
        sid = self._bus.subscribe()
        try:
            while True:
                event = await self._bus.next_event(sid)
                yield json.dumps(event, separators=(",", ":"), sort_keys=True)
        finally:
            self._bus.unsubscribe(sid)


class KanchiSystem:
    def __init__(self, db_path: str = ":memory:") -> None:
        self.db = Database(db_path)
        self.bus = EventBus()
        self.tasks_repo = TaskRepository(self.db)
        self.workers_repo = WorkerRepository(self.db)
        self.stats_repo = StatsRepository(self.db)
        self.task_service = TaskService(self.tasks_repo, self.workers_repo, self.stats_repo, self.bus)
        self.worker_health = WorkerHealthService(self.workers_repo, self.bus)
        self.websocket = WebSocketServer(self.bus)

    def close(self) -> None:
        self.db.close()


__all__ = [
    "TaskStatus",
    "WorkerStatus",
    "TaskEvent",
    "TaskRecord",
    "WorkerRecord",
    "DailyStats",
    "TaskFilter",
    "Database",
    "TaskRepository",
    "WorkerRepository",
    "StatsRepository",
    "EventBus",
    "TaskService",
    "WorkerHealthService",
    "WebSocketServer",
    "KanchiSystem",
]