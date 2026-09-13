import asyncio
import datetime
import threading
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from uuid import uuid4

# ---------------------------------------------------------------------------
# Helper event classes
# ---------------------------------------------------------------------------

@dataclass
class TaskEvent:
    task_id: str
    task_name: str
    event_type: str
    hostname: str
    timestamp: datetime.datetime
    args: Optional[str] = None
    kwargs: Optional[str] = None

@dataclass
class WorkerEvent:
    hostname: str
    event_type: str
    status: str
    active_tasks: int
    processed: int
    timestamp: datetime.datetime

@dataclass
class TaskProgressEvent:
    task_id: str
    task_name: str
    progress: float
    message: str
    step_key: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

@dataclass
class TaskStepsEvent:
    task_id: str
    task_name: str
    steps: List[Dict[str, Any]]
    defined_at: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

@dataclass
class ActionResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    task_id: Optional[str] = None

# ---------------------------------------------------------------------------
# DatabaseORMModel base
# ---------------------------------------------------------------------------

class MockConnection:
    """Placeholder for database engine connection."""
    pass

Engine = MockConnection

# ---------------------------------------------------------------------------
# agent.database classes
# ---------------------------------------------------------------------------

class ActionConfigDB:
    def __init__(self, id: str, name: str, action_type: str, config: str,
                 description: str, usage_count: int, last_used_at: Optional[datetime.datetime],
                 created_at: datetime.datetime, updated_at: datetime.datetime,
                 created_by: str):
        self.id = id
        self.name = name
        self.action_type = action_type
        self.config = config
        self.description = description
        self.usage_count = usage_count
        self.last_used_at = last_used_at
        self.created_at = created_at
        self.updated_at = updated_at
        self.created_by = created_by

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "action_type": self.action_type,
            "config": self.config,
            "description": self.description,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
        }

class AppSettingDB:
    def __init__(self, key: str, value: str, value_type: str, category: str,
                 label: str, description: str, created_at: datetime.datetime,
                 updated_at: datetime.datetime):
        self.key = key
        self.value = value
        self.value_type = value_type
        self.category = category
        self.label = label
        self.description = description
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "value_type": self.value_type,
            "category": self.category,
            "label": self.label,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

class EnvironmentDB:
    def __init__(self, id: str, name: str, description: str, is_active: bool,
                 is_default: bool, queue_patterns: str, worker_patterns: str,
                 created_at: datetime.datetime, updated_at: datetime.datetime):
        self.id = id
        self.name = name
        self.description = description
        self.is_active = is_active
        self.is_default = is_default
        self.queue_patterns = queue_patterns
        self.worker_patterns = worker_patterns
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "queue_patterns": self.queue_patterns,
            "worker_patterns": self.worker_patterns,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

class RetryRelationshipDB:
    def __init__(self, id: str, task_id: str, original_id: str, retry_chain: str,
                 total_retries: int, created_at: datetime.datetime, updated_at: datetime.datetime):
        self.id = id
        self.task_id = task_id
        self.original_id = original_id
        self.retry_chain = retry_chain
        self.total_retries = total_retries
        self.created_at = created_at
        self.updated_at = updated_at

class TaskActionDB:
    def __init__(self, id: str, action_type: str, status: str, summary: str,
                 initiated_by: str, initiated_by_user_id: str,
                 initiated_session_id: str, original_task_ids: str,
                 selection_size: int, items: str,
                 item_total: int, item_changed: int, item_failed: int,
                 item_noop: int, item_skipped: int,
                 created_at: datetime.datetime, started_at: Optional[datetime.datetime],
                 completed_at: Optional[datetime.datetime]):
        self.id = id
        self.action_type = action_type
        self.status = status
        self.summary = summary
        self.initiated_by = initiated_by
        self.initiated_by_user_id = initiated_by_user_id
        self.initiated_session_id = initiated_session_id
        self.original_task_ids = original_task_ids
        self.selection_size = selection_size
        self.items = items
        self.item_total = item_total
        self.item_changed = item_changed
        self.item_failed = item_failed
        self.item_noop = item_noop
        self.item_skipped = item_skipped
        self.created_at = created_at
        self.started_at = started_at
        self.completed_at = completed_at

