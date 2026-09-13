from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union
from urllib.parse import parse_qs, urlparse

try:
    import websockets  # type: ignore
except Exception:  # pragma: no cover
    websockets = None


def _utc_now() -> datetime:
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
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


class WorkerStatus(str, Enum):
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TaskFilter:
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    statuses: Optional[Set[TaskStatus]] = None
    name: Optional[str] = None
    worker: Optional[str] = None
    full_text: Optional[str] = None
    include_orphans: Optional[bool] = None

    def validate(self) -> None:
        if self.start and self.start.tzinfo is None:
            raise ValueError("start must be timezone-aware")
        if self.end and self.end.tzinfo is None:
            raise ValueError("end must be timezone-aware")
        if self.start and self.end and self.start > self.end:
            raise ValueError("start must be <= end")


@dataclass(frozen=True)
class TaskEvent:
    task_id: str
    event_type: str
    timestamp: datetime
    payload: Dict[str, Any]


class MigrationManager:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = threading.Lock()

    def migrate(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON")
            cur.execute(
                "CREATE TABLE IF NOT EXISTS schema_version ("
                "version INTEGER NOT NULL PRIMARY KEY"
                ")"
            )
            cur.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            row = cur.fetchone()
            current = int(row[0]) if row else 0

            target = 1
            if current < 1:
                self._apply_v1(cur)
                cur.execute("INSERT INTO schema_version(version) VALUES (?)", (1,))
                current = 1

            if current != target:
                raise RuntimeError("Migration did not reach target schema version")

            self._conn.commit()

    def _apply_v1(self, cur: sqlite3.Cursor) -> None:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS tasks ("
            "id TEXT NOT NULL PRIMARY KEY,"
            "name TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "worker TEXT,"
            "args_json TEXT,"
            "kwargs_json TEXT,"
            "result_json TEXT,"
            "error TEXT,"
            "created_at TEXT NOT NULL,"
            "received_at TEXT,"
            "started_at TEXT,"
            "finished_at TEXT,"
            "retries INTEGER NOT NULL DEFAULT 0,"
            "max_retries INTEGER,"
            "parent_id TEXT,"
            "orphaned INTEGER NOT NULL DEFAULT 0"
            ")"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_name ON tasks(name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_orphaned ON tasks(orphaned)")

        cur.execute(
            "CREATE TABLE IF NOT EXISTS task_events ("
            "id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,"
            "task_id TEXT NOT NULL,"
            "event_type TEXT NOT NULL,"
            "timestamp TEXT NOT NULL,"
            "payload_json TEXT NOT NULL,"
            "FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE"
            ")"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_task_events_task_id ON task_events(task_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_task_events_timestamp ON task_events(timestamp)")

        cur.execute(
            "CREATE TABLE IF NOT EXISTS workers ("
            "name TEXT NOT NULL PRIMARY KEY,"
            "status TEXT NOT NULL,"
            "last_heartbeat TEXT,"
            "last_seen TEXT,"
            "meta_json TEXT"
            ")"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_workers_last_seen ON workers(last_seen)")

        cur.execute(
            "CREATE TABLE IF NOT EXISTS daily_stats ("
            "day TEXT NOT NULL PRIMARY KEY,"
            "total INTEGER NOT NULL,"
            "success INTEGER NOT NULL,"
            "failure INTEGER NOT NULL,"
            "retry INTEGER NOT NULL,"
            "revoked INTEGER NOT NULL,"
            "started INTEGER NOT NULL,"
            "received INTEGER NOT NULL,"
            "pending INTEGER NOT NULL,"
            "orphaned INTEGER NOT NULL"
            ")"
        )


class Database:
    def __init__(self, path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        MigrationManager(self._conn).migrate()

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

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

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Set[Callable[[TaskEvent], None]] = set()
        self._lock = threading.Lock()

    def subscribe(self, callback: Callable[[TaskEvent], None]) -> Callable[[], None]:
        with self._lock:
            self._subscribers.add(callback)

        def unsubscribe() -> None:
            with self._lock:
                self._subscribers.discard(callback)

        return unsubscribe

    def publish(self, event: TaskEvent) -> None:
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
        created_at: datetime,
        received_at: Optional[datetime] = None,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        args: Optional[Any] = None,
        kwargs: Optional[Any] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        retries: int = 0,
        max_retries: Optional[int] = None,
        parent_id: Optional[str] = None,
        orphaned: bool = False,
    ) -> None:
        if not task_id:
            raise ValueError("task_id is required")
        if not name:
            raise ValueError("name is required")
        if created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if retries < 0:
            raise ValueError("retries must be >= 0")
        if max_retries is not None and max_retries < 0:
            raise ValueError("max_retries must be >= 0")

        row = self._db.query_one("SELECT id FROM tasks WHERE id = ?", (task_id,))
        if row is None:
            self._db.execute(
                "INSERT INTO tasks (id, name, status, worker, args_json, kwargs_json, result_json, error, "
                "created_at, received_at, started_at, finished_at, retries, max_retries, parent_id, orphaned) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    task_id,
                    name,
                    status.value,
                    worker,
                    json.dumps(args) if args is not None else None,
                    json.dumps(kwargs) if kwargs is not None else None,
                    json.dumps(result) if result is not None else None,
                    error,
                    _dt_to_iso(created_at),
                    _dt_to_iso(received_at),
                    _dt_to_iso(started_at),
                    _dt_to_iso(finished_at),
                    int(retries),
                    max_retries,
                    parent_id,
                    1 if orphaned else 0,
                ),
            )
        else:
            self._db.execute(
                "UPDATE tasks SET name=?, status=?, worker=?, args_json=?, kwargs_json=?, result_json=?, error=?, "
                "created_at=?, received_at=?, started_at=?, finished_at=?, retries=?, max_retries=?, parent_id=?, orphaned=? "
                "WHERE id=?",
                (
                    name,
                    status.value,
                    worker,
                    json.dumps(args) if args is not None else None,
                    json.dumps(kwargs) if kwargs is not None else None,
                    json.dumps(result) if result is not None else None,
                    error,
                    _dt_to_iso(created_at),
                    _dt_to_iso(received_at),
                    _dt_to_iso(started_at),
                    _dt_to_iso(finished_at),
                    int(retries),
                    max_retries,
                    parent_id,
                    1 if orphaned else 0,
                    task_id,
                ),
            )

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        row = self._db.query_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if row is None:
            return None
        return self._row_to_task(row)

    def list_tasks(self, flt: TaskFilter, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        flt.validate()
        if limit <= 0 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if offset < 0:
            raise ValueError("offset must be >= 0")

        where: List[str] = []
        params: List[Any] = []

        if flt.start is not None:
            where.append("created_at >= ?")
            params.append(_dt_to_iso(flt.start))
        if flt.end is not None:
            where.append("created_at <= ?")
            params.append(_dt_to_iso(flt.end))
        if flt.statuses:
            where.append("status IN (%s)" % ",".join(["?"] * len(flt.statuses)))
            params.extend([s.value for s in sorted(flt.statuses, key=lambda x: x.value)])
        if flt.name:
            where.append("name = ?")
            params.append(flt.name)
        if flt.worker:
            where.append("worker = ?")
            params.append(flt.worker)
        if flt.include_orphans is not None:
            where.append("orphaned = ?")
            params.append(1 if flt.include_orphans else 0)
        if flt.full_text:
            q = f"%{flt.full_text}%"
            where.append(
                "(id LIKE ? OR name LIKE ? OR COALESCE(worker,'') LIKE ? OR "
                "COALESCE(args_json,'') LIKE ? OR COALESCE(kwargs_json,'') LIKE ? OR "
                "COALESCE(result_json,'') LIKE ? OR COALESCE(error,'') LIKE ?)"
            )
            params.extend([q, q, q, q, q, q, q])

        sql = "SELECT * FROM tasks"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = self._db.query(sql, params)
        return [self._row_to_task(r) for r in rows]

    def mark_orphaned(self, task_id: str, orphaned: bool) -> None:
        self._db.execute("UPDATE tasks SET orphaned=? WHERE id=?", (1 if orphaned else 0, task_id))

    def increment_retry(self, task_id: str) -> None:
        self._db.execute("UPDATE tasks SET retries = retries + 1 WHERE id = ?", (task_id,))

    def insert_event(self, event: TaskEvent) -> None:
        if event.timestamp.tzinfo is None:
            raise ValueError("event.timestamp must be timezone-aware")
        self._db.execute(
            "INSERT INTO task_events (task_id, event_type, timestamp, payload_json) VALUES (?, ?, ?, ?)",
            (event.task_id, event.event_type, _dt_to_iso(event.timestamp), json.dumps(event.payload)),
        )

    def list_events(self, task_id: str, limit: int = 200) -> List[TaskEvent]:
        if limit <= 0 or limit > 2000:
            raise ValueError("limit must be between 1 and 2000")
        rows = self._db.query(
            "SELECT task_id, event_type, timestamp, payload_json FROM task_events WHERE task_id=? "
            "ORDER BY timestamp ASC LIMIT ?",
            (task_id, limit),
        )
        out: List[TaskEvent] = []
        for r in rows:
            out.append(
                TaskEvent(
                    task_id=str(r["task_id"]),
                    event_type=str(r["event_type"]),
                    timestamp=_iso_to_dt(str(r["timestamp"])) or _utc_now(),
                    payload=json.loads(str(r["payload_json"])) if r["payload_json"] else {},
                )
            )
        return out

    def _row_to_task(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": str(row["id"]),
            "name": str(row["name"]),
            "status": TaskStatus(str(row["status"])),
            "worker": row["worker"],
            "args": json.loads(row["args_json"]) if row["args_json"] else None,
            "kwargs": json.loads(row["kwargs_json"]) if row["kwargs_json"] else None,
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "error": row["error"],
            "created_at": _iso_to_dt(row["created_at"]),
            "received_at": _iso_to_dt(row["received_at"]),
            "started_at": _iso_to_dt(row["started_at"]),
            "finished_at": _iso_to_dt(row["finished_at"]),
            "retries": int(row["retries"]),
            "max_retries": row["max_retries"],
            "parent_id": row["parent_id"],
            "orphaned": bool(row["orphaned"]),
        }


class WorkerRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert_worker(
        self,
        name: str,
        status: WorkerStatus,
        last_heartbeat: Optional[datetime] = None,
        last_seen: Optional[datetime] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not name:
            raise ValueError("worker name is required")
        if last_heartbeat and last_heartbeat.tzinfo is None:
            raise ValueError("last_heartbeat must be timezone-aware")
        if last_seen and last_seen.tzinfo is None:
            raise ValueError("last_seen must be timezone-aware")

        row = self._db.query_one("SELECT name FROM workers WHERE name = ?", (name,))
        if row is None:
            self._db.execute(
                "INSERT INTO workers (name, status, last_heartbeat, last_seen, meta_json) VALUES (?, ?, ?, ?, ?)",
                (
                    name,
                    status.value,
                    _dt_to_iso(last_heartbeat),
                    _dt_to_iso(last_seen),
                    json.dumps(meta) if meta is not None else None,
                ),
            )
        else:
            self._db.execute(
                "UPDATE workers SET status=?, last_heartbeat=?, last_seen=?, meta_json=? WHERE name=?",
                (
                    status.value,
                    _dt_to_iso(last_heartbeat),
                    _dt_to_iso(last_seen),
                    json.dumps(meta) if meta is not None else None,
                    name,
                ),
            )

    def get_worker(self, name: str) -> Optional[Dict[str, Any]]:
        row = self._db.query_one("SELECT * FROM workers WHERE name=?", (name,))
        if row is None:
            return None
        return self._row_to_worker(row)

    def list_workers(self) -> List[Dict[str, Any]]:
        rows = self._db.query("SELECT * FROM workers ORDER BY name ASC")
        return [self._row_to_worker(r) for r in rows]

    def _row_to_worker(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "name": str(row["name"]),
            "status": WorkerStatus(str(row["status"])),
            "last_heartbeat": _iso_to_dt(row["last_heartbeat"]),
            "last_seen": _iso_to_dt(row["last_seen"]),
            "meta": json.loads(row["meta_json"]) if row["meta_json"] else None,
        }


class StatsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert_day(
        self,
        day: date,
        total: int,
        success: int,
        failure: int,
        retry: int,
        revoked: int,
        started: int,
        received: int,
        pending: int,
        orphaned: int,
    ) -> None:
        if total < 0 or any(x < 0 for x in [success, failure, retry, revoked, started, received, pending, orphaned]):
            raise ValueError("stats values must be >= 0")
        day_s = day.isoformat()
        row = self._db.query_one("SELECT day FROM daily_stats WHERE day=?", (day_s,))
        if row is None:
            self._db.execute(
                "INSERT INTO daily_stats (day, total, success, failure, retry, revoked, started, received, pending, orphaned) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (day_s, total, success, failure, retry, revoked, started, received, pending, orphaned),
            )
        else:
            self._db.execute(
                "UPDATE daily_stats SET total=?, success=?, failure=?, retry=?, revoked=?, started=?, received=?, pending=?, orphaned=? "
                "WHERE day=?",
                (total, success, failure, retry, revoked, started, received, pending, orphaned, day_s),
            )

    def get_day(self, day: date) -> Optional[Dict[str, Any]]:
        row = self._db.query_one("SELECT * FROM daily_stats WHERE day=?", (day.isoformat(),))
        if row is None:
            return None
        return dict(row)

    def list_days(self, start: date, end: date) -> List[Dict[str, Any]]:
        if start > end:
            raise ValueError("start must be <= end")
        rows = self._db.query(
            "SELECT * FROM daily_stats WHERE day >= ? AND day <= ? ORDER BY day ASC",
            (start.isoformat(), end.isoformat()),
        )
        return [dict(r) for r in rows]


class OrphanDetector:
    def __init__(self, tasks: TaskRepository) -> None:
        self._tasks = tasks

    def detect_and_mark(self, older_than: timedelta) -> List[str]:
        if older_than.total_seconds() <= 0:
            raise ValueError("older_than must be > 0")
        cutoff = _utc_now() - older_than
        flt = TaskFilter(end=cutoff, statuses={TaskStatus.STARTED, TaskStatus.RECEIVED, TaskStatus.PENDING})
        candidates = self._tasks.list_tasks(flt, limit=1000, offset=0)
        orphaned_ids: List[str] = []
        for t in candidates:
            if t["finished_at"] is None and not t["orphaned"]:
                self._tasks.mark_orphaned(t["id"], True)
                orphaned_ids.append(t["id"])
        return orphaned_ids


class WorkerHealthMonitor:
    def __init__(self, workers: WorkerRepository) -> None:
        self._workers = workers

    def update_heartbeat(self, worker_name: str, meta: Optional[Dict[str, Any]] = None) -> None:
        now = _utc_now()
        existing = self._workers.get_worker(worker_name)
        self._workers.upsert_worker(
            name=worker_name,
            status=WorkerStatus.HEALTHY,
            last_heartbeat=now,
            last_seen=now,
            meta=meta if meta is not None else (existing["meta"] if existing else None),
        )

    def evaluate(self, unhealthy_after: timedelta) -> List[Dict[str, Any]]:
        if unhealthy_after.total_seconds() <= 0:
            raise ValueError("unhealthy_after must be > 0")
        now = _utc_now()
        updated: List[Dict[str, Any]] = []
        for w in self._workers.list_workers():
            hb = w["last_heartbeat"]
            if hb is None:
                desired = WorkerStatus.UNKNOWN
            else:
                desired = WorkerStatus.UNHEALTHY if (now - hb) > unhealthy_after else WorkerStatus.HEALTHY
            if w["status"] != desired:
                self._workers.upsert_worker(
                    name=w["name"],
                    status=desired,
                    last_heartbeat=hb,
                    last_seen=w["last_seen"],
                    meta=w["meta"],
                )
                updated.append({**w, "status": desired})
        return updated


class DailyStatsService:
    def __init__(self, db: Database, stats_repo: StatsRepository) -> None:
        self._db = db
        self._stats = stats_repo

    def recompute_day(self, day: date) -> Dict[str, Any]:
        start_dt = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(days=1)

        rows = self._db.query(
            "SELECT status, orphaned, COUNT(*) as c FROM tasks WHERE created_at >= ? AND created_at < ? "
            "GROUP BY status, orphaned",
            (_dt_to_iso(start_dt), _dt_to_iso(end_dt)),
        )

        counts: Dict[str, int] = {s.value: 0 for s in TaskStatus}
        orphaned = 0
        total = 0
        for r in rows:
            status = str(r["status"])
            c = int(r["c"])
            total += c
            if status in counts:
                counts[status] += c
            if int(r["orphaned"]) == 1:
                orphaned += c

        self._stats.upsert_day(
            day=day,
            total=total,
            success=counts[TaskStatus.SUCCESS.value],
            failure=counts[TaskStatus.FAILURE.value],
            retry=counts[TaskStatus.RETRY.value],
            revoked=counts[TaskStatus.REVOKED.value],
            started=counts[TaskStatus.STARTED.value],
            received=counts[TaskStatus.RECEIVED.value],
            pending=counts[TaskStatus.PENDING.value],
            orphaned=orphaned,
        )
        out = self._stats.get_day(day)
        return out if out is not None else {"day": day.isoformat()}

    def recompute_range(self, start: date, end: date) -> List[Dict[str, Any]]:
        if start > end:
            raise ValueError("start must be <= end")
        out: List[Dict[str, Any]] = []
        d = start
        while d <= end:
            out.append(self.recompute_day(d))
            d = d + timedelta(days=1)
        return out


class TaskService:
    def __init__(self, tasks: TaskRepository, workers: WorkerRepository, stats: DailyStatsService, bus: EventBus) -> None:
        self._tasks = tasks
        self._workers = workers
        self._stats = stats
        self._bus = bus

    def record_event(self, event: TaskEvent) -> None:
        if not event.task_id:
            raise ValueError("event.task_id is required")
        if event.timestamp.tzinfo is None:
            raise ValueError("event.timestamp must be timezone-aware")

        et = event.event_type.upper()
        payload = dict(event.payload or {})
        task_id = event.task_id

        existing = self._tasks.get_task(task_id)
        now = event.timestamp

        if et == "TASK_SENT":
            name = str(payload.get("name") or (existing["name"] if existing else ""))
            if not name:
                raise ValueError("TASK_SENT requires task name")
            self._tasks.upsert_task(
                task_id=task_id,
                name=name,
                status=TaskStatus.PENDING,
                worker=None,
                created_at=now,
                args=payload.get("args"),
                kwargs=payload.get("kwargs"),
                retries=int(payload.get("retries") or 0),
                max_retries=payload.get("max_retries"),
                parent_id=payload.get("parent_id"),
            )
        elif et == "TASK_RECEIVED":
            if existing is None:
                name = str(payload.get("name") or "")
                if not name:
                    raise ValueError("TASK_RECEIVED requires task name when task is unknown")
                created_at = _iso_to_dt(payload.get("created_at")) or now
                self._tasks.upsert_task(
                    task_id=task_id,
                    name=name,
                    status=TaskStatus.RECEIVED,
                    worker=payload.get("worker"),
                    created_at=created_at,
                    received_at=now,
                    args=payload.get("args"),
                    kwargs=payload.get("kwargs"),
                    retries=int(payload.get("retries") or 0),
                    max_retries=payload.get("max_retries"),
                    parent_id=payload.get("parent_id"),
                )
            else:
                self._tasks.upsert_task(
                    task_id=task_id,
                    name=existing["name"],
                    status=TaskStatus.RECEIVED,
                    worker=payload.get("worker") or existing["worker"],
                    created_at=existing["created_at"] or now,
                    received_at=now,
                    started_at=existing["started_at"],
                    finished_at=existing["finished_at"],
                    args=existing["args"],
                    kwargs=existing["kwargs"],
                    result=existing["result"],
                    error=existing["error"],
                    retries=int(existing["retries"]),
                    max_retries=existing["max_retries"],
                    parent_id=existing["parent_id"],
                    orphaned=bool(existing["orphaned"]),
                )
        elif et == "TASK_STARTED":
            if existing is None:
                name = str(payload.get("name") or "")
                if not name:
                    raise ValueError("TASK_STARTED requires task name when task is unknown")
                created_at = _iso_to_dt(payload.get("created_at")) or now
                self._tasks.upsert_task(
                    task_id=task_id,
                    name=name,
                    status=TaskStatus.STARTED,
                    worker=payload.get("worker"),
                    created_at=created_at,
                    received_at=_iso_to_dt(payload.get("received_at")),
                    started_at=now,
                    args=payload.get("args"),
                    kwargs=payload.get("kwargs"),
                    retries=int(payload.get("retries") or 0),
                    max_retries=payload.get("max_retries"),
                    parent_id=payload.get("parent_id"),
                )
            else:
                self._tasks.upsert_task(
                    task_id=task_id,
                    name=existing["name"],
                    status=TaskStatus.STARTED,
                    worker=payload.get("worker") or existing["worker"],
                    created_at=existing["created_at"] or now,
                    received_at=existing["received_at"],
                    started_at=now,
                    finished_at=existing["finished_at"],
                    args=existing["args"],
                    kwargs=existing["kwargs"],
                    result=existing["result"],
                    error=existing["error"],
                    retries=int(existing["retries"]),
                    max_retries=existing["max_retries"],
                    parent_id=existing["parent_id"],
                    orphaned=bool(existing["orphaned"]),
                )
        elif et == "TASK_RETRY":
            if existing is None:
                name = str(payload.get("name") or "")
                if not name:
                    raise ValueError("TASK_RETRY requires task name when task is unknown")
                created_at = _iso_to_dt(payload.get("created_at")) or now
                retries = int(payload.get("retries") or 1)
                self._tasks.upsert_task(
                    task_id=task_id,
                    name=name,
                    status=TaskStatus.RETRY,
                    worker=payload.get("worker"),
                    created_at=created_at,
                    received_at=_iso_to_dt(payload.get("received_at")),
                    started_at=_iso_to_dt(payload.get("started_at")),
                    finished_at=None,
                    args=payload.get("args"),
                    kwargs=payload.get("kwargs"),
                    error=str(payload.get("error") or ""),
                    retries=retries,
                    max_retries=payload.get("max_retries"),
                    parent_id=payload.get("parent_id"),
                )
            else:
                self._tasks.increment_retry(task_id)
                updated = self._tasks.get_task(task_id) or existing
                self._tasks.upsert_task(
                    task_id=task_id,
                    name=updated["name"],
                    status=TaskStatus.RETRY,
                    worker=payload.get("worker") or updated["worker"],
                    created_at=updated["created_at"] or now,
                    received_at=updated["received_at"],
                    started_at=updated["started_at"],
                    finished_at=None,
                    args=updated["args"],
                    kwargs=updated["kwargs"],
                    result=None,
                    error=str(payload.get("error") or updated["error"] or ""),
                    retries=int(updated["retries"]),
                    max_retries=updated["max_retries"],
                    parent_id=updated["parent_id"],
                    orphaned=bool(updated["orphaned"]),
                )
        elif et == "TASK_SUCCESS":
            if existing is None:
                name = str(payload.get("name") or "")
                if not name:
                    raise ValueError("TASK_SUCCESS requires task name when task is unknown")
                created_at = _iso_to_dt(payload.get("created_at")) or now
                self._tasks.upsert_task(
                    task_id=task_id,
                    name=name,
                    status=TaskStatus.SUCCESS,
                    worker=payload.get("worker"),
                    created_at=created_at,
                    received_at=_iso_to_dt(payload.get("received_at")),
                    started_at=_iso_to_dt(payload.get("started_at")),
                    finished_at=now,
                    args=payload.get("args"),
                    kwargs=payload.get("kwargs"),
                    result=payload.get("result"),
                    error=None,
                    retries=int(payload.get("retries") or 0),
                    max_retries=payload.get("max_retries"),
                    parent_id=payload.get("parent_id"),
                )
            else:
                self._tasks.upsert_task(
                    task_id=task_id,
                    name=existing["name"],
                    status=TaskStatus.SUCCESS,
                    worker=payload.get("worker") or existing["worker"],
                    created_at=existing["created_at"] or now,
                    received_at=existing["received_at"],
                    started_at=existing["started_at"],
                    finished_at=now,
                    args=existing["args"],
                    kwargs=existing["kwargs"],
                    result=payload.get("result"),
                    error=None,
                    retries=int(existing["retries"]),
                    max_retries=existing["max_retries"],
                    parent_id=existing["parent_id"],
                    orphaned=bool(existing["orphaned"]),
                )
        elif et == "TASK_FAILURE":
            if existing is None:
                name = str(payload.get("name") or "")
                if not name:
                    raise ValueError("TASK_FAILURE requires task name when task is unknown")
                created_at = _iso_to_dt(payload.get("created_at")) or now
                self._tasks.upsert_task(
                    task_id=task_id,
                    name=name,
                    status=TaskStatus.FAILURE,
                    worker=payload.get("worker"),
                    created_at=created_at,
                    received_at=_iso_to_dt(payload.get("received_at")),
                    started_at=_iso_to_dt(payload.get("started_at")),
                    finished_at=now,
                    args=payload.get("args"),
                    kwargs=payload.get("kwargs"),
                    result=None,
                    error=str(payload.get("error") or ""),
                    retries=int(payload.get("retries") or 0),
                    max_retries=payload.get("max_retries"),
                    parent_id=payload.get("parent_id"),
                )
            else:
                self._tasks.upsert_task(
                    task_id=task_id,
                    name=existing["name"],
                    status=TaskStatus.FAILURE,
                    worker=payload.get("worker") or existing["worker"],
                    created_at=existing["created_at"] or now,
                    received_at=existing["received_at"],
                    started_at=existing["started_at"],
                    finished_at=now,
                    args=existing["args"],
                    kwargs=existing["kwargs"],
                    result=None,
                    error=str(payload.get("error") or existing["error"] or ""),
                    retries=int(existing["retries"]),
                    max_retries=existing["max_retries"],
                    parent_id=existing["parent_id"],
                    orphaned=bool(existing["orphaned"]),
                )
        elif et == "TASK_REVOKED":
            if existing is None:
                name = str(payload.get("name") or "")
                if not name:
                    raise ValueError("TASK_REVOKED requires task name when task is unknown")
                created_at = _iso_to_dt(payload.get("created_at")) or now
                self._tasks.upsert_task(
                    task_id=task_id,
                    name=name,
                    status=TaskStatus.REVOKED,
                    worker=payload.get("worker"),
                    created_at=created_at,
                    received_at=_iso_to_dt(payload.get("received_at")),
                    started_at=_iso_to_dt(payload.get("started_at")),
                    finished_at=now,
                    args=payload.get("args"),
                    kwargs=payload.get("kwargs"),
                    result=None,
                    error=str(payload.get("error") or ""),
                    retries=int(payload.get("retries") or 0),
                    max_retries=payload.get("max_retries"),
                    parent_id=payload.get("parent_id"),
                )
            else:
                self._tasks.upsert_task(
                    task_id=task_id,
                    name=existing["name"],
                    status=TaskStatus.REVOKED,
                    worker=payload.get("worker") or existing["worker"],
                    created_at=existing["created_at"] or now,
                    received_at=existing["received_at"],
                    started_at=existing["started_at"],
                    finished_at=now,
                    args=existing["args"],
                    kwargs=existing["kwargs"],
                    result=None,
                    error=str(payload.get("error") or existing["error"] or ""),
                    retries=int(existing["retries"]),
                    max_retries=existing["max_retries"],
                    parent_id=existing["parent_id"],
                    orphaned=bool(existing["orphaned"]),
                )
        elif et == "WORKER_HEARTBEAT":
            worker = str(payload.get("worker") or "")
            if not worker:
                raise ValueError("WORKER_HEARTBEAT requires worker")
            self._workers.upsert_worker(
                name=worker,
                status=WorkerStatus.HEALTHY,
                last_heartbeat=now,
                last_seen=now,
                meta=payload.get("meta"),
            )
        else:
            raise ValueError(f"Unknown event_type: {event.event_type}")

        self._tasks.insert_event(TaskEvent(task_id=task_id, event_type=et, timestamp=now, payload=payload))
        self._bus.publish(TaskEvent(task_id=task_id, event_type=et, timestamp=now, payload=payload))

        created = self._tasks.get_task(task_id)
        if created and created["created_at"]:
            self._stats.recompute_day(created["created_at"].date())


class TaskManager:
    def __init__(self, task_service: TaskService, tasks: TaskRepository) -> None:
        self._svc = task_service
        self._tasks = tasks

    def retry_task(self, task_id: str, when: Optional[datetime] = None) -> None:
        t = self._tasks.get_task(task_id)
        if t is None:
            raise ValueError("task not found")
        now = when or _utc_now()
        if now.tzinfo is None:
            raise ValueError("when must be timezone-aware")
        self._svc.record_event(
            TaskEvent(
                task_id=task_id,
                event_type="TASK_RETRY",
                timestamp=now,
                payload={
                    "name": t["name"],
                    "worker": t["worker"],
                    "error": "manual retry",
                },
            )
        )


class WebSocketServer:
    def __init__(self, host: str, port: int, bus: EventBus) -> None:
        self._host = host
        self._port = port
        self._bus = bus
        self._server: Any = None
        self._clients: Set[Any] = set()
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if websockets is None:
            raise RuntimeError("websockets package is required to run WebSocketServer")
        self._server = await websockets.serve(self._handler, self._host, self._port)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handler(self, websocket: Any, path: str) -> None:
        async with self._lock:
            self._clients.add(websocket)

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[TaskEvent] = asyncio.Queue()

        def on_event(ev: TaskEvent) -> None:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, ev)
            except Exception:
                pass

        unsubscribe = self._bus.subscribe(on_event)
        try:
            await websocket.send(json.dumps({"type": "hello", "ts": _dt_to_iso(_utc_now())}))
            consumer = asyncio.create_task(self._consume_client(websocket))
            producer = asyncio.create_task(self._produce_events(websocket, queue, path))
            done, pending = await asyncio.wait({consumer, producer}, return_when=asyncio.FIRST_COMPLETED)
            for p in pending:
                p.cancel()
            for d in done:
                _ = d.exception() if d.done() else None
        finally:
            unsubscribe()
            async with self._lock:
                self._clients.discard(websocket)

    async def _consume_client(self, websocket: Any) -> None:
        async for _ in websocket:
            pass

    async def _produce_events(self, websocket: Any, queue: asyncio.Queue[TaskEvent], path: str) -> None:
        flt = self._parse_path_filter(path)
        while True:
            ev = await queue.get()
            if self._event_matches_filter(ev, flt):
                await websocket.send(
                    json.dumps(
                        {
                            "type": "task_event",
                            "task_id": ev.task_id,
                            "event_type": ev.event_type,
                            "timestamp": _dt_to_iso(ev.timestamp),
                            "payload": ev.payload,
                        }
                    )
                )

    def _parse_path_filter(self, path: str) -> Dict[str, Any]:
        try:
            q = parse_qs(urlparse(path).query)
        except Exception:
            return {}
        out: Dict[str, Any] = {}
        if "status" in q:
            statuses: Set[str] = set()
            for v in q.get("status", []):
                for part in v.split(","):
                    part = part.strip().upper()
                    if part:
                        statuses.add(part)
            out["statuses"] = statuses
        if "name" in q and q["name"]:
            out["name"] = q["name"][0]
        if "worker" in q and q["worker"]:
            out["worker"] = q["worker"][0]
        if "task_id" in q and q["task_id"]:
            out["task_id"] = q["task_id"][0]
        return out

    def _event_matches_filter(self, ev: TaskEvent, flt: Dict[str, Any]) -> bool:
        if not flt:
            return True
        if "task_id" in flt and flt["task_id"] != ev.task_id:
            return False
        if "name" in flt:
            name = ev.payload.get("name")
            if name is not None and str(name) != str(flt["name"]):
                return False
        if "worker" in flt:
            worker = ev.payload.get("worker")
            if worker is not None and str(worker) != str(flt["worker"]):
                return False
        if "statuses" in flt:
            statuses: Set[str] = set(flt["statuses"])
            if ev.event_type in {"TASK_SENT"}:
                status = TaskStatus.PENDING.value
            elif ev.event_type in {"TASK_RECEIVED"}:
                status = TaskStatus.RECEIVED.value
            elif ev.event_type in {"TASK_STARTED"}:
                status = TaskStatus.STARTED.value
            elif ev.event_type in {"TASK_SUCCESS"}:
                status = TaskStatus.SUCCESS.value
            elif ev.event_type in {"TASK_FAILURE"}:
                status = TaskStatus.FAILURE.value
            elif ev.event_type in {"TASK_RETRY"}:
                status = TaskStatus.RETRY.value
            elif ev.event_type in {"TASK_REVOKED"}:
                status = TaskStatus.REVOKED.value
            else:
                status = ""
            if status and status not in statuses:
                return False
        return True


class KanchiSystem:
    def __init__(self, db_path: str = ":memory:") -> None:
        self.db = Database(db_path)
        self.bus = EventBus()

        self.tasks = TaskRepository(self.db)
        self.workers = WorkerRepository(self.db)
        self.stats_repo = StatsRepository(self.db)
        self.stats = DailyStatsService(self.db, self.stats_repo)

        self.task_service = TaskService(self.tasks, self.workers, self.stats, self.bus)
        self.task_manager = TaskManager(self.task_service, self.tasks)

        self.orphan_detector = OrphanDetector(self.tasks)
        self.worker_health = WorkerHealthMonitor(self.workers)

    def close(self) -> None:
        self.db.close()


class InMemoryCeleryEventIngestor:
    def __init__(self, system: KanchiSystem) -> None:
        self._system = system

    def ingest(self, event_type: str, task_id: str, payload: Optional[Dict[str, Any]] = None, timestamp: Optional[datetime] = None) -> None:
        ts = timestamp or _utc_now()
        if ts.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        self._system.task_service.record_event(
            TaskEvent(task_id=task_id, event_type=event_type, timestamp=ts, payload=payload or {})
        )


def _demo() -> None:
    sys = KanchiSystem()
    ing = InMemoryCeleryEventIngestor(sys)

    ing.ingest("TASK_SENT", "t1", {"name": "add", "args": [1, 2], "kwargs": {}})
    ing.ingest("TASK_RECEIVED", "t1", {"name": "add", "worker": "w1"})
    ing.ingest("WORKER_HEARTBEAT", "w1", {"worker": "w1", "meta": {"pid": 123}})
    ing.ingest("TASK_STARTED", "t1", {"name": "add", "worker": "w1"})
    ing.ingest("TASK_SUCCESS", "t1", {"name": "add", "worker": "w1", "result": 3})

    tasks = sys.tasks.list_tasks(TaskFilter(), limit=10)
    _ = tasks
    sys.close()


if __name__ == "__main__":
    _demo()