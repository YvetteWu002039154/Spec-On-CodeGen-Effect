from __future__ import annotations

import asyncio
import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


class Engine:
    def __init__(self, url: str):
        self.url = url


class MockConnection:
    def __init__(self, url: str):
        self.url = url


class Session:
    def __init__(self) -> None:
        self._closed = False

    def close(self) -> None:
        self._closed = True


class sessionmaker:
    def __init__(self, bind: Optional[Union[Engine, MockConnection]] = None):
        self.bind = bind

    def __call__(self) -> Session:
        return Session()


class WebSocket:
    def __init__(self) -> None:
        self._accepted = False
        self._closed = False
        self.sent_messages: List[str] = []

    async def accept(self) -> None:
        self._accepted = True

    async def send_text(self, message: str) -> None:
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.sent_messages.append(message)

    async def close(self) -> None:
        self._closed = True


@dataclass(frozen=True)
class TaskEvent:
    task_id: str
    task_name: str
    event_type: str
    timestamp: datetime
    payload: Dict[str, Any]


@dataclass(frozen=True)
class TaskProgressEvent:
    task_id: str
    task_name: str
    timestamp: datetime
    progress: float
    message: str
    step_key: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class TaskStepsEvent:
    task_id: str
    task_name: str
    defined_at: datetime
    steps: List[Dict[str, Any]]


@dataclass(frozen=True)
class WorkerEvent:
    hostname: str
    event_type: str
    timestamp: datetime
    status: Optional[str] = None
    active_tasks: Optional[int] = None
    processed: Optional[int] = None


@dataclass(frozen=True)
class ActionResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url: str = database_url
        self.engine: Optional[Union[Engine, MockConnection]] = None
        self.SessionLocal: sessionmaker = sessionmaker(bind=None)

    def run_migrations(self) -> None:
        if self.engine is None:
            self.engine = Engine(self.database_url)
            self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        if self.engine is None:
            self.run_migrations()
        return self.SessionLocal()


class ActionConfigDB:
    def __init__(
        self,
        id: int,
        name: str,
        action_type: str,
        config: Dict[str, Any],
        description: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
        last_used_at: Optional[datetime] = None,
        usage_count: int = 0,
    ):
        self.id = id
        self.name = name
        self.action_type = action_type
        self.config = config
        self.description = description
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at
        self.created_by = created_by
        self.last_used_at = last_used_at
        self.usage_count = usage_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "action_type": self.action_type,
            "config": _jsonable(self.config),
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "usage_count": self.usage_count,
        }


