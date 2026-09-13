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
        json.dumps(value, default=str)
        return value
    except Exception:
        return str(value)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class WebSocket:
    async def send_text(self, message: str) -> None:
        raise NotImplementedError


class Engine:
    pass


class MockConnection:
    pass


class Session:
    def __init__(self) -> None:
        self._closed = False

    def close(self) -> None:
        self._closed = True


class sessionmaker:
    def __init__(self, bind: Optional[Union[Engine, MockConnection]] = None) -> None:
        self.bind = bind

    def __call__(self) -> Session:
        return Session()


@dataclass(frozen=True)
class TaskEvent:
    task_id: str
    task_name: Optional[str] = None
    event_type: Optional[str] = None
    timestamp: Optional[datetime] = None
    payload: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class TaskProgressEvent:
    task_id: str
    task_name: Optional[str] = None
    progress: Optional[float] = None
    message: Optional[str] = None
    step_key: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None


@dataclass(frozen=True)
class TaskStepsEvent:
    task_id: str
    task_name: Optional[str] = None
    steps: Optional[List[Dict[str, Any]]] = None
    defined_at: Optional[datetime] = None


@dataclass(frozen=True)
class WorkerEvent:
    hostname: str
    event_type: Optional[str] = None
    status: Optional[str] = None
    active_tasks: Optional[int] = None
    processed: Optional[int] = None
    timestamp: Optional[datetime] = None


@dataclass(frozen=True)
class ActionResult:
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None


class ActionConfigDB:
    def __init__(
        self,
        *,
        id: Optional[int] = None,
        name: str,
        action_type: str,
        config: Dict[str, Any],
        description: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
        last_used_at: Optional[datetime] = None,
        usage_count: int = 0,
    ) -> None:
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
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
            "last_used_at": self.last_used_at,
            "usage_count": self.usage_count,
        }


