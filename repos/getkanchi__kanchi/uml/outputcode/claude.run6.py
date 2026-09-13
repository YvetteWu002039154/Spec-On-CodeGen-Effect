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
# Simple named-tuple / dataclass stand-ins for event types referenced in
# signatures but not defined in the diagram.
# ---------------------------------------------------------------------------

class TaskEvent(NamedTuple):
    task_id: str
    task_name: str
    event_type: str
    hostname: str = ""
    timestamp: Optional[float] = None
    extra: Dict[str, Any] = {}


class WorkerEvent(NamedTuple):
    hostname: str
    event_type: str
    status: str = ""
    timestamp: Optional[float] = None
    extra: Dict[str, Any] = {}


class TaskProgressEvent(NamedTuple):
    task_id: str
    task_name: str
    progress: float = 0.0
    message: str = ""
    meta: Dict[str, Any] = {}
    step_key: str = ""
    timestamp: Optional[float] = None


class TaskStepsEvent(NamedTuple):
    task_id: str
    task_name: str
    steps: Dict[str, Any] = {}
    defined_at: Optional[float] = None


class ActionResult(NamedTuple):
    success: bool
    message: str = ""
    data: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Database models
# ---------------------------------------------------------------------------

class ActionConfigDB:
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
    ) -> None:
        self.id = id
        self.name = name
        self.action_type = action_type
        self.config: Dict[str, Any] = config if config is not None else {}
        self.description = description
        self.created_by = created_by
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.last_used_at = last_used_at
        self.usage_count = usage_count

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


class AppSettingDB:
    def __init__(
        self,
        key: str = "",
        value: str = "",
        value_type: str = "string",
        category: str = "",
        label: str = "",
        description: str = "",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.key = key
        self.value = value
        self.value_type = value_type
        self.category = category
        self.label = label
        self.description = description
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "value_type": self.value_type,
            "category": self.category,
            "label": self.label,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class EnvironmentDB:
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
    ) -> None:
        self.id = id
        self.name = name
        self.description = description
        self.is_active = is_active
        self.is_default = is_default
        self.queue_patterns: List[str] = queue_patterns if queue_patterns is not None else []
        self.worker_patterns: List[str] = worker_patterns if worker_patterns is not None else []
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

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


