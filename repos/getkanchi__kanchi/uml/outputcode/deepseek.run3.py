import asyncio
import datetime
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# ---------------------------------------------------------------------------
# Utility / base types
# ---------------------------------------------------------------------------

class WebSocket:
    """Stub for a WebSocket connection."""
    pass

class ActionResult:
    """Simple result container for action execution."""
    def __init__(self, success: bool, message: str = "", data: Any = None):
        self.success = success
        self.message = message
        self.data = data

@dataclass
class TaskEvent:
    """Event representing a task state change."""
    task_id: str
    task_name: str
    event_type: str
    timestamp: datetime.datetime
    hostname: Optional[str] = None
    args: Optional[Any] = None
    kwargs: Optional[Any] = None
    # ... other fields can be added

@dataclass
class TaskProgressEvent:
    """Event carrying progress information."""
    task_id: str
    task_name: str
    progress: float
    message: str = ""
    step_key: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

@dataclass
class TaskStepsEvent:
    """Event describing defined steps for a task."""
    task_id: str
    task_name: str
    steps: List[str] = field(default_factory=list)
    defined_at: datetime.datetime = field(default_factory=datetime.datetime.now)

@dataclass
class WorkerEvent:
    """Event about worker status changes."""
    hostname: str
    event_type: str
    status: str
    timestamp: datetime.datetime
    active_tasks: int = 0
    processed: int = 0

@dataclass
class TaskActionEvent:
    """Event representing a bulk action on tasks."""
    action_id: str
    action_type: str
    status: str
    summary: str = ""

# ---------------------------------------------------------------------------
# Database model classes (plain Python – no ORM needed for this skeleton)
# ---------------------------------------------------------------------------

class ActionConfigDB:
    def __init__(self,
                 action_type: str = "",
                 config: Optional[Dict[str, Any]] = None,
                 created_at: Optional[datetime.datetime] = None,
                 created_by: Optional[str] = None,
                 description: str = "",
                 id: Optional[int] = None,
                 last_used_at: Optional[datetime.datetime] = None,
                 name: str = "",
                 updated_at: Optional[datetime.datetime] = None,
                 usage_count: int = 0):
        self.action_type = action_type
        self.config = config or {}
        self.created_at = created_at or datetime.datetime.now()
        self.created_by = created_by
        self.description = description
        self.id = id
        self.last_used_at = last_used_at
        self.name = name
        self.updated_at = updated_at or datetime.datetime.now()
        self.usage_count = usage_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "config": self.config,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "description": self.description,
            "id": self.id,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "name": self.name,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "usage_count": self.usage_count,
        }

class AppSettingDB:
    def __init__(self,
                 category: str = "",
                 created_at: Optional[datetime.datetime] = None,
                 description: str = "",
                 key: str = "",
                 label: str = "",
                 updated_at: Optional[datetime.datetime] = None,
                 value: str = "",
                 value_type: str = "string"):
        self.category = category
        self.created_at = created_at or datetime.datetime.now()
        self.description = description
        self.key = key
        self.label = label
        self.updated_at = updated_at or datetime.datetime.now()
        self.value = value
        self.value_type = value_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "description": self.description,
            "key": self.key,
            "label": self.label,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "value": self.value,
            "value_type": self.value_type,
        }

class EnvironmentDB:
    def __init__(self,
                 created_at: Optional[datetime.datetime] = None,
                 description: str = "",
                 id: Optional[int] = None,
                 is_active: bool = False,
                 is_default: bool = False,
                 name: str = "",
                 queue_patterns: Optional[List[str]] = None,
                 updated_at: Optional[datetime.datetime] = None,
                 worker_patterns: Optional[List[str]] = None):
        self.created_at = created_at or datetime.datetime.now()
        self.description = description
        self.id = id
        self.is_active = is_active
        self.is_default = is_default
        self.name = name
        self.queue_patterns = queue_patterns or []
        self.updated_at = updated_at or datetime.datetime.now()
        self.worker_patterns = worker_patterns or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "description": self.description,
            "id": self.id,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "name": self.name,
            "queue_patterns": self.queue_patterns,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "worker_patterns": self.worker_patterns,
        }