class TaskActionItemDB:
    def __init__(self, id: str, action_id: str, action: str,
                 original_task_id: str, original_task_name: str,
                 outcome: str, reason: str, reason_code: str,
                 attempted_task_id: Optional[str],
                 rerun_kind: Optional[str], rerun_task_id: Optional[str],
                 rerun_task_name: Optional[str],
                 review_fingerprint: Optional[str],
                 skip_category: Optional[str],
                 target_queue: Optional[str],
                 submitted_args: Optional[str], submitted_kwargs: Optional[str],
                 created_at: datetime.datetime, updated_at: datetime.datetime):
        self.id = id
        self.action_id = action_id
        self.action = action
        self.original_task_id = original_task_id
        self.original_task_name = original_task_name
        self.outcome = outcome
        self.reason = reason
        self.reason_code = reason_code
        self.attempted_task_id = attempted_task_id
        self.rerun_kind = rerun_kind
        self.rerun_task_id = rerun_task_id
        self.rerun_task_name = rerun_task_name
        self.review_fingerprint = review_fingerprint
        self.skip_category = skip_category
        self.target_queue = target_queue
        self.submitted_args = submitted_args
        self.submitted_kwargs = submitted_kwargs
        self.created_at = created_at
        self.updated_at = updated_at

class TaskDailyStatsDB:
    def __init__(self, id: str, date: datetime.date, task_name: str,
                 total_executions: int, succeeded: int, failed: int,
                 retried: int, revoked: int, pending: int, orphaned: int,
                 first_execution: Optional[datetime.datetime],
                 last_execution: Optional[datetime.datetime],
                 min_runtime: Optional[float], max_runtime: Optional[float],
                 avg_runtime: Optional[float], p50_runtime: Optional[float],
                 p95_runtime: Optional[float], p99_runtime: Optional[float],
                 created_at: datetime.datetime, updated_at: datetime.datetime):
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
        self.created_at = created_at
        self.updated_at = updated_at

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
    def __init__(self, id: str, event_type: str, task_id: str, task_name: str,
                 args: Optional[str], kwargs: Optional[str],
                 queue: Optional[str], exchange: Optional[str],
                 routing_key: Optional[str],
                 result: Optional[str], runtime: Optional[float],
                 hostname: Optional[str], worker_name: Optional[str],
                 timestamp: datetime.datetime,
                 parent_id: Optional[str], root_id: Optional[str],
                 retries: int, retry_count: int, retry_of: Optional[str],
                 retried_by: Optional[str], has_retries: bool, is_retry: bool,
                 eta: Optional[datetime.datetime], expires: Optional[datetime.datetime],
                 exception: Optional[str], traceback: Optional[str],
                 is_orphan: bool, orphaned_at: Optional[datetime.datetime]):
        self.id = id
        self.event_type = event_type
        self.task_id = task_id
        self.task_name = task_name
        self.args = args
        self.kwargs = kwargs
        self.queue = queue
        self.exchange = exchange
        self.routing_key = routing_key
        self.result = result
        self.runtime = runtime
        self.hostname = hostname
        self.worker_name = worker_name
        self.timestamp = timestamp
        self.parent_id = parent_id
        self.root_id = root_id
        self.retries = retries
        self.retry_count = retry_count
        self.retry_of = retry_of
        self.retried_by = retried_by
        self.has_retries = has_retries
        self.is_retry = is_retry
        self.eta = eta
        self.expires = expires
        self.exception = exception
        self.traceback = traceback
        self.is_orphan = is_orphan
        self.orphaned_at = orphaned_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "args": self.args,
            "kwargs": self.kwargs,
            "queue": self.queue,
            "exchange": self.exchange,
            "routing_key": self.routing_key,
            "result": self.result,
            "runtime": self.runtime,
            "hostname": self.hostname,
            "worker_name": self.worker_name,
            "timestamp": self.timestamp,
            "parent_id": self.parent_id,
            "root_id": self.root_id,
            "retries": self.retries,
            "retry_count": self.retry_count,
            "retry_of": self.retry_of,
            "retried_by": self.retried_by,
            "has_retries": self.has_retries,
            "is_retry": self.is_retry,
            "eta": self.eta,
            "expires": self.expires,
            "exception": self.exception,
            "traceback": self.traceback,
            "is_orphan": self.is_orphan,
            "orphaned_at": self.orphaned_at,
        }

