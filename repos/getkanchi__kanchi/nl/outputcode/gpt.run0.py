from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.websockets import WebSocketState


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


def _utc_now_ts() -> float:
    return time.time()


def _ts_to_iso(ts: Optional[float]) -> Optional[str]:
    if ts is None:
        return None
    return datetime.utcfromtimestamp(ts).isoformat() + "Z"


def _iso_to_ts(iso: Optional[str]) -> Optional[float]:
    if iso is None:
        return None
    s = iso.strip()
    if s.endswith("Z"):
        s = s[:-1]
    dt = datetime.fromisoformat(s)
    return dt.timestamp()


def _date_from_ts(ts: float) -> str:
    return datetime.utcfromtimestamp(ts).date().isoformat()


def _normalize_text(s: Optional[str]) -> str:
    return (s or "").strip()


class Database:
    def __init__(self, path: str = "kanchi.db") -> None:
        self._path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def _executemany(self, sql: str, seq_of_params: Iterable[Sequence[Any]]) -> None:
        with self._lock:
            self._conn.executemany(sql, seq_of_params)
            self._conn.commit()

    def _ensure_schema(self) -> None:
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at REAL NOT NULL
            )
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                worker TEXT,
                args_json TEXT,
                kwargs_json TEXT,
                result_json TEXT,
                error TEXT,
                retries INTEGER NOT NULL DEFAULT 0,
                created_at REAL NOT NULL,
                received_at REAL,
                started_at REAL,
                finished_at REAL,
                updated_at REAL NOT NULL
            )
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS task_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                status TEXT,
                worker TEXT,
                message TEXT,
                created_at REAL NOT NULL,
                FOREIGN KEY(task_id) REFERENCES tasks(id)
            )
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS workers (
                name TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                last_heartbeat REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS daily_task_stats (
                day TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                count INTEGER NOT NULL,
                updated_at REAL NOT NULL,
                PRIMARY KEY(day, name, status)
            )
            """
        )
        self._apply_migrations()

    def _apply_migrations(self) -> None:
        migrations: List[Tuple[str, Callable[[], None]]] = [
            ("0001_initial", lambda: None),
        ]
        existing = {
            row["version"]
            for row in self._execute("SELECT version FROM schema_migrations").fetchall()
        }
        for version, fn in migrations:
            if version in existing:
                continue
            fn()
            self._execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)",
                (version, _utc_now_ts()),
            )


@dataclass(frozen=True)
class TaskRecord:
    id: str
    name: str
    status: TaskStatus
    worker: Optional[str]
    args: Optional[Any]
    kwargs: Optional[Any]
    result: Optional[Any]
    error: Optional[str]
    retries: int
    created_at: float
    received_at: Optional[float]
    started_at: Optional[float]
    finished_at: Optional[float]
    updated_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "worker": self.worker,
            "args": self.args,
            "kwargs": self.kwargs,
            "result": self.result,
            "error": self.error,
            "retries": self.retries,
            "created_at": _ts_to_iso(self.created_at),
            "received_at": _ts_to_iso(self.received_at),
            "started_at": _ts_to_iso(self.started_at),
            "finished_at": _ts_to_iso(self.finished_at),
            "updated_at": _ts_to_iso(self.updated_at),
        }


@dataclass(frozen=True)
class WorkerRecord:
    name: str
    status: WorkerStatus
    last_heartbeat: float
    updated_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "last_heartbeat": _ts_to_iso(self.last_heartbeat),
            "updated_at": _ts_to_iso(self.updated_at),
        }


class TaskRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def upsert_task(
        self,
        task_id: str,
        name: str,
        status: TaskStatus,
        worker: Optional[str] = None,
        args: Optional[Any] = None,
        kwargs: Optional[Any] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        retries: Optional[int] = None,
        created_at: Optional[float] = None,
        received_at: Optional[float] = None,
        started_at: Optional[float] = None,
        finished_at: Optional[float] = None,
        updated_at: Optional[float] = None,
    ) -> TaskRecord:
        if not task_id or not _normalize_text(task_id):
            raise ValueError("task_id is required")
        if not name or not _normalize_text(name):
            raise ValueError("name is required")
        now = _utc_now_ts()
        created = created_at if created_at is not None else now
        upd = updated_at if updated_at is not None else now

        row = self._db._execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            r = int(retries or 0)
            self._db._execute(
                """
                INSERT INTO tasks(
                    id, name, status, worker, args_json, kwargs_json, result_json, error,
                    retries, created_at, received_at, started_at, finished_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    name,
                    status.value,
                    worker,
                    json.dumps(args) if args is not None else None,
                    json.dumps(kwargs) if kwargs is not None else None,
                    json.dumps(result) if result is not None else None,
                    error,
                    r,
                    created,
                    received_at,
                    started_at,
                    finished_at,
                    upd,
                ),
            )
        else:
            current_retries = int(row["retries"])
            r = current_retries if retries is None else int(retries)
            self._db._execute(
                """
                UPDATE tasks SET
                    name = ?,
                    status = ?,
                    worker = ?,
                    args_json = COALESCE(?, args_json),
                    kwargs_json = COALESCE(?, kwargs_json),
                    result_json = COALESCE(?, result_json),
                    error = COALESCE(?, error),
                    retries = ?,
                    received_at = COALESCE(?, received_at),
                    started_at = COALESCE(?, started_at),
                    finished_at = COALESCE(?, finished_at),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    name,
                    status.value,
                    worker,
                    json.dumps(args) if args is not None else None,
                    json.dumps(kwargs) if kwargs is not None else None,
                    json.dumps(result) if result is not None else None,
                    error,
                    r,
                    received_at,
                    started_at,
                    finished_at,
                    upd,
                    task_id,
                ),
            )

        return self.get_task(task_id)

    def get_task(self, task_id: str) -> TaskRecord:
        row = self._db._execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        return self._row_to_task(row)

    def add_event(
        self,
        task_id: str,
        event_type: str,
        status: Optional[TaskStatus] = None,
        worker: Optional[str] = None,
        message: Optional[str] = None,
        created_at: Optional[float] = None,
    ) -> None:
        if not task_id or not _normalize_text(task_id):
            raise ValueError("task_id is required")
        if not event_type or not _normalize_text(event_type):
            raise ValueError("event_type is required")
        ts = created_at if created_at is not None else _utc_now_ts()
        self._db._execute(
            """
            INSERT INTO task_events(task_id, event_type, status, worker, message, created_at)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (task_id, event_type, status.value if status else None, worker, message, ts),
        )

    def list_events(self, task_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        lim = max(1, min(int(limit), 1000))
        rows = self._db._execute(
            """
            SELECT id, task_id, event_type, status, worker, message, created_at
            FROM task_events
            WHERE task_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (task_id, lim),
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "id": r["id"],
                    "task_id": r["task_id"],
                    "event_type": r["event_type"],
                    "status": r["status"],
                    "worker": r["worker"],
                    "message": r["message"],
                    "created_at": _ts_to_iso(r["created_at"]),
                }
            )
        return out

    def search_tasks(
        self,
        *,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        status: Optional[TaskStatus] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_desc: bool = True,
    ) -> List[TaskRecord]:
        lim = max(1, min(int(limit), 500))
        off = max(0, int(offset))
        clauses: List[str] = []
        params: List[Any] = []

        if date_from is not None:
            start_ts = datetime.combine(date_from, datetime.min.time()).timestamp()
            clauses.append("created_at >= ?")
            params.append(start_ts)
        if date_to is not None:
            end_ts = datetime.combine(date_to, datetime.max.time()).timestamp()
            clauses.append("created_at <= ?")
            params.append(end_ts)
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if name is not None and _normalize_text(name):
            clauses.append("name = ?")
            params.append(name.strip())
        if worker is not None and _normalize_text(worker):
            clauses.append("worker = ?")
            params.append(worker.strip())
        if q is not None and _normalize_text(q):
            qq = f"%{q.strip()}%"
            clauses.append(
                "(id LIKE ? OR name LIKE ? OR worker LIKE ? OR error LIKE ? OR args_json LIKE ? OR kwargs_json LIKE ? OR result_json LIKE ?)"
            )
            params.extend([qq, qq, qq, qq, qq, qq, qq])

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        order = "ORDER BY updated_at DESC" if order_desc else "ORDER BY updated_at ASC"
        rows = self._db._execute(
            f"""
            SELECT * FROM tasks
            {where}
            {order}
            LIMIT ? OFFSET ?
            """,
            (*params, lim, off),
        ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def detect_orphans(self, *, older_than_seconds: int = 3600) -> List[TaskRecord]:
        threshold = _utc_now_ts() - max(1, int(older_than_seconds))
        rows = self._db._execute(
            """
            SELECT * FROM tasks
            WHERE status IN (?, ?, ?, ?)
              AND updated_at < ?
            ORDER BY updated_at ASC
            """,
            (
                TaskStatus.PENDING.value,
                TaskStatus.RECEIVED.value,
                TaskStatus.STARTED.value,
                TaskStatus.RETRY.value,
                threshold,
            ),
        ).fetchall()
        return [self._row_to_task(r) for r in rows]

    def _row_to_task(self, row: sqlite3.Row) -> TaskRecord:
        def _loads(v: Any) -> Any:
            if v is None:
                return None
            try:
                return json.loads(v)
            except Exception:
                return None

        return TaskRecord(
            id=row["id"],
            name=row["name"],
            status=TaskStatus(row["status"]),
            worker=row["worker"],
            args=_loads(row["args_json"]),
            kwargs=_loads(row["kwargs_json"]),
            result=_loads(row["result_json"]),
            error=row["error"],
            retries=int(row["retries"]),
            created_at=float(row["created_at"]),
            received_at=float(row["received_at"]) if row["received_at"] is not None else None,
            started_at=float(row["started_at"]) if row["started_at"] is not None else None,
            finished_at=float(row["finished_at"]) if row["finished_at"] is not None else None,
            updated_at=float(row["updated_at"]),
        )


class WorkerRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def heartbeat(self, name: str, ts: Optional[float] = None) -> WorkerRecord:
        n = _normalize_text(name)
        if not n:
            raise ValueError("worker name is required")
        now = ts if ts is not None else _utc_now_ts()
        row = self._db._execute("SELECT * FROM workers WHERE name = ?", (n,)).fetchone()
        if row is None:
            self._db._execute(
                "INSERT INTO workers(name, status, last_heartbeat, updated_at) VALUES(?, ?, ?, ?)",
                (n, WorkerStatus.ONLINE.value, now, now),
            )
        else:
            self._db._execute(
                "UPDATE workers SET status = ?, last_heartbeat = ?, updated_at = ? WHERE name = ?",
                (WorkerStatus.ONLINE.value, now, now, n),
            )
        return self.get(n)

    def set_status(self, name: str, status: WorkerStatus, ts: Optional[float] = None) -> WorkerRecord:
        n = _normalize_text(name)
        if not n:
            raise ValueError("worker name is required")
        now = ts if ts is not None else _utc_now_ts()
        row = self._db._execute("SELECT * FROM workers WHERE name = ?", (n,)).fetchone()
        if row is None:
            self._db._execute(
                "INSERT INTO workers(name, status, last_heartbeat, updated_at) VALUES(?, ?, ?, ?)",
                (n, status.value, now, now),
            )
        else:
            self._db._execute(
                "UPDATE workers SET status = ?, updated_at = ? WHERE name = ?",
                (status.value, now, n),
            )
        return self.get(n)

    def get(self, name: str) -> WorkerRecord:
        n = _normalize_text(name)
        row = self._db._execute("SELECT * FROM workers WHERE name = ?", (n,)).fetchone()
        if row is None:
            raise KeyError(n)
        return WorkerRecord(
            name=row["name"],
            status=WorkerStatus(row["status"]),
            last_heartbeat=float(row["last_heartbeat"]),
            updated_at=float(row["updated_at"]),
        )

    def list(self) -> List[WorkerRecord]:
        rows = self._db._execute("SELECT * FROM workers ORDER BY name ASC").fetchall()
        return [
            WorkerRecord(
                name=r["name"],
                status=WorkerStatus(r["status"]),
                last_heartbeat=float(r["last_heartbeat"]),
                updated_at=float(r["updated_at"]),
            )
            for r in rows
        ]

    def mark_offline_stale(self, *, stale_after_seconds: int = 60) -> List[WorkerRecord]:
        stale = _utc_now_ts() - max(1, int(stale_after_seconds))
        self._db._execute(
            "UPDATE workers SET status = ?, updated_at = ? WHERE last_heartbeat < ?",
            (WorkerStatus.OFFLINE.value, _utc_now_ts(), stale),
        )
        return self.list()


class StatsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def increment(self, day: str, name: str, status: TaskStatus, delta: int = 1) -> None:
        d = _normalize_text(day)
        n = _normalize_text(name)
        if not d:
            raise ValueError("day is required")
        if not n:
            raise ValueError("name is required")
        if delta == 0:
            return
        now = _utc_now_ts()
        row = self._db._execute(
            "SELECT count FROM daily_task_stats WHERE day = ? AND name = ? AND status = ?",
            (d, n, status.value),
        ).fetchone()
        if row is None:
            self._db._execute(
                "INSERT INTO daily_task_stats(day, name, status, count, updated_at) VALUES(?, ?, ?, ?, ?)",
                (d, n, status.value, int(delta), now),
            )
        else:
            self._db._execute(
                "UPDATE daily_task_stats SET count = count + ?, updated_at = ? WHERE day = ? AND name = ? AND status = ?",
                (int(delta), now, d, n, status.value),
            )

    def get_day(self, day: str) -> List[Dict[str, Any]]:
        d = _normalize_text(day)
        rows = self._db._execute(
            """
            SELECT day, name, status, count, updated_at
            FROM daily_task_stats
            WHERE day = ?
            ORDER BY name ASC, status ASC
            """,
            (d,),
        ).fetchall()
        return [
            {
                "day": r["day"],
                "name": r["name"],
                "status": r["status"],
                "count": int(r["count"]),
                "updated_at": _ts_to_iso(float(r["updated_at"])),
            }
            for r in rows
        ]

    def history(self, *, days: int = 30, name: Optional[str] = None) -> List[Dict[str, Any]]:
        d = max(1, min(int(days), 365))
        cutoff = (datetime.utcfromtimestamp(_utc_now_ts()).date().toordinal() - (d - 1))
        name_filter = _normalize_text(name) if name is not None else ""
        clauses: List[str] = ["CAST(strftime('%s', day || 'T00:00:00') AS INTEGER) IS NOT NULL"]
        params: List[Any] = []
        if name_filter:
            clauses.append("name = ?")
            params.append(name_filter)

        rows = self._db._execute(
            f"""
            SELECT day, name, status, count, updated_at
            FROM daily_task_stats
            {"WHERE " + " AND ".join(clauses) if clauses else ""}
            ORDER BY day DESC, name ASC, status ASC
            """,
            params,
        ).fetchall()

        out: List[Dict[str, Any]] = []
        for r in rows:
            try:
                day_ord = date.fromisoformat(r["day"]).toordinal()
            except Exception:
                continue
            if day_ord < cutoff:
                continue
            out.append(
                {
                    "day": r["day"],
                    "name": r["name"],
                    "status": r["status"],
                    "count": int(r["count"]),
                    "updated_at": _ts_to_iso(float(r["updated_at"])),
                }
            )
        return out


class EventBus:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._clients: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.append(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients = [c for c in self._clients if c is not ws]

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        msg = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        async with self._lock:
            clients = list(self._clients)
        if not clients:
            return
        dead: List[WebSocket] = []
        for c in clients:
            try:
                if c.application_state != WebSocketState.CONNECTED:
                    dead.append(c)
                    continue
                await c.send_text(msg)
            except Exception:
                dead.append(c)
        if dead:
            async with self._lock:
                self._clients = [c for c in self._clients if c not in dead]


class TaskService:
    def __init__(self, tasks: TaskRepository, workers: WorkerRepository, stats: StatsRepository, bus: EventBus) -> None:
        self._tasks = tasks
        self._workers = workers
        self._stats = stats
        self._bus = bus

    async def ingest_event(self, event: Dict[str, Any]) -> TaskRecord:
        event_type = _normalize_text(str(event.get("event_type") or ""))
        task_id = _normalize_text(str(event.get("task_id") or ""))
        name = _normalize_text(str(event.get("name") or ""))
        status_raw = event.get("status")
        worker = _normalize_text(str(event.get("worker") or "")) or None
        message = event.get("message")
        args = event.get("args")
        kwargs = event.get("kwargs")
        result = event.get("result")
        error = event.get("error")
        retries = event.get("retries")
        ts = event.get("timestamp")

        if not event_type:
            raise ValueError("event_type is required")
        if not task_id:
            raise ValueError("task_id is required")

        created_at = None
        if ts is not None:
            if isinstance(ts, (int, float)):
                created_at = float(ts)
            elif isinstance(ts, str) and _normalize_text(ts):
                created_at = _iso_to_ts(ts)
        if created_at is None:
            created_at = _utc_now_ts()

        status: Optional[TaskStatus] = None
        if status_raw is not None and _normalize_text(str(status_raw)):
            status = TaskStatus(str(status_raw))

        if worker is not None:
            self._workers.heartbeat(worker, created_at)

        existing: Optional[TaskRecord] = None
        try:
            existing = self._tasks.get_task(task_id)
        except KeyError:
            existing = None

        if existing is None:
            if not name:
                name = "unknown"
            initial_status = status or TaskStatus.PENDING
            rec = self._tasks.upsert_task(
                task_id=task_id,
                name=name,
                status=initial_status,
                worker=worker,
                args=args,
                kwargs=kwargs,
                result=result,
                error=error,
                retries=int(retries) if retries is not None else 0,
                created_at=created_at,
                updated_at=created_at,
                received_at=created_at if initial_status == TaskStatus.RECEIVED else None,
                started_at=created_at if initial_status == TaskStatus.STARTED else None,
                finished_at=created_at if initial_status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED) else None,
            )
            self._tasks.add_event(task_id, event_type, status=initial_status, worker=worker, message=_normalize_text(str(message)) or None, created_at=created_at)
            if initial_status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED):
                self._stats.increment(_date_from_ts(created_at), rec.name, initial_status, 1)
            await self._bus.broadcast({"type": "task_event", "task": rec.to_dict(), "event": event})
            return rec

        new_name = name or existing.name
        new_status = status or existing.status
        new_retries = existing.retries
        if new_status == TaskStatus.RETRY:
            new_retries = existing.retries + 1
        if retries is not None:
            new_retries = int(retries)

        received_at = existing.received_at
        started_at = existing.started_at
        finished_at = existing.finished_at

        if new_status == TaskStatus.RECEIVED and received_at is None:
            received_at = created_at
        if new_status == TaskStatus.STARTED and started_at is None:
            started_at = created_at
        if new_status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED) and finished_at is None:
            finished_at = created_at

        rec = self._tasks.upsert_task(
            task_id=task_id,
            name=new_name,
            status=new_status,
            worker=worker or existing.worker,
            args=args,
            kwargs=kwargs,
            result=result,
            error=error,
            retries=new_retries,
            received_at=received_at,
            started_at=started_at,
            finished_at=finished_at,
            updated_at=created_at,
        )
        self._tasks.add_event(task_id, event_type, status=new_status, worker=worker or existing.worker, message=_normalize_text(str(message)) or None, created_at=created_at)

        if existing.status != rec.status and rec.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED):
            self._stats.increment(_date_from_ts(created_at), rec.name, rec.status, 1)

        await self._bus.broadcast({"type": "task_event", "task": rec.to_dict(), "event": event})
        return rec

    def search(
        self,
        *,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        status: Optional[TaskStatus] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        q: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        tasks = self._tasks.search_tasks(
            date_from=date_from,
            date_to=date_to,
            status=status,
            name=name,
            worker=worker,
            q=q,
            limit=limit,
            offset=offset,
        )
        return [t.to_dict() for t in tasks]

    def task_detail(self, task_id: str) -> Dict[str, Any]:
        t = self._tasks.get_task(task_id)
        return {"task": t.to_dict(), "events": self._tasks.list_events(task_id)}

    def orphans(self, older_than_seconds: int = 3600) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._tasks.detect_orphans(older_than_seconds=older_than_seconds)]

    def workers(self, stale_after_seconds: int = 60) -> List[Dict[str, Any]]:
        self._workers.mark_offline_stale(stale_after_seconds=stale_after_seconds)
        return [w.to_dict() for w in self._workers.list()]

    def stats_day(self, day: str) -> List[Dict[str, Any]]:
        return self._stats.get_day(day)

    def stats_history(self, days: int = 30, name: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._stats.history(days=days, name=name)


class IngestEventModel(BaseModel):
    event_type: str = Field(..., min_length=1)
    task_id: str = Field(..., min_length=1)
    name: Optional[str] = None
    status: Optional[str] = None
    worker: Optional[str] = None
    message: Optional[str] = None
    args: Optional[Any] = None
    kwargs: Optional[Any] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    retries: Optional[int] = None
    timestamp: Optional[Union[float, int, str]] = None


def create_app(db_path: str = "kanchi.db") -> FastAPI:
    db = Database(db_path)
    tasks_repo = TaskRepository(db)
    workers_repo = WorkerRepository(db)
    stats_repo = StatsRepository(db)
    bus = EventBus()
    service = TaskService(tasks_repo, workers_repo, stats_repo, bus)

    app = FastAPI(title="Kanchi", version="1.0.0")

    @app.on_event("shutdown")
    def _shutdown() -> None:
        db.close()

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await bus.connect(ws)
        try:
            while True:
                try:
                    msg = await ws.receive_text()
                except WebSocketDisconnect:
                    break
                except Exception:
                    break
                if _normalize_text(msg).lower() in ("ping", '{"type":"ping"}', '{"type": "ping"}'):
                    try:
                        await ws.send_text('{"type":"pong"}')
                    except Exception:
                        break
        finally:
            await bus.disconnect(ws)

    @app.post("/api/events")
    async def ingest_event(payload: IngestEventModel) -> JSONResponse:
        try:
            rec = await service.ingest_event(payload.model_dump())
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        return JSONResponse(rec.to_dict())

    @app.get("/api/tasks")
    def list_tasks(
        date_from: Optional[str] = Query(default=None),
        date_to: Optional[str] = Query(default=None),
        status: Optional[str] = Query(default=None),
        name: Optional[str] = Query(default=None),
        worker: Optional[str] = Query(default=None),
        q: Optional[str] = Query(default=None),
        limit: int = Query(default=100, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> JSONResponse:
        df: Optional[date] = date.fromisoformat(date_from) if date_from else None
        dt: Optional[date] = date.fromisoformat(date_to) if date_to else None
        st: Optional[TaskStatus] = TaskStatus(status) if status else None
        return JSONResponse(service.search(date_from=df, date_to=dt, status=st, name=name, worker=worker, q=q, limit=limit, offset=offset))

    @app.get("/api/tasks/{task_id}")
    def task_detail(task_id: str) -> JSONResponse:
        try:
            return JSONResponse(service.task_detail(task_id))
        except KeyError:
            raise HTTPException(status_code=404, detail="task not found")

    @app.get("/api/tasks/{task_id}/events")
    def task_events(task_id: str, limit: int = Query(default=200, ge=1, le=1000)) -> JSONResponse:
        try:
            tasks_repo.get_task(task_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="task not found")
        return JSONResponse(tasks_repo.list_events(task_id, limit=limit))

    @app.get("/api/orphans")
    def orphans(older_than_seconds: int = Query(default=3600, ge=1)) -> JSONResponse:
        return JSONResponse(service.orphans(older_than_seconds=older_than_seconds))

    @app.get("/api/workers")
    def workers(stale_after_seconds: int = Query(default=60, ge=1)) -> JSONResponse:
        return JSONResponse(service.workers(stale_after_seconds=stale_after_seconds))

    @app.get("/api/stats/daily/{day}")
    def stats_day(day: str) -> JSONResponse:
        try:
            date.fromisoformat(day)
        except Exception:
            raise HTTPException(status_code=400, detail="invalid day")
        return JSONResponse(service.stats_day(day))

    @app.get("/api/stats/history")
    def stats_history(days: int = Query(default=30, ge=1, le=365), name: Optional[str] = Query(default=None)) -> JSONResponse:
        return JSONResponse(service.stats_history(days=days, name=name))

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)