class RetryRelationshipDB:
    def __init__(self,
                 created_at: Optional[datetime.datetime] = None,
                 id: Optional[int] = None,
                 original_id: Optional[str] = None,
                 retry_chain: Optional[List[str]] = None,
                 task_id: str = "",
                 total_retries: int = 0,
                 updated_at: Optional[datetime.datetime] = None):
        self.created_at = created_at or datetime.datetime.now()
        self.id = id
        self.original_id = original_id
        self.retry_chain = retry_chain or []
        self.task_id = task_id
        self.total_retries = total_retries
        self.updated_at = updated_at or datetime.datetime.now()

class TaskActionDB:
    def __init__(self,
                 action_type: str = "",
                 completed_at: Optional[datetime.datetime] = None,
                 created_at: Optional[datetime.datetime] = None,
                 id: Optional[int] = None,
                 initiated_by: Optional[str] = None,
                 initiated_by_user_id: Optional[int] = None,
                 initiated_session_id: Optional[str] = None,
                 item_changed: int = 0,
                 item_created: int = 0,
                 item_failed: int = 0,
                 item_noop: int = 0,
                 item_skipped: int = 0,
                 item_total: int = 0,
                 items: Optional[List[Any]] = None,
                 original_task_ids: Optional[List[str]] = None,
                 selection_size: int = 0,
                 started_at: Optional[datetime.datetime] = None,
                 status: str = "pending",
                 summary: str = ""):
        self.action_type = action_type
        self.completed_at = completed_at
        self.created_at = created_at or datetime.datetime.now()
        self.id = id
        self.initiated_by = initiated_by
        self.initiated_by_user_id = initiated_by_user_id
        self.initiated_session_id = initiated_session_id
        self.item_changed = item_changed
        self.item_created = item_created
        self.item_failed = item_failed
        self.item_noop = item_noop
        self.item_skipped = item_skipped
        self.item_total = item_total
        self.items = items or []
        self.original_task_ids = original_task_ids or []
        self.selection_size = selection_size
        self.started_at = started_at
        self.status = status
        self.summary = summary

class TaskActionItemDB:
    def __init__(self,
                 action: Optional[TaskActionDB] = None,
                 action_id: Optional[int] = None,
                 attempted_task_id: Optional[str] = None,
                 created_at: Optional[datetime.datetime] = None,
                 id: Optional[int] = None,
                 original_task_id: str = "",
                 original_task_name: str = "",
                 outcome: str = "",
                 reason: str = "",
                 reason_code: str = "",
                 rerun_kind: str = "",
                 rerun_task_id: Optional[str] = None,
                 rerun_task_name: str = "",
                 review_fingerprint: str = "",
                 skip_category: str = "",
                 submitted_args: Optional[Any] = None,
                 submitted_kwargs: Optional[Any] = None,
                 target_queue: str = "",
                 updated_at: Optional[datetime.datetime] = None):
        self.action = action
        self.action_id = action_id
        self.attempted_task_id = attempted_task_id
        self.created_at = created_at or datetime.datetime.now()
        self.id = id
        self.original_task_id = original_task_id
        self.original_task_name = original_task_name
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
        self.updated_at = updated_at or datetime.datetime.now()

