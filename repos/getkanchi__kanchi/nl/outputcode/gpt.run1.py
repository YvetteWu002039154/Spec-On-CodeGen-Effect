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

from wsgiref.simple_server import make_server, WSGIServer, WSGIRequestHandler


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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _parse_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _date_from_dt(dt: datetime) -> date:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date()


def _ensure_non_empty(s: str, field: str) -> str:
    if not isinstance(s, str) or not s.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return s.strip()


def _ensure_int_ge(n: int, min_value: int, field: str) -> int:
    if not isinstance(n, int) or n < min_value:
        raise ValueError(f"{field} must be an int >= {min_value}")
    return n


def _ensure_dt(dt: datetime, field: str) -> datetime:
    if not isinstance(dt, datetime):
        raise ValueError(f"{field} must be a datetime")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class TaskEvent:
    task_id: str
    event_type: str
    status: TaskStatus
    timestamp: datetime
    worker: Optional[str]
    name: Optional[str]
    message: Optional[str]
    retry_count: Optional[int]


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
    retry_count: int
    last_message: Optional[str]
    orphaned: bool


@dataclass(frozen=True)
class WorkerRecord:
    worker_id: str
    hostname: str
    status: WorkerStatus
    last_heartbeat: datetime
    last_seen: datetime
    active_tasks: int


