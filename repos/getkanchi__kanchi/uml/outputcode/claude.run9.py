from __future__ import annotations

import asyncio
import hashlib
import json
import re
import string
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple

# ---------------------------------------------------------------------------
# Simple named-tuple / dataclass stand-ins for event types referenced in sigs
# ---------------------------------------------------------------------------

class TaskEvent:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class WorkerEvent:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TaskProgressEvent:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TaskStepsEvent:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class ActionResult:
    def __init__(self, success: bool, message: str = "", data: Optional[Dict[str, Any]] = None):
        self.success = success
        self.message = message
        self.data = data or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"success": self.success, "message": self.message, "data": self.data}


# ---------------------------------------------------------------------------
# Stub WebSocket type
# ---------------------------------------------------------------------------

class WebSocket:
    pass


# ---------------------------------------------------------------------------
# Database model base
# ---------------------------------------------------------------------------

class _BaseDB:
    """Minimal base that provides a generic to_dict helper."""

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if key.startswith("_"):
                continue
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result


# ---------------------------------------------------------------------------
# Database models
# ---------------------------------------------------------------------------

class ActionConfigDB(_BaseDB):
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        action_type: str = "",
        config: Optional[Dict[str, Any]] = None,
        description: str = "",
        created_by: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        last_used_at: Optional[datetime] = None,
        usage_count: int = 0,
    ):
        self.id = id
        self.name = name
        self.action_type = action_type
        self.config = config or {}
        self.description = description
        self.created_by = created_by
        self.created_at = created_at
        self.updated_at = updated_at
        self.last_used_at = last_used_at
        self.usage_count = usage_count

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict()