class TaskDailyStatsDB:
    def __init__(self,
                 avg_runtime: float = 0.0,
                 created_at: Optional[datetime.datetime] = None,
                 date: Optional[datetime.date] = None,
                 failed: int = 0,
                 first_execution: Optional[datetime.datetime] = None,
                 id: Optional[int] = None,
                 last_execution: Optional[datetime.datetime] = None,
                 max_runtime: float = 0.0,
                 min_runtime: float = 0.0,
                 orphaned: int = 0,
                 p50_runtime: float = 0.0,
                 p95_runtime: float = 0.0,
                 p99_runtime: float = 0.0,
                 pending: int = 0,
                 retried: int = 0,
                 revoked: int = 0,
                 succeeded: int = 0,
                 task_name: str = "",
                 total_executions: int = 0,
                 updated_at: Optional[datetime.datetime] = None):
        self.avg_runtime = avg_runtime
        self.created_at = created_at or datetime.datetime.now()
        self.date = date or datetime.date.today()
        self.failed = failed
        self.first_execution = first_execution
        self.id = id
        self.last_execution = last_execution
        self.max_runtime = max_runtime
        self.min_runtime = min_runtime
        self.orphaned = orphaned
        self.p50_runtime = p50_runtime
        self.p95_runtime = p95_runtime
        self.p99_runtime = p99_runtime
        self.pending = pending
        self.retried = retried
        self.revoked = revoked
        self.succeeded = succeeded
        self.task_name = task_name
        self.total_executions = total_executions
        self.updated_at = updated_at or datetime.datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_runtime": self.avg_runtime,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "date": self.date.isoformat() if self.date else None,
            "failed": self.failed,
            "first_execution": self.first_execution.isoformat() if self.first_execution else None,
            "id": self.id,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "max_runtime": self.max_runtime,
            "min_runtime": self.min_runtime,
            "orphaned": self.orphaned,
            "p50_runtime": self.p50_runtime,
            "p95_runtime": self.p95_runtime,
            "p99_runtime": self.p99_runtime,
            "pending": self.pending,
            "retried": self.retried,
            "revoked": self.revoked,
            "succeeded": self.succeeded,
            "task_name": self.task_name,
            "total_executions": self.total_executions,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class TaskEventDB:
    def __init__(self,
                 args: Optional[Any] = None,
                 eta: Optional[str] = None,
                 event_type: str = "",
                 exception: str = "",
                 exchange: str = "",
                 expires: Optional[str] = None,
                 has_retries: bool = False,
                 hostname: str = "",
                 id: Optional[int] = None,
                 is_orphan: bool = False,
                 is_retry: bool = False,
                 kwargs: Optional[Any] = None,
                 orphaned_at: Optional[datetime.datetime] = None,
                 parent_id: Optional[str] = None,
                 queue: str = "",
                 result: Optional[Any] = None,
                 retried_by: Optional[str] = None,
                 retries: int = 0,
                 retry_count: int = 0,
                 retry_of: Optional[str] = None,
                 root_id: Optional[str] = None,
                 routing_key: str = "",
                 runtime: Optional[float] = None,
                 task_id: str = "",
                 task_name: str = "",
                 timestamp: Optional[datetime.datetime] = None,
                 traceback: Optional[str] = None,
                 worker_name: str = ""):
        self.args = args
        self.eta = eta
        self.event_type = event_type
        self.exception = exception
        self.exchange = exchange
        self.expires = expires
        self.has_retries = has_retries
        self.hostname = hostname
        self.id = id
        self.is_orphan = is_orphan
        self.is_retry = is_retry
        self.kwargs = kwargs
        self.orphaned_at = orphaned_at
        self.parent_id = parent_id
        self.queue = queue
        self.result = result
        self.retried_by = retried_by
        self.retries = retries
        self.retry_count = retry_count
        self.retry_of = retry_of
        self.root_id = root_id
        self.routing_key = routing_key
        self.runtime = runtime
        self.task_id = task_id
        self.task_name = task_name
        self.timestamp = timestamp or datetime.datetime.now()
        self.traceback = traceback
        self.worker_name = worker_name

    def to_dict(self) -> Dict[str, Any]:
        return {attr: getattr(self, attr) for attr in self.__dict__ if not attr.startswith("_")}

class TaskLatestDB:
    def __init__(self,
                 args: Optional[Any] = None,
                 eta: Optional[str] = None,
                 event_id: Optional[int] = None,
                 event_type: str = "",
                 exception: str = "",
                 exchange: str = "",
                 expires: Optional[str] = None,
                 has_retries: bool = False,
                 hostname: str = "",
                 is_orphan: bool = False,
                 is_retry: bool = False,
                 kwargs: Optional[Any] = None,
                 orphaned_at: Optional[datetime.datetime] = None,
                 parent_id: Optional[str] = None,
                 queue: str = "",
                 resolved: bool = False,
                 resolved_at: Optional[datetime.datetime] = None,
                 resolved_by: Optional[str] = None,
                 result: Optional[Any] = None,
                 retried_by: Optional[str] = None,
                 retries: int = 0,
                 retry_count: int = 0,
                 retry_of: Optional[str] = None,
                 root_id: Optional[str] = None,
                 routing_key: str = "",
                 runtime: Optional[float] = None,
                 task_id: str = "",
                 task_name: str = "",
                 timestamp: Optional[datetime.datetime] = None,
                 traceback: Optional[str] = None,
                 worker_name: str = ""):
        self.args = args
        self.eta = eta
        self.event_id = event_id
        self.event_type = event_type
        self.exception = exception
        self.exchange = exchange
        self.expires = expires
        self.has_retries = has_retries
        self.hostname = hostname
        self.is_orphan = is_orphan
        self.is_retry = is_retry
        self.kwargs = kwargs
        self.orphaned_at = orphaned_at
        self.parent_id = parent_id
        self.queue = queue
        self.resolved = resolved
        self.resolved_at = resolved_at
        self.resolved_by = resolved_by
        self.result = result
        self.retried_by = retried_by
        self.retries = retries
        self.retry_count = retry_count
        self.retry_of = retry_of
        self.root_id = root_id
        self.routing_key = routing_key
        self.runtime = runtime
        self.task_id = task_id
        self.task_name = task_name
        self.timestamp = timestamp or datetime.datetime.now()
        self.traceback = traceback
        self.worker_name = worker_name

