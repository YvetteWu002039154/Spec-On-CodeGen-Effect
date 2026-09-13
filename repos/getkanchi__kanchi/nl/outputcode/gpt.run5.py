from __future__ import annotations

import asyncio
import json
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, date
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


UTC = timezone.utc


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("Invalid datetime format; expected ISO-8601")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


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
    traceback: Optional[str] = None
    retries: int = 0
    eta: Optional[datetime] = None
    expires: Optional[datetime] = None


class Database:
    def __init__(self, path: str) -> None:
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

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def executemany(self, sql: str, seq_of_params: Iterable[Sequence[Any]]) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.executemany(sql, seq_of_params)
            self._conn.commit()
            return cur

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


class MigrationManager:
    def __init__(self, db: Database) -> None:
        self._db = db

    def migrate(self) -> None:
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version INTEGER PRIMARY KEY,"
            "applied_at TEXT NOT NULL"
            ")"
        )
        row = self._db.query_one("SELECT MAX(version) AS v FROM schema_migrations")
        current = int(row["v"]) if row and row["v"] is not None else 0

        migrations: List[Tuple[int, Callable[[], None]]] = [
            (1, self._migration_1),
        ]

        for version, fn in migrations:
            if version > current:
                fn()
                self._db.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)",
                    (version, _to_iso(_utcnow())),
                )

    def _migration_1(self) -> None:
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS tasks ("
            "id TEXT PRIMARY KEY,"
            "name TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "worker TEXT,"
            "created_at TEXT NOT NULL,"
            "received_at TEXT,"
            "started_at TEXT,"
            "finished_at TEXT,"
            "args TEXT,"
            "kwargs TEXT,"
            "result TEXT,"
            "traceback TEXT,"
            "retries INTEGER NOT NULL DEFAULT 0,"
            "eta TEXT,"
            "expires TEXT,"
            "last_event_at TEXT NOT NULL"
            ")"
        )
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_name ON tasks(name)")
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker)")
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)")
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_last_event_at ON tasks(last_event_at)")

        self._db.execute(
            "CREATE TABLE IF NOT EXISTS task_events ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "task_id TEXT NOT NULL,"
            "name TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "worker TEXT,"
            "timestamp TEXT NOT NULL,"
            "args TEXT,"
            "kwargs TEXT,"
            "result TEXT,"
            "traceback TEXT,"
            "retries INTEGER NOT NULL DEFAULT 0,"
            "eta TEXT,"
            "expires TEXT,"
            "FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE"
            ")"
        )
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_task_events_task_id ON task_events(task_id)")
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_task_events_timestamp ON task_events(timestamp)")

        self._db.execute(
            "CREATE TABLE IF NOT EXISTS workers ("
            "name TEXT PRIMARY KEY,"
            "status TEXT NOT NULL,"
            "first_seen_at TEXT NOT NULL,"
            "last_heartbeat_at TEXT NOT NULL,"
            "last_seen_at TEXT NOT NULL"
            ")"
        )
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status)")
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_workers_last_heartbeat ON workers(last_heartbeat_at)")

        self._db.execute(
            "CREATE TABLE IF NOT EXISTS daily_task_stats ("
            "day TEXT NOT NULL,"
            "name TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "count INTEGER NOT NULL,"
            "PRIMARY KEY(day, name, status)"
            ")"
        )
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_daily_task_stats_day ON daily_task_stats(day)")


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: Dict[str, Callable[[Dict[str, Any]], None]] = {}

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> str:
        token = secrets.token_urlsafe(16)
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
            try:
                cb(message)
            except Exception:
                pass


class TaskRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert_task_from_event(self, event: TaskEvent) -> None:
        now_iso = _to_iso(event.timestamp)
        existing = self._db.query_one("SELECT * FROM tasks WHERE id = ?", (event.task_id,))
        if existing is None:
            created_at = now_iso
            received_at = now_iso if event.status == TaskStatus.RECEIVED else None
            started_at = now_iso if event.status == TaskStatus.STARTED else None
            finished_at = now_iso if event.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED) else None
            self._db.execute(
                "INSERT INTO tasks(id, name, status, worker, created_at, received_at, started_at, finished_at, "
                "args, kwargs, result, traceback, retries, eta, expires, last_event_at) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event.task_id,
                    event.name,
                    event.status.value,
                    event.worker,
                    created_at,
                    received_at,
                    started_at,
                    finished_at,
                    event.args,
                    event.kwargs,
                    event.result,
                    event.traceback,
                    int(event.retries),
                    _to_iso(event.eta),
                    _to_iso(event.expires),
                    now_iso,
                ),
            )
        else:
            received_at = existing["received_at"]
            started_at = existing["started_at"]
            finished_at = existing["finished_at"]

            if event.status == TaskStatus.RECEIVED and received_at is None:
                received_at = now_iso
            if event.status == TaskStatus.STARTED and started_at is None:
                started_at = now_iso
            if event.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED):
                finished_at = now_iso

            self._db.execute(
                "UPDATE tasks SET name = ?, status = ?, worker = ?, received_at = ?, started_at = ?, finished_at = ?, "
                "args = COALESCE(?, args), kwargs = COALESCE(?, kwargs), result = COALESCE(?, result), "
                "traceback = COALESCE(?, traceback), retries = ?, eta = COALESCE(?, eta), expires = COALESCE(?, expires), "
                "last_event_at = ? "
                "WHERE id = ?",
                (
                    event.name,
                    event.status.value,
                    event.worker if event.worker is not None else existing["worker"],
                    received_at,
                    started_at,
                    finished_at,
                    event.args,
                    event.kwargs,
                    event.result,
                    event.traceback,
                    int(event.retries),
                    _to_iso(event.eta),
                    _to_iso(event.expires),
                    now_iso,
                    event.task_id,
                ),
            )

        self._db.execute(
            "INSERT INTO task_events(task_id, name, status, worker, timestamp, args, kwargs, result, traceback, retries, eta, expires) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.task_id,
                event.name,
                event.status.value,
                event.worker,
                now_iso,
                event.args,
                event.kwargs,
                event.result,
                event.traceback,
                int(event.retries),
                _to_iso(event.eta),
                _to_iso(event.expires),
            ),
        )

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        row = self._db.query_one("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return dict(row) if row else None

    def list_tasks(
        self,
        *,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        status: Optional[TaskStatus] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_desc: bool = True,
    ) -> List[Dict[str, Any]]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        if offset < 0:
            raise ValueError("offset must be >= 0")

        where: List[str] = []
        params: List[Any] = []

        if date_from is not None:
            where.append("created_at >= ?")
            params.append(_to_iso(date_from))
        if date_to is not None:
            where.append("created_at <= ?")
            params.append(_to_iso(date_to))
        if status is not None:
            where.append("status = ?")
            params.append(status.value)
        if name is not None:
            where.append("name = ?")
            params.append(name)
        if worker is not None:
            where.append("worker = ?")
            params.append(worker)
        if q is not None and q.strip():
            like = f"%{q.strip()}%"
            where.append("(id LIKE ? OR name LIKE ? OR worker LIKE ? OR args LIKE ? OR kwargs LIKE ? OR result LIKE ? OR traceback LIKE ?)")
            params.extend([like, like, like, like, like, like, like])

        where_sql = (" WHERE " + " AND ".join(where)) if where else ""
        order_sql = " ORDER BY last_event_at DESC" if order_desc else " ORDER BY last_event_at ASC"
        sql = f"SELECT * FROM tasks{where_sql}{order_sql} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self._db.query(sql, params)
        return [dict(r) for r in rows]

    def task_retry_count(self, task_id: str) -> int:
        row = self._db.query_one("SELECT retries FROM tasks WHERE id = ?", (task_id,))
        if not row:
            raise KeyError("task not found")
        return int(row["retries"])

    def list_task_events(self, task_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        if limit < 1 or limit > 2000:
            raise ValueError("limit must be between 1 and 2000")
        rows = self._db.query(
            "SELECT * FROM task_events WHERE task_id = ? ORDER BY timestamp DESC LIMIT ?",
            (task_id, limit),
        )
        return [dict(r) for r in rows]


class WorkerRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def heartbeat(self, worker_name: str, at: Optional[datetime] = None) -> None:
        if not worker_name or not worker_name.strip():
            raise ValueError("worker_name is required")
        at = at or _utcnow()
        at_iso = _to_iso(at)
        existing = self._db.query_one("SELECT * FROM workers WHERE name = ?", (worker_name,))
        if existing is None:
            self._db.execute(
                "INSERT INTO workers(name, status, first_seen_at, last_heartbeat_at, last_seen_at) VALUES(?, ?, ?, ?, ?)",
                (worker_name, WorkerStatus.ONLINE.value, at_iso, at_iso, at_iso),
            )
        else:
            self._db.execute(
                "UPDATE workers SET status = ?, last_heartbeat_at = ?, last_seen_at = ? WHERE name = ?",
                (WorkerStatus.ONLINE.value, at_iso, at_iso, worker_name),
            )

    def mark_offline_if_stale(self, stale_after_seconds: int) -> int:
        if stale_after_seconds < 1:
            raise ValueError("stale_after_seconds must be >= 1")
        cutoff = _utcnow() - timedelta(seconds=stale_after_seconds)
        cutoff_iso = _to_iso(cutoff)
        cur = self._db.execute(
            "UPDATE workers SET status = ? WHERE last_heartbeat_at < ? AND status != ?",
            (WorkerStatus.OFFLINE.value, cutoff_iso, WorkerStatus.OFFLINE.value),
        )
        return int(cur.rowcount)

    def list_workers(self) -> List[Dict[str, Any]]:
        rows = self._db.query("SELECT * FROM workers ORDER BY name ASC")
        return [dict(r) for r in rows]

    def get_worker(self, name: str) -> Optional[Dict[str, Any]]:
        row = self._db.query_one("SELECT * FROM workers WHERE name = ?", (name,))
        return dict(row) if row else None


class StatsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def increment_daily(self, day: date, task_name: str, status: TaskStatus, delta: int = 1) -> None:
        if delta <= 0:
            raise ValueError("delta must be > 0")
        day_s = day.isoformat()
        existing = self._db.query_one(
            "SELECT count FROM daily_task_stats WHERE day = ? AND name = ? AND status = ?",
            (day_s, task_name, status.value),
        )
        if existing is None:
            self._db.execute(
                "INSERT INTO daily_task_stats(day, name, status, count) VALUES(?, ?, ?, ?)",
                (day_s, task_name, status.value, int(delta)),
            )
        else:
            self._db.execute(
                "UPDATE daily_task_stats SET count = count + ? WHERE day = ? AND name = ? AND status = ?",
                (int(delta), day_s, task_name, status.value),
            )

    def get_daily(self, day: date) -> List[Dict[str, Any]]:
        rows = self._db.query(
            "SELECT day, name, status, count FROM daily_task_stats WHERE day = ? ORDER BY name ASC, status ASC",
            (day.isoformat(),),
        )
        return [dict(r) for r in rows]

    def get_range(self, day_from: date, day_to: date) -> List[Dict[str, Any]]:
        if day_to < day_from:
            raise ValueError("day_to must be >= day_from")
        rows = self._db.query(
            "SELECT day, name, status, count FROM daily_task_stats WHERE day >= ? AND day <= ? ORDER BY day ASC, name ASC, status ASC",
            (day_from.isoformat(), day_to.isoformat()),
        )
        return [dict(r) for r in rows]


class OrphanDetector:
    def __init__(self, db: Database) -> None:
        self._db = db

    def find_orphans(self, *, started_before_seconds: int = 3600, limit: int = 200) -> List[Dict[str, Any]]:
        if started_before_seconds < 1:
            raise ValueError("started_before_seconds must be >= 1")
        if limit < 1 or limit > 2000:
            raise ValueError("limit must be between 1 and 2000")
        cutoff = _utcnow() - timedelta(seconds=started_before_seconds)
        cutoff_iso = _to_iso(cutoff)
        rows = self._db.query(
            "SELECT * FROM tasks "
            "WHERE status IN (?, ?, ?) AND started_at IS NOT NULL AND started_at < ? "
            "ORDER BY started_at ASC LIMIT ?",
            (TaskStatus.STARTED.value, TaskStatus.RECEIVED.value, TaskStatus.RETRY.value, cutoff_iso, limit),
        )
        return [dict(r) for r in rows]


class TaskService:
    def __init__(self, tasks: TaskRepository, workers: WorkerRepository, stats: StatsRepository, bus: EventBus) -> None:
        self._tasks = tasks
        self._workers = workers
        self._stats = stats
        self._bus = bus

    def ingest_event(self, event: TaskEvent) -> None:
        if not event.task_id or not event.task_id.strip():
            raise ValueError("task_id is required")
        if not event.name or not event.name.strip():
            raise ValueError("name is required")
        if event.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        if event.retries < 0:
            raise ValueError("retries must be >= 0")

        self._tasks.upsert_task_from_event(event)

        if event.worker:
            self._workers.heartbeat(event.worker, at=event.timestamp)

        self._stats.increment_daily(event.timestamp.date(), event.name, event.status, delta=1)

        self._bus.publish(
            {
                "type": "task_event",
                "task_id": event.task_id,
                "name": event.name,
                "status": event.status.value,
                "worker": event.worker,
                "timestamp": _to_iso(event.timestamp),
                "retries": int(event.retries),
            }
        )


class WebSocketHub:
    def __init__(self, bus: EventBus) -> None:
        self._bus = bus
        self._lock = asyncio.Lock()
        self._connections: Dict[str, WebSocket] = {}
        self._tokens: Dict[str, str] = {}

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        conn_id = secrets.token_urlsafe(12)
        async with self._lock:
            self._connections[conn_id] = websocket

        loop = asyncio.get_running_loop()

        def _cb(message: Dict[str, Any]) -> None:
            asyncio.run_coroutine_threadsafe(self._send(conn_id, message), loop)

        token = self._bus.subscribe(_cb)
        async with self._lock:
            self._tokens[conn_id] = token
        return conn_id

    async def disconnect(self, conn_id: str) -> None:
        async with self._lock:
            token = self._tokens.pop(conn_id, None)
            self._connections.pop(conn_id, None)
        if token:
            self._bus.unsubscribe(token)

    async def _send(self, conn_id: str, message: Dict[str, Any]) -> None:
        async with self._lock:
            ws = self._connections.get(conn_id)
        if ws is None:
            return
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            await self.disconnect(conn_id)


class TaskEventIn(BaseModel):
    task_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    status: TaskStatus
    worker: Optional[str] = None
    timestamp: Optional[datetime] = None
    args: Optional[str] = None
    kwargs: Optional[str] = None
    result: Optional[str] = None
    traceback: Optional[str] = None
    retries: int = 0
    eta: Optional[datetime] = None
    expires: Optional[datetime] = None


class RetryRequest(BaseModel):
    task_id: str = Field(..., min_length=1)


class HeartbeatIn(BaseModel):
    worker: str = Field(..., min_length=1)
    timestamp: Optional[datetime] = None


class KanchiApp:
    def __init__(self, db_path: str = "kanchi.sqlite3", worker_stale_after_seconds: int = 30) -> None:
        self._db = Database(db_path)
        self._migrations = MigrationManager(self._db)
        self._migrations.migrate()

        self._bus = EventBus()
        self._tasks = TaskRepository(self._db)
        self._workers = WorkerRepository(self._db)
        self._stats = StatsRepository(self._db)
        self._orphans = OrphanDetector(self._db)
        self._service = TaskService(self._tasks, self._workers, self._stats, self._bus)
        self._hub = WebSocketHub(self._bus)

        self._worker_stale_after_seconds = worker_stale_after_seconds

        self.app = FastAPI(title="Kanchi", version="1.0")
        self._register_routes()
        self._register_background_tasks()

    def _register_background_tasks(self) -> None:
        @self.app.on_event("startup")
        async def _startup() -> None:
            asyncio.create_task(self._worker_health_loop())

        @self.app.on_event("shutdown")
        async def _shutdown() -> None:
            self._db.close()

    async def _worker_health_loop(self) -> None:
        while True:
            try:
                self._workers.mark_offline_if_stale(self._worker_stale_after_seconds)
                self._bus.publish({"type": "worker_health_tick", "timestamp": _to_iso(_utcnow())})
            except Exception:
                pass
            await asyncio.sleep(max(1, self._worker_stale_after_seconds // 2))

    def _register_routes(self) -> None:
        @self.app.get("/health")
        async def health() -> Dict[str, Any]:
            return {"status": "ok", "time": _to_iso(_utcnow())}

        @self.app.post("/events/task")
        async def ingest_task_event(payload: TaskEventIn) -> Dict[str, Any]:
            ts = payload.timestamp or _utcnow()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            event = TaskEvent(
                task_id=payload.task_id,
                name=payload.name,
                status=payload.status,
                worker=payload.worker,
                timestamp=ts.astimezone(UTC),
                args=payload.args,
                kwargs=payload.kwargs,
                result=payload.result,
                traceback=payload.traceback,
                retries=int(payload.retries),
                eta=payload.eta.astimezone(UTC) if payload.eta and payload.eta.tzinfo else payload.eta.replace(tzinfo=UTC).astimezone(UTC) if payload.eta else None,
                expires=payload.expires.astimezone(UTC) if payload.expires and payload.expires.tzinfo else payload.expires.replace(tzinfo=UTC).astimezone(UTC) if payload.expires else None,
            )
            try:
                self._service.ingest_event(event)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            return {"ok": True}

        @self.app.post("/workers/heartbeat")
        async def worker_heartbeat(payload: HeartbeatIn) -> Dict[str, Any]:
            ts = payload.timestamp or _utcnow()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            try:
                self._workers.heartbeat(payload.worker, at=ts.astimezone(UTC))
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            self._bus.publish({"type": "worker_heartbeat", "worker": payload.worker, "timestamp": _to_iso(ts.astimezone(UTC))})
            return {"ok": True}

        @self.app.get("/tasks")
        async def list_tasks(
            date_from: Optional[str] = Query(None),
            date_to: Optional[str] = Query(None),
            status: Optional[TaskStatus] = Query(None),
            name: Optional[str] = Query(None),
            worker: Optional[str] = Query(None),
            q: Optional[str] = Query(None),
            limit: int = Query(100, ge=1, le=1000),
            offset: int = Query(0, ge=0),
        ) -> JSONResponse:
            try:
                df = _parse_dt(date_from)
                dt = _parse_dt(date_to)
                items = self._tasks.list_tasks(
                    date_from=df,
                    date_to=dt,
                    status=status,
                    name=name,
                    worker=worker,
                    q=q,
                    limit=limit,
                    offset=offset,
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            return JSONResponse({"items": items, "limit": limit, "offset": offset})

        @self.app.get("/tasks/{task_id}")
        async def get_task(task_id: str) -> JSONResponse:
            task = self._tasks.get_task(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="task not found")
            return JSONResponse(task)

        @self.app.get("/tasks/{task_id}/events")
        async def get_task_events(task_id: str, limit: int = Query(200, ge=1, le=2000)) -> JSONResponse:
            task = self._tasks.get_task(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="task not found")
            try:
                events = self._tasks.list_task_events(task_id, limit=limit)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            return JSONResponse({"task_id": task_id, "events": events})

        @self.app.get("/tasks/orphans")
        async def list_orphans(
            started_before_seconds: int = Query(3600, ge=1, le=7 * 24 * 3600),
            limit: int = Query(200, ge=1, le=2000),
        ) -> JSONResponse:
            try:
                items = self._orphans.find_orphans(started_before_seconds=started_before_seconds, limit=limit)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            return JSONResponse({"items": items})

        @self.app.get("/workers")
        async def list_workers() -> JSONResponse:
            items = self._workers.list_workers()
            return JSONResponse({"items": items})

        @self.app.get("/workers/{name}")
        async def get_worker(name: str) -> JSONResponse:
            w = self._workers.get_worker(name)
            if not w:
                raise HTTPException(status_code=404, detail="worker not found")
            return JSONResponse(w)

        @self.app.get("/stats/daily")
        async def daily_stats(day: Optional[str] = Query(None)) -> JSONResponse:
            if day is None:
                d = _utcnow().date()
            else:
                try:
                    d = date.fromisoformat(day)
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid day format; expected YYYY-MM-DD")
            items = self._stats.get_daily(d)
            return JSONResponse({"day": d.isoformat(), "items": items})

        @self.app.get("/stats/range")
        async def range_stats(day_from: str = Query(...), day_to: str = Query(...)) -> JSONResponse:
            try:
                df = date.fromisoformat(day_from)
                dt = date.fromisoformat(day_to)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid day format; expected YYYY-MM-DD")
            try:
                items = self._stats.get_range(df, dt)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            return JSONResponse({"from": df.isoformat(), "to": dt.isoformat(), "items": items})

        @self.app.websocket("/ws")
        async def ws_endpoint(websocket: WebSocket) -> None:
            conn_id = await self._hub.connect(websocket)
            try:
                await websocket.send_text(json.dumps({"type": "welcome", "timestamp": _to_iso(_utcnow())}))
                while True:
                    msg = await websocket.receive_text()
                    try:
                        data = json.loads(msg)
                    except Exception:
                        await websocket.send_text(json.dumps({"type": "error", "error": "invalid_json"}))
                        continue
                    if isinstance(data, dict) and data.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong", "timestamp": _to_iso(_utcnow())}))
                    else:
                        await websocket.send_text(json.dumps({"type": "ack"}))
            except WebSocketDisconnect:
                pass
            finally:
                await self._hub.disconnect(conn_id)


kanchi = KanchiApp()
app = kanchi.app