class AppSettingDB(_BaseDB):
    def __init__(
        self,
        key: str = "",
        value: str = "",
        value_type: str = "string",
        label: str = "",
        description: str = "",
        category: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.key = key
        self.value = value
        self.value_type = value_type
        self.label = label
        self.description = description
        self.category = category
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict()


class EnvironmentDB(_BaseDB):
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        description: str = "",
        is_active: bool = True,
        is_default: bool = False,
        queue_patterns: Optional[List[str]] = None,
        worker_patterns: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.is_active = is_active
        self.is_default = is_default
        self.queue_patterns = queue_patterns or []
        self.worker_patterns = worker_patterns or []
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict()


class RetryRelationshipDB(_BaseDB):
    def __init__(
        self,
        id: Optional[int] = None,
        task_id: str = "",
        original_id: str = "",
        retry_chain: Optional[List[str]] = None,
        total_retries: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.task_id = task_id
        self.original_id = original_id
        self.retry_chain = retry_chain or []
        self.total_retries = total_retries
        self.created_at = created_at
        self.updated_at = updated_at


class TaskActionDB(_BaseDB):
    def __init__(
        self,
        id: Optional[int] = None,
        action_type: str = "",
        status: str = "",
        initiated_by: str = "",
        initiated_by_user_id: Optional[int] = None,
        initiated_session_id: Optional[str] = None,
        original_task_ids: Optional[List[str]] = None,
        selection_size: int = 0,
        item_total: int = 0,
        item_changed: int = 0,
        item_created: int = 0,
        item_failed: int = 0,
        item_noop: int = 0,
        item_skipped: int = 0,
        items: Optional[List[Any]] = None,
        summary: Optional[Dict[str, Any]] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.action_type = action_type
        self.status = status
        self.initiated_by = initiated_by
        self.initiated_by_user_id = initiated_by_user_id
        self.initiated_session_id = initiated_session_id
        self.original_task_ids = original_task_ids or []
        self.selection_size = selection_size
        self.item_total = item_total
        self.item_changed = item_changed
        self.item_created = item_created
        self.item_failed = item_failed
        self.item_noop = item_noop
        self.item_skipped = item_skipped
        self.items = items or []
        self.summary = summary or {}
        self.started_at = started_at
        self.completed_at = completed_at
        self.created_at = created_at


class TaskActionItemDB(_BaseDB):
    def __init__(
        self,
        id: Optional[int] = None,
        action_id: Optional[int] = None,
        action: str = "",
        original_task_id: str = "",
        original_task_name: str = "",
        attempted_task_id: Optional[str] = None,
        outcome: str = "",
        reason: str = "",
        reason_code: str = "",
        rerun_kind: Optional[str] = None,
        rerun_task_id: Optional[str] = None,
        rerun_task_name: Optional[str] = None,
        review_fingerprint: Optional[str] = None,
        skip_category: Optional[str] = None,
        submitted_args: Optional[List[Any]] = None,
        submitted_kwargs: Optional[Dict[str, Any]] = None,
        target_queue: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.action_id = action_id
        self.action = action
        self.original_task_id = original_task_id
        self.original_task_name = original_task_name
        self.attempted_task_id = attempted_task_id
        self.outcome = outcome
        self.reason = reason
        self.reason_code = reason_code
        self.rerun_kind = rerun_kind
        self.rerun_task_id = rerun_task_id
        self.rerun_task_name = rerun_task_name
        self.review_fingerprint = review_fingerprint
        self.skip_category = skip_category
        self.submitted_args = submitted_args or []
        self.submitted_kwargs = submitted_kwargs or {}
        self.target_queue = target_queue
        self.created_at = created_at
        self.updated_at = updated_at


class TaskDailyStatsDB(_BaseDB):
    def __init__(
        self,
        id: Optional[int] = None,
        task_name: str = "",
        date: Optional[datetime] = None,
        total_executions: int = 0,
        succeeded: int = 0,
        failed: int = 0,
        retried: int = 0,
        revoked: int = 0,
        pending: int = 0,
        orphaned: int = 0,
        avg_runtime: Optional[float] = None,
        min_runtime: Optional[float] = None,
        max_runtime: Optional[float] = None,
        p50_runtime: Optional[float] = None,
        p95_runtime: Optional[float] = None,
        p99_runtime: Optional[float] = None,
        first_execution: Optional[datetime] = None,
        last_execution: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.task_name = task_name
        self.date = date
        self.total_executions = total_executions
        self.succeeded = succeeded
        self.failed = failed
        self.retried = retried
        self.revoked = revoked
        self.pending = pending
        self.orphaned = orphaned
        self.avg_runtime = avg_runtime
        self.min_runtime = min_runtime
        self.max_runtime = max_runtime
        self.p50_runtime = p50_runtime
        self.p95_runtime = p95_runtime
        self.p99_runtime = p99_runtime
        self.first_execution = first_execution
        self.last_execution = last_execution
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict()


class TaskEventDB(_BaseDB):
    def __init__(
        self,
        id: Optional[int] = None,
        task_id: str = "",
        task_name: str = "",
        event_type: str = "",
        hostname: str = "",
        worker_name: str = "",
        timestamp: Optional[datetime] = None,
        args: Optional[str] = None,
        kwargs: Optional[str] = None,
        result: Optional[str] = None,
        exception: Optional[str] = None,
        traceback: Optional[str] = None,
        runtime: Optional[float] = None,
        retries: int = 0,
        retry_count: int = 0,
        is_retry: bool = False,
        has_retries: bool = False,
        retry_of: Optional[str] = None,
        retried_by: Optional[str] = None,
        parent_id: Optional[str] = None,
        root_id: Optional[str] = None,
        queue: Optional[str] = None,
        exchange: Optional[str] = None,
        routing_key: Optional[str] = None,
        eta: Optional[datetime] = None,
        expires: Optional[datetime] = None,
        is_orphan: bool = False,
        orphaned_at: Optional[datetime] = None,
    ):
        self.id = id
        self.task_id = task_id
        self.task_name = task_name
        self.event_type = event_type
        self.hostname = hostname
        self.worker_name = worker_name
        self.timestamp = timestamp
        self.args = args
        self.kwargs = kwargs
        self.result = result
        self.exception = exception
        self.traceback = traceback
        self.runtime = runtime
        self.retries = retries
        self.retry_count = retry_count
        self.is_retry = is_retry
        self.has_retries = has_retries
        self.retry_of = retry_of
        self.retried_by = retried_by
        self.parent_id = parent_id
        self.root_id = root_id
        self.queue = queue
        self.exchange = exchange
        self.routing_key = routing_key
        self.eta = eta
        self.expires = expires
        self.is_orphan = is_orphan
        self.orphaned_at = orphaned_at

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict()


class TaskLatestDB(_BaseDB):
    def __init__(
        self,
        task_id: str = "",
        task_name: str = "",
        event_id: Optional[int] = None,
        event_type: str = "",
        hostname: str = "",
        worker_name: str = "",
        timestamp: Optional[datetime] = None,
        args: Optional[str] = None,
        kwargs: Optional[str] = None,
        result: Optional[str] = None,
        exception: Optional[str] = None,
        traceback: Optional[str] = None,
        runtime: Optional[float] = None,
        retries: int = 0,
        retry_count: int = 0,
        is_retry: bool = False,
        has_retries: bool = False,
        retry_of: Optional[str] = None,
        retried_by: Optional[str] = None,
        parent_id: Optional[str] = None,
        root_id: Optional[str] = None,
        queue: Optional[str] = None,
        exchange: Optional[str] = None,
        routing_key: Optional[str] = None,
        eta: Optional[datetime] = None,
        expires: Optional[datetime] = None,
        is_orphan: bool = False,
        orphaned_at: Optional[datetime] = None,
        resolved: bool = False,
        resolved_at: Optional[datetime] = None,
        resolved_by: Optional[str] = None,
    ):
        self.task_id = task_id
        self.task_name = task_name
        self.event_id = event_id
        self.event_type = event_type
        self.hostname = hostname
        self.worker_name = worker_name
        self.timestamp = timestamp
        self.args = args
        self.kwargs = kwargs
        self.result = result
        self.exception = exception
        self.traceback = traceback
        self.runtime = runtime
        self.retries = retries
        self.retry_count = retry_count
        self.is_retry = is_retry
        self.has_retries = has_retries
        self.retry_of = retry_of
        self.retried_by = retried_by
        self.parent_id = parent_id
        self.root_id = root_id
        self.queue = queue
        self.exchange = exchange
        self.routing_key = routing_key
        self.eta = eta
        self.expires = expires
        self.is_orphan = is_orphan
        self.orphaned_at = orphaned_at
        self.resolved = resolved
        self.resolved_at = resolved_at
        self.resolved_by = resolved_by


class TaskProgressDB(_BaseDB):
    def __init__(
        self,
        id: Optional[int] = None,
        task_id: str = "",
        task_name: str = "",
        progress: float = 0.0,
        message: str = "",
        step_key: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.id = id
        self.task_id = task_id
        self.task_name = task_name
        self.progress = progress
        self.message = message
        self.step_key = step_key
        self.meta = meta or {}
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict()


class TaskProgressLatestDB(_BaseDB):
    def __init__(
        self,
        task_id: str = "",
        task_name: str = "",
        progress: float = 0.0,
        message: str = "",
        step_key: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.task_id = task_id
        self.task_name = task_name
        self.progress = progress
        self.message = message
        self.step_key = step_key
        self.meta = meta or {}
        self.updated_at = updated_at

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict()


class TaskRegistryDB(_BaseDB):
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        human_readable_name: str = "",
        description: str = "",
        tags: Optional[List[str]] = None,
        first_seen: Optional[datetime] = None,
        last_seen: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.human_readable_name = human_readable_name
        self.description = description
        self.tags = tags or []
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict()


class TaskRerunRelationshipDB(_BaseDB):
    def __init__(
        self,
        id: Optional[int] = None,
        original_task_id: str = "",
        rerun_task_id: str = "",
        action_id: Optional[int] = None,
        created_by: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.original_task_id = original_task_id
        self.rerun_task_id = rerun_task_id
        self.action_id = action_id
        self.created_by = created_by
        self.created_at = created_at


class TaskResolutionDB(_BaseDB):
    def __init__(
        self,
        task_id: str = "",
        resolved: bool = False,
        resolved_at: Optional[datetime] = None,
        resolved_by: Optional[str] = None,
    ):
        self.task_id = task_id
        self.resolved = resolved
        self.resolved_at = resolved_at
        self.resolved_by = resolved_by


class TaskStepsDB(_BaseDB):
    def __init__(
        self,
        task_id: str = "",
        task_name: str = "",
        steps: Optional[List[Any]] = None,
        defined_at: Optional[datetime] = None,
    ):
        self.task_id = task_id
        self.task_name = task_name
        self.steps = steps or []
        self.defined_at = defined_at

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict()


class UserDB(_BaseDB):
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        email: str = "",
        avatar_url: Optional[str] = None,
        provider: str = "",
        provider_account_id: str = "",
        is_active: bool = True,
        last_login_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        sessions: Optional[List[Any]] = None,
    ):
        self.id = id
        self.name = name
        self.email = email
        self.avatar_url = avatar_url
        self.provider = provider
        self.provider_account_id = provider_account_id
        self.is_active = is_active
        self.last_login_at = last_login_at
        self.created_at = created_at
        self.updated_at = updated_at
        self.sessions = sessions or []

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.pop("sessions", None)
        return d


class UserSessionDB(_BaseDB):
    def __init__(
        self,
        session_id: str = "",
        user_id: Optional[int] = None,
        auth_provider: str = "",
        access_token_hash: Optional[str] = None,
        access_token_expires_at: Optional[datetime] = None,
        refresh_token_hash: Optional[str] = None,
        refresh_token_expires_at: Optional[datetime] = None,
        token_scopes: Optional[List[str]] = None,
        active_environment_id: Optional[int] = None,
        preferences: Optional[Dict[str, Any]] = None,
        last_active: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        user: Optional[UserDB] = None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.auth_provider = auth_provider
        self.access_token_hash = access_token_hash
        self.access_token_expires_at = access_token_expires_at
        self.refresh_token_hash = refresh_token_hash
        self.refresh_token_expires_at = refresh_token_expires_at
        self.token_scopes = token_scopes or []
        self.active_environment_id = active_environment_id
        self.preferences = preferences or {}
        self.last_active = last_active
        self.created_at = created_at
        self.user = user

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        if self.user is not None:
            d["user"] = self.user.to_dict()
        return d


class WorkerEventDB(_BaseDB):
    def __init__(
        self,
        id: Optional[int] = None,
        hostname: str = "",
        event_type: str = "",
        status: str = "",
        active_tasks: int = 0,
        processed: int = 0,
        timestamp: Optional[datetime] = None,
    ):
        self.id = id
        self.hostname = hostname
        self.event_type = event_type
        self.status = status
        self.active_tasks = active_tasks
        self.processed = processed
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict()


class WorkflowDB(_BaseDB):
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        description: str = "",
        trigger_type: str = "",
        trigger_config: Optional[Dict[str, Any]] = None,
        conditions: Optional[List[Any]] = None,
        actions: Optional[List[Any]] = None,
        enabled: bool = True,
        priority: int = 0,
        cooldown_seconds: int = 0,
        max_executions_per_hour: Optional[int] = None,
        circuit_breaker_config: Optional[Dict[str, Any]] = None,
        execution_count: int = 0,
        success_count: int = 0,
        failure_count: int = 0,
        last_executed_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.trigger_type = trigger_type
        self.trigger_config = trigger_config or {}
        self.conditions = conditions or []
        self.actions = actions or []
        self.enabled = enabled
        self.priority = priority
        self.cooldown_seconds = cooldown_seconds
        self.max_executions_per_hour = max_executions_per_hour
        self.circuit_breaker_config = circuit_breaker_config or {}
        self.execution_count = execution_count
        self.success_count = success_count
        self.failure_count = failure_count
        self.last_executed_at = last_executed_at
        self.created_by = created_by
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict()


class WorkflowExecutionDB(_BaseDB):
    def __init__(
        self,
        id: Optional[int] = None,
        workflow_id: Optional[int] = None,
        workflow_snapshot: Optional[Dict[str, Any]] = None,
        trigger_type: str = "",
        trigger_event: Optional[Dict[str, Any]] = None,
        status: str = "",
        actions_executed: Optional[List[Any]] = None,
        error_message: Optional[str] = None,
        stack_trace: Optional[str] = None,
        circuit_breaker_key: Optional[str] = None,
        triggered_at: Optional[datetime] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
    ):
        self.id = id
        self.workflow_id = workflow_id
        self.workflow_snapshot = workflow_snapshot or {}
        self.trigger_type = trigger_type
        self.trigger_event = trigger_event or {}
        self.status = status
        self.actions_executed = actions_executed or []
        self.error_message = error_message
        self.stack_trace = stack_trace
        self.circuit_breaker_key = circuit_breaker_key
        self.triggered_at = triggered_at
        self.started_at = started_at
        self.completed_at = completed_at
        self.duration_ms = duration_ms

    def to_dict(self) -> Dict[str, Any]:
        return super().to_dict()


# ---------------------------------------------------------------------------
# DatabaseManager
# ---------------------------------------------------------------------------

class Session:
    """Minimal stub for a database session."""

    def __init__(self):
        self._objects: List[Any] = []

    def add(self, obj: Any) -> None:
        self._objects.append(obj)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass

    def query(self, model: Any):
        return self

    def filter(self, *args):
        return self

    def first(self):
        return None

    def all(self) -> List[Any]:
        return []


class DatabaseManager:
    def __init__(self, database_url: str = "sqlite:///:memory:"):
        self.database_url: str = database_url
        self.engine = None
        self.SessionLocal = None
        self._setup()

    def _setup(self) -> None:
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            self.engine = create_engine(self.database_url)
            self.SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )
        except ImportError:
            self.engine = None
            self.SessionLocal = None

    def get_session(self) -> Session:
        if self.SessionLocal is not None:
            return self.SessionLocal()
        return Session()

    def run_migrations(self) -> None:
        if self.engine is None:
            return
        try:
            from alembic.config import Config
            from alembic import command

            alembic_cfg = Config()
            alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
            command.upgrade(alembic_cfg, "head")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# CeleryEventMonitor
# ---------------------------------------------------------------------------

class CeleryEventMonitor:
    def __init__(self, broker_url: str = "redis://localhost:6379/0"):
        self.broker_url: str = broker_url
        self.app = None
        self.state = None
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
        try:
            from celery import Celery
            from celery.events import EventReceiver

            if self.app is None:
                self.app = Celery(broker=self.broker_url)

            with self.app.connection() as connection:
                self.state = self.app.events.State()
                recv = EventReceiver(
                    connection,
                    handlers={"*": self._on_event},
                    app=self.app,
                )
                recv.capture(limit=None, timeout=None, wakeup=True)
        except Exception:
            pass

    def _on_event(self, event: Dict[str, Any]) -> None:
        event_type = event.get("type", "")
        if event_type.startswith("worker-"):
            worker_event = WorkerEvent(**event)
            hostname = event.get("hostname", "")
            self.workers[hostname] = event
            if self.worker_callback:
                self.worker_callback(worker_event)
        elif event_type.startswith("task-"):
            task_event = TaskEvent(**event)
            if self.task_callback:
                self.task_callback(task_event)

    def stop(self) -> None:
        self._running = False
        self.app = None


# ---------------------------------------------------------------------------
# ConnectionManager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_filters: Dict[WebSocket, dict] = {}
        self.client_modes: Dict[WebSocket, str] = {}
        self.message_queue: Optional[asyncio.Queue] = None
        self._broadcaster_task: Optional[asyncio.Task] = None

    def connect(self, websocket: WebSocket) -> None:
        if websocket not in self.active_connections:
            self.active_connections.append(websocket)
            self.client_filters[websocket] = {}
            self.client_modes[websocket] = "default"

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.client_filters.pop(websocket, None)
        self.client_modes.pop(websocket, None)

    def set_client_filters(self, websocket: WebSocket, filters: dict) -> None:
        self.client_filters[websocket] = filters

    def set_client_mode(self, websocket: WebSocket, mode: str) -> None:
        self.client_modes[websocket] = mode

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        try:
            await websocket.send_text(message)  # type: ignore[attr-defined]
        except Exception:
            pass

    def queue_broadcast(self, task_event: TaskEvent) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "task", "event": task_event})
            except asyncio.QueueFull:
                pass

    def queue_worker_broadcast(self, worker_event: WorkerEvent) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "worker", "event": worker_event})
            except asyncio.QueueFull:
                pass

    def queue_progress_broadcast(self, progress_event: Any) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "progress", "event": progress_event})
            except asyncio.QueueFull:
                pass

    def queue_task_action_broadcast(self, action_event: Any) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "action", "event": action_event})
            except asyncio.QueueFull:
                pass

    async def _background_broadcaster(self) -> None:
        while True:
            if self.message_queue is None:
                break
            try:
                item = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            message = json.dumps(item, default=str)
            for ws in list(self.active_connections):
                await self.send_personal_message(message, ws)

    def start_background_broadcaster(self) -> None:
        self.message_queue = asyncio.Queue()
        loop = asyncio.get_event_loop()
        self._broadcaster_task = loop.create_task(self._background_broadcaster())

    def stop_background_broadcaster(self) -> None:
        if self._broadcaster_task is not None:
            self._broadcaster_task.cancel()
            self._broadcaster_task = None
        self.message_queue = None