class TaskProgressDB:
    def __init__(self,
                 id: Optional[int] = None,
                 message: str = "",
                 meta: Optional[Dict[str, Any]] = None,
                 progress: float = 0.0,
                 step_key: Optional[str] = None,
                 task_id: str = "",
                 task_name: str = "",
                 timestamp: Optional[datetime.datetime] = None):
        self.id = id
        self.message = message
        self.meta = meta or {}
        self.progress = progress
        self.step_key = step_key
        self.task_id = task_id
        self.task_name = task_name
        self.timestamp = timestamp or datetime.datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "message": self.message,
            "meta": self.meta,
            "progress": self.progress,
            "step_key": self.step_key,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

class TaskProgressLatestDB:
    def __init__(self,
                 message: str = "",
                 meta: Optional[Dict[str, Any]] = None,
                 progress: float = 0.0,
                 step_key: Optional[str] = None,
                 task_id: str = "",
                 task_name: str = "",
                 updated_at: Optional[datetime.datetime] = None):
        self.message = message
        self.meta = meta or {}
        self.progress = progress
        self.step_key = step_key
        self.task_id = task_id
        self.task_name = task_name
        self.updated_at = updated_at or datetime.datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "meta": self.meta,
            "progress": self.progress,
            "step_key": self.step_key,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class TaskRegistryDB:
    def __init__(self,
                 created_at: Optional[datetime.datetime] = None,
                 description: str = "",
                 first_seen: Optional[datetime.datetime] = None,
                 human_readable_name: str = "",
                 id: Optional[int] = None,
                 last_seen: Optional[datetime.datetime] = None,
                 name: str = "",
                 tags: Optional[List[str]] = None,
                 updated_at: Optional[datetime.datetime] = None):
        self.created_at = created_at or datetime.datetime.now()
        self.description = description
        self.first_seen = first_seen
        self.human_readable_name = human_readable_name
        self.id = id
        self.last_seen = last_seen
        self.name = name
        self.tags = tags or []
        self.updated_at = updated_at or datetime.datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "description": self.description,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "human_readable_name": self.human_readable_name,
            "id": self.id,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "name": self.name,
            "tags": self.tags,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class TaskRerunRelationshipDB:
    def __init__(self,
                 action_id: Optional[int] = None,
                 created_at: Optional[datetime.datetime] = None,
                 created_by: Optional[str] = None,
                 id: Optional[int] = None,
                 original_task_id: str = "",
                 rerun_task_id: str = ""):
        self.action_id = action_id
        self.created_at = created_at or datetime.datetime.now()
        self.created_by = created_by
        self.id = id
        self.original_task_id = original_task_id
        self.rerun_task_id = rerun_task_id

class TaskResolutionDB:
    def __init__(self,
                 resolved: bool = False,
                 resolved_at: Optional[datetime.datetime] = None,
                 resolved_by: Optional[str] = None,
                 task_id: str = ""):
        self.resolved = resolved
        self.resolved_at = resolved_at
        self.resolved_by = resolved_by
        self.task_id = task_id

class TaskStepsDB:
    def __init__(self,
                 defined_at: Optional[datetime.datetime] = None,
                 steps: Optional[List[str]] = None,
                 task_id: str = "",
                 task_name: str = ""):
        self.defined_at = defined_at or datetime.datetime.now()
        self.steps = steps or []
        self.task_id = task_id
        self.task_name = task_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "defined_at": self.defined_at.isoformat() if self.defined_at else None,
            "steps": self.steps,
            "task_id": self.task_id,
            "task_name": self.task_name,
        }