class RetryRelationshipDB:
    def __init__(
        self,
        id: Optional[int] = None,
        task_id: str = "",
        original_id: str = "",
        retry_chain: Optional[List[str]] = None,
        total_retries: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.task_id = task_id
        self.original_id = original_id
        self.retry_chain: List[str] = retry_chain if retry_chain is not None else []
        self.total_retries = total_retries
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()


class TaskActionDB:
    def __init__(
        self,
        id: Optional[int] = None,
        action_type: str = "",
        status: str = "",
        initiated_by: str = "",
        initiated_by_user_id: Optional[int] = None,
        initiated_session_id: Optional[str] = None,
        selection_size: int = 0,
        original_task_ids: Optional[List[str]] = None,
        items: Optional[List[Any]] = None,
        item_total: int = 0,
        item_changed: int = 0,
        item_created: int = 0,
        item_failed: int = 0,
        item_noop: int = 0,
        item_skipped: int = 0,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.action_type = action_type
        self.status = status
        self.initiated_by = initiated_by
        self.initiated_by_user_id = initiated_by_user_id
        self.initiated_session_id = initiated_session_id
        self.selection_size = selection_size
        self.original_task_ids: List[str] = original_task_ids if original_task_ids is not None else []
        self.items: List[Any] = items if items is not None else []
        self.item_total = item_total
        self.item_changed = item_changed
        self.item_created = item_created
        self.item_failed = item_failed
        self.item_noop = item_noop
        self.item_skipped = item_skipped
        self.started_at = started_at
        self.completed_at = completed_at
        self.created_at = created_at or datetime.utcnow()


class TaskActionItemDB:
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
        rerun_kind: str = "",
        rerun_task_id: Optional[str] = None,
        rerun_task_name: Optional[str] = None,
        review_fingerprint: Optional[str] = None,
        skip_category: Optional[str] = None,
        submitted_args: Optional[Any] = None,
        submitted_kwargs: Optional[Any] = None,
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
        self.outcome = outcome
        self.reason = reason
        self.reason_code = reason_code
        self.rerun_kind = rerun_kind
        self.rerun_task_id = rerun_task_id
        self.rerun_task_name = rerun_task_name
        self.review_fingerprint = review_fingerprint
        self.skip_category = skip_category
        self.submitted_args = submitted_args
        self.submitted_kwargs = submitted_kwargs
        self.target_queue = target_queue
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()


class TaskDailyStatsDB:
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
    ) -> None:
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
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_name": self.task_name,
            "date": self.date.isoformat() if self.date else None,
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


class TaskEventDB:
    def __init__(
        self,
        id: Optional[int] = None,
        task_id: str = "",
        task_name: str = "",
        event_type: str = "",
        hostname: str = "",
        worker_name: str = "",
        queue: str = "",
        exchange: str = "",
        routing_key: str = "",
        args: Optional[Any] = None,
        kwargs: Optional[Any] = None,
        result: Optional[Any] = None,
        exception: Optional[str] = None,
        traceback: Optional[str] = None,
        runtime: Optional[float] = None,
        retries: int = 0,
        retry_count: int = 0,
        retry_of: Optional[str] = None,
        retried_by: Optional[str] = None,
        has_retries: bool = False,
        is_retry: bool = False,
        is_orphan: bool = False,
        orphaned_at: Optional[datetime] = None,
        parent_id: Optional[str] = None,
        root_id: Optional[str] = None,
        eta: Optional[datetime] = None,
        expires: Optional[datetime] = None,
        timestamp: Optional[float] = None,
    ) -> None:
        self.id = id
        self.task_id = task_id
        self.task_name = task_name
        self.event_type = event_type
        self.hostname = hostname
        self.worker_name = worker_name
        self.queue = queue
        self.exchange = exchange
        self.routing_key = routing_key
        self.args = args
        self.kwargs = kwargs
        self.result = result
        self.exception = exception
        self.traceback = traceback
        self.runtime = runtime
        self.retries = retries
        self.retry_count = retry_count
        self.retry_of = retry_of
        self.retried_by = retried_by
        self.has_retries = has_retries
        self.is_retry = is_retry
        self.is_orphan = is_orphan
        self.orphaned_at = orphaned_at
        self.parent_id = parent_id
        self.root_id = root_id
        self.eta = eta
        self.expires = expires
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "event_type": self.event_type,
            "hostname": self.hostname,
            "worker_name": self.worker_name,
            "queue": self.queue,
            "exchange": self.exchange,
            "routing_key": self.routing_key,
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
            "eta": self.eta.isoformat() if self.eta else None,
            "expires": self.expires.isoformat() if self.expires else None,
            "timestamp": self.timestamp,
        }