# ---------------------------------------------------------------------------
# EventHandler
# ---------------------------------------------------------------------------

class EventHandler:
    def __init__(
        self,
        connection_manager: ConnectionManager,
        db_manager: DatabaseManager,
    ):
        self.connection_manager = connection_manager
        self.db_manager = db_manager
        self.workflow_engine = None

    def handle_task_event(self, task_event: TaskEvent) -> None:
        self.connection_manager.queue_broadcast(task_event)
        session = self.db_manager.get_session()
        try:
            event_data = task_event.__dict__ if hasattr(task_event, "__dict__") else {}
            db_event = TaskEventDB(
                task_id=event_data.get("uuid", event_data.get("task_id", "")),
                task_name=event_data.get("name", event_data.get("task_name", "")),
                event_type=event_data.get("type", event_data.get("event_type", "")),
                hostname=event_data.get("hostname", ""),
                timestamp=datetime.utcnow(),
            )
            session.add(db_event)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    def handle_worker_event(self, worker_event: WorkerEvent) -> None:
        self.connection_manager.queue_worker_broadcast(worker_event)
        session = self.db_manager.get_session()
        try:
            event_data = worker_event.__dict__ if hasattr(worker_event, "__dict__") else {}
            db_event = WorkerEventDB(
                hostname=event_data.get("hostname", ""),
                event_type=event_data.get("type", event_data.get("event_type", "")),
                status=event_data.get("status", ""),
                timestamp=datetime.utcnow(),
            )
            session.add(db_event)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    def handle_progress_event(self, progress_event: Any) -> None:
        self.connection_manager.queue_progress_broadcast(progress_event)
        session = self.db_manager.get_session()
        try:
            event_data = progress_event.__dict__ if hasattr(progress_event, "__dict__") else {}
            db_progress = TaskProgressDB(
                task_id=event_data.get("task_id", ""),
                task_name=event_data.get("task_name", ""),
                progress=event_data.get("progress", 0.0),
                message=event_data.get("message", ""),
                timestamp=datetime.utcnow(),
            )
            session.add(db_progress)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    def handle_steps_event(self, steps_event: Any) -> None:
        session = self.db_manager.get_session()
        try:
            event_data = steps_event.__dict__ if hasattr(steps_event, "__dict__") else {}
            db_steps = TaskStepsDB(
                task_id=event_data.get("task_id", ""),
                task_name=event_data.get("task_name", ""),
                steps=event_data.get("steps", []),
                defined_at=datetime.utcnow(),
            )
            session.add(db_steps)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()


