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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
import uvicorn


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _from_iso(s: Optional[str]) -> Optional[datetime]:
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
    retries: Optional[int] = None


@dataclass
class TaskRecord:
    task_id: str
    name: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    worker: Optional[str]
    args: Optional[str]
    kwargs: Optional[str]
    result: Optional[str]
    exception: Optional[str]
    traceback: Optional[str]
    retries: int
    orphaned: bool


@dataclass
class WorkerRecord:
    worker: str
    status: WorkerStatus
    last_heartbeat: datetime
    first_seen: datetime


@dataclass(frozen=True)
class TaskFilter:
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    status: Optional[TaskStatus] = None
    name: Optional[str] = None
    worker: Optional[str] = None
    q: Optional[str] = None


class MigrationManager:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._lock = threading.Lock()

    def migrate(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute(
                "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);"
            )
            row = cur.execute("SELECT version FROM schema_version LIMIT 1;").fetchone()
            if row is None:
                cur.execute("INSERT INTO schema_version(version) VALUES (0);")
                self._conn.commit()
                version = 0
            else:
                version = int(row[0])

            if version < 1:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        started_at TEXT,
                        finished_at TEXT,
                        worker TEXT,
                        args TEXT,
                        kwargs TEXT,
                        result TEXT,
                        exception TEXT,
                        traceback TEXT,
                        retries INTEGER NOT NULL DEFAULT 0,
                        orphaned INTEGER NOT NULL DEFAULT 0
                    );
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at);"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tasks_name ON tasks(name);"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker);"
                )
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
                        retries INTEGER,
                        FOREIGN KEY(task_id) REFERENCES tasks(task_id)
                    );
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_task_events_task_id ON task_events(task_id);"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_task_events_timestamp ON task_events(timestamp);"
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS workers (
                        worker TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        last_heartbeat TEXT NOT NULL,
                        first_seen TEXT NOT NULL
                    );
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status);"
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS daily_stats (
                        day TEXT PRIMARY KEY,
                        total INTEGER NOT NULL,
                        success INTEGER NOT NULL,
                        failure INTEGER NOT NULL,
                        retry INTEGER NOT NULL,
                        revoked INTEGER NOT NULL,
                        pending INTEGER NOT NULL,
                        started INTEGER NOT NULL,
                        received INTEGER NOT NULL,
                        orphaned INTEGER NOT NULL
                    );
                    """
                )
                cur.execute("UPDATE schema_version SET version = 1;")
                self._conn.commit()
                version = 1


class Database:
    def __init__(self, path: str) -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        MigrationManager(self._conn).migrate()

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
        rows = self.query(sql, params)
        return rows[0] if rows else None


class EventBus:
    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue[str]] = set()
        self._lock = asyncio.Lock()

    async def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._subscribers.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        async with self._lock:
            self._subscribers.discard(q)

    async def publish(self, message: Dict[str, Any]) -> None:
        payload = json.dumps(message, separators=(",", ":"), default=str)
        async with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    _ = q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    q.put_nowait(payload)
                except asyncio.QueueFull:
                    pass


class TaskRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert_task_from_event(self, ev: TaskEvent) -> TaskRecord:
        existing = self._db.query_one("SELECT * FROM tasks WHERE task_id = ?;", (ev.task_id,))
        now_iso = _to_iso(ev.timestamp)
        if existing is None:
            created_at = ev.timestamp
            started_at = ev.timestamp if ev.status == TaskStatus.STARTED else None
            finished_at = ev.timestamp if ev.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED) else None
            retries = int(ev.retries) if ev.retries is not None else (1 if ev.status == TaskStatus.RETRY else 0)
            self._db.execute(
                """
                INSERT INTO tasks(task_id,name,status,created_at,updated_at,started_at,finished_at,worker,args,kwargs,result,exception,traceback,retries,orphaned)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);
                """,
                (
                    ev.task_id,
                    ev.name,
                    ev.status.value,
                    _to_iso(created_at),
                    now_iso,
                    _to_iso(started_at),
                    _to_iso(finished_at),
                    ev.worker,
                    ev.args,
                    ev.kwargs,
                    ev.result,
                    ev.exception,
                    ev.traceback,
                    retries,
                    0,
                ),
            )
        else:
            created_at = _from_iso(existing["created_at"]) or ev.timestamp
            started_at = _from_iso(existing["started_at"])
            finished_at = _from_iso(existing["finished_at"])
            retries = int(existing["retries"] or 0)
            orphaned = int(existing["orphaned"] or 0)

            if ev.status == TaskStatus.STARTED and started_at is None:
                started_at = ev.timestamp
            if ev.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED):
                finished_at = ev.timestamp
            if ev.status == TaskStatus.RETRY:
                if ev.retries is not None:
                    retries = max(retries, int(ev.retries))
                else:
                    retries += 1

            worker = ev.worker if ev.worker is not None else existing["worker"]
            args = ev.args if ev.args is not None else existing["args"]
            kwargs = ev.kwargs if ev.kwargs is not None else existing["kwargs"]
            result = ev.result if ev.result is not None else existing["result"]
            exception = ev.exception if ev.exception is not None else existing["exception"]
            traceback = ev.traceback if ev.traceback is not None else existing["traceback"]

            self._db.execute(
                """
                UPDATE tasks
                SET name=?, status=?, updated_at=?, started_at=?, finished_at=?, worker=?, args=?, kwargs=?, result=?, exception=?, traceback=?, retries=?, orphaned=?
                WHERE task_id=?;
                """,
                (
                    ev.name,
                    ev.status.value,
                    now_iso,
                    _to_iso(started_at),
                    _to_iso(finished_at),
                    worker,
                    args,
                    kwargs,
                    result,
                    exception,
                    traceback,
                    retries,
                    orphaned,
                    ev.task_id,
                ),
            )

        self._db.execute(
            """
            INSERT INTO task_events(task_id,name,status,timestamp,worker,args,kwargs,result,exception,traceback,retries)
            VALUES(?,?,?,?,?,?,?,?,?,?,?);
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
                ev.retries,
            ),
        )
        return self.get_task(ev.task_id)

    def get_task(self, task_id: str) -> TaskRecord:
        row = self._db.query_one("SELECT * FROM tasks WHERE task_id = ?;", (task_id,))
        if row is None:
            raise KeyError(task_id)
        return self._row_to_task(row)

    def list_tasks(self, flt: TaskFilter, limit: int = 200, offset: int = 0) -> List[TaskRecord]:
        if limit < 1:
            limit = 1
        if limit > 1000:
            limit = 1000
        if offset < 0:
            offset = 0

        where: List[str] = []
        params: List[Any] = []

        if flt.start is not None:
            where.append("updated_at >= ?")
            params.append(_to_iso(flt.start))
        if flt.end is not None:
            where.append("updated_at <= ?")
            params.append(_to_iso(flt.end))
        if flt.status is not None:
            where.append("status = ?")
            params.append(flt.status.value)
        if flt.name is not None:
            where.append("name = ?")
            params.append(flt.name)
        if flt.worker is not None:
            where.append("worker = ?")
            params.append(flt.worker)
        if flt.q is not None and flt.q.strip():
            q = f"%{flt.q.strip()}%"
            where.append("(task_id LIKE ? OR name LIKE ? OR worker LIKE ? OR args LIKE ? OR kwargs LIKE ? OR result LIKE ? OR exception LIKE ? OR traceback LIKE ?)")
            params.extend([q, q, q, q, q, q, q, q])

        sql = "SELECT * FROM tasks"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])

        rows = self._db.query(sql, params)
        return [self._row_to_task(r) for r in rows]

    def task_history(self, task_id: str, limit: int = 200) -> List[TaskEvent]:
        if limit < 1:
            limit = 1
        if limit > 2000:
            limit = 2000
        rows = self._db.query(
            "SELECT * FROM task_events WHERE task_id = ? ORDER BY timestamp ASC, id ASC LIMIT ?;",
            (task_id, limit),
        )
        events: List[TaskEvent] = []
        for r in rows:
            events.append(
                TaskEvent(
                    task_id=r["task_id"],
                    name=r["name"],
                    status=TaskStatus(r["status"]),
                    timestamp=_from_iso(r["timestamp"]) or _utcnow(),
                    worker=r["worker"],
                    args=r["args"],
                    kwargs=r["kwargs"],
                    result=r["result"],
                    exception=r["exception"],
                    traceback=r["traceback"],
                    retries=r["retries"],
                )
            )
        return events

    def mark_orphaned(self, task_id: str, orphaned: bool) -> None:
        self._db.execute("UPDATE tasks SET orphaned = ? WHERE task_id = ?;", (1 if orphaned else 0, task_id))

    def detect_orphans(self, older_than: timedelta) -> int:
        cutoff = _utcnow() - older_than
        cutoff_iso = _to_iso(cutoff)
        rows = self._db.query(
            """
            SELECT task_id FROM tasks
            WHERE orphaned = 0
              AND status IN ('STARTED','RECEIVED')
              AND updated_at < ?;
            """,
            (cutoff_iso,),
        )
        for r in rows:
            self.mark_orphaned(r["task_id"], True)
        return len(rows)

    @staticmethod
    def _row_to_task(r: sqlite3.Row) -> TaskRecord:
        return TaskRecord(
            task_id=r["task_id"],
            name=r["name"],
            status=TaskStatus(r["status"]),
            created_at=_from_iso(r["created_at"]) or _utcnow(),
            updated_at=_from_iso(r["updated_at"]) or _utcnow(),
            started_at=_from_iso(r["started_at"]),
            finished_at=_from_iso(r["finished_at"]),
            worker=r["worker"],
            args=r["args"],
            kwargs=r["kwargs"],
            result=r["result"],
            exception=r["exception"],
            traceback=r["traceback"],
            retries=int(r["retries"] or 0),
            orphaned=bool(int(r["orphaned"] or 0)),
        )


class WorkerRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def heartbeat(self, worker: str, ts: Optional[datetime] = None) -> WorkerRecord:
        if not worker or not worker.strip():
            raise ValueError("worker must be non-empty")
        ts = ts or _utcnow()
        row = self._db.query_one("SELECT * FROM workers WHERE worker = ?;", (worker,))
        if row is None:
            self._db.execute(
                "INSERT INTO workers(worker,status,last_heartbeat,first_seen) VALUES(?,?,?,?);",
                (worker, WorkerStatus.ONLINE.value, _to_iso(ts), _to_iso(ts)),
            )
        else:
            self._db.execute(
                "UPDATE workers SET status=?, last_heartbeat=? WHERE worker=?;",
                (WorkerStatus.ONLINE.value, _to_iso(ts), worker),
            )
        return self.get(worker)

    def get(self, worker: str) -> WorkerRecord:
        row = self._db.query_one("SELECT * FROM workers WHERE worker = ?;", (worker,))
        if row is None:
            raise KeyError(worker)
        return self._row_to_worker(row)

    def list(self) -> List[WorkerRecord]:
        rows = self._db.query("SELECT * FROM workers ORDER BY worker ASC;")
        return [self._row_to_worker(r) for r in rows]

    def update_health(self, offline_after: timedelta) -> int:
        cutoff = _utcnow() - offline_after
        cutoff_iso = _to_iso(cutoff)
        rows = self._db.query("SELECT worker FROM workers WHERE last_heartbeat < ? AND status != 'OFFLINE';", (cutoff_iso,))
        for r in rows:
            self._db.execute("UPDATE workers SET status=? WHERE worker=?;", (WorkerStatus.OFFLINE.value, r["worker"]))
        return len(rows)

    @staticmethod
    def _row_to_worker(r: sqlite3.Row) -> WorkerRecord:
        return WorkerRecord(
            worker=r["worker"],
            status=WorkerStatus(r["status"]),
            last_heartbeat=_from_iso(r["last_heartbeat"]) or _utcnow(),
            first_seen=_from_iso(r["first_seen"]) or _utcnow(),
        )


class StatsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def recompute_day(self, day: date) -> Dict[str, Any]:
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        start_iso = _to_iso(start)
        end_iso = _to_iso(end)

        rows = self._db.query(
            """
            SELECT status, COUNT(*) as c FROM tasks
            WHERE updated_at >= ? AND updated_at < ?
            GROUP BY status;
            """,
            (start_iso, end_iso),
        )
        counts: Dict[str, int] = {r["status"]: int(r["c"]) for r in rows}
        orphaned_row = self._db.query_one(
            """
            SELECT COUNT(*) as c FROM tasks
            WHERE orphaned = 1 AND updated_at >= ? AND updated_at < ?;
            """,
            (start_iso, end_iso),
        )
        orphaned = int(orphaned_row["c"]) if orphaned_row is not None else 0

        total = sum(counts.values())
        payload = {
            "day": day.isoformat(),
            "total": total,
            "success": counts.get(TaskStatus.SUCCESS.value, 0),
            "failure": counts.get(TaskStatus.FAILURE.value, 0),
            "retry": counts.get(TaskStatus.RETRY.value, 0),
            "revoked": counts.get(TaskStatus.REVOKED.value, 0),
            "pending": counts.get(TaskStatus.PENDING.value, 0),
            "started": counts.get(TaskStatus.STARTED.value, 0),
            "received": counts.get(TaskStatus.RECEIVED.value, 0),
            "orphaned": orphaned,
        }

        self._db.execute(
            """
            INSERT INTO daily_stats(day,total,success,failure,retry,revoked,pending,started,received,orphaned)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(day) DO UPDATE SET
                total=excluded.total,
                success=excluded.success,
                failure=excluded.failure,
                retry=excluded.retry,
                revoked=excluded.revoked,
                pending=excluded.pending,
                started=excluded.started,
                received=excluded.received,
                orphaned=excluded.orphaned;
            """,
            (
                payload["day"],
                payload["total"],
                payload["success"],
                payload["failure"],
                payload["retry"],
                payload["revoked"],
                payload["pending"],
                payload["started"],
                payload["received"],
                payload["orphaned"],
            ),
        )
        return payload

    def get_range(self, start_day: date, end_day: date) -> List[Dict[str, Any]]:
        if end_day < start_day:
            start_day, end_day = end_day, start_day
        days: List[str] = []
        d = start_day
        while d <= end_day:
            days.append(d.isoformat())
            d = d + timedelta(days=1)
        if not days:
            return []
        placeholders = ",".join(["?"] * len(days))
        rows = self._db.query(f"SELECT * FROM daily_stats WHERE day IN ({placeholders}) ORDER BY day ASC;", days)
        by_day: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            by_day[r["day"]] = {
                "day": r["day"],
                "total": int(r["total"]),
                "success": int(r["success"]),
                "failure": int(r["failure"]),
                "retry": int(r["retry"]),
                "revoked": int(r["revoked"]),
                "pending": int(r["pending"]),
                "started": int(r["started"]),
                "received": int(r["received"]),
                "orphaned": int(r["orphaned"]),
            }
        out: List[Dict[str, Any]] = []
        for ds in days:
            out.append(
                by_day.get(
                    ds,
                    {
                        "day": ds,
                        "total": 0,
                        "success": 0,
                        "failure": 0,
                        "retry": 0,
                        "revoked": 0,
                        "pending": 0,
                        "started": 0,
                        "received": 0,
                        "orphaned": 0,
                    },
                )
            )
        return out


