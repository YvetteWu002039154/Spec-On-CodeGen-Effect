from __future__ import annotations

import asyncio
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


def _as_dict(obj: Any, fields: List[str]) -> Dict[str, Any]:
    return {k: _jsonable(getattr(obj, k)) for k in fields}


@dataclass(frozen=True)
class ActionResult:
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None


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
        self._bind = bind

    def __call__(self) -> Session:
        return Session()


class DatabaseManager:
    def __init__(self, database_url: str) -> None:
        self.database_url: str = database_url
        self.engine: Optional[Union[Engine, MockConnection]] = None
        self.SessionLocal: sessionmaker = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def run_migrations(self) -> None:
        return None


class ActionConfigDB:
    def __init__(
        self,
        id: Optional[int] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        action_type: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        created_by: Optional[str] = None,
        last_used_at: Optional[datetime] = None,
        usage_count: int = 0,
    ) -> None:
        self.id = id
        self.name = name
        self.description = description
        self.action_type = action_type
        self.config = config if config is not None else {}
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at
        self.created_by = created_by
        self.last_used_at = last_used_at
        self.usage_count = usage_count

    def to_dict(self) -> Dict[str, Any]:
        return _as_dict(
            self,
            [
                "id",
                "name",
                "description",
                "action_type",
                "config",
                "created_at",
                "updated_at",
                "created_by",
                "last_used_at",
                "usage_count",
            ],
        )