class TaskLatestDB:
    def __init__(
        self,
        task_id: str = "",
        task_name: str = "",
        event_id: Optional[int] = None,
        event_type: str = "",
        hostname: str = "",
        worker_name: str = "",
        queue: str = "",
        exchange: str = "",
        routing_key: str = "",
        args: Optional[Any] = None,
        kwargs: Optional[Any] = None,
        result: Optional[Any] = None,
        exception: Optional[str] = None,
        traceback: Optional[str] = None,
        runtime: Optional[float] = None,
        retries: int = 0,
        retry_count: int = 0,
        retry_of: Optional[str] = None,
        retried_by: Optional[str] = None,
        has_retries: bool = False,
        is_retry: bool = False,
        is_orphan: bool = False,
        orphaned_at: Optional[datetime] = None,
        parent_id: Optional[str] = None,
        root_id: Optional[str] = None,
        eta: Optional[datetime] = None,
        expires: Optional[datetime] = None,
        timestamp: Optional[float] = None,
        resolved: bool = False,
        resolved_at: Optional[datetime] = None,
        resolved_by: Optional[str] = None,
    ) -> None:
        self.task_id = task_id
        self.task_name = task_name
        self.event_id = event_id
        self.event_type = event_type
        self.hostname = hostname
        self.worker_name = worker_name
        self.queue = queue
        self.exchange = exchange
        self.routing_key = routing_key
        self.args = args
        self.kwargs = kwargs
        self.result = result
        self.exception = exception
        self.traceback = traceback
        self.runtime = runtime
        self.retries = retries
        self.retry_count = retry_count
        self.retry_of = retry_of
        self.retried_by = retried_by
        self.has_retries = has_retries
        self.is_retry = is_retry
        self.is_orphan = is_orphan
        self.orphaned_at = orphaned_at
        self.parent_id = parent_id
        self.root_id = root_id
        self.eta = eta
        self.expires = expires
        self.timestamp = timestamp
        self.resolved = resolved
        self.resolved_at = resolved_at
        self.resolved_by = resolved_by


class TaskProgressDB:
    def __init__(
        self,
        id: Optional[int] = None,
        task_id: str = "",
        task_name: str = "",
        progress: float = 0.0,
        message: str = "",
        meta: Optional[Dict[str, Any]] = None,
        step_key: str = "",
        timestamp: Optional[float] = None,
    ) -> None:
        self.id = id
        self.task_id = task_id
        self.task_name = task_name
        self.progress = progress
        self.message = message
        self.meta: Dict[str, Any] = meta if meta is not None else {}
        self.step_key = step_key
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "progress": self.progress,
            "message": self.message,
            "meta": self.meta,
            "step_key": self.step_key,
            "timestamp": self.timestamp,
        }


class TaskProgressLatestDB:
    def __init__(
        self,
        task_id: str = "",
        task_name: str = "",
        progress: float = 0.0,
        message: str = "",
        meta: Optional[Dict[str, Any]] = None,
        step_key: str = "",
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.task_id = task_id
        self.task_name = task_name
        self.progress = progress
        self.message = message
        self.meta: Dict[str, Any] = meta if meta is not None else {}
        self.step_key = step_key
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "progress": self.progress,
            "message": self.message,
            "meta": self.meta,
            "step_key": self.step_key,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TaskRegistryDB:
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
    ) -> None:
        self.id = id
        self.name = name
        self.human_readable_name = human_readable_name
        self.description = description
        self.tags: List[str] = tags if tags is not None else []
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

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


class TaskRerunRelationshipDB:
    def __init__(
        self,
        id: Optional[int] = None,
        original_task_id: str = "",
        rerun_task_id: str = "",
        action_id: Optional[int] = None,
        created_by: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.original_task_id = original_task_id
        self.rerun_task_id = rerun_task_id
        self.action_id = action_id
        self.created_by = created_by
        self.created_at = created_at or datetime.utcnow()


class TaskResolutionDB:
    def __init__(
        self,
        task_id: str = "",
        resolved: bool = False,
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
        task_id: str = "",
        task_name: str = "",
        steps: Optional[Dict[str, Any]] = None,
        defined_at: Optional[float] = None,
    ) -> None:
        self.task_id = task_id
        self.task_name = task_name
        self.steps: Dict[str, Any] = steps if steps is not None else {}
        self.defined_at = defined_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "steps": self.steps,
            "defined_at": self.defined_at,
        }


