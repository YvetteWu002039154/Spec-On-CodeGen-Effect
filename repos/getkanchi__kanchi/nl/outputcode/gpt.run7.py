from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

try:
    import websockets  # type: ignore
except Exception:  # pragma: no cover
    websockets = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _from_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"
    ORPHANED = "ORPHANED"


class WorkerStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


@dataclass(frozen=True)
class TaskEvent:
    task_id: str
    name: str
    status: TaskStatus
    timestamp: datetime
    worker: Optional[str] = None
    args: Optional[str] = None
    kwargs: Optional[str] = None
    result: Optional[str] = None
    exception: Optional[str] = None
    traceback: Optional[str] = None
    retries: int = 0
    eta: Optional[datetime] = None
    expires: Optional[datetime] = None
    parent_id: Optional[str] = None
    root_id: Optional[str] = None


@dataclass(frozen=True)
class WorkerHeartbeat:
    worker: str
    timestamp: datetime


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    name: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    worker: Optional[str]
    args: Optional[str]
    kwargs: Optional[str]
    result: Optional[str]
    exception: Optional[str]
    traceback: Optional[str]
    retries: int
    eta: Optional[datetime]
    expires: Optional[datetime]
    parent_id: Optional[str]
    root_id: Optional[str]
    received_at: Optional[datetime]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    orphaned: bool


@dataclass(frozen=True)
class WorkerRecord:
    worker: str
    status: WorkerStatus
    last_heartbeat_at: Optional[datetime]
    first_seen_at: datetime
    last_seen_at: datetime


@dataclass(frozen=True)
class DailyStat:
    day: date
    total: int
    success: int
    failure: int
    retry: int
    revoked: int
    orphaned: int
    avg_runtime_ms: Optional[float]


