from __future__ import annotations

import asyncio
import hashlib
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Lightweight stand-ins for SQLAlchemy / FastAPI types so the module is
# importable without those dependencies being installed.
# ---------------------------------------------------------------------------
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
    from sqlalchemy.engine import Engine
except ImportError:  # pragma: no cover
    create_engine = None  # type: ignore
    sessionmaker = None  # type: ignore
    Session = object  # type: ignore
    Engine = object  # type: ignore

    class DeclarativeBase:  # type: ignore
        pass


try:
    from fastapi import WebSocket
except ImportError:  # pragma: no cover
    WebSocket = object  # type: ignore

try:
    from celery import Celery
    from celery.events import EventReceiver
except ImportError:  # pragma: no cover
    Celery = object  # type: ignore
    EventReceiver = object  # type: ignore


# ---------------------------------------------------------------------------
# Simple named-tuple-like result type used by action handlers
# ---------------------------------------------------------------------------
class ActionResult:
    def __init__(self, success: bool, message: str = "", data: Optional[Dict[str, Any]] = None):
        self.success = success
        self.message = message
        self.data = data or {}

    def __repr__(self) -> str:
        return f"ActionResult(success={self.success}, message={self.message!r})"


# ---------------------------------------------------------------------------
# Event data-classes (lightweight, no ORM)
# ---------------------------------------------------------------------------
class TaskEvent:
    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)


class WorkerEvent:
    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TaskProgressEvent:
    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TaskStepsEvent:
    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# Database model base
# ---------------------------------------------------------------------------
class _Base:
    """Minimal base that provides a plain-Python fallback when SQLAlchemy is
    not available."""

    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# Database models
# ---------------------------------------------------------------------------

class ActionConfigDB(_Base):
    __tablename__ = "action_configs"

    id: Any = None
    name: str = ""
    action_type: str = ""
    config: Any = None
    description: str = ""
    created_by: Any = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "action_type": self.action_type,
            "config": self.config,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "usage_count": self.usage_count,
        }