class UserDB:
    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        email: str = "",
        provider: str = "",
        provider_account_id: str = "",
        avatar_url: Optional[str] = None,
        is_active: bool = True,
        last_login_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        sessions: Optional[List[Any]] = None,
    ) -> None:
        self.id = id
        self.name = name
        self.email = email
        self.provider = provider
        self.provider_account_id = provider_account_id
        self.avatar_url = avatar_url
        self.is_active = is_active
        self.last_login_at = last_login_at
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.sessions: List[Any] = sessions if sessions is not None else []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "provider": self.provider,
            "provider_account_id": self.provider_account_id,
            "avatar_url": self.avatar_url,
            "is_active": self.is_active,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserSessionDB:
    def __init__(
        self,
        session_id: str = "",
        user_id: Optional[int] = None,
        user: Optional[UserDB] = None,
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
    ) -> None:
        self.session_id = session_id
        self.user_id = user_id
        self.user = user
        self.auth_provider = auth_provider
        self.access_token_hash = access_token_hash
        self.access_token_expires_at = access_token_expires_at
        self.refresh_token_hash = refresh_token_hash
        self.refresh_token_expires_at = refresh_token_expires_at
        self.token_scopes: List[str] = token_scopes if token_scopes is not None else []
        self.active_environment_id = active_environment_id
        self.preferences: Dict[str, Any] = preferences if preferences is not None else {}
        self.last_active = last_active or datetime.utcnow()
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "auth_provider": self.auth_provider,
            "access_token_expires_at": self.access_token_expires_at.isoformat() if self.access_token_expires_at else None,
            "refresh_token_expires_at": self.refresh_token_expires_at.isoformat() if self.refresh_token_expires_at else None,
            "token_scopes": self.token_scopes,
            "active_environment_id": self.active_environment_id,
            "preferences": self.preferences,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WorkerEventDB:
    def __init__(
        self,
        id: Optional[int] = None,
        hostname: str = "",
        event_type: str = "",
        status: str = "",
        active_tasks: int = 0,
        processed: int = 0,
        timestamp: Optional[float] = None,
    ) -> None:
        self.id = id
        self.hostname = hostname
        self.event_type = event_type
        self.status = status
        self.active_tasks = active_tasks
        self.processed = processed
        self.timestamp = timestamp

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
        id: Optional[int] = None,
        name: str = "",
        description: str = "",
        enabled: bool = True,
        trigger_type: str = "",
        trigger_config: Optional[Dict[str, Any]] = None,
        conditions: Optional[List[Any]] = None,
        actions: Optional[List[Any]] = None,
        priority: int = 0,
        cooldown_seconds: int = 0,
        max_executions_per_hour: int = 0,
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
        self.description = description
        self.enabled = enabled
        self.trigger_type = trigger_type
        self.trigger_config: Dict[str, Any] = trigger_config if trigger_config is not None else {}
        self.conditions: List[Any] = conditions if conditions is not None else []
        self.actions: List[Any] = actions if actions is not None else []
        self.priority = priority
        self.cooldown_seconds = cooldown_seconds
        self.max_executions_per_hour = max_executions_per_hour
        self.circuit_breaker_config: Dict[str, Any] = circuit_breaker_config if circuit_breaker_config is not None else {}
        self.execution_count = execution_count
        self.success_count = success_count
        self.failure_count = failure_count
        self.last_executed_at = last_executed_at
        self.created_by = created_by
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

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


class WorkflowExecutionDB:
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
    ) -> None:
        self.id = id
        self.workflow_id = workflow_id
        self.workflow_snapshot: Dict[str, Any] = workflow_snapshot if workflow_snapshot is not None else {}
        self.trigger_type = trigger_type
        self.trigger_event: Dict[str, Any] = trigger_event if trigger_event is not None else {}
        self.status = status
        self.actions_executed: List[Any] = actions_executed if actions_executed is not None else []
        self.error_message = error_message
        self.stack_trace = stack_trace
        self.circuit_breaker_key = circuit_breaker_key
        self.triggered_at = triggered_at
        self.started_at = started_at
        self.completed_at = completed_at
        self.duration_ms = duration_ms

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
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
        }


# ---------------------------------------------------------------------------
# DatabaseManager
# ---------------------------------------------------------------------------

class Session:
    """Minimal stand-in for a SQLAlchemy Session."""

    def __init__(self) -> None:
        self._objects: List[Any] = []

    def add(self, obj: Any) -> None:
        self._objects.append(obj)

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass

    def close(self) -> None:
        pass

    def query(self, model: Any) -> "Session":
        return self

    def filter(self, *args: Any) -> "Session":
        return self

    def first(self) -> None:
        return None

    def all(self) -> List[Any]:
        return []