class Database:
    def __init__(self, path: str = "kanchi.db") -> None:
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
                cur.execute("INSERT INTO schema_version(version) VALUES (1)")
                self._conn.commit()
            else:
                # Placeholder for future migrations
                pass

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    worker TEXT,
                    args TEXT,
                    kwargs TEXT,
                    result TEXT,
                    exception TEXT,
                    traceback TEXT,
                    retries INTEGER NOT NULL DEFAULT 0,
                    eta TEXT,
                    expires TEXT,
                    parent_id TEXT,
                    root_id TEXT,
                    received_at TEXT,
                    started_at TEXT,
                    finished_at TEXT,
                    orphaned INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_name ON tasks(name)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_orphaned ON tasks(orphaned)")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS task_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    worker TEXT,
                    args TEXT,
                    kwargs TEXT,
                    result TEXT,
                    exception TEXT,
                    traceback TEXT,
                    retries INTEGER NOT NULL DEFAULT 0,
                    eta TEXT,
                    expires TEXT,
                    parent_id TEXT,
                    root_id TEXT,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_task_events_task_id ON task_events(task_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_task_events_timestamp ON task_events(timestamp)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_task_events_status ON task_events(status)")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS workers (
                    worker TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    last_heartbeat_at TEXT,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_workers_last_seen ON workers(last_seen_at)")

            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS worker_heartbeats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    worker TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY(worker) REFERENCES workers(worker) ON DELETE CASCADE
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_worker_heartbeats_worker ON worker_heartbeats(worker)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_worker_heartbeats_timestamp ON worker_heartbeats(timestamp)")

            self._conn.commit()

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            self._conn.commit()
            return cur

    def query(self, sql: str, params: Sequence[Any] = ()) -> List[sqlite3.Row]:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            return cur.fetchall()

    def query_one(self, sql: str, params: Sequence[Any] = ()) -> Optional[sqlite3.Row]:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            return cur.fetchone()


class TaskRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert_task_from_event(self, ev: TaskEvent) -> None:
        now_iso = _to_iso(ev.timestamp)
        existing = self._db.query_one("SELECT task_id, created_at, received_at, started_at, finished_at, retries, orphaned FROM tasks WHERE task_id = ?", (ev.task_id,))
        if existing is None:
            created_at = ev.timestamp
            received_at = ev.timestamp if ev.status == TaskStatus.RECEIVED else None
            started_at = ev.timestamp if ev.status == TaskStatus.STARTED else None
            finished_at = ev.timestamp if ev.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED) else None
            orphaned = 1 if ev.status == TaskStatus.ORPHANED else 0
            self._db.execute(
                """
                INSERT INTO tasks(
                    task_id, name, status, created_at, updated_at, worker, args, kwargs, result,
                    exception, traceback, retries, eta, expires, parent_id, root_id,
                    received_at, started_at, finished_at, orphaned
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ev.task_id,
                    ev.name,
                    ev.status.value,
                    _to_iso(created_at),
                    now_iso,
                    ev.worker,
                    ev.args,
                    ev.kwargs,
                    ev.result,
                    ev.exception,
                    ev.traceback,
                    int(ev.retries),
                    _to_iso(ev.eta) if ev.eta else None,
                    _to_iso(ev.expires) if ev.expires else None,
                    ev.parent_id,
                    ev.root_id,
                    _to_iso(received_at) if received_at else None,
                    _to_iso(started_at) if started_at else None,
                    _to_iso(finished_at) if finished_at else None,
                    orphaned,
                ),
            )
        else:
            created_at = _from_iso(existing["created_at"])
            received_at = _from_iso(existing["received_at"]) if existing["received_at"] else None
            started_at = _from_iso(existing["started_at"]) if existing["started_at"] else None
            finished_at = _from_iso(existing["finished_at"]) if existing["finished_at"] else None
            retries = int(existing["retries"] or 0)
            orphaned = int(existing["orphaned"] or 0)

            if ev.status == TaskStatus.RECEIVED and received_at is None:
                received_at = ev.timestamp
            if ev.status == TaskStatus.STARTED and started_at is None:
                started_at = ev.timestamp
            if ev.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED) and finished_at is None:
                finished_at = ev.timestamp
            if ev.status == TaskStatus.RETRY:
                retries = max(retries, int(ev.retries))
            if ev.status == TaskStatus.ORPHANED:
                orphaned = 1

            self._db.execute(
                """
                UPDATE tasks SET
                    name = ?,
                    status = ?,
                    updated_at = ?,
                    worker = COALESCE(?, worker),
                    args = COALESCE(?, args),
                    kwargs = COALESCE(?, kwargs),
                    result = COALESCE(?, result),
                    exception = COALESCE(?, exception),
                    traceback = COALESCE(?, traceback),
                    retries = ?,
                    eta = COALESCE(?, eta),
                    expires = COALESCE(?, expires),
                    parent_id = COALESCE(?, parent_id),
                    root_id = COALESCE(?, root_id),
                    received_at = ?,
                    started_at = ?,
                    finished_at = ?,
                    orphaned = ?
                WHERE task_id = ?
                """,
                (
                    ev.name,
                    ev.status.value,
                    now_iso,
                    ev.worker,
                    ev.args,
                    ev.kwargs,
                    ev.result,
                    ev.exception,
                    ev.traceback,
                    int(retries),
                    _to_iso(ev.eta) if ev.eta else None,
                    _to_iso(ev.expires) if ev.expires else None,
                    ev.parent_id,
                    ev.root_id,
                    _to_iso(received_at) if received_at else None,
                    _to_iso(started_at) if started_at else None,
                    _to_iso(finished_at) if finished_at else None,
                    int(orphaned),
                    ev.task_id,
                ),
            )

        self._db.execute(
            """
            INSERT INTO task_events(
                task_id, name, status, timestamp, worker, args, kwargs, result, exception, traceback,
                retries, eta, expires, parent_id, root_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ev.task_id,
                ev.name,
                ev.status.value,
                now_iso,
                ev.worker,
                ev.args,
                ev.kwargs,
                ev.result,
                ev.exception,
                ev.traceback,
                int(ev.retries),
                _to_iso(ev.eta) if ev.eta else None,
                _to_iso(ev.expires) if ev.expires else None,
                ev.parent_id,
                ev.root_id,
            ),
        )

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        row = self._db.query_one("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        if row is None:
            return None
        return self._row_to_task(row)

    def _row_to_task(self, row: sqlite3.Row) -> TaskRecord:
        return TaskRecord(
            task_id=row["task_id"],
            name=row["name"],
            status=TaskStatus(row["status"]),
            created_at=_from_iso(row["created_at"]),
            updated_at=_from_iso(row["updated_at"]),
            worker=row["worker"],
            args=row["args"],
            kwargs=row["kwargs"],
            result=row["result"],
            exception=row["exception"],
            traceback=row["traceback"],
            retries=int(row["retries"] or 0),
            eta=_from_iso(row["eta"]) if row["eta"] else None,
            expires=_from_iso(row["expires"]) if row["expires"] else None,
            parent_id=row["parent_id"],
            root_id=row["root_id"],
            received_at=_from_iso(row["received_at"]) if row["received_at"] else None,
            started_at=_from_iso(row["started_at"]) if row["started_at"] else None,
            finished_at=_from_iso(row["finished_at"]) if row["finished_at"] else None,
            orphaned=bool(row["orphaned"]),
        )

    def search_tasks(
        self,
        *,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[TaskStatus] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        full_text: Optional[str] = None,
        orphaned: Optional[bool] = None,
        limit: int = 200,
        offset: int = 0,
        order_desc: bool = True,
    ) -> List[TaskRecord]:
        if limit <= 0 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if offset < 0:
            raise ValueError("offset must be >= 0")

        clauses: List[str] = []
        params: List[Any] = []

        if date_from is not None:
            clauses.append("updated_at >= ?")
            params.append(_to_iso(date_from))
        if date_to is not None:
            clauses.append("updated_at <= ?")
            params.append(_to_iso(date_to))
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if name is not None:
            clauses.append("name = ?")
            params.append(name)
        if worker is not None:
            clauses.append("worker = ?")
            params.append(worker)
        if orphaned is not None:
            clauses.append("orphaned = ?")
            params.append(1 if orphaned else 0)
        if full_text is not None and full_text.strip():
            ft = f"%{full_text.strip()}%"
            clauses.append(
                "("
                "task_id LIKE ? OR name LIKE ? OR COALESCE(worker,'') LIKE ? OR "
                "COALESCE(args,'') LIKE ? OR COALESCE(kwargs,'') LIKE ? OR "
                "COALESCE(result,'') LIKE ? OR COALESCE(exception,'') LIKE ? OR COALESCE(traceback,'') LIKE ?"
                ")"
            )
            params.extend([ft, ft, ft, ft, ft, ft, ft, ft])

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        order = "DESC" if order_desc else "ASC"
        sql = f"SELECT * FROM tasks {where} ORDER BY updated_at {order} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self._db.query(sql, params)
        return [self._row_to_task(r) for r in rows]

    def get_task_events(self, task_id: str, limit: int = 500) -> List[TaskEvent]:
        if limit <= 0 or limit > 5000:
            raise ValueError("limit must be between 1 and 5000")
        rows = self._db.query(
            "SELECT * FROM task_events WHERE task_id = ? ORDER BY timestamp ASC LIMIT ?",
            (task_id, limit),
        )
        out: List[TaskEvent] = []
        for r in rows:
            out.append(
                TaskEvent(
                    task_id=r["task_id"],
                    name=r["name"],
                    status=TaskStatus(r["status"]),
                    timestamp=_from_iso(r["timestamp"]),
                    worker=r["worker"],
                    args=r["args"],
                    kwargs=r["kwargs"],
                    result=r["result"],
                    exception=r["exception"],
                    traceback=r["traceback"],
                    retries=int(r["retries"] or 0),
                    eta=_from_iso(r["eta"]) if r["eta"] else None,
                    expires=_from_iso(r["expires"]) if r["expires"] else None,
                    parent_id=r["parent_id"],
                    root_id=r["root_id"],
                )
            )
        return out

    def mark_orphaned(self, task_id: str, when: Optional[datetime] = None) -> None:
        when = when or _utcnow()
        row = self._db.query_one("SELECT task_id FROM tasks WHERE task_id = ?", (task_id,))
        if row is None:
            return
        self._db.execute(
            "UPDATE tasks SET status = ?, orphaned = 1, updated_at = ? WHERE task_id = ?",
            (TaskStatus.ORPHANED.value, _to_iso(when), task_id),
        )
        task = self.get_task(task_id)
        if task is None:
            return
        self._db.execute(
            """
            INSERT INTO task_events(task_id, name, status, timestamp, worker, args, kwargs, result, exception, traceback, retries, eta, expires, parent_id, root_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.task_id,
                task.name,
                TaskStatus.ORPHANED.value,
                _to_iso(when),
                task.worker,
                task.args,
                task.kwargs,
                task.result,
                task.exception,
                task.traceback,
                int(task.retries),
                _to_iso(task.eta) if task.eta else None,
                _to_iso(task.expires) if task.expires else None,
                task.parent_id,
                task.root_id,
            ),
        )


class WorkerRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def record_heartbeat(self, hb: WorkerHeartbeat, offline_after: timedelta) -> None:
        now_iso = _to_iso(hb.timestamp)
        row = self._db.query_one("SELECT worker, first_seen_at FROM workers WHERE worker = ?", (hb.worker,))
        if row is None:
            self._db.execute(
                "INSERT INTO workers(worker, status, last_heartbeat_at, first_seen_at, last_seen_at) VALUES (?, ?, ?, ?, ?)",
                (hb.worker, WorkerStatus.ONLINE.value, now_iso, now_iso, now_iso),
            )
        else:
            self._db.execute(
                "UPDATE workers SET status = ?, last_heartbeat_at = ?, last_seen_at = ? WHERE worker = ?",
                (WorkerStatus.ONLINE.value, now_iso, now_iso, hb.worker),
            )
        self._db.execute(
            "INSERT INTO worker_heartbeats(worker, timestamp) VALUES (?, ?)",
            (hb.worker, now_iso),
        )
        self.refresh_worker_statuses(hb.timestamp, offline_after)

    def refresh_worker_statuses(self, now: Optional[datetime], offline_after: timedelta) -> None:
        now = now or _utcnow()
        threshold = now - offline_after
        rows = self._db.query("SELECT worker, last_heartbeat_at FROM workers")
        for r in rows:
            last = _from_iso(r["last_heartbeat_at"]) if r["last_heartbeat_at"] else None
            status = WorkerStatus.ONLINE if (last is not None and last >= threshold) else WorkerStatus.OFFLINE
            self._db.execute("UPDATE workers SET status = ? WHERE worker = ?", (status.value, r["worker"]))

    def list_workers(self) -> List[WorkerRecord]:
        rows = self._db.query("SELECT * FROM workers ORDER BY worker ASC")
        out: List[WorkerRecord] = []
        for r in rows:
            out.append(
                WorkerRecord(
                    worker=r["worker"],
                    status=WorkerStatus(r["status"]),
                    last_heartbeat_at=_from_iso(r["last_heartbeat_at"]) if r["last_heartbeat_at"] else None,
                    first_seen_at=_from_iso(r["first_seen_at"]),
                    last_seen_at=_from_iso(r["last_seen_at"]),
                )
            )
        return out

    def get_worker(self, worker: str) -> Optional[WorkerRecord]:
        r = self._db.query_one("SELECT * FROM workers WHERE worker = ?", (worker,))
        if r is None:
            return None
        return WorkerRecord(
            worker=r["worker"],
            status=WorkerStatus(r["status"]),
            last_heartbeat_at=_from_iso(r["last_heartbeat_at"]) if r["last_heartbeat_at"] else None,
            first_seen_at=_from_iso(r["first_seen_at"]),
            last_seen_at=_from_iso(r["last_seen_at"]),
        )


class StatsService:
    def __init__(self, db: Database) -> None:
        self._db = db

    def daily_stats(self, date_from: date, date_to: date) -> List[DailyStat]:
        if date_to < date_from:
            raise ValueError("date_to must be >= date_from")
        start_dt = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
        end_dt = datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

        rows = self._db.query(
            """
            SELECT * FROM tasks
            WHERE finished_at IS NOT NULL AND finished_at >= ? AND finished_at < ?
            """,
            (_to_iso(start_dt), _to_iso(end_dt)),
        )

        by_day: Dict[date, List[TaskRecord]] = {}
        for r in rows:
            tr = TaskRepository(self._db)._row_to_task(r)
            if tr.finished_at is None:
                continue
            d = tr.finished_at.astimezone(timezone.utc).date()
            by_day.setdefault(d, []).append(tr)

        out: List[DailyStat] = []
        cur = date_from
        while cur <= date_to:
            tasks = by_day.get(cur, [])
            total = len(tasks)
            success = sum(1 for t in tasks if t.status == TaskStatus.SUCCESS)
            failure = sum(1 for t in tasks if t.status == TaskStatus.FAILURE)
            retry = sum(1 for t in tasks if t.status == TaskStatus.RETRY)
            revoked = sum(1 for t in tasks if t.status == TaskStatus.REVOKED)
            orphaned = sum(1 for t in tasks if t.orphaned or t.status == TaskStatus.ORPHANED)

            runtimes: List[float] = []
            for t in tasks:
                if t.started_at and t.finished_at:
                    runtimes.append((t.finished_at - t.started_at).total_seconds() * 1000.0)
            avg_runtime_ms = (sum(runtimes) / len(runtimes)) if runtimes else None

            out.append(
                DailyStat(
                    day=cur,
                    total=total,
                    success=success,
                    failure=failure,
                    retry=retry,
                    revoked=revoked,
                    orphaned=orphaned,
                    avg_runtime_ms=avg_runtime_ms,
                )
            )
            cur += timedelta(days=1)
        return out


class OrphanDetector:
    def __init__(self, task_repo: TaskRepository, worker_repo: WorkerRepository) -> None:
        self._task_repo = task_repo
        self._worker_repo = worker_repo

    def detect_and_mark_orphans(
        self,
        *,
        now: Optional[datetime] = None,
        offline_after: timedelta = timedelta(seconds=60),
        orphan_after: timedelta = timedelta(minutes=5),
        limit: int = 500,
    ) -> List[str]:
        if limit <= 0 or limit > 5000:
            raise ValueError("limit must be between 1 and 5000")
        now = now or _utcnow()
        self._worker_repo.refresh_worker_statuses(now, offline_after)

        # Candidates: tasks that started but not finished, not already orphaned
        db = self._task_repo._db
        threshold = now - orphan_after
        rows = db.query(
            """
            SELECT * FROM tasks
            WHERE started_at IS NOT NULL
              AND finished_at IS NULL
              AND orphaned = 0
              AND updated_at <= ?
            ORDER BY updated_at ASC
            LIMIT ?
            """,
            (_to_iso(threshold), limit),
        )

        workers = {w.worker: w for w in self._worker_repo.list_workers()}
        marked: List[str] = []
        for r in rows:
            task = self._task_repo._row_to_task(r)
            if task.worker is None:
                self._task_repo.mark_orphaned(task.task_id, when=now)
                marked.append(task.task_id)
                continue
            w = workers.get(task.worker)
            if w is None or w.status == WorkerStatus.OFFLINE:
                self._task_repo.mark_orphaned(task.task_id, when=now)
                marked.append(task.task_id)
        return marked


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: Dict[str, Callable[[Dict[str, Any]], None]] = {}

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> str:
        token = uuid.uuid4().hex
        with self._lock:
            self._subscribers[token] = callback
        return token

    def unsubscribe(self, token: str) -> None:
        with self._lock:
            self._subscribers.pop(token, None)

    def publish(self, message: Dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subscribers.values())
        for cb in subs:
            cb(message)


class TaskMonitorService:
    def __init__(
        self,
        task_repo: TaskRepository,
        worker_repo: WorkerRepository,
        event_bus: Optional[EventBus] = None,
        *,
        offline_after: timedelta = timedelta(seconds=60),
    ) -> None:
        self._task_repo = task_repo
        self._worker_repo = worker_repo
        self._bus = event_bus or EventBus()
        self._offline_after = offline_after

    @property
    def event_bus(self) -> EventBus:
        return self._bus

    def ingest_task_event(self, ev: TaskEvent) -> None:
        self._task_repo.upsert_task_from_event(ev)
        self._bus.publish(
            {
                "type": "task_event",
                "task_id": ev.task_id,
                "name": ev.name,
                "status": ev.status.value,
                "timestamp": _to_iso(ev.timestamp),
                "worker": ev.worker,
                "retries": int(ev.retries),
            }
        )

    def ingest_worker_heartbeat(self, hb: WorkerHeartbeat) -> None:
        self._worker_repo.record_heartbeat(hb, self._offline_after)
        self._bus.publish(
            {
                "type": "worker_heartbeat",
                "worker": hb.worker,
                "timestamp": _to_iso(hb.timestamp),
            }
        )

    def refresh_worker_health(self, now: Optional[datetime] = None) -> None:
        self._worker_repo.refresh_worker_statuses(now or _utcnow(), self._offline_after)


class WebSocketServer:
    def __init__(self, host: str, port: int, bus: EventBus) -> None:
        if websockets is None:
            raise RuntimeError("websockets package is required to run WebSocketServer")
        self._host = host
        self._port = port
        self._bus = bus
        self._server: Any = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._loop is not None:
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._server = self._loop.run_until_complete(websockets.serve(self._handler, self._host, self._port))
        try:
            self._loop.run_forever()
        finally:
            try:
                self._server.close()
                self._loop.run_until_complete(self._server.wait_closed())
            except Exception:
                pass
            self._loop.close()

    async def _handler(self, websocket: Any) -> None:
        queue: asyncio.Queue[str] = asyncio.Queue()

        def on_message(msg: Dict[str, Any]) -> None:
            try:
                payload = json.dumps(msg, separators=(",", ":"), ensure_ascii=False)
            except Exception:
                return
            if self._loop is None:
                return
            self._loop.call_soon_threadsafe(queue.put_nowait, payload)

        token = self._bus.subscribe(on_message)
        try:
            consumer = asyncio.create_task(self._consume_client(websocket))
            producer = asyncio.create_task(self._produce_client(websocket, queue))
            done, pending = await asyncio.wait({consumer, producer}, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
            for t in done:
                _ = t.result()
        finally:
            self._bus.unsubscribe(token)

    async def _consume_client(self, websocket: Any) -> None:
        async for _ in websocket:
            # Client messages are ignored in this minimal implementation
            pass

    async def _produce_client(self, websocket: Any, queue: asyncio.Queue[str]) -> None:
        while True:
            msg = await queue.get()
            await websocket.send(msg)


class KanchiApp:
    def __init__(
        self,
        *,
        db_path: str = "kanchi.db",
        websocket_host: Optional[str] = None,
        websocket_port: int = 8765,
        offline_after: timedelta = timedelta(seconds=60),
    ) -> None:
        self.db = Database(db_path)
        self.tasks = TaskRepository(self.db)
        self.workers = WorkerRepository(self.db)
        self.stats = StatsService(self.db)
        self.bus = EventBus()
        self.monitor = TaskMonitorService(self.tasks, self.workers, self.bus, offline_after=offline_after)
        self.orphans = OrphanDetector(self.tasks, self.workers)
        self.websocket: Optional[WebSocketServer] = None
        if websocket_host is not None:
            self.websocket = WebSocketServer(websocket_host, websocket_port, self.bus)

    def start(self) -> None:
        if self.websocket is not None:
            self.websocket.start()

    def stop(self) -> None:
        if self.websocket is not None:
            self.websocket.stop()
        self.db.close()


__all__ = [
    "TaskStatus",
    "WorkerStatus",
    "TaskEvent",
    "WorkerHeartbeat",
    "TaskRecord",
    "WorkerRecord",
    "DailyStat",
    "Database",
    "TaskRepository",
    "WorkerRepository",
    "StatsService",
    "OrphanDetector",
    "EventBus",
    "TaskMonitorService",
    "WebSocketServer",
    "KanchiApp",
]