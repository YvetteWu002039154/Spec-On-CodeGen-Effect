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
from pydantic import BaseModel, Field


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
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


class WorkerStatus(str, Enum):
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


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
    eta: Optional[datetime] = None
    expires: Optional[datetime] = None


class Database:
    def __init__(self, path: str = "kanchi.db") -> None:
        self._path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._apply_migrations()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _apply_migrations(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                );
                """
            )
            self._conn.commit()

            cur.execute("SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations;")
            row = cur.fetchone()
            current = int(row["v"]) if row else 0

            migrations: List[Tuple[int, Callable[[sqlite3.Connection], None]]] = [
                (1, self._migration_1),
            ]

            for version, fn in migrations:
                if version > current:
                    fn(self._conn)
                    cur.execute(
                        "INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?);",
                        (version, _to_iso(_utcnow())),
                    )
                    self._conn.commit()

    def _migration_1(self, conn: sqlite3.Connection) -> None:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                worker TEXT,
                created_at TEXT NOT NULL,
                received_at TEXT,
                started_at TEXT,
                finished_at TEXT,
                args TEXT,
                kwargs TEXT,
                result TEXT,
                exception TEXT,
                traceback TEXT,
                retries INTEGER NOT NULL DEFAULT 0,
                last_event_at TEXT NOT NULL,
                eta TEXT,
                expires TEXT
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_name ON tasks(name);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_last_event_at ON tasks(last_event_at);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);")

        cur.execute(
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
                eta TEXT,
                expires TEXT,
                FOREIGN KEY(task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_task_events_task_id ON task_events(task_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_task_events_timestamp ON task_events(timestamp);")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS workers (
                worker TEXT PRIMARY KEY,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                status TEXT NOT NULL
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_workers_last_seen_at ON workers(last_seen_at);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_workers_status ON workers(status);")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_task_stats (
                day TEXT PRIMARY KEY,
                total INTEGER NOT NULL,
                success INTEGER NOT NULL,
                failure INTEGER NOT NULL,
                retry INTEGER NOT NULL,
                revoked INTEGER NOT NULL,
                started INTEGER NOT NULL,
                pending INTEGER NOT NULL,
                received INTEGER NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

        conn.commit()

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
        existing = self._db.query_one("SELECT * FROM tasks WHERE task_id = ?;", (ev.task_id,))
        now_iso = _to_iso(ev.timestamp)
        if existing is None:
            created_at = now_iso
            received_at = now_iso if ev.status == TaskStatus.RECEIVED else None
            started_at = now_iso if ev.status == TaskStatus.STARTED else None
            finished_at = now_iso if ev.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED) else None
            self._db.execute(
                """
                INSERT INTO tasks(
                    task_id, name, status, worker, created_at, received_at, started_at, finished_at,
                    args, kwargs, result, exception, traceback, retries, last_event_at, eta, expires
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    ev.task_id,
                    ev.name,
                    ev.status.value,
                    ev.worker,
                    created_at,
                    received_at,
                    started_at,
                    finished_at,
                    ev.args,
                    ev.kwargs,
                    ev.result,
                    ev.exception,
                    ev.traceback,
                    int(ev.retries),
                    now_iso,
                    _to_iso(ev.eta),
                    _to_iso(ev.expires),
                ),
            )
        else:
            received_at = existing["received_at"]
            started_at = existing["started_at"]
            finished_at = existing["finished_at"]

            if ev.status == TaskStatus.RECEIVED and received_at is None:
                received_at = now_iso
            if ev.status == TaskStatus.STARTED and started_at is None:
                started_at = now_iso
            if ev.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED):
                finished_at = now_iso

            retries = max(int(existing["retries"]), int(ev.retries))

            self._db.execute(
                """
                UPDATE tasks SET
                    name = ?,
                    status = ?,
                    worker = COALESCE(?, worker),
                    received_at = ?,
                    started_at = ?,
                    finished_at = ?,
                    args = COALESCE(?, args),
                    kwargs = COALESCE(?, kwargs),
                    result = COALESCE(?, result),
                    exception = COALESCE(?, exception),
                    traceback = COALESCE(?, traceback),
                    retries = ?,
                    last_event_at = ?,
                    eta = COALESCE(?, eta),
                    expires = COALESCE(?, expires)
                WHERE task_id = ?;
                """,
                (
                    ev.name,
                    ev.status.value,
                    ev.worker,
                    received_at,
                    started_at,
                    finished_at,
                    ev.args,
                    ev.kwargs,
                    ev.result,
                    ev.exception,
                    ev.traceback,
                    retries,
                    now_iso,
                    _to_iso(ev.eta),
                    _to_iso(ev.expires),
                    ev.task_id,
                ),
            )

        self._db.execute(
            """
            INSERT INTO task_events(
                task_id, name, status, worker, timestamp, args, kwargs, result, exception, traceback, retries, eta, expires
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                ev.task_id,
                ev.name,
                ev.status.value,
                ev.worker,
                now_iso,
                ev.args,
                ev.kwargs,
                ev.result,
                ev.exception,
                ev.traceback,
                int(ev.retries),
                _to_iso(ev.eta),
                _to_iso(ev.expires),
            ),
        )

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        row = self._db.query_one("SELECT * FROM tasks WHERE task_id = ?;", (task_id,))
        if row is None:
            return None
        return dict(row)

    def get_task_events(self, task_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 2000))
        rows = self._db.query(
            "SELECT * FROM task_events WHERE task_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?;",
            (task_id, limit),
        )
        return [dict(r) for r in rows]

    def search_tasks(
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
    ) -> List[Dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        offset = max(0, int(offset))

        clauses: List[str] = []
        params: List[Any] = []

        if date_from is not None:
            clauses.append("created_at >= ?")
            params.append(_to_iso(date_from))
        if date_to is not None:
            clauses.append("created_at <= ?")
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
        if q is not None and q.strip():
            qq = f"%{q.strip()}%"
            clauses.append(
                "("
                "task_id LIKE ? OR name LIKE ? OR COALESCE(worker,'') LIKE ? OR "
                "COALESCE(args,'') LIKE ? OR COALESCE(kwargs,'') LIKE ? OR "
                "COALESCE(result,'') LIKE ? OR COALESCE(exception,'') LIKE ? OR COALESCE(traceback,'') LIKE ?"
                ")"
            )
            params.extend([qq, qq, qq, qq, qq, qq, qq, qq])

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM tasks {where} ORDER BY last_event_at DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])
        rows = self._db.query(sql, params)
        return [dict(r) for r in rows]

    def detect_orphans(self, *, orphan_after_seconds: int = 900, limit: int = 200) -> List[Dict[str, Any]]:
        orphan_after_seconds = max(30, int(orphan_after_seconds))
        limit = max(1, min(int(limit), 1000))
        cutoff = _utcnow() - timedelta(seconds=orphan_after_seconds)
        rows = self._db.query(
            """
            SELECT * FROM tasks
            WHERE status IN (?, ?, ?)
              AND last_event_at < ?
            ORDER BY last_event_at ASC
            LIMIT ?;
            """,
            (TaskStatus.PENDING.value, TaskStatus.RECEIVED.value, TaskStatus.STARTED.value, _to_iso(cutoff), limit),
        )
        return [dict(r) for r in rows]


class WorkerRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def touch(self, worker: str, seen_at: datetime) -> None:
        if not worker:
            return
        row = self._db.query_one("SELECT * FROM workers WHERE worker = ?;", (worker,))
        ts = _to_iso(seen_at)
        if row is None:
            self._db.execute(
                "INSERT INTO workers(worker, first_seen_at, last_seen_at, status) VALUES(?, ?, ?, ?);",
                (worker, ts, ts, WorkerStatus.HEALTHY.value),
            )
        else:
            self._db.execute(
                "UPDATE workers SET last_seen_at = ?, status = ? WHERE worker = ?;",
                (ts, WorkerStatus.HEALTHY.value, worker),
            )

    def set_status(self, worker: str, status: WorkerStatus) -> None:
        row = self._db.query_one("SELECT * FROM workers WHERE worker = ?;", (worker,))
        if row is None:
            now = _utcnow()
            self._db.execute(
                "INSERT INTO workers(worker, first_seen_at, last_seen_at, status) VALUES(?, ?, ?, ?);",
                (worker, _to_iso(now), _to_iso(now), status.value),
            )
        else:
            self._db.execute("UPDATE workers SET status = ? WHERE worker = ?;", (status.value, worker))

    def list_workers(self) -> List[Dict[str, Any]]:
        rows = self._db.query("SELECT * FROM workers ORDER BY last_seen_at DESC;")
        return [dict(r) for r in rows]

    def update_health(self, *, unhealthy_after_seconds: int = 60) -> None:
        unhealthy_after_seconds = max(5, int(unhealthy_after_seconds))
        cutoff = _utcnow() - timedelta(seconds=unhealthy_after_seconds)
        self._db.execute(
            "UPDATE workers SET status = ? WHERE last_seen_at < ?;",
            (WorkerStatus.UNHEALTHY.value, _to_iso(cutoff)),
        )
        self._db.execute(
            "UPDATE workers SET status = ? WHERE last_seen_at >= ?;",
            (WorkerStatus.HEALTHY.value, _to_iso(cutoff)),
        )


class DailyStatsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def _day_key(self, dt: datetime) -> str:
        d = dt.astimezone(timezone.utc).date()
        return d.isoformat()

    def update_for_event(self, ev: TaskEvent) -> None:
        day = self._day_key(ev.timestamp)
        row = self._db.query_one("SELECT * FROM daily_task_stats WHERE day = ?;", (day,))
        if row is None:
            counts = {
                TaskStatus.SUCCESS: 0,
                TaskStatus.FAILURE: 0,
                TaskStatus.RETRY: 0,
                TaskStatus.REVOKED: 0,
                TaskStatus.STARTED: 0,
                TaskStatus.PENDING: 0,
                TaskStatus.RECEIVED: 0,
            }
            if ev.status in counts:
                counts[ev.status] += 1
            total = sum(counts.values())
            self._db.execute(
                """
                INSERT INTO daily_task_stats(day, total, success, failure, retry, revoked, started, pending, received, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    day,
                    total,
                    counts[TaskStatus.SUCCESS],
                    counts[TaskStatus.FAILURE],
                    counts[TaskStatus.RETRY],
                    counts[TaskStatus.REVOKED],
                    counts[TaskStatus.STARTED],
                    counts[TaskStatus.PENDING],
                    counts[TaskStatus.RECEIVED],
                    _to_iso(_utcnow()),
                ),
            )
        else:
            col_map = {
                TaskStatus.SUCCESS: "success",
                TaskStatus.FAILURE: "failure",
                TaskStatus.RETRY: "retry",
                TaskStatus.REVOKED: "revoked",
                TaskStatus.STARTED: "started",
                TaskStatus.PENDING: "pending",
                TaskStatus.RECEIVED: "received",
            }
            if ev.status in col_map:
                col = col_map[ev.status]
                self._db.execute(
                    f"""
                    UPDATE daily_task_stats
                    SET {col} = {col} + 1,
                        total = total + 1,
                        updated_at = ?
                    WHERE day = ?;
                    """,
                    (_to_iso(_utcnow()), day),
                )

    def get_range(self, day_from: date, day_to: date) -> List[Dict[str, Any]]:
        if day_to < day_from:
            day_from, day_to = day_to, day_from
        rows = self._db.query(
            "SELECT * FROM daily_task_stats WHERE day >= ? AND day <= ? ORDER BY day ASC;",
            (day_from.isoformat(), day_to.isoformat()),
        )
        return [dict(r) for r in rows]


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: Set[asyncio.Queue[str]] = set()

    async def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=1000)
        with self._lock:
            self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        with self._lock:
            self._subscribers.discard(q)

    def publish(self, message: Dict[str, Any]) -> None:
        payload = json.dumps(message, default=str)
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass


class KanchiService:
    def __init__(self, db_path: str = "kanchi.db") -> None:
        self._db = Database(db_path)
        self._tasks = TaskRepository(self._db)
        self._workers = WorkerRepository(self._db)
        self._stats = DailyStatsRepository(self._db)
        self._bus = EventBus()

    @property
    def bus(self) -> EventBus:
        return self._bus

    def ingest_event(self, ev: TaskEvent) -> None:
        self._tasks.upsert_task_from_event(ev)
        if ev.worker:
            self._workers.touch(ev.worker, ev.timestamp)
        self._stats.update_for_event(ev)
        self._bus.publish(
            {
                "type": "task_event",
                "task_id": ev.task_id,
                "name": ev.name,
                "status": ev.status.value,
                "worker": ev.worker,
                "timestamp": _to_iso(ev.timestamp),
                "retries": ev.retries,
            }
        )

    def update_worker_health(self, unhealthy_after_seconds: int = 60) -> None:
        self._workers.update_health(unhealthy_after_seconds=unhealthy_after_seconds)

    def search_tasks(
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
    ) -> List[Dict[str, Any]]:
        return self._tasks.search_tasks(
            date_from=date_from,
            date_to=date_to,
            status=status,
            name=name,
            worker=worker,
            q=q,
            limit=limit,
            offset=offset,
        )

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get_task(task_id)

    def get_task_events(self, task_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        return self._tasks.get_task_events(task_id, limit=limit)

    def detect_orphans(self, orphan_after_seconds: int = 900, limit: int = 200) -> List[Dict[str, Any]]:
        return self._tasks.detect_orphans(orphan_after_seconds=orphan_after_seconds, limit=limit)

    def list_workers(self) -> List[Dict[str, Any]]:
        return self._workers.list_workers()

    def get_daily_stats(self, day_from: date, day_to: date) -> List[Dict[str, Any]]:
        return self._stats.get_range(day_from, day_to)


class IngestEventModel(BaseModel):
    task_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    status: TaskStatus
    worker: Optional[str] = None
    timestamp: Optional[datetime] = None
    args: Optional[Union[str, Dict[str, Any], List[Any]]] = None
    kwargs: Optional[Union[str, Dict[str, Any]]] = None
    result: Optional[Union[str, Dict[str, Any], List[Any]]] = None
    exception: Optional[str] = None
    traceback: Optional[str] = None
    retries: int = 0
    eta: Optional[datetime] = None
    expires: Optional[datetime] = None

    def to_event(self) -> TaskEvent:
        ts = self.timestamp or _utcnow()

        def _norm(v: Any) -> Optional[str]:
            if v is None:
                return None
            if isinstance(v, str):
                return v
            return json.dumps(v, default=str)

        return TaskEvent(
            task_id=self.task_id,
            name=self.name,
            status=self.status,
            worker=self.worker,
            timestamp=ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc),
            args=_norm(self.args),
            kwargs=_norm(self.kwargs),
            result=_norm(self.result),
            exception=self.exception,
            traceback=self.traceback,
            retries=int(self.retries),
            eta=self.eta if (self.eta is None or self.eta.tzinfo) else self.eta.replace(tzinfo=timezone.utc),
            expires=self.expires if (self.expires is None or self.expires.tzinfo) else self.expires.replace(tzinfo=timezone.utc),
        )


