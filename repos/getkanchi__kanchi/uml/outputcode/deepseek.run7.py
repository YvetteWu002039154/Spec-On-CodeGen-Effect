from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import asyncio
from starlette.websockets import WebSocket


# Stub event classes
@dataclass
class TaskProgressEvent:
    pass

@dataclass
class TaskStepsEvent:
    pass

@dataclass
class TaskEvent:
    pass

@dataclass
class WorkerEvent:
    pass

@dataclass
class ActionResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Database model dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ActionConfigDB:
    action_type: str
    config: Dict[str, Any]
    created_at: datetime
    created_by: str
    description: str
    id: int
    last_used_at: Optional[datetime]
    name: str
    updated_at: datetime
    usage_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "config": self.config,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "description": self.description,
            "id": self.id,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "name": self.name,
            "updated_at": self.updated_at.isoformat(),
            "usage_count": self.usage_count,
        }

@dataclass
class AppSettingDB:
    category: str
    created_at: datetime
    description: str
    key: str
    label: str
    updated_at: datetime
    value: str
    value_type: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "key": self.key,
            "label": self.label,
            "updated_at": self.updated_at.isoformat(),
            "value": self.value,
            "value_type": self.value_type,
        }

@dataclass
class EnvironmentDB:
    created_at: datetime
    description: str
    id: int
    is_active: bool
    is_default: bool
    name: str
    queue_patterns: str
    updated_at: datetime
    worker_patterns: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "id": self.id,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "name": self.name,
            "queue_patterns": self.queue_patterns,
            "updated_at": self.updated_at.isoformat(),
            "worker_patterns": self.worker_patterns,
        }

@dataclass
class RetryRelationshipDB:
    created_at: datetime
    id: int
    original_id: str
    retry_chain: List[str]
    task_id: str
    total_retries: int
    updated_at: datetime

@dataclass
class TaskActionItemDB:
    action_id: int
    attempted_task_id: str
    created_at: datetime
    id: int
    original_task_id: str
    original_task_name: str
    outcome: str
    reason: str
    reason_code: str
    rerun_kind: str
    rerun_task_id: Optional[str]
    rerun_task_name: Optional[str]
    review_fingerprint: str
    skip_category: str
    submitted_args: Any
    submitted_kwargs: Any
    target_queue: str
    updated_at: datetime
    action: TaskActionDB = field(init=False)  # will be set by parent

@dataclass
class TaskActionDB:
    action_type: str
    completed_at: Optional[datetime]
    created_at: datetime
    id: int
    initiated_by: str
    initiated_by_user_id: int
    initiated_session_id: str
    item_changed: int
    item_created: int
    item_failed: int
    item_noop: int
    item_skipped: int
    item_total: int
    selection_size: int
    started_at: Optional[datetime]
    status: str
    summary: str
    items: List[TaskActionItemDB] = field(default_factory=list)
    original_task_ids: List[str] = field(default_factory=list)

@dataclass
class TaskDailyStatsDB:
    avg_runtime: float
    created_at: datetime
    date: datetime
    failed: int
    first_execution: datetime
    id: int
    last_execution: datetime
    max_runtime: float
    min_runtime: float
    orphaned: int
    p50_runtime: float
    p95_runtime: float
    p99_runtime: float
    pending: int
    retried: int
    revoked: int
    succeeded: int
    task_name: str
    total_executions: int
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avg_runtime": self.avg_runtime,
            "created_at": self.created_at.isoformat(),
            "date": self.date.isoformat(),
            "failed": self.failed,
            "first_execution": self.first_execution.isoformat(),
            "id": self.id,
            "last_execution": self.last_execution.isoformat(),
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
            "updated_at": self.updated_at.isoformat(),
        }

@dataclass
class TaskEventDB:
    args: Any
    eta: Optional[datetime]
    event_type: str
    exception: Optional[str]
    exchange: str
    expires: Optional[datetime]
    has_retries: bool
    hostname: str
    id: int
    is_orphan: bool
    is_retry: bool
    kwargs: Any
    orphaned_at: Optional[datetime]
    parent_id: Optional[str]
    queue: str
    result: Any
    retried_by: Optional[str]
    retries: int
    retry_count: int
    retry_of: Optional[str]
    root_id: str
    routing_key: str
    runtime: float
    task_id: str
    task_name: str
    timestamp: datetime
    traceback: Optional[str]
    worker_name: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "args": self.args,
            "eta": self.eta.isoformat() if self.eta else None,
            "event_type": self.event_type,
            "exception": self.exception,
            "exchange": self.exchange,
            "expires": self.expires.isoformat() if self.expires else None,
            "has_retries": self.has_retries,
            "hostname": self.hostname,
            "id": self.id,
            "is_orphan": self.is_orphan,
            "is_retry": self.is_retry,
            "kwargs": self.kwargs,
            "orphaned_at": self.orphaned_at.isoformat() if self.orphaned_at else None,
            "parent_id": self.parent_id,
            "queue": self.queue,
            "result": self.result,
            "retried_by": self.retried_by,
            "retries": self.retries,
            "retry_count": self.retry_count,
            "retry_of": self.retry_of,
            "root_id": self.root_id,
            "routing_key": self.routing_key,
            "runtime": self.runtime,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "timestamp": self.timestamp.isoformat(),
            "traceback": self.traceback,
            "worker_name": self.worker_name,
        }