class AppSettingDB:
    def __init__(
        self,
        *,
        key: str,
        value: Any,
        value_type: str,
        category: Optional[str] = None,
        label: Optional[str] = None,
        description: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
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
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class EnvironmentDB:
    def __init__(
        self,
        *,
        id: Optional[int] = None,
        name: str,
        description: Optional[str] = None,
        is_active: bool = True,
        is_default: bool = False,
        queue_patterns: Optional[List[str]] = None,
        worker_patterns: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.name = name
        self.description = description
        self.is_active = is_active
        self.is_default = is_default
        self.queue_patterns = queue_patterns or []
        self.worker_patterns = worker_patterns or []
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "queue_patterns": list(self.queue_patterns),
            "worker_patterns": list(self.worker_patterns),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class RetryRelationshipDB:
    def __init__(
        self,
        *,
        id: Optional[int] = None,
        task_id: str,
        original_id: str,
        retry_chain: List[str],
        total_retries: int,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
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
        *,
        id: Optional[int] = None,
        action_type: str,
        status: str,
        summary: Optional[str] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        selection_size: Optional[int] = None,
        original_task_ids: Optional[List[str]] = None,
        initiated_by: Optional[str] = None,
        initiated_by_user_id: Optional[int] = None,
        initiated_session_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        item_total: int = 0,
        item_created: int = 0,
        item_changed: int = 0,
        item_failed: int = 0,
        item_skipped: int = 0,
        item_noop: int = 0,
    ) -> None:
        self.id = id
        self.action_type = action_type
        self.status = status
        self.summary = summary
        self.items = items or []
        self.selection_size = selection_size
        self.original_task_ids = original_task_ids or []
        self.initiated_by = initiated_by
        self.initiated_by_user_id = initiated_by_user_id
        self.initiated_session_id = initiated_session_id
        self.created_at = created_at or _utcnow()
        self.started_at = started_at
        self.completed_at = completed_at
        self.item_total = item_total
        self.item_created = item_created
        self.item_changed = item_changed
        self.item_failed = item_failed
        self.item_skipped = item_skipped
        self.item_noop = item_noop


class TaskActionItemDB:
    def __init__(
        self,
        *,
        id: Optional[int] = None,
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
        review_fingerprint: Optional[str] = None,
        skip_category: Optional[str] = None,
        submitted_args: Optional[List[Any]] = None,
        submitted_kwargs: Optional[Dict[str, Any]] = None,
        target_queue: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
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
        self.review_fingerprint = review_fingerprint
        self.skip_category = skip_category
        self.submitted_args = submitted_args or []
        self.submitted_kwargs = submitted_kwargs or {}
        self.target_queue = target_queue
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at


class TaskDailyStatsDB:
    def __init__(
        self,
        *,
        id: Optional[int] = None,
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
    ) -> None:
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
            "date": self.date,
            "task_name": self.task_name,
            "total_executions": self.total_executions,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "retried": self.retried,
            "revoked": self.revoked,
            "pending": self.pending,
            "orphaned": self.orphaned,
            "first_execution": self.first_execution,
            "last_execution": self.last_execution,
            "min_runtime": self.min_runtime,
            "max_runtime": self.max_runtime,
            "avg_runtime": self.avg_runtime,
            "p50_runtime": self.p50_runtime,
            "p95_runtime": self.p95_runtime,
            "p99_runtime": self.p99_runtime,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TaskEventDB:
    def __init__(
        self,
        *,
        id: Optional[int] = None,
        task_id: str,
        task_name: Optional[str] = None,
        event_type: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        eta: Optional[datetime] = None,
        expires: Optional[datetime] = None,
        exchange: Optional[str] = None,
        routing_key: Optional[str] = None,
        queue: Optional[str] = None,
        hostname: Optional[str] = None,
        worker_name: Optional[str] = None,
        result: Any = None,
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
        is_orphan: bool = False,
        orphaned_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.task_id = task_id
        self.task_name = task_name
        self.event_type = event_type
        self.timestamp = timestamp or _utcnow()
        self.args = args or []
        self.kwargs = kwargs or {}
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
            "timestamp": self.timestamp,
            "args": _jsonable(self.args),
            "kwargs": _jsonable(self.kwargs),
            "eta": self.eta,
            "expires": self.expires,
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
            "orphaned_at": self.orphaned_at,
        }


class TaskLatestDB:
    def __init__(
        self,
        *,
        task_id: str,
        event_id: Optional[int] = None,
        task_name: Optional[str] = None,
        event_type: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        eta: Optional[datetime] = None,
        expires: Optional[datetime] = None,
        exchange: Optional[str] = None,
        routing_key: Optional[str] = None,
        queue: Optional[str] = None,
        hostname: Optional[str] = None,
        worker_name: Optional[str] = None,
        result: Any = None,
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
        is_orphan: bool = False,
        orphaned_at: Optional[datetime] = None,
        resolved: bool = False,
        resolved_at: Optional[datetime] = None,
        resolved_by: Optional[str] = None,
    ) -> None:
        self.task_id = task_id
        self.event_id = event_id
        self.task_name = task_name
        self.event_type = event_type
        self.timestamp = timestamp
        self.args = args or []
        self.kwargs = kwargs or {}
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
        *,
        id: Optional[int] = None,
        task_id: str,
        task_name: Optional[str] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        step_key: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.task_id = task_id
        self.task_name = task_name
        self.progress = progress
        self.message = message
        self.step_key = step_key
        self.meta = meta or {}
        self.timestamp = timestamp or _utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "progress": self.progress,
            "message": self.message,
            "step_key": self.step_key,
            "meta": _jsonable(self.meta),
            "timestamp": self.timestamp,
        }


class TaskProgressLatestDB:
    def __init__(
        self,
        *,
        task_id: str,
        task_name: Optional[str] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        step_key: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.task_id = task_id
        self.task_name = task_name
        self.progress = progress
        self.message = message
        self.step_key = step_key
        self.meta = meta or {}
        self.updated_at = updated_at or _utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "progress": self.progress,
            "message": self.message,
            "step_key": self.step_key,
            "meta": _jsonable(self.meta),
            "updated_at": self.updated_at,
        }


class TaskRegistryDB:
    def __init__(
        self,
        *,
        id: Optional[int] = None,
        name: str,
        human_readable_name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        first_seen: Optional[datetime] = None,
        last_seen: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
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
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TaskRerunRelationshipDB:
    def __init__(
        self,
        *,
        id: Optional[int] = None,
        action_id: int,
        original_task_id: str,
        rerun_task_id: str,
        created_by: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.action_id = action_id
        self.original_task_id = original_task_id
        self.rerun_task_id = rerun_task_id
        self.created_by = created_by
        self.created_at = created_at or _utcnow()


class TaskResolutionDB:
    def __init__(
        self,
        *,
        task_id: str,
        resolved: bool,
        resolved_at: Optional[datetime] = None,
        resolved_by: Optional[str] = None,
    ) -> None:
        self.task_id = task_id
        self.resolved = resolved
        self.resolved_at = resolved_at
        self.resolved_by = resolved_by


class TaskStepsDB:
    def __init__(
        self,
        *,
        task_id: str,
        task_name: Optional[str] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        defined_at: Optional[datetime] = None,
    ) -> None:
        self.task_id = task_id
        self.task_name = task_name
        self.steps = steps or []
        self.defined_at = defined_at or _utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "steps": _jsonable(self.steps),
            "defined_at": self.defined_at,
        }


class UserDB:
    def __init__(
        self,
        *,
        id: Optional[int] = None,
        email: str,
        name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        provider: Optional[str] = None,
        provider_account_id: Optional[str] = None,
        is_active: bool = True,
        last_login_at: Optional[datetime] = None,
        sessions: Optional[List[UserSessionDB]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.email = email
        self.name = name
        self.avatar_url = avatar_url
        self.provider = provider
        self.provider_account_id = provider_account_id
        self.is_active = is_active
        self.last_login_at = last_login_at
        self.sessions = sessions or []
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "provider": self.provider,
            "provider_account_id": self.provider_account_id,
            "is_active": self.is_active,
            "last_login_at": self.last_login_at,
            "sessions": [s.to_dict() for s in self.sessions],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class UserSessionDB:
    def __init__(
        self,
        *,
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
    ) -> None:
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

    def set_access_token(self, token: str, expires_at: Optional[datetime] = None) -> None:
        self.access_token_hash = _hash_token(token)
        self.access_token_expires_at = expires_at

    def set_refresh_token(self, token: str, expires_at: Optional[datetime] = None) -> None:
        self.refresh_token_hash = _hash_token(token)
        self.refresh_token_expires_at = expires_at

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
            "access_token_expires_at": self.access_token_expires_at,
            "refresh_token_expires_at": self.refresh_token_expires_at,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "user": self.user.to_dict() if self.user else None,
        }


class WorkerEventDB:
    def __init__(
        self,
        *,
        id: Optional[int] = None,
        hostname: str,
        event_type: Optional[str] = None,
        status: Optional[str] = None,
        active_tasks: Optional[int] = None,
        processed: Optional[int] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.hostname = hostname
        self.event_type = event_type
        self.status = status
        self.active_tasks = active_tasks
        self.processed = processed
        self.timestamp = timestamp or _utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "hostname": self.hostname,
            "event_type": self.event_type,
            "status": self.status,
            "active_tasks": self.active_tasks,
            "processed": self.processed,
            "timestamp": self.timestamp,
        }


class WorkflowDB:
    def __init__(
        self,
        *,
        id: Optional[int] = None,
        name: str,
        trigger_type: str,
        trigger_config: Dict[str, Any],
        actions: List[Dict[str, Any]],
        conditions: Optional[List[Dict[str, Any]]] = None,
        description: Optional[str] = None,
        enabled: bool = True,
        priority: int = 0,
        cooldown_seconds: Optional[int] = None,
        max_executions_per_hour: Optional[int] = None,
        circuit_breaker_config: Optional[Dict[str, Any]] = None,
        execution_count: int = 0,
        success_count: int = 0,
        failure_count: int = 0,
        last_executed_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.name = name
        self.trigger_type = trigger_type
        self.trigger_config = trigger_config
        self.actions = actions
        self.conditions = conditions or []
        self.description = description
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
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "trigger_type": self.trigger_type,
            "trigger_config": _jsonable(self.trigger_config),
            "actions": _jsonable(self.actions),
            "conditions": _jsonable(self.conditions),
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.priority,
            "cooldown_seconds": self.cooldown_seconds,
            "max_executions_per_hour": self.max_executions_per_hour,
            "circuit_breaker_config": _jsonable(self.circuit_breaker_config),
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_executed_at": self.last_executed_at,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class WorkflowExecutionDB:
    def __init__(
        self,
        *,
        id: Optional[int] = None,
        workflow_id: int,
        trigger_type: str,
        trigger_event: Dict[str, Any],
        workflow_snapshot: Dict[str, Any],
        status: str,
        triggered_at: Optional[datetime] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        actions_executed: Optional[List[Dict[str, Any]]] = None,
        error_message: Optional[str] = None,
        stack_trace: Optional[str] = None,
        circuit_breaker_key: Optional[str] = None,
    ) -> None:
        self.id = id
        self.workflow_id = workflow_id
        self.trigger_type = trigger_type
        self.trigger_event = trigger_event
        self.workflow_snapshot = workflow_snapshot
        self.status = status
        self.triggered_at = triggered_at or _utcnow()
        self.started_at = started_at
        self.completed_at = completed_at
        self.duration_ms = duration_ms
        self.actions_executed = actions_executed or []
        self.error_message = error_message
        self.stack_trace = stack_trace
        self.circuit_breaker_key = circuit_breaker_key

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "trigger_type": self.trigger_type,
            "trigger_event": _jsonable(self.trigger_event),
            "workflow_snapshot": _jsonable(self.workflow_snapshot),
            "status": self.status,
            "triggered_at": self.triggered_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
            "actions_executed": _jsonable(self.actions_executed),
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "circuit_breaker_key": self.circuit_breaker_key,
        }


class DatabaseManager:
    def __init__(self, database_url: str) -> None:
        self.database_url: str = database_url
        self.engine: Optional[Union[Engine, MockConnection]] = None
        self.SessionLocal: sessionmaker = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def run_migrations(self) -> None:
        return


class CeleryEventMonitor:
    def __init__(
        self,
        *,
        broker_url: str,
        app: Any = None,
    ) -> None:
        self.app = app
        self.broker_url: str = broker_url
        self.state: NoneType = None
        self.workers: Dict[str, Dict[str, Any]] = {}
        self.progress_callback: Optional[Callable[[TaskProgressEvent], None]] = None
        self.steps_callback: Optional[Callable[[TaskStepsEvent], None]] = None
        self.task_callback: Optional[Callable[[TaskEvent], None]] = None
        self.worker_callback: Optional[Callable[[WorkerEvent], None]] = None
        self._running: bool = False

    def set_progress_callback(self, callback: Callable[[TaskProgressEvent], None]) -> None:
        self.progress_callback = callback

    def set_steps_callback(self, callback: Callable[[TaskStepsEvent], None]) -> None:
        self.steps_callback = callback

    def set_task_callback(self, callback: Callable[[TaskEvent], None]) -> None:
        self.task_callback = callback

    def set_worker_callback(self, callback: Callable[[WorkerEvent], None]) -> None:
        self.worker_callback = callback

    def get_workers_info(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.workers)

    def start_monitoring(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self.client_filters: Dict[WebSocket, dict] = {}
        self.client_modes: Dict[WebSocket, str] = {}
        self.message_queue: Optional[asyncio.Queue] = None
        self._broadcaster_task: Optional[asyncio.Task] = None
        self._stop_event: Optional[asyncio.Event] = None

    async def connect(self, websocket: WebSocket) -> None:
        if websocket not in self.active_connections:
            self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.client_filters.pop(websocket, None)
        self.client_modes.pop(websocket, None)

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        await websocket.send_text(message)

    def set_client_filters(self, websocket: WebSocket, filters: dict) -> None:
        self.client_filters[websocket] = filters

    def set_client_mode(self, websocket: WebSocket, mode: str) -> None:
        self.client_modes[websocket] = mode

    def start_background_broadcaster(self) -> None:
        if self.message_queue is None:
            self.message_queue = asyncio.Queue()
        if self._stop_event is None:
            self._stop_event = asyncio.Event()
        if self._broadcaster_task is None or self._broadcaster_task.done():
            self._broadcaster_task = asyncio.create_task(self._broadcaster_loop())

    async def _broadcaster_loop(self) -> None:
        assert self.message_queue is not None
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            try:
                payload = await asyncio.wait_for(self.message_queue.get(), timeout=0.25)
            except asyncio.TimeoutError:
                continue
            message = json.dumps(payload, default=str)
            for ws in list(self.active_connections):
                try:
                    await ws.send_text(message)
                except Exception:
                    self.disconnect(ws)

    def stop_background_broadcaster(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        self._stop_event = None
        self._broadcaster_task = None

    def _queue(self, payload: Dict[str, Any]) -> None:
        if self.message_queue is None:
            self.message_queue = asyncio.Queue()
        try:
            self.message_queue.put_nowait(payload)
        except Exception:
            pass

    def queue_broadcast(self, task_event: TaskEvent) -> None:
        self._queue(
            {
                "type": "task_event",
                "task_id": task_event.task_id,
                "task_name": task_event.task_name,
                "event_type": task_event.event_type,
                "timestamp": task_event.timestamp,
                "payload": _jsonable(task_event.payload),
            }
        )

    def queue_progress_broadcast(self, progress_event: Any) -> None:
        if isinstance(progress_event, TaskProgressEvent):
            payload = {
                "type": "progress_event",
                "task_id": progress_event.task_id,
                "task_name": progress_event.task_name,
                "progress": progress_event.progress,
                "message": progress_event.message,
                "step_key": progress_event.step_key,
                "meta": _jsonable(progress_event.meta),
                "timestamp": progress_event.timestamp,
            }
        else:
            payload = {"type": "progress_event", "data": _jsonable(progress_event)}
        self._queue(payload)

    def queue_task_action_broadcast(self, action_event: Any) -> None:
        self._queue({"type": "task_action_event", "data": _jsonable(action_event)})

    def queue_worker_broadcast(self, worker_event: WorkerEvent) -> None:
        self._queue(
            {
                "type": "worker_event",
                "hostname": worker_event.hostname,
                "event_type": worker_event.event_type,
                "status": worker_event.status,
                "active_tasks": worker_event.active_tasks,
                "processed": worker_event.processed,
                "timestamp": worker_event.timestamp,
            }
        )


class EventHandler:
    def __init__(self, *, connection_manager: ConnectionManager, db_manager: DatabaseManager) -> None:
        self.connection_manager = connection_manager
        self.db_manager = db_manager
        self.workflow_engine: NoneType = None

    def handle_task_event(self, task_event: TaskEvent) -> None:
        self.connection_manager.queue_broadcast(task_event)

    def handle_progress_event(self, progress_event: Any) -> None:
        self.connection_manager.queue_progress_broadcast(progress_event)

    def handle_steps_event(self, steps_event: Any) -> None:
        self.connection_manager.queue_task_action_broadcast({"type": "steps_event", "data": _jsonable(steps_event)})

    def handle_worker_event(self, worker_event: WorkerEvent) -> None:
        self.connection_manager.queue_worker_broadcast(worker_event)


class ActionHandler(ABC):
    def __init__(self, *, db_manager: DatabaseManager, session: Optional[Session] = None) -> None:
        self.db_manager = db_manager
        self.session = session or db_manager.get_session()
        self.monitor_instance: NoneType = None

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        raise NotImplementedError

    @abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        raise NotImplementedError

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        try:
            return template.format(**context)
        except Exception:
            return template


class RetryActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(params, dict):
            return False, "params must be a dict"
        if "task_id" not in params:
            return False, "missing required param: task_id"
        if not isinstance(params["task_id"], str) or not params["task_id"].strip():
            return False, "task_id must be a non-empty string"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        ok, msg = self.validate_params(params)
        if not ok:
            return ActionResult(success=False, message=msg, data=None)
        task_id = params["task_id"]
        return ActionResult(success=True, message="retry requested", data={"task_id": task_id})


class SlackActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(params, dict):
            return False, "params must be a dict"
        if "message" not in params:
            return False, "missing required param: message"
        if not isinstance(params["message"], str) or not params["message"].strip():
            return False, "message must be a non-empty string"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        ok, msg = self.validate_params(params)
        if not ok:
            return ActionResult(success=False, message=msg, data=None)
        message_template = params["message"]
        rendered = self.render_template(message_template, context)
        return ActionResult(success=True, message="slack message prepared", data={"message": rendered})


NoneType = type(None)