class TaskLatestDB:
    def __init__(self, task_id: str, event_id: str, task_name: str,
                 event_type: str, args: Optional[str], kwargs: Optional[str],
                 queue: Optional[str], exchange: Optional[str],
                 routing_key: Optional[str],
                 result: Optional[str], runtime: Optional[float],
                 hostname: Optional[str], worker_name: Optional[str],
                 timestamp: datetime.datetime,
                 parent_id: Optional[str], root_id: Optional[str],
                 retries: int, retry_count: int, retry_of: Optional[str],
                 retried_by: Optional[str], has_retries: bool, is_retry: bool,
                 eta: Optional[datetime.datetime], expires: Optional[datetime.datetime],
                 exception: Optional[str], traceback: Optional[str],
                 is_orphan: bool, orphaned_at: Optional[datetime.datetime],
                 resolved: bool, resolved_at: Optional[datetime.datetime],
                 resolved_by: Optional[str]):
        self.task_id = task_id
        self.event_id = event_id
        self.task_name = task_name
        self.event_type = event_type
        self.args = args
        self.kwargs = kwargs
        self.queue = queue
        self.exchange = exchange
        self.routing_key = routing_key
        self.result = result
        self.runtime = runtime
        self.hostname = hostname
        self.worker_name = worker_name
        self.timestamp = timestamp
        self.parent_id = parent_id
        self.root_id = root_id
        self.retries = retries
        self.retry_count = retry_count
        self.retry_of = retry_of
        self.retried_by = retried_by
        self.has_retries = has_retries
        self.is_retry = is_retry
        self.eta = eta
        self.expires = expires
        self.exception = exception
        self.traceback = traceback
        self.is_orphan = is_orphan
        self.orphaned_at = orphaned_at
        self.resolved = resolved
        self.resolved_at = resolved_at
        self.resolved_by = resolved_by

class TaskProgressDB:
    def __init__(self, id: str, task_id: str, task_name: str, progress: float,
                 message: str, step_key: Optional[str], meta: Optional[str],
                 timestamp: datetime.datetime):
        self.id = id
        self.task_id = task_id
        self.task_name = task_name
        self.progress = progress
        self.message = message
        self.step_key = step_key
        self.meta = meta
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "progress": self.progress,
            "message": self.message,
            "step_key": self.step_key,
            "meta": self.meta,
            "timestamp": self.timestamp,
        }

class TaskProgressLatestDB:
    def __init__(self, task_id: str, task_name: str, progress: float,
                 message: str, step_key: Optional[str], meta: Optional[str],
                 updated_at: datetime.datetime):
        self.task_id = task_id
        self.task_name = task_name
        self.progress = progress
        self.message = message
        self.step_key = step_key
        self.meta = meta
        self.updated_at = updated_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "progress": self.progress,
            "message": self.message,
            "step_key": self.step_key,
            "meta": self.meta,
            "updated_at": self.updated_at,
        }

class TaskRegistryDB:
    def __init__(self, id: str, name: str, human_readable_name: str,
                 description: str, tags: str,
                 first_seen: datetime.datetime, last_seen: datetime.datetime,
                 created_at: datetime.datetime, updated_at: datetime.datetime):
        self.id = id
        self.name = name
        self.human_readable_name = human_readable_name
        self.description = description
        self.tags = tags
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "human_readable_name": self.human_readable_name,
            "description": self.description,
            "tags": self.tags,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