class AppSettingDB:
    def __init__(
        self,
        key: str,
        value: Any,
        value_type: str,
        label: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.key = key
        self.value = value
        self.value_type = value_type
        self.label = label
        self.description = description
        self.category = category
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return _as_dict(
            self,
            [
                "key",
                "value",
                "value_type",
                "label",
                "description",
                "category",
                "created_at",
                "updated_at",
            ],
        )


class EnvironmentDB:
    def __init__(
        self,
        id: Optional[int] = None,
        name: Optional[str] = None,
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
        self.queue_patterns = queue_patterns if queue_patterns is not None else []
        self.worker_patterns = worker_patterns if worker_patterns is not None else []
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return _as_dict(
            self,
            [
                "id",
                "name",
                "description",
                "is_active",
                "is_default",
                "queue_patterns",
                "worker_patterns",
                "created_at",
                "updated_at",
            ],
        )


class RetryRelationshipDB:
    def __init__(
        self,
        id: Optional[int] = None,
        task_id: Optional[str] = None,
        original_id: Optional[str] = None,
        retry_chain: Optional[List[str]] = None,
        total_retries: int = 0,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.task_id = task_id
        self.original_id = original_id
        self.retry_chain = retry_chain if retry_chain is not None else []
        self.total_retries = total_retries
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at


class TaskActionDB:
    def __init__(
        self,
        id: Optional[int] = None,
        action_type: Optional[str] = None,
        status: Optional[str] = None,
        summary: Optional[str] = None,
        initiated_by: Optional[str] = None,
        initiated_by_user_id: Optional[int] = None,
        initiated_session_id: Optional[str] = None,
        selection_size: Optional[int] = None,
        original_task_ids: Optional[List[str]] = None,
        items: Optional[List["TaskActionItemDB"]] = None,
        item_total: int = 0,
        item_created: int = 0,
        item_changed: int = 0,
        item_failed: int = 0,
        item_skipped: int = 0,
        item_noop: int = 0,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
    ) -> None:
        self.id = id
        self.action_type = action_type
        self.status = status
        self.summary = summary
        self.initiated_by = initiated_by
        self.initiated_by_user_id = initiated_by_user_id
        self.initiated_session_id = initiated_session_id
        self.selection_size = selection_size
        self.original_task_ids = original_task_ids if original_task_ids is not None else []
        self.items = items if items is not None else []
        self.item_total = item_total
        self.item_created = item_created
        self.item_changed = item_changed
        self.item_failed = item_failed
        self.item_skipped = item_skipped
        self.item_noop = item_noop
        self.started_at = started_at
        self.completed_at = completed_at
        self.created_at = created_at or _utcnow()


class TaskActionItemDB:
    def __init__(
        self,
        id: Optional[int] = None,
        action_id: Optional[int] = None,
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
        target_queue: Optional[str] = None,
        submitted_args: Optional[Any] = None,
        submitted_kwargs: Optional[Any] = None,
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
        self.skip_category = skip_category
        self.review_fingerprint = review_fingerprint
        self.target_queue = target_queue
        self.submitted_args = submitted_args
        self.submitted_kwargs = submitted_kwargs
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at


class TaskDailyStatsDB:
    def __init__(
        self,
        id: Optional[int] = None,
        date: Optional[date] = None,
        task_name: Optional[str] = None,
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
        self.date = date or datetime.now(timezone.utc).date()
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
        return _as_dict(
            self,
            [
                "id",
                "date",
                "task_name",
                "total_executions",
                "succeeded",
                "failed",
                "retried",
                "revoked",
                "pending",
                "orphaned",
                "first_execution",
                "last_execution",
                "min_runtime",
                "max_runtime",
                "avg_runtime",
                "p50_runtime",
                "p95_runtime",
                "p99_runtime",
                "created_at",
                "updated_at",
            ],
        )


class TaskEventDB:
    def __init__(
        self,
        id: Optional[int] = None,
        task_id: Optional[str] = None,
        task_name: Optional[str] = None,
        event_type: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        hostname: Optional[str] = None,
        worker_name: Optional[str] = None,
        queue: Optional[str] = None,
        exchange: Optional[str] = None,
        routing_key: Optional[str] = None,
        args: Optional[Any] = None,
        kwargs: Optional[Any] = None,
        eta: Optional[datetime] = None,
        expires: Optional[datetime] = None,
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
    ) -> None:
        self.id = id
        self.task_id = task_id
        self.task_name = task_name
        self.event_type = event_type
        self.timestamp = timestamp or _utcnow()
        self.hostname = hostname
        self.worker_name = worker_name
        self.queue = queue
        self.exchange = exchange
        self.routing_key = routing_key
        self.args = args
        self.kwargs = kwargs
        self.eta = eta
        self.expires = expires
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
        return _as_dict(
            self,
            [
                "id",
                "task_id",
                "task_name",
                "event_type",
                "timestamp",
                "hostname",
                "worker_name",
                "queue",
                "exchange",
                "routing_key",
                "args",
                "kwargs",
                "eta",
                "expires",
                "result",
                "exception",
                "traceback",
                "runtime",
                "retries",
                "retry_count",
                "has_retries",
                "is_retry",
                "retry_of",
                "retried_by",
                "parent_id",
                "root_id",
                "is_orphan",
                "orphaned_at",
            ],
        )


class TaskLatestDB:
    def __init__(
        self,
        task_id: str,
        task_name: Optional[str] = None,
        event_id: Optional[int] = None,
        event_type: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        hostname: Optional[str] = None,
        worker_name: Optional[str] = None,
        queue: Optional[str] = None,
        exchange: Optional[str] = None,
        routing_key: Optional[str] = None,
        args: Optional[Any] = None,
        kwargs: Optional[Any] = None,
        eta: Optional[datetime] = None,
        expires: Optional[datetime] = None,
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
    ) -> None:
        self.task_id = task_id
        self.task_name = task_name
        self.event_id = event_id
        self.event_type = event_type
        self.timestamp = timestamp
        self.hostname = hostname
        self.worker_name = worker_name
        self.queue = queue
        self.exchange = exchange
        self.routing_key = routing_key
        self.args = args
        self.kwargs = kwargs
        self.eta = eta
        self.expires = expires
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
        id: Optional[int] = None,
        task_id: Optional[str] = None,
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
        self.meta = meta if meta is not None else {}
        self.timestamp = timestamp or _utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return _as_dict(
            self,
            ["id", "task_id", "task_name", "progress", "message", "step_key", "meta", "timestamp"],
        )


class TaskProgressLatestDB:
    def __init__(
        self,
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
        self.meta = meta if meta is not None else {}
        self.updated_at = updated_at or _utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return _as_dict(
            self,
            ["task_id", "task_name", "progress", "message", "step_key", "meta", "updated_at"],
        )


class TaskRegistryDB:
    def __init__(
        self,
        id: Optional[int] = None,
        name: Optional[str] = None,
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
        self.tags = tags if tags is not None else []
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return _as_dict(
            self,
            [
                "id",
                "name",
                "human_readable_name",
                "description",
                "tags",
                "first_seen",
                "last_seen",
                "created_at",
                "updated_at",
            ],
        )


class TaskRerunRelationshipDB:
    def __init__(
        self,
        id: Optional[int] = None,
        action_id: Optional[int] = None,
        original_task_id: Optional[str] = None,
        rerun_task_id: Optional[str] = None,
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
        task_id: str,
        resolved: bool,
        resolved_at: Optional[datetime] = None,
        resolved_by: Optional[str] = None,
    ) -> None:
        self.task_id = task_id
        self.resolved = resolved
        self.resolved_at = resolved_at or _utcnow()
        self.resolved_by = resolved_by


class TaskStepsDB:
    def __init__(
        self,
        task_id: str,
        task_name: Optional[str] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        defined_at: Optional[datetime] = None,
    ) -> None:
        self.task_id = task_id
        self.task_name = task_name
        self.steps = steps if steps is not None else []
        self.defined_at = defined_at or _utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return _as_dict(self, ["task_id", "task_name", "steps", "defined_at"])


class UserDB:
    def __init__(
        self,
        id: Optional[int] = None,
        email: Optional[str] = None,
        name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        provider: Optional[str] = None,
        provider_account_id: Optional[str] = None,
        is_active: bool = True,
        last_login_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        sessions: Optional[List["UserSessionDB"]] = None,
    ) -> None:
        self.id = id
        self.email = email
        self.name = name
        self.avatar_url = avatar_url
        self.provider = provider
        self.provider_account_id = provider_account_id
        self.is_active = is_active
        self.last_login_at = last_login_at
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at
        self.sessions = sessions if sessions is not None else []

    def to_dict(self) -> Dict[str, Any]:
        return _as_dict(
            self,
            [
                "id",
                "email",
                "name",
                "avatar_url",
                "provider",
                "provider_account_id",
                "is_active",
                "last_login_at",
                "created_at",
                "updated_at",
            ],
        )


class UserSessionDB:
    def __init__(
        self,
        session_id: str,
        user_id: Optional[int] = None,
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
        self.token_scopes = token_scopes if token_scopes is not None else []
        self.preferences = preferences if preferences is not None else {}
        self.active_environment_id = active_environment_id
        self.access_token_hash = access_token_hash
        self.refresh_token_hash = refresh_token_hash
        self.access_token_expires_at = access_token_expires_at
        self.refresh_token_expires_at = refresh_token_expires_at
        self.created_at = created_at or _utcnow()
        self.last_active = last_active or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return _as_dict(
            self,
            [
                "session_id",
                "user_id",
                "auth_provider",
                "token_scopes",
                "preferences",
                "active_environment_id",
                "access_token_expires_at",
                "refresh_token_expires_at",
                "created_at",
                "last_active",
            ],
        )


class WorkerEventDB:
    def __init__(
        self,
        id: Optional[int] = None,
        hostname: Optional[str] = None,
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
        return _as_dict(
            self,
            ["id", "hostname", "event_type", "status", "active_tasks", "processed", "timestamp"],
        )


class WorkflowDB:
    def __init__(
        self,
        id: Optional[int] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        enabled: bool = True,
        priority: Optional[int] = None,
        trigger_type: Optional[str] = None,
        trigger_config: Optional[Dict[str, Any]] = None,
        conditions: Optional[List[Dict[str, Any]]] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
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
        self.description = description
        self.enabled = enabled
        self.priority = priority
        self.trigger_type = trigger_type
        self.trigger_config = trigger_config if trigger_config is not None else {}
        self.conditions = conditions if conditions is not None else []
        self.actions = actions if actions is not None else []
        self.cooldown_seconds = cooldown_seconds
        self.max_executions_per_hour = max_executions_per_hour
        self.circuit_breaker_config = circuit_breaker_config if circuit_breaker_config is not None else {}
        self.execution_count = execution_count
        self.success_count = success_count
        self.failure_count = failure_count
        self.last_executed_at = last_executed_at
        self.created_by = created_by
        self.created_at = created_at or _utcnow()
        self.updated_at = updated_at or self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return _as_dict(
            self,
            [
                "id",
                "name",
                "description",
                "enabled",
                "priority",
                "trigger_type",
                "trigger_config",
                "conditions",
                "actions",
                "cooldown_seconds",
                "max_executions_per_hour",
                "circuit_breaker_config",
                "execution_count",
                "success_count",
                "failure_count",
                "last_executed_at",
                "created_by",
                "created_at",
                "updated_at",
            ],
        )


class WorkflowExecutionDB:
    def __init__(
        self,
        id: Optional[int] = None,
        workflow_id: Optional[int] = None,
        trigger_type: Optional[str] = None,
        trigger_event: Optional[Dict[str, Any]] = None,
        triggered_at: Optional[datetime] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_ms: Optional[int] = None,
        status: Optional[str] = None,
        error_message: Optional[str] = None,
        stack_trace: Optional[str] = None,
        actions_executed: Optional[List[Dict[str, Any]]] = None,
        workflow_snapshot: Optional[Dict[str, Any]] = None,
        circuit_breaker_key: Optional[str] = None,
    ) -> None:
        self.id = id
        self.workflow_id = workflow_id
        self.trigger_type = trigger_type
        self.trigger_event = trigger_event if trigger_event is not None else {}
        self.triggered_at = triggered_at or _utcnow()
        self.started_at = started_at
        self.completed_at = completed_at
        self.duration_ms = duration_ms
        self.status = status
        self.error_message = error_message
        self.stack_trace = stack_trace
        self.actions_executed = actions_executed if actions_executed is not None else []
        self.workflow_snapshot = workflow_snapshot if workflow_snapshot is not None else {}
        self.circuit_breaker_key = circuit_breaker_key

    def to_dict(self) -> Dict[str, Any]:
        return _as_dict(
            self,
            [
                "id",
                "workflow_id",
                "trigger_type",
                "trigger_event",
                "triggered_at",
                "started_at",
                "completed_at",
                "duration_ms",
                "status",
                "error_message",
                "stack_trace",
                "actions_executed",
                "workflow_snapshot",
                "circuit_breaker_key",
            ],
        )


class ActionHandler(ABC):
    def __init__(self, db_manager: DatabaseManager, session: Optional[Session] = None) -> None:
        self.db_manager = db_manager
        self.session = session if session is not None else db_manager.get_session()
        self.monitor_instance: None = None

    @abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        raise NotImplementedError

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        safe_context = {k: v for k, v in context.items()}
        try:
            return template.format(**safe_context)
        except Exception as e:
            raise ValueError(f"Template rendering failed: {e}") from e

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        raise NotImplementedError


class RetryActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(params, dict):
            return False, "params must be a dict"
        task_ids = params.get("task_ids")
        if not isinstance(task_ids, list) or not task_ids or not all(isinstance(x, str) and x for x in task_ids):
            return False, "task_ids must be a non-empty list of strings"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        ok, msg = self.validate_params(params)
        if not ok:
            return ActionResult(success=False, message=msg, data=None)
        task_ids: List[str] = params["task_ids"]
        data = {"retried_task_ids": task_ids, "count": len(task_ids)}
        return ActionResult(success=True, message="Retry initiated", data=data)


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
            return ActionResult(success=False, message=msg, data=None)
        channel: str = params["channel"]
        text: str = params["text"]
        rendered = self.render_template(text, context)
        data = {"channel": channel, "text": rendered}
        return ActionResult(success=True, message="Slack message prepared", data=data)


class CeleryEventMonitor:
    def __init__(
        self,
        broker_url: str,
        app: Any = None,
        progress_callback: Optional[Callable[[TaskProgressEvent], None]] = None,
        steps_callback: Optional[Callable[[TaskStepsEvent], None]] = None,
        task_callback: Optional[Callable[[TaskEvent], None]] = None,
        worker_callback: Optional[Callable[[WorkerEvent], None]] = None,
    ) -> None:
        self.app = app
        self.broker_url: str = broker_url
        self.progress_callback: Optional[Callable[[TaskProgressEvent], None]] = progress_callback
        self.steps_callback: Optional[Callable[[TaskStepsEvent], None]] = steps_callback
        self.task_callback: Optional[Callable[[TaskEvent], None]] = task_callback
        self.worker_callback: Optional[Callable[[WorkerEvent], None]] = worker_callback
        self.state: None = None
        self.workers: Dict[str, Dict[str, Any]] = {}
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
                item = await asyncio.wait_for(self.message_queue.get(), timeout=0.25)
            except asyncio.TimeoutError:
                continue
            if item is None:
                continue
            message, payload = item
            await self._broadcast(message, payload)

    async def _broadcast(self, message_type: str, payload: Any) -> None:
        text = json.dumps({"type": message_type, "data": _jsonable(payload)}, default=str)
        conns = list(self.active_connections)
        for ws in conns:
            try:
                await ws.send_text(text)
            except Exception:
                self.disconnect(ws)

    def stop_background_broadcaster(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._broadcaster_task is not None:
            self._broadcaster_task.cancel()
        self._broadcaster_task = None
        self._stop_event = None

    def queue_broadcast(self, task_event: TaskEvent) -> None:
        if self.message_queue is None:
            return
        self.message_queue.put_nowait(("task_event", task_event.__dict__))

    def queue_progress_broadcast(self, progress_event: Any) -> None:
        if self.message_queue is None:
            return
        payload = progress_event.__dict__ if hasattr(progress_event, "__dict__") else progress_event
        self.message_queue.put_nowait(("progress_event", payload))

    def queue_task_action_broadcast(self, action_event: Any) -> None:
        if self.message_queue is None:
            return
        payload = action_event.__dict__ if hasattr(action_event, "__dict__") else action_event
        self.message_queue.put_nowait(("task_action_event", payload))

    def queue_worker_broadcast(self, worker_event: WorkerEvent) -> None:
        if self.message_queue is None:
            return
        self.message_queue.put_nowait(("worker_event", worker_event.__dict__))


class EventHandler:
    def __init__(self, connection_manager: ConnectionManager, db_manager: DatabaseManager) -> None:
        self.connection_manager = connection_manager
        self.db_manager = db_manager
        self.workflow_engine: None = None

    def handle_task_event(self, task_event: TaskEvent) -> None:
        self.connection_manager.queue_broadcast(task_event)

    def handle_progress_event(self, progress_event: Any) -> None:
        self.connection_manager.queue_progress_broadcast(progress_event)

    def handle_steps_event(self, steps_event: Any) -> None:
        payload = steps_event.__dict__ if hasattr(steps_event, "__dict__") else steps_event
        if self.connection_manager.message_queue is None:
            return
        self.connection_manager.message_queue.put_nowait(("steps_event", payload))

    def handle_worker_event(self, worker_event: WorkerEvent) -> None:
        self.connection_manager.queue_worker_broadcast(worker_event)