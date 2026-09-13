from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, Union
from urllib.parse import parse_qs, urlparse

try:
    import websockets  # type: ignore
except Exception:  # pragma: no cover
    websockets = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


class WorkerStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


@dataclass(frozen=True)
class TaskEvent:
    task_id: str
    name: str
    status: TaskStatus
    worker: Optional[str]
    timestamp: datetime
    args: Optional[str] = None
    kwargs: Optional[str] = None
    result: Optional[str] = None
    exception: Optional[str] = None
    traceback: Optional[str] = None
    retries: int = 0


@dataclass(frozen=True)
class WorkerHeartbeat:
    worker: str
    timestamp: datetime


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    name: str
    status: TaskStatus
    worker: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    retries: int
    args: Optional[str]
    kwargs: Optional[str]
    result: Optional[str]
    exception: Optional[str]
    traceback: Optional[str]
    orphaned: bool


@dataclass(frozen=True)
class WorkerRecord:
    worker: str
    status: WorkerStatus
    last_heartbeat_at: Optional[datetime]
    first_seen_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class DailyStat:
    day: date
    name: Optional[str]
    worker: Optional[str]
    status: TaskStatus
    count: int


class ValidationError(ValueError):
    pass


class NotFoundError(LookupError):
    pass


class Database:
    def __init__(self, path: str = "kanchi.db") -> None:
        self._path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA synchronous = NORMAL")

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def executemany(self, sql: str, seq: Iterable[Tuple[Any, ...]]) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.executemany(sql, seq)
            self._conn.commit()
            return cur

    def query(self, sql: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.fetchall()

    def query_one(self, sql: str, params: Tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return cur.fetchone()


class MigrationManager:
    def __init__(self, db: Database) -> None:
        self._db = db

    def migrate(self) -> None:
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
        )
        row = self._db.query_one("SELECT version FROM schema_version LIMIT 1")
        if row is None:
            self._db.execute("INSERT INTO schema_version(version) VALUES (1)")
            self._apply_v1()
        else:
            version = int(row["version"])
            if version < 1:
                self._db.execute("UPDATE schema_version SET version = 1")
                self._apply_v1()

    def _apply_v1(self) -> None:
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                worker TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                retries INTEGER NOT NULL DEFAULT 0,
                args TEXT,
                kwargs TEXT,
                result TEXT,
                exception TEXT,
                traceback TEXT,
                orphaned INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self._db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at)
            """
        )
        self._db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
            """
        )
        self._db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_name ON tasks(name)
            """
        )
        self._db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker)
            """
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS task_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                worker TEXT,
                timestamp TEXT NOT NULL,
                args TEXT,
                kwargs TEXT,
                result TEXT,
                exception TEXT,
                traceback TEXT,
                retries INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            )
            """
        )
        self._db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_events_task_id ON task_events(task_id)
            """
        )
        self._db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_task_events_timestamp ON task_events(timestamp)
            """
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS workers (
                worker TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                last_heartbeat_at TEXT,
                first_seen_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self._db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status)
            """
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_stats (
                day TEXT NOT NULL,
                name TEXT,
                worker TEXT,
                status TEXT NOT NULL,
                count INTEGER NOT NULL,
                PRIMARY KEY(day, name, worker, status)
            )
            """
        )
        self._db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_daily_stats_day ON daily_stats(day)
            """
        )


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: Set[Callable[[Dict[str, Any]], None]] = set()

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> Callable[[], None]:
        with self._lock:
            self._subscribers.add(callback)

        def _unsub() -> None:
            with self._lock:
                self._subscribers.discard(callback)

        return _unsub

    def publish(self, event: Dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subscribers)
        for cb in subs:
            try:
                cb(event)
            except Exception:
                pass


class TaskRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    @staticmethod
    def _dt_to_str(dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        return _to_utc(dt).isoformat()

    @staticmethod
    def _str_to_dt(s: Optional[str]) -> Optional[datetime]:
        if s is None:
            return None
        return datetime.fromisoformat(s)

    def upsert_task_from_event(self, ev: TaskEvent) -> TaskRecord:
        now = _to_utc(ev.timestamp)
        existing = self._db.query_one("SELECT * FROM tasks WHERE task_id = ?", (ev.task_id,))
        if existing is None:
            created_at = now
            started_at = now if ev.status == TaskStatus.STARTED else None
            finished_at = now if ev.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED) else None
            self._db.execute(
                """
                INSERT INTO tasks(task_id, name, status, worker, created_at, updated_at, started_at, finished_at,
                                  retries, args, kwargs, result, exception, traceback, orphaned)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    ev.task_id,
                    ev.name,
                    ev.status.value,
                    ev.worker,
                    self._dt_to_str(created_at),
                    self._dt_to_str(now),
                    self._dt_to_str(started_at),
                    self._dt_to_str(finished_at),
                    int(ev.retries),
                    ev.args,
                    ev.kwargs,
                    ev.result,
                    ev.exception,
                    ev.traceback,
                ),
            )
        else:
            created_at = self._str_to_dt(existing["created_at"]) or now
            started_at = self._str_to_dt(existing["started_at"])
            finished_at = self._str_to_dt(existing["finished_at"])
            orphaned = int(existing["orphaned"]) != 0

            if ev.status == TaskStatus.STARTED and started_at is None:
                started_at = now
            if ev.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED):
                finished_at = now

            retries = max(int(existing["retries"]), int(ev.retries))
            if ev.status == TaskStatus.RETRY:
                retries = max(retries, int(ev.retries), int(existing["retries"]) + 1)

            if ev.worker is not None:
                worker = ev.worker
            else:
                worker = existing["worker"]

            self._db.execute(
                """
                UPDATE tasks
                SET name = ?,
                    status = ?,
                    worker = ?,
                    updated_at = ?,
                    started_at = ?,
                    finished_at = ?,
                    retries = ?,
                    args = COALESCE(?, args),
                    kwargs = COALESCE(?, kwargs),
                    result = COALESCE(?, result),
                    exception = COALESCE(?, exception),
                    traceback = COALESCE(?, traceback),
                    orphaned = ?
                WHERE task_id = ?
                """,
                (
                    ev.name,
                    ev.status.value,
                    worker,
                    self._dt_to_str(now),
                    self._dt_to_str(started_at),
                    self._dt_to_str(finished_at),
                    int(retries),
                    ev.args,
                    ev.kwargs,
                    ev.result,
                    ev.exception,
                    ev.traceback,
                    1 if orphaned else 0,
                    ev.task_id,
                ),
            )

        self._db.execute(
            """
            INSERT INTO task_events(task_id, name, status, worker, timestamp, args, kwargs, result, exception, traceback, retries)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ev.task_id,
                ev.name,
                ev.status.value,
                ev.worker,
                self._dt_to_str(now),
                ev.args,
                ev.kwargs,
                ev.result,
                ev.exception,
                ev.traceback,
                int(ev.retries),
            ),
        )
        row = self._db.query_one("SELECT * FROM tasks WHERE task_id = ?", (ev.task_id,))
        if row is None:
            raise NotFoundError(ev.task_id)
        return self._row_to_task(row)

    def _row_to_task(self, row: sqlite3.Row) -> TaskRecord:
        return TaskRecord(
            task_id=str(row["task_id"]),
            name=str(row["name"]),
            status=TaskStatus(str(row["status"])),
            worker=row["worker"],
            created_at=self._str_to_dt(row["created_at"]) or _utcnow(),
            updated_at=self._str_to_dt(row["updated_at"]) or _utcnow(),
            started_at=self._str_to_dt(row["started_at"]),
            finished_at=self._str_to_dt(row["finished_at"]),
            retries=int(row["retries"]),
            args=row["args"],
            kwargs=row["kwargs"],
            result=row["result"],
            exception=row["exception"],
            traceback=row["traceback"],
            orphaned=int(row["orphaned"]) != 0,
        )

    def get_task(self, task_id: str) -> TaskRecord:
        row = self._db.query_one("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        if row is None:
            raise NotFoundError(task_id)
        return self._row_to_task(row)

    def list_task_events(self, task_id: str, limit: int = 200) -> List[TaskEvent]:
        if limit <= 0 or limit > 5000:
            raise ValidationError("limit must be between 1 and 5000")
        rows = self._db.query(
            """
            SELECT task_id, name, status, worker, timestamp, args, kwargs, result, exception, traceback, retries
            FROM task_events
            WHERE task_id = ?
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            (task_id, int(limit)),
        )
        out: List[TaskEvent] = []
        for r in rows:
            out.append(
                TaskEvent(
                    task_id=str(r["task_id"]),
                    name=str(r["name"]),
                    status=TaskStatus(str(r["status"])),
                    worker=r["worker"],
                    timestamp=self._str_to_dt(r["timestamp"]) or _utcnow(),
                    args=r["args"],
                    kwargs=r["kwargs"],
                    result=r["result"],
                    exception=r["exception"],
                    traceback=r["traceback"],
                    retries=int(r["retries"]),
                )
            )
        return out

    def search_tasks(
        self,
        *,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[TaskStatus] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        full_text: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[TaskRecord]:
        if limit <= 0 or limit > 5000:
            raise ValidationError("limit must be between 1 and 5000")
        if offset < 0:
            raise ValidationError("offset must be >= 0")

        clauses: List[str] = []
        params: List[Any] = []

        if date_from is not None:
            clauses.append("updated_at >= ?")
            params.append(self._dt_to_str(_to_utc(date_from)))
        if date_to is not None:
            clauses.append("updated_at <= ?")
            params.append(self._dt_to_str(_to_utc(date_to)))
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if name is not None:
            clauses.append("name = ?")
            params.append(name)
        if worker is not None:
            clauses.append("worker = ?")
            params.append(worker)
        if full_text is not None and full_text.strip():
            q = f"%{full_text.strip()}%"
            clauses.append(
                "("
                "task_id LIKE ? OR name LIKE ? OR COALESCE(worker,'') LIKE ? OR "
                "COALESCE(args,'') LIKE ? OR COALESCE(kwargs,'') LIKE ? OR "
                "COALESCE(result,'') LIKE ? OR COALESCE(exception,'') LIKE ? OR COALESCE(traceback,'') LIKE ?"
                ")"
            )
            params.extend([q, q, q, q, q, q, q, q])

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self._db.query(
            f"""
            SELECT * FROM tasks
            {where}
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params + [int(limit), int(offset)]),
        )
        return [self._row_to_task(r) for r in rows]

    def mark_orphaned(self, task_ids: List[str], orphaned: bool) -> int:
        if not task_ids:
            return 0
        placeholders = ",".join(["?"] * len(task_ids))
        self._db.execute(
            f"UPDATE tasks SET orphaned = ?, updated_at = ? WHERE task_id IN ({placeholders})",
            tuple([1 if orphaned else 0, self._dt_to_str(_utcnow())] + task_ids),
        )
        row = self._db.query_one(
            f"SELECT changes() AS n"
        )
        return int(row["n"]) if row else 0

    def list_active_tasks_older_than(self, cutoff: datetime) -> List[TaskRecord]:
        cutoff_s = self._dt_to_str(_to_utc(cutoff))
        rows = self._db.query(
            """
            SELECT * FROM tasks
            WHERE status IN ('PENDING','RECEIVED','STARTED','RETRY')
              AND updated_at < ?
            """,
            (cutoff_s,),
        )
        return [self._row_to_task(r) for r in rows]


class WorkerRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    @staticmethod
    def _dt_to_str(dt: Optional[datetime]) -> Optional[str]:
        if dt is None:
            return None
        return _to_utc(dt).isoformat()

    @staticmethod
    def _str_to_dt(s: Optional[str]) -> Optional[datetime]:
        if s is None:
            return None
        return datetime.fromisoformat(s)

    def upsert_heartbeat(self, hb: WorkerHeartbeat, offline_after: timedelta) -> WorkerRecord:
        now = _to_utc(hb.timestamp)
        existing = self._db.query_one("SELECT * FROM workers WHERE worker = ?", (hb.worker,))
        if existing is None:
            self._db.execute(
                """
                INSERT INTO workers(worker, status, last_heartbeat_at, first_seen_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    hb.worker,
                    WorkerStatus.ONLINE.value,
                    self._dt_to_str(now),
                    self._dt_to_str(now),
                    self._dt_to_str(now),
                ),
            )
        else:
            self._db.execute(
                """
                UPDATE workers
                SET status = ?,
                    last_heartbeat_at = ?,
                    updated_at = ?
                WHERE worker = ?
                """,
                (
                    WorkerStatus.ONLINE.value,
                    self._dt_to_str(now),
                    self._dt_to_str(now),
                    hb.worker,
                ),
            )
        self._refresh_offline(offline_after)
        row = self._db.query_one("SELECT * FROM workers WHERE worker = ?", (hb.worker,))
        if row is None:
            raise NotFoundError(hb.worker)
        return self._row_to_worker(row)

    def _row_to_worker(self, row: sqlite3.Row) -> WorkerRecord:
        return WorkerRecord(
            worker=str(row["worker"]),
            status=WorkerStatus(str(row["status"])),
            last_heartbeat_at=self._str_to_dt(row["last_heartbeat_at"]),
            first_seen_at=self._str_to_dt(row["first_seen_at"]) or _utcnow(),
            updated_at=self._str_to_dt(row["updated_at"]) or _utcnow(),
        )

    def _refresh_offline(self, offline_after: timedelta) -> int:
        cutoff = _utcnow() - offline_after
        cutoff_s = self._dt_to_str(cutoff)
        self._db.execute(
            """
            UPDATE workers
            SET status = ?, updated_at = ?
            WHERE (last_heartbeat_at IS NULL OR last_heartbeat_at < ?)
              AND status != ?
            """,
            (WorkerStatus.OFFLINE.value, self._dt_to_str(_utcnow()), cutoff_s, WorkerStatus.OFFLINE.value),
        )
        row = self._db.query_one("SELECT changes() AS n")
        return int(row["n"]) if row else 0

    def refresh_offline(self, offline_after: timedelta) -> int:
        return self._refresh_offline(offline_after)

    def list_workers(self) -> List[WorkerRecord]:
        rows = self._db.query("SELECT * FROM workers ORDER BY worker ASC")
        return [self._row_to_worker(r) for r in rows]

    def get_worker(self, worker: str) -> WorkerRecord:
        row = self._db.query_one("SELECT * FROM workers WHERE worker = ?", (worker,))
        if row is None:
            raise NotFoundError(worker)
        return self._row_to_worker(row)


class StatsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def increment_daily(self, *, day: date, name: Optional[str], worker: Optional[str], status: TaskStatus, delta: int = 1) -> None:
        if delta == 0:
            return
        day_s = day.isoformat()
        self._db.execute(
            """
            INSERT INTO daily_stats(day, name, worker, status, count)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(day, name, worker, status) DO UPDATE SET count = count + excluded.count
            """,
            (day_s, name, worker, status.value, int(delta)),
        )

    def list_daily(
        self,
        *,
        day_from: Optional[date] = None,
        day_to: Optional[date] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[DailyStat]:
        if limit <= 0 or limit > 10000:
            raise ValidationError("limit must be between 1 and 10000")
        if offset < 0:
            raise ValidationError("offset must be >= 0")

        clauses: List[str] = []
        params: List[Any] = []

        if day_from is not None:
            clauses.append("day >= ?")
            params.append(day_from.isoformat())
        if day_to is not None:
            clauses.append("day <= ?")
            params.append(day_to.isoformat())
        if name is not None:
            clauses.append("name = ?")
            params.append(name)
        if worker is not None:
            clauses.append("worker = ?")
            params.append(worker)
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self._db.query(
            f"""
            SELECT day, name, worker, status, count
            FROM daily_stats
            {where}
            ORDER BY day DESC, status ASC
            LIMIT ? OFFSET ?
            """,
            tuple(params + [int(limit), int(offset)]),
        )
        out: List[DailyStat] = []
        for r in rows:
            out.append(
                DailyStat(
                    day=date.fromisoformat(str(r["day"])),
                    name=r["name"],
                    worker=r["worker"],
                    status=TaskStatus(str(r["status"])),
                    count=int(r["count"]),
                )
            )
        return out


class TaskService:
    def __init__(
        self,
        tasks: TaskRepository,
        workers: WorkerRepository,
        stats: StatsRepository,
        bus: EventBus,
        *,
        worker_offline_after: timedelta = timedelta(seconds=30),
        orphan_after: timedelta = timedelta(minutes=10),
    ) -> None:
        self._tasks = tasks
        self._workers = workers
        self._stats = stats
        self._bus = bus
        self._worker_offline_after = worker_offline_after
        self._orphan_after = orphan_after

    def ingest_task_event(self, ev: TaskEvent) -> TaskRecord:
        if not ev.task_id or not isinstance(ev.task_id, str):
            raise ValidationError("task_id is required")
        if not ev.name or not isinstance(ev.name, str):
            raise ValidationError("name is required")
        if not isinstance(ev.status, TaskStatus):
            raise ValidationError("status is required")
        ts = _to_utc(ev.timestamp)
        ev = TaskEvent(
            task_id=ev.task_id,
            name=ev.name,
            status=ev.status,
            worker=ev.worker,
            timestamp=ts,
            args=ev.args,
            kwargs=ev.kwargs,
            result=ev.result,
            exception=ev.exception,
            traceback=ev.traceback,
            retries=int(ev.retries),
        )

        rec = self._tasks.upsert_task_from_event(ev)
        self._stats.increment_daily(
            day=ts.date(),
            name=rec.name,
            worker=rec.worker,
            status=rec.status,
            delta=1,
        )
        self._bus.publish(
            {
                "type": "task_event",
                "task": self._task_to_dict(rec),
                "event": self._task_event_to_dict(ev),
            }
        )
        return rec

    def ingest_worker_heartbeat(self, hb: WorkerHeartbeat) -> WorkerRecord:
        if not hb.worker or not isinstance(hb.worker, str):
            raise ValidationError("worker is required")
        ts = _to_utc(hb.timestamp)
        hb = WorkerHeartbeat(worker=hb.worker, timestamp=ts)
        rec = self._workers.upsert_heartbeat(hb, self._worker_offline_after)
        self._bus.publish({"type": "worker_heartbeat", "worker": self._worker_to_dict(rec)})
        return rec

    def refresh_worker_health(self) -> int:
        n = self._workers.refresh_offline(self._worker_offline_after)
        if n:
            self._bus.publish({"type": "worker_health_refresh", "changed": n})
        return n

    def detect_orphans(self) -> int:
        cutoff = _utcnow() - self._orphan_after
        candidates = self._tasks.list_active_tasks_older_than(cutoff)
        to_mark = [t.task_id for t in candidates if not t.orphaned]
        n = self._tasks.mark_orphaned(to_mark, True) if to_mark else 0
        if n:
            self._bus.publish({"type": "orphan_detection", "marked": n})
        return n

    def retry_task(self, task_id: str) -> TaskRecord:
        existing = self._tasks.get_task(task_id)
        ev = TaskEvent(
            task_id=existing.task_id,
            name=existing.name,
            status=TaskStatus.RETRY,
            worker=existing.worker,
            timestamp=_utcnow(),
            args=existing.args,
            kwargs=existing.kwargs,
            result=None,
            exception=None,
            traceback=None,
            retries=existing.retries + 1,
        )
        return self.ingest_task_event(ev)

    def search_tasks(
        self,
        *,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[TaskStatus] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        full_text: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
    ) -> List[TaskRecord]:
        return self._tasks.search_tasks(
            date_from=date_from,
            date_to=date_to,
            status=status,
            name=name,
            worker=worker,
            full_text=full_text,
            limit=limit,
            offset=offset,
        )

    def get_task(self, task_id: str) -> TaskRecord:
        return self._tasks.get_task(task_id)

    def list_task_events(self, task_id: str, limit: int = 200) -> List[TaskEvent]:
        return self._tasks.list_task_events(task_id, limit=limit)

    def list_workers(self) -> List[WorkerRecord]:
        self.refresh_worker_health()
        return self._workers.list_workers()

    def list_daily_stats(
        self,
        *,
        day_from: Optional[date] = None,
        day_to: Optional[date] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[DailyStat]:
        return self._stats.list_daily(
            day_from=day_from,
            day_to=day_to,
            name=name,
            worker=worker,
            status=status,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    def _task_to_dict(t: TaskRecord) -> Dict[str, Any]:
        return {
            "task_id": t.task_id,
            "name": t.name,
            "status": t.status.value,
            "worker": t.worker,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "finished_at": t.finished_at.isoformat() if t.finished_at else None,
            "retries": t.retries,
            "args": t.args,
            "kwargs": t.kwargs,
            "result": t.result,
            "exception": t.exception,
            "traceback": t.traceback,
            "orphaned": t.orphaned,
        }

    @staticmethod
    def _worker_to_dict(w: WorkerRecord) -> Dict[str, Any]:
        return {
            "worker": w.worker,
            "status": w.status.value,
            "last_heartbeat_at": w.last_heartbeat_at.isoformat() if w.last_heartbeat_at else None,
            "first_seen_at": w.first_seen_at.isoformat(),
            "updated_at": w.updated_at.isoformat(),
        }

    @staticmethod
    def _task_event_to_dict(e: TaskEvent) -> Dict[str, Any]:
        return {
            "task_id": e.task_id,
            "name": e.name,
            "status": e.status.value,
            "worker": e.worker,
            "timestamp": e.timestamp.isoformat(),
            "args": e.args,
            "kwargs": e.kwargs,
            "result": e.result,
            "exception": e.exception,
            "traceback": e.traceback,
            "retries": e.retries,
        }


class WebSocketServer:
    def __init__(self, bus: EventBus, host: str = "127.0.0.1", port: int = 8765) -> None:
        self._bus = bus
        self._host = host
        self._port = port
        self._clients_lock = asyncio.Lock()
        self._clients: Set[Any] = set()
        self._server: Any = None
        self._unsub: Optional[Callable[[], None]] = None

    async def start(self) -> None:
        if websockets is None:
            raise RuntimeError("websockets package is required to run WebSocketServer")
        self._unsub = self._bus.subscribe(self._on_bus_event)
        self._server = await websockets.serve(self._handler, self._host, self._port)

    async def stop(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        async with self._clients_lock:
            clients = list(self._clients)
            self._clients.clear()
        for ws in clients:
            try:
                await ws.close()
            except Exception:
                pass

    async def _handler(self, websocket: Any, path: str) -> None:
        parsed = urlparse(path)
        qs = parse_qs(parsed.query)
        types = set()
        if "types" in qs and qs["types"]:
            for part in ",".join(qs["types"]).split(","):
                p = part.strip()
                if p:
                    types.add(p)

        async with self._clients_lock:
            self._clients.add((websocket, frozenset(types)))

        try:
            await websocket.send(json.dumps({"type": "hello", "server_time": _utcnow().isoformat()}))
            async for _ in websocket:
                pass
        finally:
            async with self._clients_lock:
                self._clients.discard((websocket, frozenset(types)))

    def _on_bus_event(self, event: Dict[str, Any]) -> None:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._broadcast(event))
        except RuntimeError:
            pass

    async def _broadcast(self, event: Dict[str, Any]) -> None:
        payload = json.dumps(event, default=str)
        etype = str(event.get("type", ""))
        async with self._clients_lock:
            clients = list(self._clients)
        to_remove: List[Tuple[Any, frozenset[str]]] = []
        for ws, types in clients:
            if types and etype not in types:
                continue
            try:
                await ws.send(payload)
            except Exception:
                to_remove.append((ws, types))
        if to_remove:
            async with self._clients_lock:
                for item in to_remove:
                    self._clients.discard(item)


class KanchiApp:
    def __init__(
        self,
        *,
        db_path: str = "kanchi.db",
        ws_host: str = "127.0.0.1",
        ws_port: int = 8765,
        worker_offline_after_seconds: int = 30,
        orphan_after_seconds: int = 600,
    ) -> None:
        self._db = Database(db_path)
        self._migrations = MigrationManager(self._db)
        self._migrations.migrate()

        self._bus = EventBus()
        self._tasks = TaskRepository(self._db)
        self._workers = WorkerRepository(self._db)
        self._stats = StatsRepository(self._db)
        self._service = TaskService(
            self._tasks,
            self._workers,
            self._stats,
            self._bus,
            worker_offline_after=timedelta(seconds=int(worker_offline_after_seconds)),
            orphan_after=timedelta(seconds=int(orphan_after_seconds)),
        )
        self._ws = WebSocketServer(self._bus, host=ws_host, port=int(ws_port))
        self._bg_task: Optional[asyncio.Task[None]] = None
        self._running = False

    @property
    def service(self) -> TaskService:
        return self._service

    @property
    def bus(self) -> EventBus:
        return self._bus

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        await self._ws.start()
        self._bg_task = asyncio.create_task(self._background_loop())

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._bg_task is not None:
            self._bg_task.cancel()
            try:
                await self._bg_task
            except Exception:
                pass
            self._bg_task = None
        await self._ws.stop()
        self._db.close()

    async def _background_loop(self) -> None:
        while self._running:
            try:
                self._service.refresh_worker_health()
                self._service.detect_orphans()
            except Exception:
                pass
            await asyncio.sleep(5.0)


def _parse_status(s: Optional[str]) -> Optional[TaskStatus]:
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    return TaskStatus(s)


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    dt = datetime.fromisoformat(s)
    return _to_utc(dt)


def _parse_date(s: Optional[str]) -> Optional[date]:
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    return date.fromisoformat(s)


class SimpleHTTPAPI:
    def __init__(self, app: KanchiApp, host: str = "127.0.0.1", port: int = 8000) -> None:
        self._app = app
        self._host = host
        self._port = port
        self._server: Optional[asyncio.base_events.Server] = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle, self._host, self._port)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            data = await reader.readuntil(b"\r\n\r\n")
        except Exception:
            writer.close()
            return

        header = data.decode("utf-8", errors="ignore")
        first = header.split("\r\n", 1)[0]
        parts = first.split()
        if len(parts) < 2:
            await self._send(writer, 400, {"error": "bad request"})
            return
        method, target = parts[0].upper(), parts[1]
        parsed = urlparse(target)
        path = parsed.path
        qs = parse_qs(parsed.query)

        body = b""
        content_length = 0
        for line in header.split("\r\n")[1:]:
            if not line:
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                if k.strip().lower() == "content-length":
                    try:
                        content_length = int(v.strip())
                    except Exception:
                        content_length = 0
        if content_length > 0:
            body = await reader.readexactly(content_length)

        try:
            if method == "GET" and path == "/health":
                await self._send(writer, 200, {"status": "ok", "time": _utcnow().isoformat()})
                return

            if method == "POST" and path == "/ingest/task":
                payload = json.loads(body.decode("utf-8") or "{}")
                ev = TaskEvent(
                    task_id=str(payload["task_id"]),
                    name=str(payload["name"]),
                    status=TaskStatus(str(payload["status"])),
                    worker=payload.get("worker"),
                    timestamp=_parse_dt(payload.get("timestamp")) or _utcnow(),
                    args=payload.get("args"),
                    kwargs=payload.get("kwargs"),
                    result=payload.get("result"),
                    exception=payload.get("exception"),
                    traceback=payload.get("traceback"),
                    retries=int(payload.get("retries") or 0),
                )
                rec = self._app.service.ingest_task_event(ev)
                await self._send(writer, 200, {"task": TaskService._task_to_dict(rec)})
                return

            if method == "POST" and path == "/ingest/heartbeat":
                payload = json.loads(body.decode("utf-8") or "{}")
                hb = WorkerHeartbeat(
                    worker=str(payload["worker"]),
                    timestamp=_parse_dt(payload.get("timestamp")) or _utcnow(),
                )
                rec = self._app.service.ingest_worker_heartbeat(hb)
                await self._send(writer, 200, {"worker": TaskService._worker_to_dict(rec)})
                return

            if method == "POST" and path.startswith("/tasks/") and path.endswith("/retry"):
                task_id = path.split("/")[2]
                rec = self._app.service.retry_task(task_id)
                await self._send(writer, 200, {"task": TaskService._task_to_dict(rec)})
                return

            if method == "GET" and path == "/tasks":
                date_from = _parse_dt(qs.get("from", [None])[0])
                date_to = _parse_dt(qs.get("to", [None])[0])
                status = _parse_status(qs.get("status", [None])[0])
                name = qs.get("name", [None])[0]
                worker = qs.get("worker", [None])[0]
                full_text = qs.get("q", [None])[0]
                limit = int(qs.get("limit", ["200"])[0])
                offset = int(qs.get("offset", ["0"])[0])
                tasks = self._app.service.search_tasks(
                    date_from=date_from,
                    date_to=date_to,
                    status=status,
                    name=name,
                    worker=worker,
                    full_text=full_text,
                    limit=limit,
                    offset=offset,
                )
                await self._send(writer, 200, {"tasks": [TaskService._task_to_dict(t) for t in tasks]})
                return

            if method == "GET" and path.startswith("/tasks/") and path.count("/") == 2:
                task_id = path.split("/")[2]
                rec = self._app.service.get_task(task_id)
                await self._send(writer, 200, {"task": TaskService._task_to_dict(rec)})
                return

            if method == "GET" and path.startswith("/tasks/") and path.endswith("/events"):
                task_id = path.split("/")[2]
                limit = int(qs.get("limit", ["200"])[0])
                events = self._app.service.list_task_events(task_id, limit=limit)
                await self._send(writer, 200, {"events": [TaskService._task_event_to_dict(e) for e in events]})
                return

            if method == "GET" and path == "/workers":
                workers = self._app.service.list_workers()
                await self._send(writer, 200, {"workers": [TaskService._worker_to_dict(w) for w in workers]})
                return

            if method == "GET" and path == "/stats/daily":
                day_from = _parse_date(qs.get("from", [None])[0])
                day_to = _parse_date(qs.get("to", [None])[0])
                name = qs.get("name", [None])[0]
                worker = qs.get("worker", [None])[0]
                status = _parse_status(qs.get("status", [None])[0])
                limit = int(qs.get("limit", ["1000"])[0])
                offset = int(qs.get("offset", ["0"])[0])
                stats = self._app.service.list_daily_stats(
                    day_from=day_from,
                    day_to=day_to,
                    name=name,
                    worker=worker,
                    status=status,
                    limit=limit,
                    offset=offset,
                )
                await self._send(
                    writer,
                    200,
                    {
                        "stats": [
                            {
                                "day": s.day.isoformat(),
                                "name": s.name,
                                "worker": s.worker,
                                "status": s.status.value,
                                "count": s.count,
                            }
                            for s in stats
                        ]
                    },
                )
                return

            await self._send(writer, 404, {"error": "not found"})
        except NotFoundError as e:
            await self._send(writer, 404, {"error": str(e)})
        except ValidationError as e:
            await self._send(writer, 400, {"error": str(e)})
        except Exception:
            await self._send(writer, 500, {"error": "internal error"})

    async def _send(self, writer: asyncio.StreamWriter, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        reason = {
            200: "OK",
            400: "Bad Request",
            404: "Not Found",
            500: "Internal Server Error",
        }.get(status, "OK")
        headers = [
            f"HTTP/1.1 {status} {reason}",
            "Content-Type: application/json; charset=utf-8",
            f"Content-Length: {len(body)}",
            "Connection: close",
            "",
            "",
        ]
        writer.write("\r\n".join(headers).encode("utf-8") + body)
        try:
            await writer.drain()
        finally:
            writer.close()


async def run_server(
    *,
    db_path: str = "kanchi.db",
    ws_host: str = "127.0.0.1",
    ws_port: int = 8765,
    http_host: str = "127.0.0.1",
    http_port: int = 8000,
) -> None:
    app = KanchiApp(db_path=db_path, ws_host=ws_host, ws_port=ws_port)
    api = SimpleHTTPAPI(app, host=http_host, port=http_port)
    await app.start()
    await api.start()
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await api.stop()
        await app.stop()


def main() -> None:
    asyncio.run(run_server())


if __name__ == "__main__":
    main()