@dataclass
class TaskLatestDB:
    args: Any
    eta: Optional[datetime]
    event_id: int
    event_type: str
    exception: Optional[str]
    exchange: str
    expires: Optional[datetime]
    has_retries: bool
    hostname: str
    is_orphan: bool
    is_retry: bool
    kwargs: Any
    orphaned_at: Optional[datetime]
    parent_id: Optional[str]
    queue: str
    resolved: bool
    resolved_at: Optional[datetime]
    resolved_by: Optional[str]
    result: Any
    retried_by: Optional[str]
    retries: int
    retry_count: int
    retry_of: Optional[str]
    root_id: str
    routing_key: str
    runtime: float
    task_id: str
    task_name: str
    timestamp: datetime
    traceback: Optional[str]
    worker_name: str

@dataclass
class TaskProgressDB:
    id: int
    message: str
    meta: Dict[str, Any]
    progress: int
    step_key: str
    task_id: str
    task_name: str
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "message": self.message,
            "meta": self.meta,
            "progress": self.progress,
            "step_key": self.step_key,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "timestamp": self.timestamp.isoformat(),
        }

@dataclass
class TaskProgressLatestDB:
    message: str
    meta: Dict[str, Any]
    progress: int
    step_key: str
    task_id: str
    task_name: str
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "meta": self.meta,
            "progress": self.progress,
            "step_key": self.step_key,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "updated_at": self.updated_at.isoformat(),
        }

@dataclass
class TaskRegistryDB:
    created_at: datetime
    description: str
    first_seen: datetime
    human_readable_name: str
    id: int
    last_seen: datetime
    name: str
    tags: List[str]
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "first_seen": self.first_seen.isoformat(),
            "human_readable_name": self.human_readable_name,
            "id": self.id,
            "last_seen": self.last_seen.isoformat(),
            "name": self.name,
            "tags": self.tags,
            "updated_at": self.updated_at.isoformat(),
        }

@dataclass
class TaskRerunRelationshipDB:
    action_id: int
    created_at: datetime
    created_by: str
    id: int
    original_task_id: str
    rerun_task_id: str

@dataclass
class TaskResolutionDB:
    resolved: bool
    resolved_at: datetime
    resolved_by: str
    task_id: str

@dataclass
class TaskStepsDB:
    defined_at: datetime
    steps: List[Dict[str, Any]]
    task_id: str
    task_name: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "defined_at": self.defined_at.isoformat(),
            "steps": self.steps,
            "task_id": self.task_id,
            "task_name": self.task_name,
        }

@dataclass
class UserSessionDB:
    access_token_expires_at: datetime
    access_token_hash: str
    active_environment_id: int
    auth_provider: str
    created_at: datetime
    last_active: datetime
    preferences: Dict[str, Any]
    refresh_token_expires_at: datetime
    refresh_token_hash: str
    session_id: str
    token_scopes: List[str]
    user_id: int
    user: UserDB = field(init=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token_expires_at": self.access_token_expires_at.isoformat(),
            "access_token_hash": self.access_token_hash,
            "active_environment_id": self.active_environment_id,
            "auth_provider": self.auth_provider,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "preferences": self.preferences,
            "refresh_token_expires_at": self.refresh_token_expires_at.isoformat(),
            "refresh_token_hash": self.refresh_token_hash,
            "session_id": self.session_id,
            "token_scopes": self.token_scopes,
            "user_id": self.user_id,
        }

@dataclass
class UserDB:
    avatar_url: Optional[str]
    created_at: datetime
    email: str
    id: int
    is_active: bool
    last_login_at: Optional[datetime]
    name: str
    provider: str
    provider_account_id: str
    updated_at: datetime
    sessions: List[UserSessionDB] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat(),
            "email": self.email,
            "id": self.id,
            "is_active": self.is_active,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "name": self.name,
            "provider": self.provider,
            "provider_account_id": self.provider_account_id,
            "sessions": [s.to_dict() for s in self.sessions],
            "updated_at": self.updated_at.isoformat(),
        }

@dataclass
class WorkerEventDB:
    active_tasks: List[str]
    event_type: str
    hostname: str
    id: int
    processed: int
    status: str
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_tasks": self.active_tasks,
            "event_type": self.event_type,
            "hostname": self.hostname,
            "id": self.id,
            "processed": self.processed,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
        }

@dataclass
class WorkflowDB:
    actions: List[Any]
    circuit_breaker_config: Dict[str, Any]
    conditions: Dict[str, Any]
    cooldown_seconds: int
    created_at: datetime
    created_by: str
    description: str
    enabled: bool
    execution_count: int
    failure_count: int
    id: int
    last_executed_at: Optional[datetime]
    max_executions_per_hour: int
    name: str
    priority: int
    success_count: int
    trigger_config: Dict[str, Any]
    trigger_type: str
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actions": self.actions,
            "circuit_breaker_config": self.circuit_breaker_config,
            "conditions": self.conditions,
            "cooldown_seconds": self.cooldown_seconds,
            "created_at": self.created_at.isoformat(),
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
            "updated_at": self.updated_at.isoformat(),
        }

