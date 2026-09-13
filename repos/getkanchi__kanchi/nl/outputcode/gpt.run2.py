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


UTC = timezone.utc


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


def _from_iso(s: Optional[str]) -> Optional[datetime]:
    if s is None:
        return None
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    STARTED = "STARTED"
    RETRY = "RETRY"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    REVOKED = "REVOKED"
    ORPHANED = "ORPHANED"


class WorkerStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"


@dataclass(frozen=True)
class TaskEvent:
    task_id: str
    timestamp: datetime
    status: TaskStatus
    worker: Optional[str]
    name: Optional[str]
    message: Optional[str]
    retry_count: int


@dataclass(frozen=True)
class WorkerHeartbeat:
    worker: str
    timestamp: datetime


@dataclass(frozen=True)
class DailyTaskStats:
    day: date
    total: int
    success: int
    failure: int
    retry: int
    revoked: int
    orphaned: int


class ValidationError(ValueError):
    pass


class Database:
    def __init__(self, path: str = "kanchi.db") -> None:
        self._path = path
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self.migrate()

    def migrate(self) -> None:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
                """
            )
            cur.execute("SELECT COALESCE(MAX(version), 0) AS v FROM schema_migrations")
            row = cur.fetchone()
            current = int(row["v"]) if row else 0

            target = 1
            if current < 1:
                self._apply_migration_1(cur)
                cur.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES(?, ?)",
                    (1, _to_iso(_utcnow())),
                )
                self._conn.commit()

            if current > target:
                raise RuntimeError("Database schema version is newer than this application.")

    def _apply_migration_1(self, cur: sqlite3.Cursor) -> None:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT,
                status TEXT NOT NULL,
                worker TEXT,
                created_at TEXT NOT NULL,
                received_at TEXT,
                started_at TEXT,
                finished_at TEXT,
                updated_at TEXT NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0,
                last_message TEXT,
                args_json TEXT,
                kwargs_json TEXT
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_name ON tasks(name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_worker ON tasks(worker)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at)")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS task_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                worker TEXT,
                name TEXT,
                message TEXT,
                retry_count INTEGER NOT NULL,
                FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_task_events_task_id ON task_events(task_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_task_events_timestamp ON task_events(timestamp)")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS worker_heartbeats (
                worker TEXT PRIMARY KEY,
                last_seen TEXT NOT NULL
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_worker_heartbeats_last_seen ON worker_heartbeats(last_seen)")

    def execute(self, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            self._conn.commit()
            return cur

    def executemany(self, sql: str, seq_of_params: Iterable[Sequence[Any]]) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.cursor()
            cur.executemany(sql, seq_of_params)
            self._conn.commit()
            return cur

    def query(self, sql: str, params: Sequence[Any] = ()) -> List[sqlite3.Row]:
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(sql, params)
            return cur.fetchall()

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class TaskRepository:
    TERMINAL_STATUSES = {
        TaskStatus.SUCCESS,
        TaskStatus.FAILURE,
        TaskStatus.REVOKED,
        TaskStatus.ORPHANED,
    }

    def __init__(self, db: Database) -> None:
        self._db = db

    def create_task(
        self,
        task_id: Optional[str] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        status: TaskStatus = TaskStatus.PENDING,
        created_at: Optional[datetime] = None,
        args: Optional[Any] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
    ) -> str:
        if task_id is None:
            task_id = str(uuid.uuid4())
        if created_at is None:
            created_at = _utcnow()
        now = _utcnow()
        if status not in TaskStatus:
            raise ValidationError("Invalid task status.")
        self._db.execute(
            """
            INSERT INTO tasks(id, name, status, worker, created_at, received_at, started_at, finished_at, updated_at,
                              retry_count, last_message, args_json, kwargs_json)
            VALUES(?, ?, ?, ?, ?, NULL, NULL, NULL, ?, 0, ?, ?, ?)
            """,
            (
                task_id,
                name,
                status.value,
                worker,
                _to_iso(created_at),
                _to_iso(now),
                message,
                json.dumps(args) if args is not None else None,
                json.dumps(kwargs) if kwargs is not None else None,
            ),
        )
        self._insert_event(
            task_id=task_id,
            timestamp=now,
            status=status,
            worker=worker,
            name=name,
            message=message,
            retry_count=0,
        )
        return task_id

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        rows = self._db.query("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if not rows:
            return None
        return self._row_to_task(rows[0])

    def update_status(
        self,
        task_id: str,
        status: TaskStatus,
        timestamp: Optional[datetime] = None,
        worker: Optional[str] = None,
        name: Optional[str] = None,
        message: Optional[str] = None,
        increment_retry: bool = False,
    ) -> Dict[str, Any]:
        if timestamp is None:
            timestamp = _utcnow()
        task = self.get_task(task_id)
        if task is None:
            task_id = self.create_task(task_id=task_id, name=name, worker=worker, status=TaskStatus.PENDING)
            task = self.get_task(task_id)
            if task is None:
                raise RuntimeError("Failed to create task.")

        current_status = TaskStatus(task["status"])
        if current_status in self.TERMINAL_STATUSES and status != current_status:
            raise ValidationError("Cannot transition a terminal task to a different status.")

        retry_count = int(task["retry_count"])
        if increment_retry:
            retry_count += 1

        received_at = task["received_at"]
        started_at = task["started_at"]
        finished_at = task["finished_at"]

        if status == TaskStatus.RECEIVED and received_at is None:
            received_at = timestamp
        if status == TaskStatus.STARTED and started_at is None:
            started_at = timestamp
        if status in self.TERMINAL_STATUSES and finished_at is None:
            finished_at = timestamp

        new_worker = worker if worker is not None else task["worker"]
        new_name = name if name is not None else task["name"]

        self._db.execute(
            """
            UPDATE tasks
            SET status = ?, worker = ?, name = ?, received_at = ?, started_at = ?, finished_at = ?,
                updated_at = ?, retry_count = ?, last_message = ?
            WHERE id = ?
            """,
            (
                status.value,
                new_worker,
                new_name,
                _to_iso(received_at),
                _to_iso(started_at),
                _to_iso(finished_at),
                _to_iso(timestamp),
                retry_count,
                message if message is not None else task["last_message"],
                task_id,
            ),
        )
        self._insert_event(
            task_id=task_id,
            timestamp=timestamp,
            status=status,
            worker=new_worker,
            name=new_name,
            message=message,
            retry_count=retry_count,
        )
        updated = self.get_task(task_id)
        if updated is None:
            raise RuntimeError("Task disappeared after update.")
        return updated

    def mark_orphaned(self, task_id: str, timestamp: Optional[datetime] = None, message: Optional[str] = None) -> Dict[str, Any]:
        return self.update_status(task_id, TaskStatus.ORPHANED, timestamp=timestamp, message=message)

    def list_events(self, task_id: str, limit: int = 1000) -> List[TaskEvent]:
        if limit <= 0:
            raise ValidationError("limit must be positive.")
        rows = self._db.query(
            """
            SELECT task_id, timestamp, status, worker, name, message, retry_count
            FROM task_events
            WHERE task_id = ?
            ORDER BY timestamp ASC, id ASC
            LIMIT ?
            """,
            (task_id, limit),
        )
        out: List[TaskEvent] = []
        for r in rows:
            out.append(
                TaskEvent(
                    task_id=r["task_id"],
                    timestamp=_from_iso(r["timestamp"]) or _utcnow(),
                    status=TaskStatus(r["status"]),
                    worker=r["worker"],
                    name=r["name"],
                    message=r["message"],
                    retry_count=int(r["retry_count"]),
                )
            )
        return out

    def search_tasks(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        statuses: Optional[Sequence[TaskStatus]] = None,
        name: Optional[str] = None,
        worker: Optional[str] = None,
        full_text: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
        order_desc: bool = True,
    ) -> List[Dict[str, Any]]:
        if limit <= 0 or limit > 5000:
            raise ValidationError("limit must be between 1 and 5000.")
        if offset < 0:
            raise ValidationError("offset must be non-negative.")
        clauses: List[str] = []
        params: List[Any] = []

        if date_from is not None:
            clauses.append("created_at >= ?")
            params.append(_to_iso(date_from))
        if date_to is not None:
            clauses.append("created_at <= ?")
            params.append(_to_iso(date_to))
        if statuses:
            clauses.append("status IN (%s)" % ",".join(["?"] * len(statuses)))
            params.extend([s.value for s in statuses])
        if name is not None:
            clauses.append("name = ?")
            params.append(name)
        if worker is not None:
            clauses.append("worker = ?")
            params.append(worker)
        if full_text is not None and full_text.strip():
            ft = f"%{full_text.strip()}%"
            clauses.append("(id LIKE ? OR name LIKE ? OR worker LIKE ? OR last_message LIKE ?)")
            params.extend([ft, ft, ft, ft])

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        order = "DESC" if order_desc else "ASC"
        rows = self._db.query(
            f"""
            SELECT *
            FROM tasks
            {where}
            ORDER BY updated_at {order}
            LIMIT ? OFFSET ?
            """,
            tuple(params + [limit, offset]),
        )
        return [self._row_to_task(r) for r in rows]

    def compute_daily_stats(self, day: date) -> DailyTaskStats:
        start = datetime(day.year, day.month, day.day, tzinfo=UTC)
        end = start + timedelta(days=1)
        rows = self._db.query(
            """
            SELECT status, COUNT(*) AS c
            FROM tasks
            WHERE created_at >= ? AND created_at < ?
            GROUP BY status
            """,
            (_to_iso(start), _to_iso(end)),
        )
        counts: Dict[str, int] = {r["status"]: int(r["c"]) for r in rows}
        total = sum(counts.values())
        return DailyTaskStats(
            day=day,
            total=total,
            success=counts.get(TaskStatus.SUCCESS.value, 0),
            failure=counts.get(TaskStatus.FAILURE.value, 0),
            retry=counts.get(TaskStatus.RETRY.value, 0),
            revoked=counts.get(TaskStatus.REVOKED.value, 0),
            orphaned=counts.get(TaskStatus.ORPHANED.value, 0),
        )

    def _insert_event(
        self,
        task_id: str,
        timestamp: datetime,
        status: TaskStatus,
        worker: Optional[str],
        name: Optional[str],
        message: Optional[str],
        retry_count: int,
    ) -> None:
        self._db.execute(
            """
            INSERT INTO task_events(task_id, timestamp, status, worker, name, message, retry_count)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, _to_iso(timestamp), status.value, worker, name, message, int(retry_count)),
        )

    def _row_to_task(self, r: sqlite3.Row) -> Dict[str, Any]:
        return {
            "id": r["id"],
            "name": r["name"],
            "status": r["status"],
            "worker": r["worker"],
            "created_at": _from_iso(r["created_at"]),
            "received_at": _from_iso(r["received_at"]),
            "started_at": _from_iso(r["started_at"]),
            "finished_at": _from_iso(r["finished_at"]),
            "updated_at": _from_iso(r["updated_at"]),
            "retry_count": int(r["retry_count"]),
            "last_message": r["last_message"],
            "args": json.loads(r["args_json"]) if r["args_json"] else None,
            "kwargs": json.loads(r["kwargs_json"]) if r["kwargs_json"] else None,
        }


class WorkerRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def heartbeat(self, worker: str, timestamp: Optional[datetime] = None) -> WorkerHeartbeat:
        if not worker or not worker.strip():
            raise ValidationError("worker must be a non-empty string.")
        if timestamp is None:
            timestamp = _utcnow()
        self._db.execute(
            """
            INSERT INTO worker_heartbeats(worker, last_seen)
            VALUES(?, ?)
            ON CONFLICT(worker) DO UPDATE SET last_seen = excluded.last_seen
            """,
            (worker, _to_iso(timestamp)),
        )
        return WorkerHeartbeat(worker=worker, timestamp=timestamp)

    def last_seen(self, worker: str) -> Optional[datetime]:
        rows = self._db.query("SELECT last_seen FROM worker_heartbeats WHERE worker = ?", (worker,))
        if not rows:
            return None
        return _from_iso(rows[0]["last_seen"])

    def list_workers(self) -> List[Tuple[str, datetime]]:
        rows = self._db.query("SELECT worker, last_seen FROM worker_heartbeats ORDER BY worker ASC")
        out: List[Tuple[str, datetime]] = []
        for r in rows:
            dt = _from_iso(r["last_seen"]) or _utcnow()
            out.append((r["worker"], dt))
        return out

    def health(self, now: Optional[datetime] = None, offline_after: timedelta = timedelta(seconds=60)) -> Dict[str, WorkerStatus]:
        if now is None:
            now = _utcnow()
        if offline_after.total_seconds() <= 0:
            raise ValidationError("offline_after must be positive.")
        workers = self.list_workers()
        out: Dict[str, WorkerStatus] = {}
        for w, last in workers:
            age = now - last
            out[w] = WorkerStatus.OFFLINE if age > offline_after else WorkerStatus.ONLINE
        return out