class AppSettingDB(_Base):
    __tablename__ = "app_settings"

    key: str = ""
    value: Any = None
    value_type: str = ""
    label: str = ""
    description: str = ""
    category: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "value_type": self.value_type,
            "label": self.label,
            "description": self.description,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EnvironmentDB(_Base):
    __tablename__ = "environments"

    id: Any = None
    name: str = ""
    description: str = ""
    is_active: bool = True
    is_default: bool = False
    queue_patterns: Any = None
    worker_patterns: Any = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "queue_patterns": self.queue_patterns,
            "worker_patterns": self.worker_patterns,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RetryRelationshipDB(_Base):
    __tablename__ = "retry_relationships"

    id: Any = None
    task_id: str = ""
    original_id: str = ""
    retry_chain: Any = None
    total_retries: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TaskActionDB(_Base):
    __tablename__ = "task_actions"

    id: Any = None
    action_type: str = ""
    status: str = ""
    initiated_by: str = ""
    initiated_by_user_id: Any = None
    initiated_session_id: Any = None
    selection_size: int = 0
    item_total: int = 0
    item_changed: int = 0
    item_created: int = 0
    item_failed: int = 0
    item_noop: int = 0
    item_skipped: int = 0
    items: Any = None
    original_task_ids: Any = None
    summary: Any = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class TaskActionItemDB(_Base):
    __tablename__ = "task_action_items"

    id: Any = None
    action_id: Any = None
    action: str = ""
    original_task_id: str = ""
    original_task_name: str = ""
    attempted_task_id: Any = None
    outcome: str = ""
    reason: str = ""
    reason_code: str = ""
    rerun_kind: str = ""
    rerun_task_id: Any = None
    rerun_task_name: Any = None
    review_fingerprint: Any = None
    skip_category: Any = None
    submitted_args: Any = None
    submitted_kwargs: Any = None
    target_queue: Any = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TaskDailyStatsDB(_Base):
    __tablename__ = "task_daily_stats"

    id: Any = None
    task_name: str = ""
    date: Any = None
    total_executions: int = 0
    succeeded: int = 0
    failed: int = 0
    retried: int = 0
    revoked: int = 0
    pending: int = 0
    orphaned: int = 0
    avg_runtime: Optional[float] = None
    min_runtime: Optional[float] = None
    max_runtime: Optional[float] = None
    p50_runtime: Optional[float] = None
    p95_runtime: Optional[float] = None
    p99_runtime: Optional[float] = None
    first_execution: Optional[datetime] = None
    last_execution: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_name": self.task_name,
            "date": str(self.date) if self.date else None,
            "total_executions": self.total_executions,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "retried": self.retried,
            "revoked": self.revoked,
            "pending": self.pending,
            "orphaned": self.orphaned,
            "avg_runtime": self.avg_runtime,
            "min_runtime": self.min_runtime,
            "max_runtime": self.max_runtime,
            "p50_runtime": self.p50_runtime,
            "p95_runtime": self.p95_runtime,
            "p99_runtime": self.p99_runtime,
            "first_execution": self.first_execution.isoformat() if self.first_execution else None,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TaskEventDB(_Base):
    __tablename__ = "task_events"

    id: Any = None
    task_id: str = ""
    task_name: str = ""
    event_type: str = ""
    hostname: str = ""
    worker_name: str = ""
    timestamp: Optional[datetime] = None
    args: Any = None
    kwargs: Any = None
    result: Any = None
    exception: Any = None
    traceback: Any = None
    runtime: Optional[float] = None
    retries: int = 0
    retry_count: int = 0
    retry_of: Any = None
    retried_by: Any = None
    has_retries: bool = False
    is_retry: bool = False
    is_orphan: bool = False
    orphaned_at: Optional[datetime] = None
    parent_id: Any = None
    root_id: Any = None
    queue: Any = None
    exchange: Any = None
    routing_key: Any = None
    eta: Any = None
    expires: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "event_type": self.event_type,
            "hostname": self.hostname,
            "worker_name": self.worker_name,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "args": self.args,
            "kwargs": self.kwargs,
            "result": self.result,
            "exception": self.exception,
            "traceback": self.traceback,
            "runtime": self.runtime,
            "retries": self.retries,
            "retry_count": self.retry_count,
            "retry_of": self.retry_of,
            "retried_by": self.retried_by,
            "has_retries": self.has_retries,
            "is_retry": self.is_retry,
            "is_orphan": self.is_orphan,
            "orphaned_at": self.orphaned_at.isoformat() if self.orphaned_at else None,
            "parent_id": self.parent_id,
            "root_id": self.root_id,
            "queue": self.queue,
            "exchange": self.exchange,
            "routing_key": self.routing_key,
            "eta": self.eta,
            "expires": self.expires,
        }


class TaskLatestDB(_Base):
    __tablename__ = "task_latest"

    task_id: str = ""
    task_name: str = ""
    event_id: Any = None
    event_type: str = ""
    hostname: str = ""
    worker_name: str = ""
    timestamp: Optional[datetime] = None
    args: Any = None
    kwargs: Any = None
    result: Any = None
    exception: Any = None
    traceback: Any = None
    runtime: Optional[float] = None
    retries: int = 0
    retry_count: int = 0
    retry_of: Any = None
    retried_by: Any = None
    has_retries: bool = False
    is_retry: bool = False
    is_orphan: bool = False
    orphaned_at: Optional[datetime] = None
    parent_id: Any = None
    root_id: Any = None
    queue: Any = None
    exchange: Any = None
    routing_key: Any = None
    eta: Any = None
    expires: Any = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Any = None


class TaskProgressDB(_Base):
    __tablename__ = "task_progress"

    id: Any = None
    task_id: str = ""
    task_name: str = ""
    progress: Optional[float] = None
    message: str = ""
    step_key: Any = None
    meta: Any = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "progress": self.progress,
            "message": self.message,
            "step_key": self.step_key,
            "meta": self.meta,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class TaskProgressLatestDB(_Base):
    __tablename__ = "task_progress_latest"

    task_id: str = ""
    task_name: str = ""
    progress: Optional[float] = None
    message: str = ""
    step_key: Any = None
    meta: Any = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "progress": self.progress,
            "message": self.message,
            "step_key": self.step_key,
            "meta": self.meta,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TaskRegistryDB(_Base):
    __tablename__ = "task_registry"

    id: Any = None
    name: str = ""
    human_readable_name: str = ""
    description: str = ""
    tags: Any = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "human_readable_name": self.human_readable_name,
            "description": self.description,
            "tags": self.tags,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TaskRerunRelationshipDB(_Base):
    __tablename__ = "task_rerun_relationships"

    id: Any = None
    original_task_id: str = ""
    rerun_task_id: str = ""
    action_id: Any = None
    created_by: Any = None
    created_at: Optional[datetime] = None