@dataclass(frozen=True)
class DailyStat:
    day: date
    total: int
    success: int
    failure: int
    retry: int
    revoked: int
    started: int
    pending: int
    received: int
    orphaned: int


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

    def executemany(self, sql: str, seq: Iterable[Tuple[Any, ...]]) -> None:
        with self._lock:
            self._conn.executemany(sql, list(seq))
            self._conn.commit()

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
                self._db.execute("UPDATE schema_version SET version=1")
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
                retry_count INTEGER NOT NULL DEFAULT 0,
                last_message TEXT,
                orphaned INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS task_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                status TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                worker TEXT,
                name TEXT,
                message TEXT,
                retry_count INTEGER,
                FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            )
            """
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_task_events_task_id_ts ON task_events(task_id, timestamp)"
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_status_updated ON tasks(status, updated_at)"
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_name ON tasks(name)"
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker)"
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS workers (
                worker_id TEXT PRIMARY KEY,
                hostname TEXT NOT NULL,
                status TEXT NOT NULL,
                last_heartbeat TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                active_tasks INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_workers_status_seen ON workers(status, last_seen)"
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_stats (
                day TEXT PRIMARY KEY,
                total INTEGER NOT NULL,
                success INTEGER NOT NULL,
                failure INTEGER NOT NULL,
                retry INTEGER NOT NULL,
                revoked INTEGER NOT NULL,
                started INTEGER NOT NULL,
                pending INTEGER NOT NULL,
                received INTEGER NOT NULL,
                orphaned INTEGER NOT NULL
            )
            """
        )


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: Set[Callable[[Dict[str, Any]], None]] = set()

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> Callable[[], None]:
        with self._lock:
            self._subscribers.add(callback)

        def unsubscribe() -> None:
            with self._lock:
                self._subscribers.discard(callback)

        return unsubscribe

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

    def upsert_task(
        self,
        task_id: str,
        name: str,
        status: TaskStatus,
        worker: Optional[str],
        timestamp: datetime,
        message: Optional[str],
        retry_count: Optional[int],
        started_at: Optional[datetime],
        finished_at: Optional[datetime],
        orphaned: Optional[bool],
    ) -> None:
        task_id = _ensure_non_empty(task_id, "task_id")
        name = _ensure_non_empty(name, "name")
        timestamp = _ensure_dt(timestamp, "timestamp")
        if worker is not None:
            worker = worker.strip() or None
        if message is not None:
            message = str(message)
        if retry_count is not None:
            _ensure_int_ge(retry_count, 0, "retry_count")
        if started_at is not None:
            started_at = _ensure_dt(started_at, "started_at")
        if finished_at is not None:
            finished_at = _ensure_dt(finished_at, "finished_at")

        row = self._db.query_one("SELECT task_id, created_at, retry_count FROM tasks WHERE task_id=?", (task_id,))
        if row is None:
            created_at = timestamp
            rc = retry_count if retry_count is not None else 0
            self._db.execute(
                """
                INSERT INTO tasks(task_id, name, status, worker, created_at, updated_at, started_at, finished_at, retry_count, last_message, orphaned)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    task_id,
                    name,
                    status.value,
                    worker,
                    _to_iso(created_at),
                    _to_iso(timestamp),
                    _to_iso(started_at) if started_at else None,
                    _to_iso(finished_at) if finished_at else None,
                    rc,
                    message,
                    1 if (orphaned is True) else 0,
                ),
            )
        else:
            created_at = _parse_iso(row["created_at"])
            current_rc = int(row["retry_count"])
            rc = current_rc
            if retry_count is not None:
                rc = max(current_rc, retry_count)
            self._db.execute(
                """
                UPDATE tasks
                SET name=?,
                    status=?,
                    worker=?,
                    updated_at=?,
                    started_at=COALESCE(started_at, ?),
                    finished_at=COALESCE(finished_at, ?),
                    retry_count=?,
                    last_message=?,
                    orphaned=CASE WHEN ? IS NULL THEN orphaned ELSE ? END
                WHERE task_id=?
                """,
                (
                    name,
                    status.value,
                    worker,
                    _to_iso(timestamp),
                    _to_iso(started_at) if started_at else None,
                    _to_iso(finished_at) if finished_at else None,
                    rc,
                    message,
                    None if orphaned is None else (1 if orphaned else 0),
                    None if orphaned is None else (1 if orphaned else 0),
                    task_id,
                ),
            )

    def insert_event(self, ev: TaskEvent) -> None:
        self._db.execute(
            """
            INSERT INTO task_events(task_id, event_type, status, timestamp, worker, name, message, retry_count)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                ev.task_id,
                ev.event_type,
                ev.status.value,
                _to_iso(ev.timestamp),
                ev.worker,
                ev.name,
                ev.message,
                ev.retry_count,
            ),
        )

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        task_id = _ensure_non_empty(task_id, "task_id")
        row = self._db.query_one("SELECT * FROM tasks WHERE task_id=?", (task_id,))
        if row is None:
            return None
        return self._row_to_task(row)

    def list_tasks(
        self,
        *,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        status: Optional[TaskStatus] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        text: Optional[str] = None,
        orphaned: Optional[bool] = None,
        limit: int = 200,
        offset: int = 0,
        order_desc: bool = True,
    ) -> List[TaskRecord]:
        _ensure_int_ge(limit, 1, "limit")
        _ensure_int_ge(offset, 0, "offset")
        clauses: List[str] = []
        params: List[Any] = []

        if start is not None:
            start = _ensure_dt(start, "start")
            clauses.append("updated_at >= ?")
            params.append(_to_iso(start))
        if end is not None:
            end = _ensure_dt(end, "end")
            clauses.append("updated_at <= ?")
            params.append(_to_iso(end))
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if name is not None and name.strip():
            clauses.append("name = ?")
            params.append(name.strip())
        if worker is not None and worker.strip():
            clauses.append("worker = ?")
            params.append(worker.strip())
        if orphaned is not None:
            clauses.append("orphaned = ?")
            params.append(1 if orphaned else 0)
        if text is not None and str(text).strip():
            t = f"%{str(text).strip()}%"
            clauses.append("(task_id LIKE ? OR name LIKE ? OR worker LIKE ? OR COALESCE(last_message,'') LIKE ?)")
            params.extend([t, t, t, t])

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        order = "DESC" if order_desc else "ASC"
        sql = f"SELECT * FROM tasks {where} ORDER BY updated_at {order} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self._db.query(sql, tuple(params))
        return [self._row_to_task(r) for r in rows]

    def list_events(self, task_id: str, limit: int = 200) -> List[TaskEvent]:
        task_id = _ensure_non_empty(task_id, "task_id")
        _ensure_int_ge(limit, 1, "limit")
        rows = self._db.query(
            "SELECT task_id, event_type, status, timestamp, worker, name, message, retry_count FROM task_events WHERE task_id=? ORDER BY timestamp ASC LIMIT ?",
            (task_id, limit),
        )
        out: List[TaskEvent] = []
        for r in rows:
            out.append(
                TaskEvent(
                    task_id=r["task_id"],
                    event_type=r["event_type"],
                    status=TaskStatus(r["status"]),
                    timestamp=_parse_iso(r["timestamp"]),
                    worker=r["worker"],
                    name=r["name"],
                    message=r["message"],
                    retry_count=r["retry_count"] if r["retry_count"] is not None else None,
                )
            )
        return out

    def mark_orphaned(self, task_id: str, orphaned: bool, timestamp: datetime) -> None:
        task_id = _ensure_non_empty(task_id, "task_id")
        timestamp = _ensure_dt(timestamp, "timestamp")
        self._db.execute(
            "UPDATE tasks SET orphaned=?, updated_at=? WHERE task_id=?",
            (1 if orphaned else 0, _to_iso(timestamp), task_id),
        )

    def _row_to_task(self, row: sqlite3.Row) -> TaskRecord:
        return TaskRecord(
            task_id=row["task_id"],
            name=row["name"],
            status=TaskStatus(row["status"]),
            worker=row["worker"],
            created_at=_parse_iso(row["created_at"]),
            updated_at=_parse_iso(row["updated_at"]),
            started_at=_parse_iso(row["started_at"]) if row["started_at"] else None,
            finished_at=_parse_iso(row["finished_at"]) if row["finished_at"] else None,
            retry_count=int(row["retry_count"]),
            last_message=row["last_message"],
            orphaned=bool(row["orphaned"]),
        )


class WorkerRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert_worker(
        self,
        worker_id: str,
        hostname: str,
        status: WorkerStatus,
        heartbeat_at: datetime,
        active_tasks: int,
    ) -> None:
        worker_id = _ensure_non_empty(worker_id, "worker_id")
        hostname = _ensure_non_empty(hostname, "hostname")
        heartbeat_at = _ensure_dt(heartbeat_at, "heartbeat_at")
        _ensure_int_ge(active_tasks, 0, "active_tasks")

        row = self._db.query_one("SELECT worker_id FROM workers WHERE worker_id=?", (worker_id,))
        if row is None:
            self._db.execute(
                """
                INSERT INTO workers(worker_id, hostname, status, last_heartbeat, last_seen, active_tasks)
                VALUES(?,?,?,?,?,?)
                """,
                (worker_id, hostname, status.value, _to_iso(heartbeat_at), _to_iso(heartbeat_at), active_tasks),
            )
        else:
            self._db.execute(
                """
                UPDATE workers
                SET hostname=?,
                    status=?,
                    last_heartbeat=?,
                    last_seen=?,
                    active_tasks=?
                WHERE worker_id=?
                """,
                (hostname, status.value, _to_iso(heartbeat_at), _to_iso(heartbeat_at), active_tasks, worker_id),
            )

    def set_worker_status(self, worker_id: str, status: WorkerStatus, seen_at: datetime) -> None:
        worker_id = _ensure_non_empty(worker_id, "worker_id")
        seen_at = _ensure_dt(seen_at, "seen_at")
        self._db.execute(
            "UPDATE workers SET status=?, last_seen=? WHERE worker_id=?",
            (status.value, _to_iso(seen_at), worker_id),
        )

    def list_workers(self) -> List[WorkerRecord]:
        rows = self._db.query("SELECT * FROM workers ORDER BY worker_id ASC")
        out: List[WorkerRecord] = []
        for r in rows:
            out.append(
                WorkerRecord(
                    worker_id=r["worker_id"],
                    hostname=r["hostname"],
                    status=WorkerStatus(r["status"]),
                    last_heartbeat=_parse_iso(r["last_heartbeat"]),
                    last_seen=_parse_iso(r["last_seen"]),
                    active_tasks=int(r["active_tasks"]),
                )
            )
        return out

    def get_worker(self, worker_id: str) -> Optional[WorkerRecord]:
        worker_id = _ensure_non_empty(worker_id, "worker_id")
        r = self._db.query_one("SELECT * FROM workers WHERE worker_id=?", (worker_id,))
        if r is None:
            return None
        return WorkerRecord(
            worker_id=r["worker_id"],
            hostname=r["hostname"],
            status=WorkerStatus(r["status"]),
            last_heartbeat=_parse_iso(r["last_heartbeat"]),
            last_seen=_parse_iso(r["last_seen"]),
            active_tasks=int(r["active_tasks"]),
        )


class StatsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert_daily(self, stat: DailyStat) -> None:
        self._db.execute(
            """
            INSERT INTO daily_stats(day, total, success, failure, retry, revoked, started, pending, received, orphaned)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(day) DO UPDATE SET
                total=excluded.total,
                success=excluded.success,
                failure=excluded.failure,
                retry=excluded.retry,
                revoked=excluded.revoked,
                started=excluded.started,
                pending=excluded.pending,
                received=excluded.received,
                orphaned=excluded.orphaned
            """,
            (
                stat.day.isoformat(),
                stat.total,
                stat.success,
                stat.failure,
                stat.retry,
                stat.revoked,
                stat.started,
                stat.pending,
                stat.received,
                stat.orphaned,
            ),
        )

    def get_daily(self, day: date) -> Optional[DailyStat]:
        r = self._db.query_one("SELECT * FROM daily_stats WHERE day=?", (day.isoformat(),))
        if r is None:
            return None
        return DailyStat(
            day=date.fromisoformat(r["day"]),
            total=int(r["total"]),
            success=int(r["success"]),
            failure=int(r["failure"]),
            retry=int(r["retry"]),
            revoked=int(r["revoked"]),
            started=int(r["started"]),
            pending=int(r["pending"]),
            received=int(r["received"]),
            orphaned=int(r["orphaned"]),
        )

    def list_daily(self, start_day: date, end_day: date) -> List[DailyStat]:
        rows = self._db.query(
            "SELECT * FROM daily_stats WHERE day>=? AND day<=? ORDER BY day ASC",
            (start_day.isoformat(), end_day.isoformat()),
        )
        out: List[DailyStat] = []
        for r in rows:
            out.append(
                DailyStat(
                    day=date.fromisoformat(r["day"]),
                    total=int(r["total"]),
                    success=int(r["success"]),
                    failure=int(r["failure"]),
                    retry=int(r["retry"]),
                    revoked=int(r["revoked"]),
                    started=int(r["started"]),
                    pending=int(r["pending"]),
                    received=int(r["received"]),
                    orphaned=int(r["orphaned"]),
                )
            )
        return out