def create_app(db_path: str = "kanchi.db") -> FastAPI:
    service = KanchiService(db_path=db_path)
    app = FastAPI(title="Kanchi", version="1.0.0")

    async def _health_loop() -> None:
        while True:
            try:
                service.update_worker_health(unhealthy_after_seconds=60)
            except Exception:
                pass
            await asyncio.sleep(5)

    @app.on_event("startup")
    async def _startup() -> None:
        asyncio.create_task(_health_loop())

    @app.post("/api/events")
    async def ingest_event(payload: IngestEventModel) -> JSONResponse:
        ev = payload.to_event()
        service.ingest_event(ev)
        return JSONResponse({"ok": True})

    @app.get("/api/tasks")
    async def list_tasks(
        date_from: Optional[datetime] = Query(default=None),
        date_to: Optional[datetime] = Query(default=None),
        status: Optional[TaskStatus] = Query(default=None),
        name: Optional[str] = Query(default=None),
        worker: Optional[str] = Query(default=None),
        q: Optional[str] = Query(default=None),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> JSONResponse:
        items = service.search_tasks(
            date_from=date_from,
            date_to=date_to,
            status=status,
            name=name,
            worker=worker,
            q=q,
            limit=limit,
            offset=offset,
        )
        return JSONResponse({"items": items, "limit": limit, "offset": offset})

    @app.get("/api/tasks/{task_id}")
    async def get_task(task_id: str) -> JSONResponse:
        task = service.get_task(task_id)
        if task is None:
            return JSONResponse({"error": "not_found"}, status_code=404)
        events = service.get_task_events(task_id, limit=500)
        return JSONResponse({"task": task, "events": events})

    @app.get("/api/tasks/orphans")
    async def get_orphans(
        orphan_after_seconds: int = Query(default=900, ge=30, le=86400),
        limit: int = Query(default=200, ge=1, le=1000),
    ) -> JSONResponse:
        items = service.detect_orphans(orphan_after_seconds=orphan_after_seconds, limit=limit)
        return JSONResponse({"items": items})

    @app.get("/api/workers")
    async def list_workers() -> JSONResponse:
        items = service.list_workers()
        return JSONResponse({"items": items})

    @app.get("/api/stats/daily")
    async def daily_stats(
        day_from: date = Query(...),
        day_to: date = Query(...),
    ) -> JSONResponse:
        items = service.get_daily_stats(day_from, day_to)
        return JSONResponse({"items": items})

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        q = await service.bus.subscribe()
        try:
            while True:
                msg = await q.get()
                await ws.send_text(msg)
        except WebSocketDisconnect:
            pass
        finally:
            service.bus.unsubscribe(q)

    return app


app = create_app()