class DatabaseManager:
    def __init__(self, database_url: str = "sqlite:///:memory:") -> None:
        self.database_url: str = database_url
        self.engine = None
        self.SessionLocal = None
        self._initialize()

    def _initialize(self) -> None:
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker as sa_sessionmaker

            self.engine = create_engine(self.database_url)
            self.SessionLocal = sa_sessionmaker(
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
    def __init__(self, broker_url: str = "redis://localhost:6379/0") -> None:
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

            self.app = Celery(broker=self.broker_url)
            self.state = self.app.events.State()

            with self.app.connection() as connection:
                recv = self.app.events.Receiver(
                    connection,
                    handlers={
                        "task-*": self._on_task_event,
                        "worker-*": self._on_worker_event,
                        "*": self._on_any_event,
                    },
                )
                recv.capture(limit=None, timeout=None, wakeup=True)
        except Exception:
            self._running = False

    def _on_task_event(self, event: Dict[str, Any]) -> None:
        if self.state is not None:
            self.state.event(event)
        task_event = TaskEvent(
            task_id=event.get("uuid", ""),
            task_name=event.get("name", ""),
            event_type=event.get("type", ""),
            hostname=event.get("hostname", ""),
            timestamp=event.get("timestamp"),
        )
        if self.task_callback is not None:
            self.task_callback(task_event)

    def _on_worker_event(self, event: Dict[str, Any]) -> None:
        hostname = event.get("hostname", "")
        self.workers[hostname] = event
        worker_event = WorkerEvent(
            hostname=hostname,
            event_type=event.get("type", ""),
            status=event.get("status", ""),
            timestamp=event.get("timestamp"),
        )
        if self.worker_callback is not None:
            self.worker_callback(worker_event)

    def _on_any_event(self, event: Dict[str, Any]) -> None:
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

class WebSocket:
    """Minimal stand-in for a WebSocket connection."""

    def __init__(self, client_id: str = "") -> None:
        self.client_id = client_id

    async def send_text(self, data: str) -> None:
        pass

    async def accept(self) -> None:
        pass

    async def close(self) -> None:
        pass


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self.client_filters: Dict[WebSocket, dict] = {}
        self.client_modes: Dict[WebSocket, str] = {}
        self.message_queue: Optional[asyncio.Queue] = None
        self._broadcaster_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
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
        await websocket.send_text(message)

    def queue_broadcast(self, task_event: TaskEvent) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "task", "data": task_event._asdict()})
            except asyncio.QueueFull:
                pass

    def queue_worker_broadcast(self, worker_event: WorkerEvent) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "worker", "data": worker_event._asdict()})
            except asyncio.QueueFull:
                pass

    def queue_progress_broadcast(self, progress_event: Any) -> None:
        if self.message_queue is not None:
            try:
                data = progress_event._asdict() if hasattr(progress_event, "_asdict") else progress_event
                self.message_queue.put_nowait({"type": "progress", "data": data})
            except asyncio.QueueFull:
                pass

    def queue_task_action_broadcast(self, action_event: Any) -> None:
        if self.message_queue is not None:
            try:
                data = action_event._asdict() if hasattr(action_event, "_asdict") else action_event
                self.message_queue.put_nowait({"type": "task_action", "data": data})
            except asyncio.QueueFull:
                pass

    async def _broadcast_worker(self) -> None:
        while True:
            if self.message_queue is None:
                break
            try:
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            payload = json.dumps(message)
            dead: List[WebSocket] = []
            for ws in list(self.active_connections):
                try:
                    await ws.send_text(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws)

    def start_background_broadcaster(self) -> None:
        self.message_queue = asyncio.Queue(maxsize=1000)
        loop = asyncio.get_event_loop()
        self._broadcaster_task = loop.create_task(self._broadcast_worker())

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
    ) -> None:
        self.connection_manager = connection_manager
        self.db_manager = db_manager
        self.workflow_engine = None

    def handle_task_event(self, task_event: TaskEvent) -> None:
        session = self.db_manager.get_session()
        try:
            event_db = TaskEventDB(
                task_id=task_event.task_id,
                task_name=task_event.task_name,
                event_type=task_event.event_type,
                hostname=task_event.hostname,
                timestamp=task_event.timestamp,
            )
            session.add(event_db)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

        self.connection_manager.queue_broadcast(task_event)

        if self.workflow_engine is not None:
            try:
                self.workflow_engine.process_event(task_event)
            except Exception:
                pass

    def handle_worker_event(self, worker_event: WorkerEvent) -> None:
        session = self.db_manager.get_session()
        try:
            event_db = WorkerEventDB(
                hostname=worker_event.hostname,
                event_type=worker_event.event_type,
                status=worker_event.status,
                timestamp=worker_event.timestamp,
            )
            session.add(event_db)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

        self.connection_manager.queue_worker_broadcast(worker_event)

    def handle_progress_event(self, progress_event: Any) -> None:
        session = self.db_manager.get_session()
        try:
            if isinstance(progress_event, TaskProgressEvent):
                progress_db = TaskProgressDB(
                    task_id=progress_event.task_id,
                    task_name=progress_event.task_name,
                    progress=progress_event.progress,
                    message=progress_event.message,
                    meta=dict(progress_event.meta),
                    step_key=progress_event.step_key,
                    timestamp=progress_event.timestamp,
                )
                session.add(progress_db)
                session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

        self.connection_manager.queue_progress_broadcast(progress_event)

    def handle_steps_event(self, steps_event: Any) -> None:
        session = self.db_manager.get_session()
        try:
            if isinstance(steps_event, TaskStepsEvent):
                steps_db = TaskStepsDB(
                    task_id=steps_event.task_id,
                    task_name=steps_event.task_name,
                    steps=dict(steps_event.steps),
                    defined_at=steps_event.defined_at,
                )
                session.add(steps_db)
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
        session: Optional[Any] = None,
    ) -> None:
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
        valid, msg = self.validate_params(params)
        if not valid:
            return ActionResult(success=False, message=msg)

        task_ids: List[str] = []
        if "task_ids" in params:
            task_ids = list(params["task_ids"])
        elif "task_id" in params:
            task_ids = [params["task_id"]]

        if not task_ids:
            return ActionResult(success=False, message="No task IDs provided.")

        retried: List[str] = []
        failed: List[str] = []

        for task_id in task_ids:
            try:
                if self.monitor_instance is not None:
                    app = getattr(self.monitor_instance, "app", None)
                    if app is not None:
                        app.control.retry(task_id)
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
        if "message" not in params and "template" not in params:
            return False, "Either 'message' or 'template' must be provided."
        return True, ""

    def execute(
        self, context: Dict[str, Any], params: Dict[str, Any]
    ) -> ActionResult:
        valid, msg = self.validate_params(params)
        if not valid:
            return ActionResult(success=False, message=msg)

        if "template" in params:
            message_text = self.render_template(params["template"], context)
        else:
            message_text = str(params.get("message", ""))

        webhook_url: Optional[str] = params.get("webhook_url")
        channel: Optional[str] = params.get("channel")

        payload: Dict[str, Any] = {"text": message_text}
        if channel:
            payload["channel"] = channel

        try:
            import urllib.request

            if webhook_url:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    webhook_url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    status_code = resp.getcode()
                    if status_code != 200:
                        return ActionResult(
                            success=False,
                            message=f"Slack webhook returned status {status_code}.",
                        )
            return ActionResult(
                success=True,
                message="Slack message sent successfully.",
                data={"payload": payload},
            )
        except Exception as exc:
            return ActionResult(
                success=False,
                message=f"Failed to send Slack message: {exc}",
            )