class TaskService:
    def __init__(self, tasks: TaskRepository, workers: WorkerRepository, stats: StatsRepository, bus: EventBus) -> None:
        self._tasks = tasks
        self._workers = workers
        self._stats = stats
        self._bus = bus

    def ingest_task_event(
        self,
        *,
        task_id: str,
        name: str,
        status: TaskStatus,
        timestamp: Optional[datetime] = None,
        worker: Optional[str] = None,
        message: Optional[str] = None,
        retry_count: Optional[int] = None,
        event_type: str = "STATE",
    ) -> None:
        task_id = _ensure_non_empty(task_id, "task_id")
        name = _ensure_non_empty(name, "name")
        if timestamp is None:
            timestamp = _utcnow()
        timestamp = _ensure_dt(timestamp, "timestamp")
        event_type = _ensure_non_empty(event_type, "event_type")

        started_at: Optional[datetime] = None
        finished_at: Optional[datetime] = None
        if status == TaskStatus.STARTED:
            started_at = timestamp
        if status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED):
            finished_at = timestamp

        if status == TaskStatus.RETRY and retry_count is None:
            existing = self._tasks.get_task(task_id)
            retry_count = (existing.retry_count + 1) if existing else 1

        self._tasks.upsert_task(
            task_id=task_id,
            name=name,
            status=status,
            worker=worker,
            timestamp=timestamp,
            message=message,
            retry_count=retry_count,
            started_at=started_at,
            finished_at=finished_at,
            orphaned=False,
        )

        ev = TaskEvent(
            task_id=task_id,
            event_type=event_type,
            status=status,
            timestamp=timestamp,
            worker=worker.strip() if isinstance(worker, str) and worker.strip() else None,
            name=name,
            message=str(message) if message is not None else None,
            retry_count=retry_count,
        )
        self._tasks.insert_event(ev)

        self._bus.publish(
            {
                "type": "task_event",
                "task_id": task_id,
                "name": name,
                "status": status.value,
                "timestamp": _to_iso(timestamp),
                "worker": ev.worker,
                "message": ev.message,
                "retry_count": ev.retry_count,
                "event_type": event_type,
            }
        )

    def record_worker_heartbeat(
        self,
        *,
        worker_id: str,
        hostname: str,
        timestamp: Optional[datetime] = None,
        active_tasks: int = 0,
        status: WorkerStatus = WorkerStatus.ONLINE,
    ) -> None:
        worker_id = _ensure_non_empty(worker_id, "worker_id")
        hostname = _ensure_non_empty(hostname, "hostname")
        if timestamp is None:
            timestamp = _utcnow()
        timestamp = _ensure_dt(timestamp, "timestamp")
        _ensure_int_ge(active_tasks, 0, "active_tasks")

        self._workers.upsert_worker(worker_id, hostname, status, timestamp, active_tasks)
        self._bus.publish(
            {
                "type": "worker_heartbeat",
                "worker_id": worker_id,
                "hostname": hostname,
                "status": status.value,
                "timestamp": _to_iso(timestamp),
                "active_tasks": active_tasks,
            }
        )

    def retry_task(self, task_id: str, message: Optional[str] = None, timestamp: Optional[datetime] = None) -> None:
        task = self._tasks.get_task(task_id)
        if task is None:
            raise ValueError("task not found")
        if timestamp is None:
            timestamp = _utcnow()
        timestamp = _ensure_dt(timestamp, "timestamp")
        self.ingest_task_event(
            task_id=task.task_id,
            name=task.name,
            status=TaskStatus.RETRY,
            timestamp=timestamp,
            worker=task.worker,
            message=message,
            retry_count=task.retry_count + 1,
            event_type="RETRY",
        )

    def revoke_task(self, task_id: str, message: Optional[str] = None, timestamp: Optional[datetime] = None) -> None:
        task = self._tasks.get_task(task_id)
        if task is None:
            raise ValueError("task not found")
        if timestamp is None:
            timestamp = _utcnow()
        timestamp = _ensure_dt(timestamp, "timestamp")
        self.ingest_task_event(
            task_id=task.task_id,
            name=task.name,
            status=TaskStatus.REVOKED,
            timestamp=timestamp,
            worker=task.worker,
            message=message,
            retry_count=task.retry_count,
            event_type="REVOKE",
        )


class OrphanDetector:
    def __init__(self, tasks: TaskRepository, bus: EventBus, *, orphan_after: timedelta = timedelta(minutes=10)) -> None:
        self._tasks = tasks
        self._bus = bus
        self._orphan_after = orphan_after

    def detect(self, now: Optional[datetime] = None, limit: int = 1000) -> List[str]:
        if now is None:
            now = _utcnow()
        now = _ensure_dt(now, "now")
        _ensure_int_ge(limit, 1, "limit")

        cutoff = now - self._orphan_after
        candidates = self._tasks.list_tasks(
            start=None,
            end=cutoff,
            status=None,
            name=None,
            worker=None,
            text=None,
            orphaned=False,
            limit=limit,
            offset=0,
            order_desc=False,
        )
        orphaned_ids: List[str] = []
        for t in candidates:
            if t.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED):
                continue
            self._tasks.mark_orphaned(t.task_id, True, now)
            orphaned_ids.append(t.task_id)
            self._bus.publish(
                {
                    "type": "task_orphaned",
                    "task_id": t.task_id,
                    "timestamp": _to_iso(now),
                }
            )
        return orphaned_ids


class WorkerHealthMonitor:
    def __init__(
        self,
        workers: WorkerRepository,
        bus: EventBus,
        *,
        offline_after: timedelta = timedelta(seconds=30),
        degraded_after: timedelta = timedelta(seconds=10),
    ) -> None:
        self._workers = workers
        self._bus = bus
        self._offline_after = offline_after
        self._degraded_after = degraded_after

    def evaluate(self, now: Optional[datetime] = None) -> List[Tuple[str, WorkerStatus]]:
        if now is None:
            now = _utcnow()
        now = _ensure_dt(now, "now")
        updates: List[Tuple[str, WorkerStatus]] = []
        for w in self._workers.list_workers():
            age = now - w.last_heartbeat
            new_status = w.status
            if age >= self._offline_after:
                new_status = WorkerStatus.OFFLINE
            elif age >= self._degraded_after:
                new_status = WorkerStatus.DEGRADED
            else:
                new_status = WorkerStatus.ONLINE

            if new_status != w.status:
                self._workers.set_worker_status(w.worker_id, new_status, now)
                updates.append((w.worker_id, new_status))
                self._bus.publish(
                    {
                        "type": "worker_status",
                        "worker_id": w.worker_id,
                        "status": new_status.value,
                        "timestamp": _to_iso(now),
                    }
                )
        return updates