class TaskResolutionDB(_Base):
    __tablename__ = "task_resolutions"

    task_id: str = ""
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Any = None


class TaskStepsDB(_Base):
    __tablename__ = "task_steps"

    task_id: str = ""
    task_name: str = ""
    steps: Any = None
    defined_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "steps": self.steps,
            "defined_at": self.defined_at.isoformat() if self.defined_at else None,
        }


class UserDB(_Base):
    __tablename__ = "users"

    id: Any = None
    name: str = ""
    email: str = ""
    avatar_url: Any = None
    provider: str = ""
    provider_account_id: str = ""
    is_active: bool = True
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    sessions: List[Any] = None  # type: ignore

    def __init__(self, **kwargs: Any):
        self.sessions = []
        super().__init__(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "avatar_url": self.avatar_url,
            "provider": self.provider,
            "provider_account_id": self.provider_account_id,
            "is_active": self.is_active,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserSessionDB(_Base):
    __tablename__ = "user_sessions"

    session_id: str = ""
    user_id: Any = None
    user: Any = None
    auth_provider: str = ""
    access_token_hash: str = ""
    access_token_expires_at: Optional[datetime] = None
    refresh_token_hash: str = ""
    refresh_token_expires_at: Optional[datetime] = None
    token_scopes: Any = None
    active_environment_id: Any = None
    preferences: Any = None
    last_active: Optional[datetime] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "auth_provider": self.auth_provider,
            "access_token_expires_at": (
                self.access_token_expires_at.isoformat() if self.access_token_expires_at else None
            ),
            "refresh_token_expires_at": (
                self.refresh_token_expires_at.isoformat() if self.refresh_token_expires_at else None
            ),
            "token_scopes": self.token_scopes,
            "active_environment_id": self.active_environment_id,
            "preferences": self.preferences,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WorkerEventDB(_Base):
    __tablename__ = "worker_events"

    id: Any = None
    hostname: str = ""
    event_type: str = ""
    status: str = ""
    active_tasks: int = 0
    processed: int = 0
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "hostname": self.hostname,
            "event_type": self.event_type,
            "status": self.status,
            "active_tasks": self.active_tasks,
            "processed": self.processed,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class WorkflowDB(_Base):
    __tablename__ = "workflows"

    id: Any = None
    name: str = ""
    description: str = ""
    enabled: bool = True
    trigger_type: str = ""
    trigger_config: Any = None
    conditions: Any = None
    actions: Any = None
    priority: int = 0
    cooldown_seconds: int = 0
    max_executions_per_hour: int = 0
    circuit_breaker_config: Any = None
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_executed_at: Optional[datetime] = None
    created_by: Any = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "trigger_type": self.trigger_type,
            "trigger_config": self.trigger_config,
            "conditions": self.conditions,
            "actions": self.actions,
            "priority": self.priority,
            "cooldown_seconds": self.cooldown_seconds,
            "max_executions_per_hour": self.max_executions_per_hour,
            "circuit_breaker_config": self.circuit_breaker_config,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_executed_at": self.last_executed_at.isoformat() if self.last_executed_at else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkflowExecutionDB(_Base):
    __tablename__ = "workflow_executions"

    id: Any = None
    workflow_id: Any = None
    workflow_snapshot: Any = None
    trigger_type: str = ""
    trigger_event: Any = None
    status: str = ""
    actions_executed: Any = None
    error_message: Any = None
    stack_trace: Any = None
    circuit_breaker_key: Any = None
    duration_ms: Optional[int] = None
    triggered_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "workflow_snapshot": self.workflow_snapshot,
            "trigger_type": self.trigger_type,
            "trigger_event": self.trigger_event,
            "status": self.status,
            "actions_executed": self.actions_executed,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "circuit_breaker_key": self.circuit_breaker_key,
            "duration_ms": self.duration_ms,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# ---------------------------------------------------------------------------
# DatabaseManager
# ---------------------------------------------------------------------------

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url: str = database_url
        self.engine: Any = None
        self.SessionLocal: Any = None
        self._initialize()

    def _initialize(self) -> None:
        if create_engine is not None:
            try:
                self.engine = create_engine(self.database_url)
                self.SessionLocal = sessionmaker(
                    autocommit=False, autoflush=False, bind=self.engine
                )
            except Exception:
                self.engine = None
                self.SessionLocal = None

    def get_session(self) -> Any:
        if self.SessionLocal is None:
            raise RuntimeError("Database not initialised")
        return self.SessionLocal()

    def run_migrations(self) -> None:
        pass


# ---------------------------------------------------------------------------
# CeleryEventMonitor
# ---------------------------------------------------------------------------

class CeleryEventMonitor:
    def __init__(self, broker_url: str):
        self.broker_url: str = broker_url
        self.app: Any = None
        self.state: None = None
        self.workers: Dict[str, Dict[str, Any]] = {}
        self.task_callback: Optional[Callable[[TaskEvent], None]] = None
        self.worker_callback: Optional[Callable[[WorkerEvent], None]] = None
        self.progress_callback: Optional[Callable[[TaskProgressEvent], None]] = None
        self.steps_callback: Optional[Callable[[TaskStepsEvent], None]] = None
        self._running: bool = False

    def set_task_callback(self, callback: Callable[[TaskEvent], None]) -> None:
        self.task_callback = callback

    def set_worker_callback(self, callback: Callable[[WorkerEvent], None]) -> None:
        self.worker_callback = callback

    def set_progress_callback(self, callback: Callable[[TaskProgressEvent], None]) -> None:
        self.progress_callback = callback

    def set_steps_callback(self, callback: Callable[[TaskStepsEvent], None]) -> None:
        self.steps_callback = callback

    def get_workers_info(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.workers)

    def start_monitoring(self) -> None:
        self._running = True
        if Celery is not object:
            try:
                self.app = Celery(broker=self.broker_url)
                self.state = self.app.events.State()
            except Exception:
                pass

    def stop(self) -> None:
        self._running = False
        if self.app is not None:
            try:
                self.app.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# ConnectionManager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[Any] = []
        self.client_filters: Dict[Any, dict] = {}
        self.client_modes: Dict[Any, str] = {}
        self.message_queue: Optional[asyncio.Queue] = None
        self._broadcaster_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: Any) -> None:
        if hasattr(websocket, "accept"):
            await websocket.accept()
        self.active_connections.append(websocket)
        self.client_filters[websocket] = {}
        self.client_modes[websocket] = "default"

    def disconnect(self, websocket: Any) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.client_filters.pop(websocket, None)
        self.client_modes.pop(websocket, None)

    def set_client_filters(self, websocket: Any, filters: dict) -> None:
        self.client_filters[websocket] = filters

    def set_client_mode(self, websocket: Any, mode: str) -> None:
        self.client_modes[websocket] = mode

    async def send_personal_message(self, message: str, websocket: Any) -> None:
        if hasattr(websocket, "send_text"):
            await websocket.send_text(message)

    def queue_broadcast(self, task_event: TaskEvent) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait(("task", task_event))
            except asyncio.QueueFull:
                pass

    def queue_worker_broadcast(self, worker_event: WorkerEvent) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait(("worker", worker_event))
            except asyncio.QueueFull:
                pass

    def queue_progress_broadcast(self, progress_event: Any) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait(("progress", progress_event))
            except asyncio.QueueFull:
                pass

    def queue_task_action_broadcast(self, action_event: Any) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait(("action", action_event))
            except asyncio.QueueFull:
                pass

    def start_background_broadcaster(self) -> None:
        self.message_queue = asyncio.Queue()
        try:
            loop = asyncio.get_event_loop()
            self._broadcaster_task = loop.create_task(self._broadcast_loop())
        except RuntimeError:
            pass

    def stop_background_broadcaster(self) -> None:
        if self._broadcaster_task is not None:
            self._broadcaster_task.cancel()
            self._broadcaster_task = None
        self.message_queue = None

    async def _broadcast_loop(self) -> None:
        while True:
            if self.message_queue is None:
                break
            item = await self.message_queue.get()
            kind, event = item
            import json as _json
            payload = {}
            if hasattr(event, "__dict__"):
                payload = event.__dict__
            message = _json.dumps({"type": kind, "data": payload}, default=str)
            for ws in list(self.active_connections):
                try:
                    await self.send_personal_message(message, ws)
                except Exception:
                    pass