class KanchiService:
    def __init__(
        self,
        db_path: str = "kanchi.db",
        orphan_after_seconds: int = 600,
        worker_offline_after_seconds: int = 60,
    ) -> None:
        self.db = Database(db_path)
        self.tasks = TaskRepository(self.db)
        self.workers = WorkerRepository(self.db)
        self.stats = StatsRepository(self.db)
        self.bus = EventBus()
        self._orphan_after = timedelta(seconds=int(orphan_after_seconds))
        self._worker_offline_after = timedelta(seconds=int(worker_offline_after_seconds))
        self._bg_task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._bg_task is None or self._bg_task.done():
            self._stop_event = asyncio.Event()
            self._bg_task = asyncio.create_task(self._background_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._bg_task is not None:
            try:
                await asyncio.wait_for(self._bg_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._bg_task.cancel()

    def ingest_task_event(self, ev: TaskEvent) -> TaskRecord:
        rec = self.tasks.upsert_task_from_event(ev)
        day = rec.updated_at.astimezone(timezone.utc).date()
        self.stats.recompute_day(day)
        return rec

    def ingest_worker_heartbeat(self, worker: str, ts: Optional[datetime] = None) -> WorkerRecord:
        rec = self.workers.heartbeat(worker, ts=ts)
        return rec

    async def publish_task_event(self, ev: TaskEvent) -> TaskRecord:
        rec = await asyncio.to_thread(self.ingest_task_event, ev)
        await self.bus.publish(
            {
                "type": "task_event",
                "task": self._task_to_dict(rec),
                "event": self._event_to_dict(ev),
            }
        )
        return rec

    async def publish_worker_heartbeat(self, worker: str, ts: Optional[datetime] = None) -> WorkerRecord:
        rec = await asyncio.to_thread(self.ingest_worker_heartbeat, worker, ts)
        await self.bus.publish({"type": "worker_heartbeat", "worker": self._worker_to_dict(rec)})
        return rec

    async def _background_loop(self) -> None:
        while not self._stop_event.is_set():
            await asyncio.sleep(2.0)
            orphaned = await asyncio.to_thread(self.tasks.detect_orphans, self._orphan_after)
            offline = await asyncio.to_thread(self.workers.update_health, self._worker_offline_after)
            if orphaned:
                await self.bus.publish({"type": "orphan_detection", "count": orphaned, "timestamp": _to_iso(_utcnow())})
                day = _utcnow().date()
                await asyncio.to_thread(self.stats.recompute_day, day)
            if offline:
                await self.bus.publish({"type": "worker_health", "offline_marked": offline, "timestamp": _to_iso(_utcnow())})

    @staticmethod
    def _task_to_dict(t: TaskRecord) -> Dict[str, Any]:
        return {
            "task_id": t.task_id,
            "name": t.name,
            "status": t.status.value,
            "created_at": _to_iso(t.created_at),
            "updated_at": _to_iso(t.updated_at),
            "started_at": _to_iso(t.started_at),
            "finished_at": _to_iso(t.finished_at),
            "worker": t.worker,
            "args": t.args,
            "kwargs": t.kwargs,
            "result": t.result,
            "exception": t.exception,
            "traceback": t.traceback,
            "retries": t.retries,
            "orphaned": t.orphaned,
        }

    @staticmethod
    def _worker_to_dict(w: WorkerRecord) -> Dict[str, Any]:
        return {
            "worker": w.worker,
            "status": w.status.value,
            "last_heartbeat": _to_iso(w.last_heartbeat),
            "first_seen": _to_iso(w.first_seen),
        }

    @staticmethod
    def _event_to_dict(e: TaskEvent) -> Dict[str, Any]:
        return {
            "task_id": e.task_id,
            "name": e.name,
            "status": e.status.value,
            "timestamp": _to_iso(e.timestamp),
            "worker": e.worker,
            "args": e.args,
            "kwargs": e.kwargs,
            "result": e.result,
            "exception": e.exception,
            "traceback": e.traceback,
            "retries": e.retries,
        }


class KanchiAPI:
    def __init__(self, service: KanchiService) -> None:
        self.service = service
        self.app = FastAPI(title="Kanchi", version="1.0")
        self._mount_routes()

        @self.app.on_event("startup")
        async def _startup() -> None:
            await self.service.start()

        @self.app.on_event("shutdown")
        async def _shutdown() -> None:
            await self.service.stop()

    def _mount_routes(self) -> None:
        app = self.app

        @app.get("/health")
        async def health() -> JSONResponse:
            return JSONResponse({"status": "ok", "timestamp": _to_iso(_utcnow())})

        @app.post("/ingest/task_event")
        async def ingest_task_event(payload: Dict[str, Any]) -> JSONResponse:
            ev = self._parse_task_event(payload)
            rec = await self.service.publish_task_event(ev)
            return JSONResponse({"task": self.service._task_to_dict(rec)})

        @app.post("/ingest/worker_heartbeat")
        async def ingest_worker_heartbeat(payload: Dict[str, Any]) -> JSONResponse:
            worker = str(payload.get("worker") or "").strip()
            if not worker:
                return JSONResponse({"error": "worker is required"}, status_code=400)
            ts = payload.get("timestamp")
            dt = _from_iso(ts) if isinstance(ts, str) else None
            rec = await self.service.publish_worker_heartbeat(worker, dt)
            return JSONResponse({"worker": self.service._worker_to_dict(rec)})

        @app.get("/tasks")
        async def list_tasks(
            start: Optional[str] = Query(default=None),
            end: Optional[str] = Query(default=None),
            status: Optional[str] = Query(default=None),
            name: Optional[str] = Query(default=None),
            worker: Optional[str] = Query(default=None),
            q: Optional[str] = Query(default=None),
            limit: int = Query(default=200),
            offset: int = Query(default=0),
        ) -> JSONResponse:
            flt = TaskFilter(
                start=_from_iso(start) if start else None,
                end=_from_iso(end) if end else None,
                status=TaskStatus(status) if status else None,
                name=name,
                worker=worker,
                q=q,
            )
            tasks = await asyncio.to_thread(self.service.tasks.list_tasks, flt, limit, offset)
            return JSONResponse({"tasks": [self.service._task_to_dict(t) for t in tasks]})

        @app.get("/tasks/{task_id}")
        async def get_task(task_id: str) -> JSONResponse:
            try:
                t = await asyncio.to_thread(self.service.tasks.get_task, task_id)
            except KeyError:
                return JSONResponse({"error": "not_found"}, status_code=404)
            return JSONResponse({"task": self.service._task_to_dict(t)})

        @app.get("/tasks/{task_id}/history")
        async def task_history(task_id: str, limit: int = Query(default=200)) -> JSONResponse:
            try:
                _ = await asyncio.to_thread(self.service.tasks.get_task, task_id)
            except KeyError:
                return JSONResponse({"error": "not_found"}, status_code=404)
            events = await asyncio.to_thread(self.service.tasks.task_history, task_id, limit)
            return JSONResponse({"events": [self.service._event_to_dict(e) for e in events]})

        @app.get("/workers")
        async def list_workers() -> JSONResponse:
            workers = await asyncio.to_thread(self.service.workers.list)
            return JSONResponse({"workers": [self.service._worker_to_dict(w) for w in workers]})

        @app.get("/stats/daily")
        async def daily_stats(
            start_day: str = Query(..., alias="start"),
            end_day: str = Query(..., alias="end"),
        ) -> JSONResponse:
            sd = date.fromisoformat(start_day)
            ed = date.fromisoformat(end_day)
            stats = await asyncio.to_thread(self.service.stats.get_range, sd, ed)
            return JSONResponse({"days": stats})

        @app.websocket("/ws")
        async def ws(websocket: WebSocket) -> None:
            await websocket.accept()
            q = await self.service.bus.subscribe()
            try:
                while True:
                    try:
                        msg = await asyncio.wait_for(q.get(), timeout=15.0)
                        await websocket.send_text(msg)
                    except asyncio.TimeoutError:
                        await websocket.send_text(json.dumps({"type": "ping", "timestamp": _to_iso(_utcnow())}))
            except WebSocketDisconnect:
                pass
            finally:
                await self.service.bus.unsubscribe(q)

    @staticmethod
    def _parse_task_event(payload: Dict[str, Any]) -> TaskEvent:
        task_id = str(payload.get("task_id") or "").strip()
        name = str(payload.get("name") or "").strip()
        status_raw = payload.get("status")
        if not task_id:
            raise ValueError("task_id is required")
        if not name:
            raise ValueError("name is required")
        if not status_raw:
            raise ValueError("status is required")
        status = TaskStatus(str(status_raw))
        ts_raw = payload.get("timestamp")
        ts = _from_iso(ts_raw) if isinstance(ts_raw, str) else None
        ts = ts or _utcnow()
        worker = payload.get("worker")
        args = payload.get("args")
        kwargs = payload.get("kwargs")
        result = payload.get("result")
        exception = payload.get("exception")
        traceback = payload.get("traceback")
        retries = payload.get("retries")
        retries_int: Optional[int]
        if retries is None:
            retries_int = None
        else:
            retries_int = int(retries)
            if retries_int < 0:
                retries_int = 0
        return TaskEvent(
            task_id=task_id,
            name=name,
            status=status,
            timestamp=ts,
            worker=str(worker) if worker is not None else None,
            args=str(args) if args is not None else None,
            kwargs=str(kwargs) if kwargs is not None else None,
            result=str(result) if result is not None else None,
            exception=str(exception) if exception is not None else None,
            traceback=str(traceback) if traceback is not None else None,
            retries=retries_int,
        )


def create_app(
    db_path: str = "kanchi.db",
    orphan_after_seconds: int = 600,
    worker_offline_after_seconds: int = 60,
) -> FastAPI:
    service = KanchiService(
        db_path=db_path,
        orphan_after_seconds=orphan_after_seconds,
        worker_offline_after_seconds=worker_offline_after_seconds,
    )
    api = KanchiAPI(service)
    return api.app


if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)