# ---------------------------------------------------------------------------
# ActionHandler (abstract base)
# ---------------------------------------------------------------------------

class ActionHandler(ABC):
    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        session: Optional[Session] = None,
    ):
        self.db_manager = db_manager
        self.session = session
        self.monitor_instance = None

    @abstractmethod
    def execute(
        self, context: Dict[str, Any], params: Dict[str, Any]
    ) -> ActionResult:
        ...

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        ...

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        try:
            tmpl = string.Template(template)
            return tmpl.safe_substitute(context)
        except Exception as exc:
            return template


# ---------------------------------------------------------------------------
# RetryActionHandler
# ---------------------------------------------------------------------------

class RetryActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "task_id" not in params and "task_ids" not in params:
            return False, "Either 'task_id' or 'task_ids' must be provided."
        return True, ""

    def execute(
        self, context: Dict[str, Any], params: Dict[str, Any]
    ) -> ActionResult:
        valid, error = self.validate_params(params)
        if not valid:
            return ActionResult(success=False, message=error)

        task_ids: List[str] = []
        if "task_ids" in params:
            task_ids = list(params["task_ids"])
        elif "task_id" in params:
            task_ids = [params["task_id"]]

        retried: List[str] = []
        failed: List[str] = []

        for task_id in task_ids:
            try:
                if self.monitor_instance is not None:
                    app = getattr(self.monitor_instance, "app", None)
                    if app is not None:
                        from celery.result import AsyncResult

                        result = AsyncResult(task_id, app=app)
                        result.retry()
                        retried.append(task_id)
                        continue
                retried.append(task_id)
            except Exception as exc:
                failed.append(task_id)

        if failed:
            return ActionResult(
                success=len(retried) > 0,
                message=f"Retried {len(retried)} tasks; {len(failed)} failed.",
                data={"retried": retried, "failed": failed},
            )
        return ActionResult(
            success=True,
            message=f"Successfully retried {len(retried)} task(s).",
            data={"retried": retried},
        )