class UserDB:
    def __init__(self,
                 avatar_url: str = "",
                 created_at: Optional[datetime.datetime] = None,
                 email: str = "",
                 id: Optional[int] = None,
                 is_active: bool = True,
                 last_login_at: Optional[datetime.datetime] = None,
                 name: str = "",
                 provider: str = "",
                 provider_account_id: str = "",
                 sessions: Optional[List[Any]] = None,
                 updated_at: Optional[datetime.datetime] = None):
        self.avatar_url = avatar_url
        self.created_at = created_at or datetime.datetime.now()
        self.email = email
        self.id = id
        self.is_active = is_active
        self.last_login_at = last_login_at
        self.name = name
        self.provider = provider
        self.provider_account_id = provider_account_id
        self.sessions = sessions or []
        self.updated_at = updated_at or datetime.datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "email": self.email,
            "id": self.id,
            "is_active": self.is_active,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "name": self.name,
            "provider": self.provider,
            "provider_account_id": self.provider_account_id,
            "sessions": [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.sessions],
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class UserSessionDB:
    def __init__(self,
                 access_token_expires_at: Optional[datetime.datetime] = None,
                 access_token_hash: str = "",
                 active_environment_id: Optional[int] = None,
                 auth_provider: str = "",
                 created_at: Optional[datetime.datetime] = None,
                 last_active: Optional[datetime.datetime] = None,
                 preferences: Optional[Dict[str, Any]] = None,
                 refresh_token_expires_at: Optional[datetime.datetime] = None,
                 refresh_token_hash: str = "",
                 session_id: str = "",
                 token_scopes: Optional[List[str]] = None,
                 user: Optional[UserDB] = None,
                 user_id: Optional[int] = None):
        self.access_token_expires_at = access_token_expires_at
        self.access_token_hash = access_token_hash
        self.active_environment_id = active_environment_id
        self.auth_provider = auth_provider
        self.created_at = created_at or datetime.datetime.now()
        self.last_active = last_active
        self.preferences = preferences or {}
        self.refresh_token_expires_at = refresh_token_expires_at
        self.refresh_token_hash = refresh_token_hash
        self.session_id = session_id
        self.token_scopes = token_scopes or []
        self.user = user
        self.user_id = user_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token_expires_at": self.access_token_expires_at.isoformat() if self.access_token_expires_at else None,
            "access_token_hash": self.access_token_hash,
            "active_environment_id": self.active_environment_id,
            "auth_provider": self.auth_provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "preferences": self.preferences,
            "refresh_token_expires_at": self.refresh_token_expires_at.isoformat() if self.refresh_token_expires_at else None,
            "refresh_token_hash": self.refresh_token_hash,
            "session_id": self.session_id,
            "token_scopes": self.token_scopes,
            "user_id": self.user_id,
        }

class WorkerEventDB:
    def __init__(self,
                 active_tasks: int = 0,
                 event_type: str = "",
                 hostname: str = "",
                 id: Optional[int] = None,
                 processed: int = 0,
                 status: str = "",
                 timestamp: Optional[datetime.datetime] = None):
        self.active_tasks = active_tasks
        self.event_type = event_type
        self.hostname = hostname
        self.id = id
        self.processed = processed
        self.status = status
        self.timestamp = timestamp or datetime.datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_tasks": self.active_tasks,
            "event_type": self.event_type,
            "hostname": self.hostname,
            "id": self.id,
            "processed": self.processed,
            "status": self.status,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