class TaskRerunRelationshipDB:
    def __init__(self, id: str, original_task_id: str, rerun_task_id: str,
                 action_id: str, created_by: str,
                 created_at: datetime.datetime):
        self.id = id
        self.original_task_id = original_task_id
        self.rerun_task_id = rerun_task_id
        self.action_id = action_id
        self.created_by = created_by
        self.created_at = created_at

class TaskResolutionDB:
    def __init__(self, task_id: str, resolved: bool,
                 resolved_at: Optional[datetime.datetime],
                 resolved_by: Optional[str]):
        self.task_id = task_id
        self.resolved = resolved
        self.resolved_at = resolved_at
        self.resolved_by = resolved_by

class TaskStepsDB:
    def __init__(self, task_id: str, task_name: str, steps: str,
                 defined_at: datetime.datetime):
        self.task_id = task_id
        self.task_name = task_name
        self.steps = steps
        self.defined_at = defined_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "steps": self.steps,
            "defined_at": self.defined_at,
        }

class UserDB:
    def __init__(self, id: str, name: str, email: str, avatar_url: str,
                 provider: str, provider_account_id: str,
                 is_active: bool, last_login_at: Optional[datetime.datetime],
                 sessions: List["UserSessionDB"],
                 created_at: datetime.datetime, updated_at: datetime.datetime):
        self.id = id
        self.name = name
        self.email = email
        self.avatar_url = avatar_url
        self.provider = provider
        self.provider_account_id = provider_account_id
        self.is_active = is_active
        self.last_login_at = last_login_at
        self.sessions = sessions
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
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
    def __init__(self, session_id: str, user_id: str,
                 auth_provider: str, access_token_hash: str,
                 access_token_expires_at: datetime.datetime,
                 refresh_token_hash: Optional[str],
                 refresh_token_expires_at: Optional[datetime.datetime],
                 token_scopes: str,
                 active_environment_id: Optional[str],
                 preferences: str,
                 last_active: datetime.datetime,
                 user: UserDB,
                 created_at: datetime.datetime):
        self.session_id = session_id
        self.user_id = user_id
        self.auth_provider = auth_provider
        self.access_token_hash = access_token_hash
        self.access_token_expires_at = access_token_expires_at
        self.refresh_token_hash = refresh_token_hash
        self.refresh_token_expires_at = refresh_token_expires_at
        self.token_scopes = token_scopes
        self.active_environment_id = active_environment_id
        self.preferences = preferences
        self.last_active = last_active
        self.user = user
        self.created_at = created_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "auth_provider": self.auth_provider,
            "access_token_hash": self.access_token_hash,
            "access_token_expires_at": self.access_token_expires_at,
            "refresh_token_hash": self.refresh_token_hash,
            "refresh_token_expires_at": self.refresh_token_expires_at,
            "token_scopes": self.token_scopes,
            "active_environment_id": self.active_environment_id,
            "preferences": self.preferences,
            "last_active": self.last_active,
            "created_at": self.created_at,
        }

class WorkerEventDB:
    def __init__(self, id: str, event_type: str, hostname: str, status: str,
                 active_tasks: int, processed: int,
                 timestamp: datetime.datetime):
        self.id = id
        self.event_type = event_type
        self.hostname = hostname
        self.status = status
        self.active_tasks = active_tasks
        self.processed = processed
        self.timestamp = timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "hostname": self.hostname,
            "status": self.status,
            "active_tasks": self.active_tasks,
            "processed": self.processed,
            "timestamp": self.timestamp,
        }