# ---------------------------------------------------------------------------
# EventHandler
# ---------------------------------------------------------------------------

class EventHandler:
    def __init__(self, connection_manager: ConnectionManager, db_manager: DatabaseManager):
        self.connection_manager = connection_manager
        self.db_manager = db_manager
        self.workflow_engine: None = None

    def handle_task_event(self, task_event: TaskEvent) -> None:
        self.connection_manager.queue_broadcast(task_event)

    def handle_worker_event(self, worker_event: WorkerEvent) -> None:
        self.connection_manager.queue_worker_broadcast(worker_event)

    def handle_progress_event(self, progress_event: Any) -> None:
        self.connection_manager.queue_progress_broadcast(progress_event)

    def handle_steps_event(self, steps_event: Any) -> None:
        self.connection_manager.queue_progress_broadcast(steps_event)


# ---------------------------------------------------------------------------
# ActionHandler (abstract base)
# ---------------------------------------------------------------------------

class ActionHandler(ABC):
    def __init__(self, db_manager: DatabaseManager, session: Any = None):
        self.db_manager = db_manager
        self.session = session
        self.monitor_instance: None = None

    @abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        ...

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        ...

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        def _replace(match: re.Match) -> str:
            key = match.group(1).strip()
            parts = key.split(".")
            value: Any = context
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, "")
                else:
                    value = getattr(value, part, "")
            return str(value)

        return re.sub(r"\{\{(.*?)\}\}", _replace, template)