class StatsService:
    def __init__(self, db: Database, stats_repo: StatsRepository) -> None:
        self._db = db
        self._stats_repo = stats_repo

    def compute_daily(self, day: date) -> DailyStat:
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)

        rows = self._db.query(
            """
            SELECT status, COUNT(*) AS c
            FROM tasks
            WHERE updated_at >= ? AND updated_at < ?
            GROUP BY status
            """,
            (_to_iso(start), _to_iso(end)),
        )
        counts: Dict[str, int] = {r["status"]: int(r["c"]) for r in rows}
        orphaned_row = self._db.query_one(
            "SELECT COUNT(*) AS c FROM tasks WHERE orphaned=1 AND updated_at >= ? AND updated_at < ?",
            (_to_iso(start), _to_iso(end)),
        )
        orphaned = int(orphaned_row["c"]) if orphaned_row else 0

        total = sum(counts.values())
        stat = DailyStat(
            day=day,
            total=total,
            success=counts.get(TaskStatus.SUCCESS.value, 0),
            failure=counts.get(TaskStatus.FAILURE.value, 0),
            retry=counts.get(TaskStatus.RETRY.value, 0),
            revoked=counts.get(TaskStatus.REVOKED.value, 0),
            started=counts.get(TaskStatus.STARTED.value, 0),
            pending=counts.get(TaskStatus.PENDING.value, 0),
            received=counts.get(TaskStatus.RECEIVED.value, 0),
            orphaned=orphaned,
        )
        self._stats_repo.upsert_daily(stat)
        return stat

    def compute_range(self, start_day: date, end_day: date) -> List[DailyStat]:
        if end_day < start_day:
            raise ValueError("end_day must be >= start_day")
        out: List[DailyStat] = []
        d = start_day
        while d <= end_day:
            out.append(self.compute_daily(d))
            d = d + timedelta(days=1)
        return out


class WebSocketFrame:
    @staticmethod
    def encode_text(payload: str) -> bytes:
        data = payload.encode("utf-8")
        fin_opcode = 0x81
        length = len(data)
        if length <= 125:
            header = bytes([fin_opcode, length])
        elif length <= 65535:
            header = bytes([fin_opcode, 126]) + length.to_bytes(2, "big")
        else:
            header = bytes([fin_opcode, 127]) + length.to_bytes(8, "big")
        return header + data

    @staticmethod
    def encode_close() -> bytes:
        return bytes([0x88, 0x00])