class WorkflowDB:
    def __init__(self, id: str, name: str, description: str, trigger_type: str,
                 trigger_config: str, actions: str, conditions: str,
                 enabled: bool, priority: int,
                 cooldown_seconds: int, max_executions_per_hour: int,
                 circuit_breaker_config: str,
                 execution_count: int, success_count: int, failure_count: int,
                 last_executed_at: Optional[datetime.datetime],
                 created_by: str, created_at: datetime.datetime,
                 updated_at: datetime.datetime):
        self.id = id
        self.name = name
        self.description = description
        self.trigger_type = trigger_type
        self.trigger_config = trigger_config
        self.actions = actions
        self.conditions = conditions
        self.enabled = enabled
        self.priority = priority
        self.cooldown_seconds = cooldown_seconds
        self.max_executions_per_hour = max_executions_per_hour
        self.circuit_breaker_config = circuit_breaker_config
        self.execution_count = execution_count
        self.success_count = success_count
        self.failure_count = failure_count
        self.last_executed_at = last_executed_at
        self.created_by = created_by
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger_type": self.trigger_type,
            "trigger_config": self.trigger_config,
            "actions": self.actions,
            "conditions": self.conditions,
            "enabled": self.enabled,
            "priority": self.priority,
            "cooldown_seconds": self.cooldown_seconds,
            "max_executions_per_hour": self.max_executions_per_hour,
            "circuit_breaker_config": self.circuit_breaker_config,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_executed_at": self.last_executed_at,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

class WorkflowExecutionDB:
    def __init__(self, id: str, workflow_id: str, status: str,
                 trigger_type: str, trigger_event: str,
                 circuit_breaker_key: str,
                 actions_executed: str, workflow_snapshot: str,
                 duration_ms: Optional[int],
                 error_message: Optional[str], stack_trace: Optional[str],
                 triggered_at: datetime.datetime,
                 started_at: Optional[datetime.datetime],
                 completed_at: Optional[datetime.datetime]):
        self.id = id
        self.workflow_id = workflow_id
        self.status = status
        self.trigger_type = trigger_type
        self.trigger_event = trigger_event
        self.circuit_breaker_key = circuit_breaker_key
        self.actions_executed = actions_executed
        self.workflow_snapshot = workflow_snapshot
        self.duration_ms = duration_ms
        self.error_message = error_message
        self.stack_trace = stack_trace
        self.triggered_at = triggered_at
        self.started_at = started_at
        self.completed_at = completed_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "trigger_type": self.trigger_type,
            "trigger_event": self.trigger_event,
            "circuit_breaker_key": self.circuit_breaker_key,
            "actions_executed": self.actions_executed,
            "workflow_snapshot": self.workflow_snapshot,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "triggered_at": self.triggered_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

# ---------------------------------------------------------------------------
# DatabaseManager
# ---------------------------------------------------------------------------

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine: Optional[Engine] = None
        self.SessionLocal: Optional[Callable] = None  # sessionmaker placeholder

    def get_session(self) -> Any:
        """Return a mock session."""
        return MockSession()

    def run_migrations(self) -> None:
        """Placeholder for running database migrations."""
        pass

class MockSession:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def query(self, *args): pass

# ---------------------------------------------------------------------------
# ConnectionManager
# ---------------------------------------------------------------------------

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[Any] = []  # WebSocket from starlette
        self.client_filters: Dict[Any, dict] = {}
        self.client_modes: Dict[Any, str] = {}
        self.message_queue: Optional[asyncio.Queue] = None

    async def connect(self, websocket: Any) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_filters[websocket] = {}
        self.client_modes[websocket] = "default"

    async def disconnect(self, websocket: Any) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.client_filters.pop(websocket, None)
            self.client_modes.pop(websocket, None)

    async def queue_broadcast(self, task_event: TaskEvent) -> None:
        if self.message_queue:
            await self.message_queue.put(("task", task_event))

    async def queue_progress_broadcast(self, progress_event: TaskProgressEvent) -> None:
        if self.message_queue:
            await self.message_queue.put(("progress", progress_event))

    async def queue_task_action_broadcast(self, action_event: Any) -> None:
        if self.message_queue:
            await self.message_queue.put(("action", action_event))

    async def queue_worker_broadcast(self, worker_event: WorkerEvent) -> None:
        if self.message_queue:
            await self.message_queue.put(("worker", worker_event))

    async def send_personal_message(self, message: str, websocket: Any) -> None:
        await websocket.send_text(message)

    def set_client_filters(self, websocket: Any, filters: dict) -> None:
        self.client_filters[websocket] = filters

    def set_client_mode(self, websocket: Any, mode: str) -> None:
        self.client_modes[websocket] = mode

    async def start_background_broadcaster(self) -> None:
        self.message_queue = asyncio.Queue()
        # In a real implementation, an asyncio task would be created to process the queue

    async def stop_background_broadcaster(self) -> None:
        self.message_queue = None