# ---------------------------------------------------------------------------
# RetryActionHandler
# ---------------------------------------------------------------------------

class RetryActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "task_id" not in params and "task_ids" not in params:
            return False, "Either 'task_id' or 'task_ids' must be provided"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        valid, message = self.validate_params(params)
        if not valid:
            return ActionResult(success=False, message=message)

        task_ids = params.get("task_ids") or [params.get("task_id")]
        retried: List[str] = []
        failed: List[str] = []

        for task_id in task_ids:
            if not task_id:
                continue
            try:
                retried.append(str(task_id))
            except Exception as exc:
                failed.append(str(task_id))

        if failed:
            return ActionResult(
                success=False,
                message=f"Failed to retry tasks: {failed}",
                data={"retried": retried, "failed": failed},
            )

        return ActionResult(
            success=True,
            message=f"Successfully retried {len(retried)} task(s)",
            data={"retried": retried},
        )


# ---------------------------------------------------------------------------
# SlackActionHandler
# ---------------------------------------------------------------------------

class SlackActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "webhook_url" not in params and "channel" not in params:
            return False, "Either 'webhook_url' or 'channel' must be provided"
        if "message" not in params:
            return False, "'message' parameter is required"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        valid, message = self.validate_params(params)
        if not valid:
            return ActionResult(success=False, message=message)

        rendered_message = self.render_template(params.get("message", ""), context)
        webhook_url = params.get("webhook_url", "")
        channel = params.get("channel", "")

        try:
            import urllib.request as _req
            import json as _json

            payload = {"text": rendered_message}
            if channel:
                payload["channel"] = channel

            data = _json.dumps(payload).encode("utf-8")
            req = _req.Request(
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with _req.urlopen(req, timeout=10) as resp:
                status = resp.status
                if status == 200:
                    return ActionResult(
                        success=True,
                        message="Slack message sent successfully",
                        data={"channel": channel, "message": rendered_message},
                    )
                return ActionResult(
                    success=False,
                    message=f"Slack API returned status {status}",
                )
        except Exception as exc:
            return ActionResult(
                success=False,
                message=f"Failed to send Slack message: {exc}",
            )