@dataclass
class WorkflowExecutionDB:
    actions_executed: int
    circuit_breaker_key: str
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    error_message: Optional[str]
    id: int
    stack_trace: Optional[str]
    started_at: datetime
    status: str
    trigger_event: Dict[str, Any]
    trigger_type: str
    triggered_at: datetime
    workflow_id: int
    workflow_snapshot: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actions_executed": self.actions_executed,
            "circuit_breaker_key": self.circuit_breaker_key,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "error_message": self.error_message,
            "id": self.id,
            "stack_trace": self.stack_trace,
            "started_at": self.started_at.isoformat(),
            "status": self.status,
            "trigger_event": self.trigger_event,
            "trigger_type": self.trigger_type,
            "triggered_at": self.triggered_at.isoformat(),
            "workflow_id": self.workflow_id,
            "workflow_snapshot": self.workflow_snapshot,
        }


# Forward declare CeleryEventMonitor for type hint
class CeleryEventMonitor:
    pass

# ---------------------------------------------------------------------------
# Service classes
# ---------------------------------------------------------------------------

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine: Any = None
        self.SessionLocal: Any = None

    def get_session(self) -> Any:
        if self.SessionLocal:
            return self.SessionLocal()
        raise NotImplementedError("SessionLocal not set")

    def run_migrations(self):
        pass


class ActionHandler(ABC):
    def __init__(self, db_manager: DatabaseManager, monitor_instance: Optional[CeleryEventMonitor] = None, session: Any = None):
        self.db_manager = db_manager
        self.monitor_instance = monitor_instance
        self.session = session

    @abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        ...

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        return template.format(**context)

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        ...


class RetroActionHandler(ActionHandler):
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        return ActionResult(success=True, message="Retry action executed")

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        return True, ""


class SlackActionHandler(ActionHandler):
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        return ActionResult(success=True, message="Slack message sent")

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        return True, ""


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_filters: Dict[WebSocket, dict] = {}
        self.client_modes: Dict[WebSocket, str] = {}
        self.message_queue: Optional[asyncio.Queue] = None
        self._broadcast_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_filters[websocket] = {}
        self.client_modes[websocket] = "default"

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.client_filters.pop(websocket, None)
            self.client_modes.pop(websocket, None)

    async def queue_broadcast(self, task_event: TaskEvent):
        if self.message_queue is not None:
            await self.message_queue.put(("task_event", task_event))

    async def queue_progress_broadcast(self, progress_event):
        if self.message_queue is not None:
            await self.message_queue.put(("progress_event", progress_event))

    async def queue_task_action_broadcast(self, action_event):
        if self.message_queue is not None:
            await self.message_queue.put(("task_action", action_event))

    async def queue_worker_broadcast(self, worker_event: WorkerEvent):
        if self.message_queue is not None:
            await self.message_queue.put(("worker_event", worker_event))

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    def set_client_filters(self, websocket: WebSocket, filters: dict):
        self.client_filters[websocket] = filters

    def set_client_mode(self, websocket: WebSocket, mode: str):
        self.client_modes[websocket] = mode

    async def start_background_broadcaster(self):
        self.message_queue = asyncio.Queue()
        self._broadcast_task = asyncio.create_task(self._broadcaster())

    async def _broadcaster(self):
        while True:
            msg = await self.message_queue.get()
            for ws in self.active_connections:
                try:
                    await ws.send_json(msg)
                except Exception:
                    pass

    async def stop_background_broadcaster(self):
        if self._broadcast_task:
            self._broadcast_task.cancel()
            self._broadcast_task = None
            self.message_queue = None


class EventHandler:
    def __init__(self, connection_manager: ConnectionManager, db_manager: DatabaseManager, workflow_engine: Any = None):
        self.connection_manager = connection_manager
        self.db_manager = db_manager
        self.workflow_engine = workflow_engine

    def handle_progress_event(self, progress_event):
        pass

    def handle_steps_event(self, steps_event):
        pass

    def handle_task_event(self, task_event: TaskEvent):
        pass

    def handle_worker_event(self, worker_event: WorkerEvent):
        pass


class CeleryEventMonitor:
    def __init__(self, app: Any, broker_url: str):
        self.app = app
        self.broker_url = broker_url
        self.state: Any = None
        self.progress_callback: Optional[Callable[[TaskProgressEvent], None]] = None
        self.steps_callback: Optional[Callable[[TaskStepsEvent], None]] = None
        self.task_callback: Optional[Callable[[TaskEvent], None]] = None
        self.worker_callback: Optional[Callable[[WorkerEvent], None]] = None
        self.workers: Dict[str, Dict[str, Any]] = {}

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

    def start_monitoring(self):
        pass

    def stop(self):
        pass