class WorkflowDB:
    def __init__(self,
                 actions: Optional[List[str]] = None,
                 circuit_breaker_config: Optional[Dict[str, Any]] = None,
                 conditions: Optional[Dict[str, Any]] = None,
                 cooldown_seconds: int = 0,
                 created_at: Optional[datetime.datetime] = None,
                 created_by: Optional[str] = None,
                 description: str = "",
                 enabled: bool = True,
                 execution_count: int = 0,
                 failure_count: int = 0,
                 id: Optional[int] = None,
                 last_executed_at: Optional[datetime.datetime] = None,
                 max_executions_per_hour: int = 0,
                 name: str = "",
                 priority: int = 0,
                 success_count: int = 0,
                 trigger_config: Optional[Dict[str, Any]] = None,
                 trigger_type: str = "",
                 updated_at: Optional[datetime.datetime] = None):
        self.actions = actions or []
        self.circuit_breaker_config = circuit_breaker_config or {}
        self.conditions = conditions or {}
        self.cooldown_seconds = cooldown_seconds
        self.created_at = created_at or datetime.datetime.now()
        self.created_by = created_by
        self.description = description
        self.enabled = enabled
        self.execution_count = execution_count
        self.failure_count = failure_count
        self.id = id
        self.last_executed_at = last_executed_at
        self.max_executions_per_hour = max_executions_per_hour
        self.name = name
        self.priority = priority
        self.success_count = success_count
        self.trigger_config = trigger_config or {}
        self.trigger_type = trigger_type
        self.updated_at = updated_at or datetime.datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actions": self.actions,
            "circuit_breaker_config": self.circuit_breaker_config,
            "conditions": self.conditions,
            "cooldown_seconds": self.cooldown_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "description": self.description,
            "enabled": self.enabled,
            "execution_count": self.execution_count,
            "failure_count": self.failure_count,
            "id": self.id,
            "last_executed_at": self.last_executed_at.isoformat() if self.last_executed_at else None,
            "max_executions_per_hour": self.max_executions_per_hour,
            "name": self.name,
            "priority": self.priority,
            "success_count": self.success_count,
            "trigger_config": self.trigger_config,
            "trigger_type": self.trigger_type,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class WorkflowExecutionDB:
    def __init__(self,
                 actions_executed: int = 0,
                 circuit_breaker_key: str = "",
                 completed_at: Optional[datetime.datetime] = None,
                 duration_ms: int = 0,
                 error_message: str = "",
                 id: Optional[int] = None,
                 stack_trace: Optional[str] = None,
                 started_at: Optional[datetime.datetime] = None,
                 status: str = "pending",
                 trigger_event: Optional[Dict[str, Any]] = None,
                 trigger_type: str = "",
                 triggered_at: Optional[datetime.datetime] = None,
                 workflow_id: Optional[int] = None,
                 workflow_snapshot: Optional[Dict[str, Any]] = None):
        self.actions_executed = actions_executed
        self.circuit_breaker_key = circuit_breaker_key
        self.completed_at = completed_at
        self.duration_ms = duration_ms
        self.error_message = error_message
        self.id = id
        self.stack_trace = stack_trace
        self.started_at = started_at
        self.status = status
        self.trigger_event = trigger_event or {}
        self.trigger_type = trigger_type
        self.triggered_at = triggered_at
        self.workflow_id = workflow_id
        self.workflow_snapshot = workflow_snapshot or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actions_executed": self.actions_executed,
            "circuit_breaker_key": self.circuit_breaker_key,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "id": self.id,
            "stack_trace": self.stack_trace,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "status": self.status,
            "trigger_event": self.trigger_event,
            "trigger_type": self.trigger_type,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "workflow_id": self.workflow_id,
            "workflow_snapshot": self.workflow_snapshot,
        }

# ---------------------------------------------------------------------------
# DatabaseManager
# ---------------------------------------------------------------------------

class DatabaseManager:
    """Provides database session management; symbols are stubs."""
    def __init__(self, database_url: str = "sqlite:///:memory:"):
        self.database_url = database_url
        self.engine: Any = None  # SQLAlchemy Engine or Mock
        self.SessionLocal: Any = None  # sessionmaker

    def get_session(self) -> Any:
        """Return a new DB session stub."""
        # In real code, this would create a SQLAlchemy session
        class DummySession:
            def close(self):
                pass
        return DummySession()

    def run_migrations(self):
        """Run database migrations (no-op here)."""
        pass

# ---------------------------------------------------------------------------
# CeleryEventMonitor
# ---------------------------------------------------------------------------