class OrphanDetector:
    def __init__(self, tasks: TaskRepository, workers: WorkerRepository) -> None:
        self._tasks = tasks
        self._workers = workers

    def detect_and_mark(
        self,
        now: Optional[datetime] = None,
        started_before: timedelta = timedelta(minutes=10),
        worker_offline_after: timedelta = timedelta(seconds=60),
        limit: int = 1000,
    ) -> List[str]:
        if now is None:
            now = _utcnow()
        if started_before.total_seconds() <= 0:
            raise ValidationError("started_before must be positive.")
        if limit <= 0:
            raise ValidationError("limit must be positive.")

        candidates = self._tasks.search_tasks(
            statuses=[TaskStatus.STARTED, TaskStatus.RECEIVED],
            limit=limit,
            order_desc=False,
        )
        health = self._workers.health(now=now, offline_after=worker_offline_after)
        marked: List[str] = []
        threshold = now - started_before

        for t in candidates:
            tid = str(t["id"])
            status = TaskStatus(t["status"])
            worker = t["worker"]
            started_at = t["started_at"]
            received_at = t["received_at"]
            basis = started_at if started_at is not None else received_at
            if basis is None:
                basis = t["created_at"] or now

            if basis >= threshold:
                continue

            if worker is None:
                self._tasks.mark_orphaned(tid, timestamp=now, message="Orphaned: no worker assigned.")
                marked.append(tid)
                continue

            wstat = health.get(worker, WorkerStatus.OFFLINE)
            if wstat == WorkerStatus.OFFLINE:
                self._tasks.mark_orphaned(
                    tid,
                    timestamp=now,
                    message=f"Orphaned: worker '{worker}' offline while task {status.value}.",
                )
                marked.append(tid)

        return marked


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._subscribers: Dict[str, Callable[[Dict[str, Any]], None]] = {}

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> str:
        sid = str(uuid.uuid4())
        with self._lock:
            self._subscribers[sid] = callback
        return sid

    def unsubscribe(self, subscription_id: str) -> None:
        with self._lock:
            self._subscribers.pop(subscription_id, None)

    def publish(self, event: Dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subscribers.values())
        for cb in subs:
            try:
                cb(event)
            except Exception:
                continue