class WebSocketServer:
    def __init__(self, host: str, port: int, bus: EventBus) -> None:
        self._host = host
        self._port = port
        self._bus = bus
        self._server: Optional[asyncio.base_events.Server] = None
        self._clients_lock = asyncio.Lock()
        self._clients: Set[asyncio.StreamWriter] = set()
        self._unsubscribe: Optional[Callable[[], None]] = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(self._handle_client, self._host, self._port)
        loop = asyncio.get_running_loop()

        def on_event(ev: Dict[str, Any]) -> None:
            payload = json.dumps(ev, separators=(",", ":"), ensure_ascii=False)
            loop.call_soon_threadsafe(asyncio.create_task, self.broadcast(payload))

        self._unsubscribe = self._bus.subscribe(on_event)

    async def stop(self) -> None:
        if self._unsubscribe:
            self._unsubscribe()
            self._unsubscribe = None
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        async with self._clients_lock:
            clients = list(self._clients)
            self._clients.clear()
        for w in clients:
            try:
                w.write(WebSocketFrame.encode_close())
                await w.drain()
            except Exception:
                pass
            try:
                w.close()
            except Exception:
                pass

    async def broadcast(self, payload: str) -> None:
        frame = WebSocketFrame.encode_text(payload)
        async with self._clients_lock:
            clients = list(self._clients)
        dead: List[asyncio.StreamWriter] = []
        for w in clients:
            try:
                w.write(frame)
                await w.drain()
            except Exception:
                dead.append(w)
        if dead:
            async with self._clients_lock:
                for w in dead:
                    self._clients.discard(w)
            for w in dead:
                try:
                    w.close()
                except Exception:
                    pass

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            req = await self._read_http_request(reader)
            if req is None:
                writer.close()
                return
            headers, _ = req
            if headers.get("upgrade", "").lower() != "websocket":
                await self._send_http(writer, 400, b"Bad Request")
                return
            key = headers.get("sec-websocket-key")
            if not key:
                await self._send_http(writer, 400, b"Bad Request")
                return
            accept = self._ws_accept(key)
            resp = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept}\r\n"
                "\r\n"
            ).encode("utf-8")
            writer.write(resp)
            await writer.drain()

            async with self._clients_lock:
                self._clients.add(writer)

            while True:
                frame = await self._read_ws_frame(reader)
                if frame is None:
                    break
                opcode, _payload = frame
                if opcode == 0x8:
                    break
                if opcode == 0x9:
                    pong = bytes([0x8A, 0x00])
                    writer.write(pong)
                    await writer.drain()
        except Exception:
            pass
        finally:
            async with self._clients_lock:
                self._clients.discard(writer)
            try:
                writer.close()
            except Exception:
                pass

    async def _send_http(self, writer: asyncio.StreamWriter, status: int, body: bytes) -> None:
        reason = {400: "Bad Request", 404: "Not Found"}.get(status, "OK")
        resp = (
            f"HTTP/1.1 {status} {reason}\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Content-Type: text/plain\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode("utf-8") + body
        writer.write(resp)
        await writer.drain()
        writer.close()

    async def _read_http_request(self, reader: asyncio.StreamReader) -> Optional[Tuple[Dict[str, str], bytes]]:
        data = b""
        while b"\r\n\r\n" not in data and len(data) < 65536:
            chunk = await reader.read(1024)
            if not chunk:
                return None
            data += chunk
        head, _, rest = data.partition(b"\r\n\r\n")
        lines = head.decode("iso-8859-1").split("\r\n")
        if not lines:
            return None
        headers: Dict[str, str] = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        return headers, rest

    def _ws_accept(self, key: str) -> str:
        import base64
        import hashlib

        GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        sha1 = hashlib.sha1((key + GUID).encode("utf-8")).digest()
        return base64.b64encode(sha1).decode("ascii")

    async def _read_ws_frame(self, reader: asyncio.StreamReader) -> Optional[Tuple[int, bytes]]:
        hdr = await reader.readexactly(2)
        b1, b2 = hdr[0], hdr[1]
        opcode = b1 & 0x0F
        masked = (b2 & 0x80) != 0
        length = b2 & 0x7F
        if length == 126:
            ext = await reader.readexactly(2)
            length = int.from_bytes(ext, "big")
        elif length == 127:
            ext = await reader.readexactly(8)
            length = int.from_bytes(ext, "big")
        mask_key = b""
        if masked:
            mask_key = await reader.readexactly(4)
        payload = await reader.readexactly(length) if length else b""
        if masked and payload:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        return opcode, payload


class APIServer:
    def __init__(self, host: str, port: int, task_repo: TaskRepository, worker_repo: WorkerRepository, stats_repo: StatsRepository, task_service: TaskService, stats_service: StatsService) -> None:
        self._host = host
        self._port = port
        self._task_repo = task_repo
        self._worker_repo = worker_repo
        self._stats_repo = stats_repo
        self._task_service = task_service
        self._stats_service = stats_service
        self._httpd: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        def app(environ: Dict[str, Any], start_response: Callable[..., Any]) -> List[bytes]:
            try:
                method = environ.get("REQUEST_METHOD", "GET").upper()
                path = environ.get("PATH_INFO", "/")
                query = environ.get("QUERY_STRING", "")
                qs = parse_qs(query, keep_blank_values=True)

                if path == "/health":
                    return self._json(start_response, 200, {"ok": True})

                if path == "/tasks" and method == "GET":
                    return self._handle_list_tasks(start_response, qs)

                if path.startswith("/tasks/") and method == "GET":
                    task_id = path.split("/", 2)[2]
                    if task_id.endswith("/events"):
                        task_id = task_id[: -len("/events")]
                        return self._handle_task_events(start_response, task_id, qs)
                    return self._handle_get_task(start_response, task_id)

                if path.startswith("/tasks/") and method == "POST":
                    parts = path.strip("/").split("/")
                    if len(parts) == 3 and parts[0] == "tasks":
                        task_id = parts[1]
                        action = parts[2]
                        body = self._read_json(environ)
                        if action == "retry":
                            self._task_service.retry_task(task_id, message=body.get("message"))
                            return self._json(start_response, 200, {"ok": True})
                        if action == "revoke":
                            self._task_service.revoke_task(task_id, message=body.get("message"))
                            return self._json(start_response, 200, {"ok": True})
                    return self._json(start_response, 404, {"error": "not_found"})

                if path == "/ingest/task_event" and method == "POST":
                    body = self._read_json(environ)
                    self._task_service.ingest_task_event(
                        task_id=body["task_id"],
                        name=body["name"],
                        status=TaskStatus(body["status"]),
                        timestamp=_parse_iso(body["timestamp"]) if "timestamp" in body and body["timestamp"] else None,
                        worker=body.get("worker"),
                        message=body.get("message"),
                        retry_count=body.get("retry_count"),
                        event_type=body.get("event_type", "STATE"),
                    )
                    return self._json(start_response, 200, {"ok": True})

                if path == "/ingest/worker_heartbeat" and method == "POST":
                    body = self._read_json(environ)
                    self._task_service.record_worker_heartbeat(
                        worker_id=body["worker_id"],
                        hostname=body["hostname"],
                        timestamp=_parse_iso(body["timestamp"]) if "timestamp" in body and body["timestamp"] else None,
                        active_tasks=int(body.get("active_tasks", 0)),
                        status=WorkerStatus(body.get("status", WorkerStatus.ONLINE.value)),
                    )
                    return self._json(start_response, 200, {"ok": True})

                if path == "/workers" and method == "GET":
                    workers = self._worker_repo.list_workers()
                    return self._json(start_response, 200, {"workers": [self._worker_to_dict(w) for w in workers]})

                if path == "/stats/daily" and method == "GET":
                    return self._handle_daily_stats(start_response, qs)

                return self._json(start_response, 404, {"error": "not_found"})
            except ValueError as e:
                return self._json(start_response, 400, {"error": "bad_request", "message": str(e)})
            except KeyError as e:
                return self._json(start_response, 400, {"error": "bad_request", "message": f"missing_field:{e.args[0]}"})
            except Exception:
                return self._json(start_response, 500, {"error": "internal_error"})

        self._httpd = make_server(self._host, self._port, app, server_class=WSGIServer, handler_class=WSGIRequestHandler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _read_json(self, environ: Dict[str, Any]) -> Dict[str, Any]:
        try:
            length = int(environ.get("CONTENT_LENGTH") or "0")
        except Exception:
            length = 0
        body = environ["wsgi.input"].read(length) if length > 0 else b"{}"
        if not body:
            return {}
        obj = json.loads(body.decode("utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("JSON body must be an object")
        return obj

    def _json(self, start_response: Callable[..., Any], status: int, obj: Dict[str, Any]) -> List[bytes]:
        data = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        headers = [("Content-Type", "application/json"), ("Content-Length", str(len(data)))]
        start_response(f"{status} OK", headers)
        return [data]

    def _handle_get_task(self, start_response: Callable[..., Any], task_id: str) -> List[bytes]:
        task = self._task_repo.get_task(task_id)
        if task is None:
            return self._json(start_response, 404, {"error": "not_found"})
        return self._json(start_response, 200, {"task": self._task_to_dict(task)})

    def _handle_task_events(self, start_response: Callable[..., Any], task_id: str, qs: Dict[str, List[str]]) -> List[bytes]:
        limit = int(qs.get("limit", ["200"])[0] or "200")
        events = self._task_repo.list_events(task_id, limit=limit)
        return self._json(
            start_response,
            200,
            {"task_id": task_id, "events": [self._event_to_dict(e) for e in events]},
        )

    def _handle_list_tasks(self, start_response: Callable[..., Any], qs: Dict[str, List[str]]) -> List[bytes]:
        def get1(k: str) -> Optional[str]:
            v = qs.get(k)
            if not v:
                return None
            s = v[0]
            return s if s != "" else None

        start_s = get1("start")
        end_s = get1("end")
        status_s = get1("status")
        name = get1("name")
        worker = get1("worker")
        text = get1("text")
        orphaned_s = get1("orphaned")
        limit = int(get1("limit") or "200")
        offset = int(get1("offset") or "0")

        start_dt = _parse_iso(start_s) if start_s else None
        end_dt = _parse_iso(end_s) if end_s else None
        status = TaskStatus(status_s) if status_s else None
        orphaned: Optional[bool] = None
        if orphaned_s is not None:
            if orphaned_s.lower() in ("1", "true", "yes"):
                orphaned = True
            elif orphaned_s.lower() in ("0", "false", "no"):
                orphaned = False
            else:
                raise ValueError("orphaned must be a boolean")

        tasks = self._task_repo.list_tasks(
            start=start_dt,
            end=end_dt,
            status=status,
            name=name,
            worker=worker,
            text=text,
            orphaned=orphaned,
            limit=limit,
            offset=offset,
            order_desc=True,
        )
        return self._json(start_response, 200, {"tasks": [self._task_to_dict(t) for t in tasks]})

    def _handle_daily_stats(self, start_response: Callable[..., Any], qs: Dict[str, List[str]]) -> List[bytes]:
        start_s = (qs.get("start", [None])[0] if qs.get("start") else None)
        end_s = (qs.get("end", [None])[0] if qs.get("end") else None)
        compute = (qs.get("compute", ["0"])[0] or "0").lower() in ("1", "true", "yes")

        if start_s:
            start_day = date.fromisoformat(start_s)
        else:
            start_day = (_utcnow() - timedelta(days=6)).date()
        if end_s:
            end_day = date.fromisoformat(end_s)
        else:
            end_day = _utcnow().date()

        if compute:
            stats = self._stats_service.compute_range(start_day, end_day)
        else:
            stats = self._stats_repo.list_daily(start_day, end_day)
        return self._json(start_response, 200, {"stats": [self._daily_to_dict(s) for s in stats]})

    def _task_to_dict(self, t: TaskRecord) -> Dict[str, Any]:
        return {
            "task_id": t.task_id,
            "name": t.name,
            "status": t.status.value,
            "worker": t.worker,
            "created_at": _to_iso(t.created_at),
            "updated_at": _to_iso(t.updated_at),
            "started_at": _to_iso(t.started_at) if t.started_at else None,
            "finished_at": _to_iso(t.finished_at) if t.finished_at else None,
            "retry_count": t.retry_count,
            "last_message": t.last_message,
            "orphaned": t.orphaned,
        }

    def _event_to_dict(self, e: TaskEvent) -> Dict[str, Any]:
        return {
            "task_id": e.task_id,
            "event_type": e.event_type,
            "status": e.status.value,
            "timestamp": _to_iso(e.timestamp),
            "worker": e.worker,
            "name": e.name,
            "message": e.message,
            "retry_count": e.retry_count,
        }

    def _worker_to_dict(self, w: WorkerRecord) -> Dict[str, Any]:
        return {
            "worker_id": w.worker_id,
            "hostname": w.hostname,
            "status": w.status.value,
            "last_heartbeat": _to_iso(w.last_heartbeat),
            "last_seen": _to_iso(w.last_seen),
            "active_tasks": w.active_tasks,
        }

    def _daily_to_dict(self, s: DailyStat) -> Dict[str, Any]:
        return {
            "day": s.day.isoformat(),
            "total": s.total,
            "success": s.success,
            "failure": s.failure,
            "retry": s.retry,
            "revoked": s.revoked,
            "started": s.started,
            "pending": s.pending,
            "received": s.received,
            "orphaned": s.orphaned,
        }


class Scheduler:
    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._jobs: List[Tuple[float, float, Callable[[], None]]] = []

    def add_job(self, interval_seconds: float, func: Callable[[], None]) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0")
        self._jobs.append((interval_seconds, time.time() + interval_seconds, func))

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _run(self) -> None:
        next_times = [t for _, t, _ in self._jobs]
        while not self._stop.is_set():
            now = time.time()
            sleep_for = 0.5
            for i, (interval, _, func) in enumerate(list(self._jobs)):
                if now >= next_times[i]:
                    try:
                        func()
                    except Exception:
                        pass
                    next_times[i] = now + interval
            time.sleep(sleep_for)


class KanchiApp:
    def __init__(
        self,
        *,
        db_path: str = "kanchi.db",
        api_host: str = "127.0.0.1",
        api_port: int = 8000,
        ws_host: str = "127.0.0.1",
        ws_port: int = 8765,
        orphan_after_seconds: int = 600,
        worker_degraded_after_seconds: int = 10,
        worker_offline_after_seconds: int = 30,
    ) -> None:
        self._db = Database(db_path)
        self._migrations = MigrationManager(self._db)
        self._migrations.migrate()

        self._bus = EventBus()
        self._task_repo = TaskRepository(self._db)
        self._worker_repo = WorkerRepository(self._db)
        self._stats_repo = StatsRepository(self._db)

        self._task_service = TaskService(self._task_repo, self._worker_repo, self._stats_repo, self._bus)
        self._stats_service = StatsService(self._db, self._stats_repo)

        self._orphan_detector = OrphanDetector(self._task_repo, self._bus, orphan_after=timedelta(seconds=orphan_after_seconds))
        self._worker_monitor = WorkerHealthMonitor(
            self._worker_repo,
            self._bus,
            degraded_after=timedelta(seconds=worker_degraded_after_seconds),
            offline_after=timedelta(seconds=worker_offline_after_seconds),
        )

        self._api = APIServer(api_host, api_port, self._task_repo, self._worker_repo, self._stats_repo, self._task_service, self._stats_service)
        self._ws = WebSocketServer(ws_host, ws_port, self._bus)

        self._scheduler = Scheduler()
        self._scheduler.add_job(5.0, self._run_worker_health)
        self._scheduler.add_job(30.0, self._run_orphan_detection)
        self._scheduler.add_job(60.0, self._run_daily_stats)

        self._ws_loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws_thread: Optional[threading.Thread] = None

    @property
    def task_service(self) -> TaskService:
        return self._task_service

    def start(self) -> None:
        self._api.start()
        self._scheduler.start()
        self._start_ws_thread()

    def stop(self) -> None:
        self._scheduler.stop()
        self._api.stop()
        self._stop_ws_thread()
        self._db.close()

    def _run_orphan_detection(self) -> None:
        self._orphan_detector.detect()

    def _run_worker_health(self) -> None:
        self._worker_monitor.evaluate()

    def _run_daily_stats(self) -> None:
        today = _utcnow().date()
        self._stats_service.compute_daily(today)

    def _start_ws_thread(self) -> None:
        if self._ws_thread and self._ws_thread.is_alive():
            return

        def run() -> None:
            loop = asyncio.new_event_loop()
            self._ws_loop = loop
            asyncio.set_event_loop(loop)

            async def main() -> None:
                await self._ws.start()
                while True:
                    await asyncio.sleep(3600)

            try:
                loop.run_until_complete(main())
            except Exception:
                pass
            finally:
                try:
                    loop.run_until_complete(self._ws.stop())
                except Exception:
                    pass
                loop.stop()
                loop.close()

        self._ws_thread = threading.Thread(target=run, daemon=True)
        self._ws_thread.start()

    def _stop_ws_thread(self) -> None:
        loop = self._ws_loop
        if loop and loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(self._ws.stop(), loop).result(timeout=2.0)
            except Exception:
                pass
            try:
                loop.call_soon_threadsafe(loop.stop)
            except Exception:
                pass
        if self._ws_thread:
            self._ws_thread.join(timeout=2.0)
            self._ws_thread = None
        self._ws_loop = None


def main() -> None:
    app = KanchiApp()
    app.start()
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        app.stop()


if __name__ == "__main__":
    main()