class CeleryEventMonitor:
    def __init__(self, app: Any = None, broker_url: str = ""):
        self.app = app
        self.broker_url = broker_url
        self.progress_callback: Optional[Callable[[TaskProgressEvent], None]] = None
        self.steps_callback: Optional[Callable[[TaskStepsEvent], None]] = None
        self.task_callback: Optional[Callable[[TaskEvent], None]] = None
        self.worker_callback: Optional[Callable[[WorkerEvent], None]] = None
        self.state = None
        self.workers: Dict[str, Dict[str, Any]] = {}  # hostname -> info
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def get_workers_info(self) -> Dict[str, Dict[str, Any]]:
        return self.workers

    def set_progress_callback(self, callback: Callable[[TaskProgressEvent], None]):
        self.progress_callback = callback

    def set_steps_callback(self, callback: Callable[[TaskStepsEvent], None]):
        self.steps_callback = callback

    def set_task_callback(self, callback: Callable[[TaskEvent], None]):
        self.task_callback = callback

    def set_worker_callback(self, callback: Callable[[WorkerEvent], None]):
        self.worker_callback = callback

    async def start_monitoring(self):
        """Starts a background loop that simulates receiving Celery events."""
        self._running = True
        # In a real implementation we would connect to Celery events
        # For this skeleton we just keep the flag.
        # If event occurs, call appropriate callbacks.
        pass

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

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

    async def connect(self, websocket: WebSocket):
        self.active_connections.append(websocket)
        self.client_filters[websocket] = {}
        self.client_modes[websocket] = "default"

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.client_filters.pop(websocket, None)
        self.client_modes.pop(websocket, None)

    async def queue_broadcast(self, task_event: TaskEvent):
        if self.message_queue:
            await self.message_queue.put(("task", task_event))

    async def queue_progress_broadcast(self, progress_event: TaskProgressEvent):
        if self.message_queue:
            await self.message_queue.put(("progress", progress_event))

    async def queue_task_action_broadcast(self, action_event: TaskActionEvent):
        if self.message_queue:
            await self.message_queue.put(("action", action_event))

    async def queue_worker_broadcast(self, worker_event: WorkerEvent):
        if self.message_queue:
            await self.message_queue.put(("worker", worker_event))

    async def send_personal_message(self, message: str, websocket: WebSocket):
        # In real code this would call websocket.send_text(message)
        pass

    def set_client_filters(self, websocket: WebSocket, filters: dict):
        self.client_filters[websocket] = filters

    def set_client_mode(self, websocket: WebSocket, mode: str):
        self.client_modes[websocket] = mode

    async def start_background_broadcaster(self):
        self.message_queue = asyncio.Queue()
        self._broadcaster_task = asyncio.create_task(self._broadcast_loop())

    async def _broadcast_loop(self):
        while True:
            event_type, event = await self.message_queue.get()
            # Simple broadcast: send to all active connections
            for ws in self.active_connections:
                # In reality we would serialize and send
                pass

    def stop_background_broadcaster(self):
        if self._broadcaster_task:
            self._broadcaster_task.cancel()
            self._broadcaster_task = None
        self.message_queue = None

# ---------------------------------------------------------------------------
# EventHandler
# ---------------------------------------------------------------------------

class EventHandler:
    def __init__(self, db_manager: DatabaseManager, connection_manager: ConnectionManager):
        self.db_manager = db_manager
        self.connection_manager = connection_manager
        self.workflow_engine = None  # placeholder

    async def handle_task_event(self, task_event: TaskEvent):
        # In real code, store in DB and broadcast
        await self.connection_manager.queue_broadcast(task_event)

    async def handle_progress_event(self, progress_event: TaskProgressEvent):
        await self.connection_manager.queue_progress_broadcast(progress_event)

    async def handle_steps_event(self, steps_event: TaskStepsEvent):
        # Broadcast steps event (no dedicated queue method, but can be added)
        pass

    async def handle_worker_event(self, worker_event: WorkerEvent):
        await self.connection_manager.queue_worker_broadcast(worker_event)

# ---------------------------------------------------------------------------
# ActionHandler (abstract base)
# ---------------------------------------------------------------------------

class ActionHandler(ABC):
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.monitor_instance: Optional[Any] = None
        self.session: Optional[Any] = None  # DB session

    @abstractmethod
    async def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        pass

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        pass

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        # Simple jinja-less template render using str.format
        try:
            return template.format(**context)
        except KeyError as e:
            return f"Error: missing key {e}"

# ---------------------------------------------------------------------------
# RetryActionHandler
# ---------------------------------------------------------------------------

class RetryActionHandler(ActionHandler):
    async def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        # Implementation would retry a task
        return ActionResult(success=True, message="Retry action executed", data={"context": context, "params": params})

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        # e.g., check required keys
        required = ["task_id"]
        for key in required:
            if key not in params:
                return False, f"Missing parameter: {key}"
        return True, ""

# ---------------------------------------------------------------------------
# SlackActionHandler
# ---------------------------------------------------------------------------

class SlackActionHandler(ActionHandler):
    async def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        # Implementation would send a Slack message
        return ActionResult(success=True, message="Slack notification sent", data={"context": context, "params": params})

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        required = ["channel", "text"]
        for key in required:
            if key not in params:
                return False, f"Missing parameter: {key}"
        return True, ""

# ---------------------------------------------------------------------------
# End of implementation
# ---------------------------------------------------------------------------