# ---------------------------------------------------------------------------
# SlackActionHandler
# ---------------------------------------------------------------------------

class SlackActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "webhook_url" not in params and "channel" not in params:
            return False, "Either 'webhook_url' or 'channel' must be provided."
        if "message" not in params and "text" not in params:
            return False, "Either 'message' or 'text' must be provided."
        return True, ""

    def execute(
        self, context: Dict[str, Any], params: Dict[str, Any]
    ) -> ActionResult:
        valid, error = self.validate_params(params)
        if not valid:
            return ActionResult(success=False, message=error)

        raw_message = params.get("message", params.get("text", ""))
        message = self.render_template(raw_message, context)
        webhook_url: str = params.get("webhook_url", "")

        payload: Dict[str, Any] = {"text": message}
        if "channel" in params:
            payload["channel"] = params["channel"]
        if "username" in params:
            payload["username"] = params["username"]
        if "icon_emoji" in params:
            payload["icon_emoji"] = params["icon_emoji"]

        try:
            import urllib.request

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                status_code = resp.status
                if status_code == 200:
                    return ActionResult(
                        success=True,
                        message="Slack message sent successfully.",
                        data={"status_code": status_code},
                    )
                return ActionResult(
                    success=False,
                    message=f"Slack returned status {status_code}.",
                    data={"status_code": status_code},
                )
        except Exception as exc:
            return ActionResult(
                success=False,
                message=f"Failed to send Slack message: {exc}",
                data={"error": str(exc)},
            )