class AppSettingDB:
    def __init__(
        self,
        key: str,
        value: Any,
        value_type: str,
        category: Optional[str] = None,
        label: Optional[str] = None,
        description: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.key = key
        self.value = value
        self.value_type = value_type
        self.category = category
        self.label = label
        self.description = description
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": _jsonable(self.value),
            "value_type": self.value_type,
            "category": self.category,
            "label": self.label,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class EnvironmentDB:
    def __init__(
        self,
        id: int,
        name: str,
        queue_patterns: Optional[List[str]] = None,
        worker_patterns: Optional[List[str]] = None,
        description: Optional[str] = None,
        is_active: bool = True,
        is_default: bool = False,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.queue_patterns = queue_patterns or []
        self.worker_patterns = worker_patterns or []
        self.description = description
        self.is_active = is_active
        self.is_default = is_default
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "queue_patterns": list(self.queue_patterns),
            "worker_patterns": list(self.worker_patterns),
            "description": self.description,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class RetryRelationshipDB:
    def __init__(
        self,
        id: int,
        task_id: str,
        original_id: str,
        retry_chain: List[str],
        total_retries: int,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.task_id = task_id
        self.original_id = original_id
        self.retry_chain = retry_chain
        self.total_retries = total_retries
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at


class TaskActionDB:
    def __init__(
        self,
        id: int,
        action_type: str,
        status: str,
        initiated_by: Optional[str] = None,
        initiated_by_user_id: Optional[int] = None,
        initiated_session_id: Optional[str] = None,
        selection_size: int = 0,
        original_task_ids: Optional[List[str]] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        item_total: int = 0,
        item_created: int = 0,
        item_changed: int = 0,
        item_skipped: int = 0,
        item_failed: int = 0,
        item_noop: int = 0,
        summary: Optional[str] = None,
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
        self.selection_size = selection_size
        self.original_task_ids = original_task_ids or []
        self.items = items or []
        self.item_total = item_total
        self.item_created = item_created
        self.item_changed = item_changed
        self.item_skipped = item_skipped
        self.item_failed = item_failed
        self.item_noop = item_noop
        self.summary = summary
        self.started_at = started_at
        self.completed_at = completed_at
        self.created_at = created_at or _utcnow()


class TaskActionItemDB:
    def __init__(
        self,
        id: int,
        action_id: int,
        action: Optional[TaskActionDB] = None,
        original_task_id: Optional[str] = None,
        original_task_name: Optional[str] = None,
        attempted_task_id: Optional[str] = None,
        rerun_task_id: Optional[str] = None,
        rerun_task_name: Optional[str] = None,
        rerun_kind: Optional[str] = None,
        outcome: Optional[str] = None,
        reason: Optional[str] = None,
        reason_code: Optional[str] = None,
        skip_category: Optional[str] = None,
        review_fingerprint: Optional[str] = None,
        submitted_args: Optional[Any] = None,
        submitted_kwargs: Optional[Any] = None,
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
        self.rerun_task_id = rerun_task_id
        self.rerun_task_name = rerun_task_name
        self.rerun_kind = rerun_kind
        self.outcome = outcome
        self.reason = reason
        self.reason_code = reason_code
        self.skip_category = skip_category
        self.review_fingerprint = review_fingerprint
        self.submitted_args = submitted_args
        self.submitted_kwargs = submitted_kwargs
        self.target_queue = target_queue
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at


class TaskDailyStatsDB:
    def __init__(
        self,
        id: int,
        date: date,
        task_name: str,
        total_executions: int = 0,
        succeeded: int = 0,
        failed: int = 0,
        retried: int = 0,
        revoked: int = 0,
        pending: int = 0,
        orphaned: int = 0,
        first_execution: Optional[datetime] = None,
        last_execution: Optional[datetime] = None,
        min_runtime: Optional[float] = None,
        max_runtime: Optional[float] = None,
        avg_runtime: Optional[float] = None,
        p50_runtime: Optional[float] = None,
        p95_runtime: Optional[float] = None,
        p99_runtime: Optional[float] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.date = date
        self.task_name = task_name
        self.total_executions = total_executions
        self.succeeded = succeeded
        self.failed = failed
        self.retried = retried
        self.revoked = revoked
        self.pending = pending
        self.orphaned = orphaned
        self.first_execution = first_execution
        self.last_execution = last_execution
        self.min_runtime = min_runtime
        self.max_runtime = max_runtime
        self.avg_runtime = avg_runtime
        self.p50_runtime = p50_runtime
        self.p95_runtime = p95_runtime
        self.p99_runtime = p99_runtime
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "task_name": self.task_name,
            "total_executions": self.total_executions,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "retried": self.retried,
            "revoked": self.revoked,
            "pending": self.pending,
            "orphaned": self.orphaned,
            "first_execution": self.first_execution.isoformat() if self.first_execution else None,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "min_runtime": self.min_runtime,
            "max_runtime": self.max_runtime,
            "avg_runtime": self.avg_runtime,
            "p50_runtime": self.p50_runtime,
            "p95_runtime": self.p95_runtime,
            "p99_runtime": self.p99_runtime,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TaskEventDB:
    def __init__(
        self,
        id: int,
        task_id: str,
        task_name: str,
        event_type: str,
        timestamp: datetime,
        args: Optional[Any] = None,
        kwargs: Optional[Any] = None,
        eta: Optional[datetime] = None,
        expires: Optional[datetime] = None,
        exchange: Optional[str] = None,
        routing_key: Optional[str] = None,
        queue: Optional[str] = None,
        hostname: Optional[str] = None,
        worker_name: Optional[str] = None,
        result: Optional[Any] = None,
        exception: Optional[str] = None,
        traceback: Optional[str] = None,
        runtime: Optional[float] = None,
        retries: Optional[int] = None,
        retry_count: Optional[int] = None,
        has_retries: Optional[bool] = None,
        is_retry: Optional[bool] = None,
        retry_of: Optional[str] = None,
        retried_by: Optional[str] = None,
        parent_id: Optional[str] = None,
        root_id: Optional[str] = None,
        is_orphan: Optional[bool] = None,
        orphaned_at: Optional[datetime] = None,
    ):
        self.id = id
        self.task_id = task_id
        self.task_name = task_name
        self.event_type = event_type
        self.timestamp = timestamp
        self.args = args
        self.kwargs = kwargs
        self.eta = eta
        self.expires = expires
        self.exchange = exchange
        self.routing_key = routing_key
        self.queue = queue
        self.hostname = hostname
        self.worker_name = worker_name
        self.result = result
        self.exception = exception
        self.traceback = traceback
        self.runtime = runtime
        self.retries = retries
        self.retry_count = retry_count
        self.has_retries = has_retries
        self.is_retry = is_retry
        self.retry_of = retry_of
        self.retried_by = retried_by
        self.parent_id = parent_id
        self.root_id = root_id
        self.is_orphan = is_orphan
        self.orphaned_at = orphaned_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "args": _jsonable(self.args),
            "kwargs": _jsonable(self.kwargs),
            "eta": self.eta.isoformat() if self.eta else None,
            "expires": self.expires.isoformat() if self.expires else None,
            "exchange": self.exchange,
            "routing_key": self.routing_key,
            "queue": self.queue,
            "hostname": self.hostname,
            "worker_name": self.worker_name,
            "result": _jsonable(self.result),
            "exception": self.exception,
            "traceback": self.traceback,
            "runtime": self.runtime,
            "retries": self.retries,
            "retry_count": self.retry_count,
            "has_retries": self.has_retries,
            "is_retry": self.is_retry,
            "retry_of": self.retry_of,
            "retried_by": self.retried_by,
            "parent_id": self.parent_id,
            "root_id": self.root_id,
            "is_orphan": self.is_orphan,
            "orphaned_at": self.orphaned_at.isoformat() if self.orphaned_at else None,
        }


class TaskLatestDB:
    def __init__(
        self,
        task_id: str,
        task_name: str,
        event_id: int,
        event_type: str,
        timestamp: datetime,
        args: Optional[Any] = None,
        kwargs: Optional[Any] = None,
        eta: Optional[datetime] = None,
        expires: Optional[datetime] = None,
        exchange: Optional[str] = None,
        routing_key: Optional[str] = None,
        queue: Optional[str] = None,
        hostname: Optional[str] = None,
        worker_name: Optional[str] = None,
        result: Optional[Any] = None,
        exception: Optional[str] = None,
        traceback: Optional[str] = None,
        runtime: Optional[float] = None,
        retries: Optional[int] = None,
        retry_count: Optional[int] = None,
        has_retries: Optional[bool] = None,
        is_retry: Optional[bool] = None,
        retry_of: Optional[str] = None,
        retried_by: Optional[str] = None,
        parent_id: Optional[str] = None,
        root_id: Optional[str] = None,
        is_orphan: Optional[bool] = None,
        orphaned_at: Optional[datetime] = None,
        resolved: Optional[bool] = None,
        resolved_at: Optional[datetime] = None,
        resolved_by: Optional[str] = None,
    ):
        self.task_id = task_id
        self.task_name = task_name
        self.event_id = event_id
        self.event_type = event_type
        self.timestamp = timestamp
        self.args = args
        self.kwargs = kwargs
        self.eta = eta
        self.expires = expires
        self.exchange = exchange
        self.routing_key = routing_key
        self.queue = queue
        self.hostname = hostname
        self.worker_name = worker_name
        self.result = result
        self.exception = exception
        self.traceback = traceback
        self.runtime = runtime
        self.retries = retries
        self.retry_count = retry_count
        self.has_retries = has_retries
        self.is_retry = is_retry
        self.retry_of = retry_of
        self.retried_by = retried_by
        self.parent_id = parent_id
        self.root_id = root_id
        self.is_orphan = is_orphan
        self.orphaned_at = orphaned_at
        self.resolved = resolved
        self.resolved_at = resolved_at
        self.resolved_by = resolved_by


class TaskProgressDB:
    def __init__(
        self,
        id: int,
        task_id: str,
        task_name: str,
        timestamp: datetime,
        progress: float,
        message: str,
        step_key: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ):
        self.id = id
        self.task_id = task_id
        self.task_name = task_name
        self.timestamp = timestamp
        self.progress = progress
        self.message = message
        self.step_key = step_key
        self.meta = meta

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "timestamp": self.timestamp.isoformat(),
            "progress": self.progress,
            "message": self.message,
            "step_key": self.step_key,
            "meta": _jsonable(self.meta),
        }


class TaskProgressLatestDB:
    def __init__(
        self,
        task_id: str,
        task_name: str,
        progress: float,
        message: str,
        updated_at: datetime,
        step_key: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ):
        self.task_id = task_id
        self.task_name = task_name
        self.progress = progress
        self.message = message
        self.updated_at = updated_at
        self.step_key = step_key
        self.meta = meta

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "progress": self.progress,
            "message": self.message,
            "updated_at": self.updated_at.isoformat(),
            "step_key": self.step_key,
            "meta": _jsonable(self.meta),
        }


class TaskRegistryDB:
    def __init__(
        self,
        id: int,
        name: str,
        human_readable_name: Optional[str] = None,
        description: Optional[str] = None,
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
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "human_readable_name": self.human_readable_name,
            "description": self.description,
            "tags": list(self.tags),
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TaskRerunRelationshipDB:
    def __init__(
        self,
        id: int,
        action_id: int,
        original_task_id: str,
        rerun_task_id: str,
        created_by: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.action_id = action_id
        self.original_task_id = original_task_id
        self.rerun_task_id = rerun_task_id
        self.created_by = created_by
        self.created_at = created_at or _utcnow()


class TaskResolutionDB:
    def __init__(
        self,
        task_id: str,
        resolved: bool,
        resolved_at: Optional[datetime] = None,
        resolved_by: Optional[str] = None,
    ):
        self.task_id = task_id
        self.resolved = resolved
        self.resolved_at = resolved_at
        self.resolved_by = resolved_by


class TaskStepsDB:
    def __init__(
        self,
        task_id: str,
        task_name: str,
        defined_at: datetime,
        steps: List[Dict[str, Any]],
    ):
        self.task_id = task_id
        self.task_name = task_name
        self.defined_at = defined_at
        self.steps = steps

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "defined_at": self.defined_at.isoformat(),
            "steps": _jsonable(self.steps),
        }


class UserDB:
    def __init__(
        self,
        id: int,
        email: str,
        name: Optional[str] = None,
        provider: Optional[str] = None,
        provider_account_id: Optional[str] = None,
        avatar_url: Optional[str] = None,
        is_active: bool = True,
        last_login_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        sessions: Optional[List[UserSessionDB]] = None,
    ):
        self.id = id
        self.email = email
        self.name = name
        self.provider = provider
        self.provider_account_id = provider_account_id
        self.avatar_url = avatar_url
        self.is_active = is_active
        self.last_login_at = last_login_at
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at
        self.sessions: List[UserSessionDB] = sessions or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "provider": self.provider,
            "provider_account_id": self.provider_account_id,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "sessions": [s.to_dict() for s in self.sessions],
        }


class UserSessionDB:
    def __init__(
        self,
        session_id: str,
        user_id: int,
        user: Optional[UserDB] = None,
        auth_provider: Optional[str] = None,
        token_scopes: Optional[List[str]] = None,
        preferences: Optional[Dict[str, Any]] = None,
        active_environment_id: Optional[int] = None,
        access_token_hash: Optional[str] = None,
        refresh_token_hash: Optional[str] = None,
        access_token_expires_at: Optional[datetime] = None,
        refresh_token_expires_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        last_active: Optional[datetime] = None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.user = user
        self.auth_provider = auth_provider
        self.token_scopes = token_scopes or []
        self.preferences = preferences or {}
        self.active_environment_id = active_environment_id
        self.access_token_hash = access_token_hash
        self.refresh_token_hash = refresh_token_hash
        self.access_token_expires_at = access_token_expires_at
        self.refresh_token_expires_at = refresh_token_expires_at
        self.created_at = created_at or _utcnow()
        self.last_active = last_active or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "auth_provider": self.auth_provider,
            "token_scopes": list(self.token_scopes),
            "preferences": _jsonable(self.preferences),
            "active_environment_id": self.active_environment_id,
            "access_token_hash": self.access_token_hash,
            "refresh_token_hash": self.refresh_token_hash,
            "access_token_expires_at": self.access_token_expires_at.isoformat() if self.access_token_expires_at else None,
            "refresh_token_expires_at": self.refresh_token_expires_at.isoformat() if self.refresh_token_expires_at else None,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "user": self.user.to_dict() if self.user else None,
        }


class WorkerEventDB:
    def __init__(
        self,
        id: int,
        hostname: str,
        event_type: str,
        timestamp: datetime,
        status: Optional[str] = None,
        active_tasks: Optional[int] = None,
        processed: Optional[int] = None,
    ):
        self.id = id
        self.hostname = hostname
        self.event_type = event_type
        self.timestamp = timestamp
        self.status = status
        self.active_tasks = active_tasks
        self.processed = processed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "hostname": self.hostname,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "active_tasks": self.active_tasks,
            "processed": self.processed,
        }


class WorkflowDB:
    def __init__(
        self,
        id: int,
        name: str,
        trigger_type: str,
        trigger_config: Dict[str, Any],
        actions: List[Dict[str, Any]],
        enabled: bool = True,
        priority: int = 0,
        conditions: Optional[List[Dict[str, Any]]] = None,
        cooldown_seconds: Optional[int] = None,
        max_executions_per_hour: Optional[int] = None,
        circuit_breaker_config: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        execution_count: int = 0,
        success_count: int = 0,
        failure_count: int = 0,
        last_executed_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.id = id
        self.name = name
        self.trigger_type = trigger_type
        self.trigger_config = trigger_config
        self.actions = actions
        self.enabled = enabled
        self.priority = priority
        self.conditions = conditions or []
        self.cooldown_seconds = cooldown_seconds
        self.max_executions_per_hour = max_executions_per_hour
        self.circuit_breaker_config = circuit_breaker_config or {}
        self.description = description
        self.created_by = created_by
        self.execution_count = execution_count
        self.success_count = success_count
        self.failure_count = failure_count
        self.last_executed_at = last_executed_at
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "trigger_type": self.trigger_type,
            "trigger_config": _jsonable(self.trigger_config),
            "actions": _jsonable(self.actions),
            "enabled": self.enabled,
            "priority": self.priority,
            "conditions": _jsonable(self.conditions),
            "cooldown_seconds": self.cooldown_seconds,
            "max_executions_per_hour": self.max_executions_per_hour,
            "circuit_breaker_config": _jsonable(self.circuit_breaker_config),
            "description": self.description,
            "created_by": self.created_by,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_executed_at": self.last_executed_at.isoformat() if self.last_executed_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class WorkflowExecutionDB:
    def __init__(
        self,
        id: int,
        workflow_id: int,
        trigger_type: str,
        trigger_event: Dict[str, Any],
        triggered_at: datetime,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        actions_executed: Optional[List[Dict[str, Any]]] = None,
        workflow_snapshot: Optional[Dict[str, Any]] = None,
        circuit_breaker_key: Optional[str] = None,
        error_message: Optional[str] = None,
        stack_trace: Optional[str] = None,
    ):
        self.id = id
        self.workflow_id = workflow_id
        self.trigger_type = trigger_type
        self.trigger_event = trigger_event
        self.triggered_at = triggered_at
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.duration_ms = duration_ms
        self.actions_executed = actions_executed or []
        self.workflow_snapshot = workflow_snapshot or {}
        self.circuit_breaker_key = circuit_breaker_key
        self.error_message = error_message
        self.stack_trace = stack_trace

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "trigger_type": self.trigger_type,
            "trigger_event": _jsonable(self.trigger_event),
            "triggered_at": self.triggered_at.isoformat(),
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "actions_executed": _jsonable(self.actions_executed),
            "workflow_snapshot": _jsonable(self.workflow_snapshot),
            "circuit_breaker_key": self.circuit_breaker_key,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
        }


class ActionHandler(ABC):
    def __init__(self, db_manager: DatabaseManager, session: Optional[Session] = None):
        self.db_manager: DatabaseManager = db_manager
        self.session: Session = session or db_manager.get_session()
        self.monitor_instance: None = None

    @abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        raise NotImplementedError

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        try:
            return template.format(**context)
        except KeyError as e:
            missing = str(e).strip("'")
            raise ValueError(f"Missing template key: {missing}") from e

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        raise NotImplementedError


class RetryActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(params, dict):
            return False, "params must be a dict"
        task_ids = params.get("task_ids")
        if not isinstance(task_ids, list) or not task_ids or not all(isinstance(t, str) and t for t in task_ids):
            return False, "task_ids must be a non-empty list of strings"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        ok, msg = self.validate_params(params)
        if not ok:
            return ActionResult(success=False, message=msg)

        task_ids: List[str] = params["task_ids"]
        rerun_kind = params.get("rerun_kind", "retry")
        if not isinstance(rerun_kind, str) or not rerun_kind:
            return ActionResult(success=False, message="rerun_kind must be a non-empty string")

        now = _utcnow()
        results: List[Dict[str, Any]] = []
        for tid in task_ids:
            digest = hashlib.sha256(f"{tid}:{now.isoformat()}".encode("utf-8")).hexdigest()[:32]
            rerun_task_id = f"retry-{digest}"
            results.append(
                {
                    "original_task_id": tid,
                    "rerun_task_id": rerun_task_id,
                    "rerun_kind": rerun_kind,
                }
            )

        return ActionResult(success=True, message="Retry action executed", data={"items": results})


class SlackActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(params, dict):
            return False, "params must be a dict"
        channel = params.get("channel")
        text = params.get("text")
        if not isinstance(channel, str) or not channel:
            return False, "channel must be a non-empty string"
        if not isinstance(text, str) or not text:
            return False, "text must be a non-empty string"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        ok, msg = self.validate_params(params)
        if not ok:
            return ActionResult(success=False, message=msg)

        channel: str = params["channel"]
        text: str = params["text"]
        rendered = self.render_template(text, context) if context else text
        return ActionResult(
            success=True,
            message="Slack action executed",
            data={"channel": channel, "text": rendered},
        )


class CeleryEventMonitor:
    def __init__(
        self,
        broker_url: str,
        app: Optional[Any] = None,
        progress_callback: Optional[Callable[[TaskProgressEvent], None]] = None,
        steps_callback: Optional[Callable[[TaskStepsEvent], None]] = None,
        task_callback: Optional[Callable[[TaskEvent], None]] = None,
        worker_callback: Optional[Callable[[WorkerEvent], None]] = None,
    ):
        self.app = app
        self.broker_url: str = broker_url
        self.progress_callback = progress_callback
        self.steps_callback = steps_callback
        self.task_callback = task_callback
        self.worker_callback = worker_callback
        self.state: None = None
        self.workers: Dict[str, Dict[str, Any]] = {}
        self._running: bool = False

    def set_progress_callback(self, callback: Callable[[TaskProgressEvent], None]):
        self.progress_callback = callback

    def set_steps_callback(self, callback: Callable[[TaskStepsEvent], None]):
        self.steps_callback = callback

    def set_task_callback(self, callback: Callable[[TaskEvent], None]):
        self.task_callback = callback

    def set_worker_callback(self, callback: Callable[[WorkerEvent], None]):
        self.worker_callback = callback

    def start_monitoring(self):
        self._running = True

    def stop(self):
        self._running = False

    def get_workers_info(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.workers)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_filters: Dict[WebSocket, dict] = {}
        self.client_modes: Dict[WebSocket, str] = {}
        self.message_queue: Optional[asyncio.Queue] = None
        self._broadcaster_task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        if websocket not in self.active_connections:
            self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.client_filters.pop(websocket, None)
        self.client_modes.pop(websocket, None)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    def set_client_filters(self, websocket: WebSocket, filters: dict):
        self.client_filters[websocket] = filters

    def set_client_mode(self, websocket: WebSocket, mode: str):
        self.client_modes[websocket] = mode

    def start_background_broadcaster(self):
        if self.message_queue is None:
            self.message_queue = asyncio.Queue()
        if self._stop_event is None:
            self._stop_event = asyncio.Event()
        if self._broadcaster_task is None or self._broadcaster_task.done():
            self._broadcaster_task = asyncio.create_task(self._background_broadcaster())

    def stop_background_broadcaster(self):
        if self._stop_event is not None:
            self._stop_event.set()
        if self._broadcaster_task is not None:
            self._broadcaster_task.cancel()

    def queue_broadcast(self, task_event: TaskEvent):
        if self.message_queue is None:
            return
        payload = {"type": "task_event", "data": _jsonable(task_event.__dict__)}
        self.message_queue.put_nowait(payload)

    def queue_progress_broadcast(self, progress_event):
        if self.message_queue is None:
            return
        data = progress_event.__dict__ if hasattr(progress_event, "__dict__") else progress_event
        payload = {"type": "progress_event", "data": _jsonable(data)}
        self.message_queue.put_nowait(payload)

    def queue_task_action_broadcast(self, action_event):
        if self.message_queue is None:
            return
        data = action_event.__dict__ if hasattr(action_event, "__dict__") else action_event
        payload = {"type": "task_action_event", "data": _jsonable(data)}
        self.message_queue.put_nowait(payload)

    def queue_worker_broadcast(self, worker_event: WorkerEvent):
        if self.message_queue is None:
            return
        payload = {"type": "worker_event", "data": _jsonable(worker_event.__dict__)}
        self.message_queue.put_nowait(payload)

    async def _background_broadcaster(self) -> None:
        assert self.message_queue is not None
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            try:
                item = await asyncio.wait_for(self.message_queue.get(), timeout=0.25)
            except asyncio.TimeoutError:
                continue

            message = json.dumps(item, default=str)
            to_remove: List[WebSocket] = []
            for ws in list(self.active_connections):
                try:
                    await ws.send_text(message)
                except Exception:
                    to_remove.append(ws)
            for ws in to_remove:
                self.disconnect(ws)


class EventHandler:
    def __init__(self, connection_manager: ConnectionManager, db_manager: DatabaseManager):
        self.connection_manager = connection_manager
        self.db_manager = db_manager
        self.workflow_engine: None = None

    def handle_task_event(self, task_event: TaskEvent):
        self.connection_manager.queue_broadcast(task_event)

    def handle_progress_event(self, progress_event):
        self.connection_manager.queue_progress_broadcast(progress_event)

    def handle_steps_event(self, steps_event):
        data = steps_event.__dict__ if hasattr(steps_event, "__dict__") else steps_event
        self.connection_manager.queue_progress_broadcast({"type": "steps_event", "data": data})

    def handle_worker_event(self, worker_event: WorkerEvent):
        self.connection_manager.queue_worker_broadcast(worker_event)