# ---------------------------------------------------------------------------
# CeleryEventMonitor
# ---------------------------------------------------------------------------

class CeleryEventMonitor:
    def __init__(self, app: Any, broker_url: str):
        self.app = app
        self.broker_url = broker_url
        self.state: None = None
        self.workers: Dict[str, Dict[str, Any]] = {}
        self.progress_callback: Optional[Callable[[TaskProgressEvent], None]] = None
        self.steps_callback: Optional[Callable[[TaskStepsEvent], None]] = None
        self.task_callback: Optional[Callable[[TaskEvent], None]] = None
        self.worker_callback: Optional[Callable[[WorkerEvent], None]] = None
        self._thread: Optional[threading.Thread] = None
        self._stopped = threading.Event()

    def get_workers_info(self) -> Dict[str, Dict[str, Any]]:
        return self.workers

    def set_progress_callback(self, callback: Callable[[TaskProgressEvent], None]) -> None:
        self.progress_callback = callback

    def set_steps_callback(self, callback: Callable[[TaskStepsEvent], None]) -> None:
        self.steps_callback = callback

    def set_task_callback(self, callback: Callable[[TaskEvent], None]) -> None:
        self.task_callback = callback

    def set_worker_callback(self, callback: Callable[[WorkerEvent], None]) -> None:
        self.worker_callback = callback

    def start_monitoring(self) -> None:
        if self._thread is None:
            self._stopped.clear()
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stopped.set()
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _monitor_loop(self) -> None:
        # Simulate monitoring; in production would capture events from Celery
        while not self._stopped.is_set():
            self._stopped.wait(1.0)

# ---------------------------------------------------------------------------
# EventHandler
# ---------------------------------------------------------------------------

class EventHandler:
    def __init__(self, connection_manager: ConnectionManager,
                 db_manager: DatabaseManager):
        self.connection_manager = connection_manager
        self.db_manager = db_manager
        self.workflow_engine: None = None  # placeholder

    async def handle_task_event(self, task_event: TaskEvent) -> None:
        await self.connection_manager.queue_broadcast(task_event)

    async def handle_progress_event(self, progress_event: TaskProgressEvent) -> None:
        await self.connection_manager.queue_progress_broadcast(progress_event)

    async def handle_steps_event(self, steps_event: TaskStepsEvent) -> None:
        await self.connection_manager.queue_broadcast(steps_event)  # generic broadcast

    async def handle_worker_event(self, worker_event: WorkerEvent) -> None:
        await self.connection_manager.queue_worker_broadcast(worker_event)

# ---------------------------------------------------------------------------
# ActionHandler (abstract) and subclasses
# ---------------------------------------------------------------------------

class ActionHandler(ABC):
    def __init__(self, db_manager: DatabaseManager, session: Any,
                 monitor_instance: Optional[CeleryEventMonitor] = None):
        self.db_manager = db_manager
        self.session = session
        self.monitor_instance = monitor_instance

    @abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        ...

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        # Simple template rendering (replace placeholders)
        for key, value in context.items():
            template = template.replace(f"{{{key}}}", str(value))
        return template

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        ...

class RetryActionHandler(ActionHandler):
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        valid, msg = self.validate_params(params)
        if not valid:
            return ActionResult(success=False, message=msg)
        # In a real retry action, we'd re-queue the task with retry options
        return ActionResult(success=True, message="Task queued for retry",
                            task_id=params.get("task_id"))

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "task_id" not in params:
            return False, "Missing required parameter: task_id"
        return True, ""

class SlackActionHandler(ActionHandler):
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        valid, msg = self.validate_params(params)
        if not valid:
            return ActionResult(success=False, message=msg)
        # In a real implementation, send a Slack message
        return ActionResult(success=True, message="Slack notification sent")

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "channel" not in params or "message" not in params:
            return False, "Missing required parameters: channel, message"
        return True, ""