class TaskService:
    def __init__(self, tasks: TaskRepository, workers: WorkerRepository, bus: Optional[EventBus] = None) -> None:
        self._tasks = tasks
        self._workers = workers
        self._bus = bus

    def record_task_event(
        self,
        task_id: str,
        status: TaskStatus,
        timestamp: Optional[datetime] = None,
        worker: Optional[str] = None,
        name: Optional[str] = None,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        increment_retry = status == TaskStatus.RETRY
        updated = self._tasks.update_status(
            task_id=task_id,
            status=status,
            timestamp=timestamp,
            worker=worker,
            name=name,
            message=message,
            increment_retry=increment_retry,
        )
        if worker:
            self._workers.heartbeat(worker, timestamp=timestamp)
        if self._bus is not None:
            self._bus.publish(
                {
                    "type": "task",
                    "task": updated,
                    "event": {
                        "task_id": task_id,
                        "status": status.value,
                        "timestamp": _to_iso(timestamp or _utcnow()),
                        "worker": worker,
                        "name": name,
                        "message": message,
                        "retry_incremented": increment_retry,
                    },
                }
            )
        return updated

    def record_worker_heartbeat(self, worker: str, timestamp: Optional[datetime] = None) -> WorkerHeartbeat:
        hb = self._workers.heartbeat(worker, timestamp=timestamp)
        if self._bus is not None:
            self._bus.publish(
                {
                    "type": "worker",
                    "worker": worker,
                    "timestamp": _to_iso(hb.timestamp),
                }
            )
        return hb


class WebSocketServer:
    def __init__(self, host: str, port: int, bus: EventBus) -> None:
        self._host = host
        self._port = port
        self._bus = bus
        self._server: Any = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if websockets is None:
            raise RuntimeError("websockets package is required to run WebSocketServer.")
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
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

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._start_server())
        try:
            self._loop.run_forever()
        finally:
            try:
                self._loop.run_until_complete(self._shutdown())
            except Exception:
                pass
            self._loop.close()

    async def _start_server(self) -> None:
        assert websockets is not None
        self._server = await websockets.serve(self._handler, self._host, self._port)

    async def _shutdown(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def _handler(self, websocket: Any) -> None:
        queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

        def on_event(evt: Dict[str, Any]) -> None:
            if self._loop is None:
                return
            try:
                self._loop.call_soon_threadsafe(queue.put_nowait, evt)
            except Exception:
                pass

        sid = self._bus.subscribe(on_event)
        try:
            await websocket.send(json.dumps({"type": "hello", "ts": _to_iso(_utcnow())}))
            while not self._stop_event.is_set():
                try:
                    evt = await asyncio.wait_for(queue.get(), timeout=0.5)
                    await websocket.send(json.dumps(evt, default=str))
                except asyncio.TimeoutError:
                    try:
                        msg = await asyncio.wait_for(websocket.recv(), timeout=0.01)
                        if msg is None:
                            break
                        if isinstance(msg, (bytes, bytearray)):
                            msg = msg.decode("utf-8", errors="ignore")
                        msg_s = str(msg).strip()
                        if msg_s.lower() in {"ping", "heartbeat"}:
                            await websocket.send(json.dumps({"type": "pong", "ts": _to_iso(_utcnow())}))
                    except asyncio.TimeoutError:
                        continue
        finally:
            self._bus.unsubscribe(sid)


class KanchiApp:
    def __init__(
        self,
        db_path: str = "kanchi.db",
        websocket_host: str = "127.0.0.1",
        websocket_port: int = 8765,
        enable_websocket: bool = True,
    ) -> None:
        self.db = Database(db_path)
        self.bus = EventBus()
        self.tasks = TaskRepository(self.db)
        self.workers = WorkerRepository(self.db)
        self.service = TaskService(self.tasks, self.workers, self.bus)
        self.orphans = OrphanDetector(self.tasks, self.workers)
        self.websocket: Optional[WebSocketServer] = None
        if enable_websocket:
            self.websocket = WebSocketServer(websocket_host, websocket_port, self.bus)

    def start(self) -> None:
        if self.websocket is not None:
            self.websocket.start()

    def stop(self) -> None:
        if self.websocket is not None:
            self.websocket.stop()
        self.db.close()


def _main() -> None:
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
    _main()