import asyncio
import json
import string
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    JSON, String, Text, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from fastapi import WebSocket

from celery import Celery
from celery.events import EventReceiver
from celery.events.state import State

Base = declarative_base()


class ActionResult:
    def __init__(self, success: bool, message: str, data: Optional[Dict] = None):
        self.success = success
        self.message = message
        self.data = data


class TaskProgressEvent:
    def __init__(self, task_id: str, task_name: str, progress: float, message: str, step_key: str, meta: Optional[Dict] = None):
        self.task_id = task_id
        self.task_name = task_name
        self.progress = progress
        self.message = message
        self.step_key = step_key
        self.meta = meta


class TaskStepsEvent:
    def __init__(self, task_id: str, task_name: str, steps: Any, defined_at: datetime):
        self.task_id = task_id
        self.task_name = task_name
        self.steps = steps
        self.defined_at = defined_at


class TaskEvent:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class WorkerEvent:
    def __init__(self, hostname: str, status: str, active_tasks: int, processed: int, timestamp: datetime):
        self.hostname = hostname
        self.status = status
        self.active_tasks = active_tasks
        self.processed = processed
        self.timestamp = timestamp


class ActionConfigDB(Base):
    __tablename__ = "action_config"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    action_type = Column(String, nullable=False)
    config = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "action_type": self.action_type,
            "config": self.config,
            "description": self.description,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AppSettingDB(Base):
    __tablename__ = "app_setting"
    key = Column(String, primary_key=True)
    value = Column(Text, nullable=True)
    value_type = Column(String, nullable=False)
    label = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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


class EnvironmentDB(Base):
    __tablename__ = "environment"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    queue_patterns = Column(JSON, nullable=True)
    worker_patterns = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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


class TaskDailyStatsDB(Base):
    __tablename__ = "task_daily_stats"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    task_name = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    total_executions = Column(Integer, default=0)
    succeeded = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    retried = Column(Integer, default=0)
    revoked = Column(Integer, default=0)
    pending = Column(Integer, default=0)
    orphaned = Column(Integer, default=0)
    avg_runtime = Column(Float, default=0.0)
    min_runtime = Column(Float, default=0.0)
    max_runtime = Column(Float, default=0.0)
    p50_runtime = Column(Float, default=0.0)
    p95_runtime = Column(Float, default=0.0)
    p99_runtime = Column(Float, default=0.0)
    first_execution = Column(DateTime, nullable=True)
    last_execution = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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


class TaskEventDB(Base):
    __tablename__ = "task_event"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    task_id = Column(String, nullable=False)
    task_name = Column(String, nullable=True)
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    args = Column(JSON, nullable=True)
    kwargs = Column(JSON, nullable=True)
    result = Column(Text, nullable=True)
    exception = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)
    hostname = Column(String, nullable=True)
    worker_name = Column(String, nullable=True)
    retries = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    queue = Column(String, nullable=True)
    exchange = Column(String, nullable=True)
    routing_key = Column(String, nullable=True)
    eta = Column(DateTime, nullable=True)
    expires = Column(DateTime, nullable=True)
    parent_id = Column(String, nullable=True)
    root_id = Column(String, nullable=True)
    retry_of = Column(String, nullable=True)
    retried_by = Column(String, nullable=True)
    is_retry = Column(Boolean, default=False)
    has_retries = Column(Boolean, default=False)
    is_orphan = Column(Boolean, default=False)
    orphaned_at = Column(DateTime, nullable=True)
    runtime = Column(Float, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "args": self.args,
            "kwargs": self.kwargs,
            "result": self.result,
            "exception": self.exception,
            "traceback": self.traceback,
            "hostname": self.hostname,
            "worker_name": self.worker_name,
            "retries": self.retries,
            "retry_count": self.retry_count,
            "queue": self.queue,
            "exchange": self.exchange,
            "routing_key": self.routing_key,
            "eta": self.eta.isoformat() if self.eta else None,
            "expires": self.expires.isoformat() if self.expires else None,
            "parent_id": self.parent_id,
            "root_id": self.root_id,
            "retry_of": self.retry_of,
            "retried_by": self.retried_by,
            "is_retry": self.is_retry,
            "has_retries": self.has_retries,
            "is_orphan": self.is_orphan,
            "orphaned_at": self.orphaned_at.isoformat() if self.orphaned_at else None,
            "runtime": self.runtime,
        }


class TaskLatestDB(Base):
    __tablename__ = "task_latest"
    task_id = Column(String, primary_key=True)
    event_id = Column(String, ForeignKey("task_event.id"), nullable=True)
    task_name = Column(String, nullable=True)
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=True)
    args = Column(JSON, nullable=True)
    kwargs = Column(JSON, nullable=True)
    result = Column(Text, nullable=True)
    exception = Column(Text, nullable=True)
    traceback = Column(Text, nullable=True)
    hostname = Column(String, nullable=True)
    worker_name = Column(String, nullable=True)
    retries = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    queue = Column(String, nullable=True)
    exchange = Column(String, nullable=True)
    routing_key = Column(String, nullable=True)
    eta = Column(DateTime, nullable=True)
    expires = Column(DateTime, nullable=True)
    parent_id = Column(String, nullable=True)
    root_id = Column(String, nullable=True)
    retry_of = Column(String, nullable=True)
    retried_by = Column(String, nullable=True)
    is_retry = Column(Boolean, default=False)
    has_retries = Column(Boolean, default=False)
    is_orphan = Column(Boolean, default=False)
    orphaned_at = Column(DateTime, nullable=True)
    runtime = Column(Float, nullable=True)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)


class TaskProgressDB(Base):
    __tablename__ = "task_progress"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    task_id = Column(String, nullable=False)
    task_name = Column(String, nullable=True)
    progress = Column(Float, default=0.0)
    message = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)
    step_key = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "progress": self.progress,
            "message": self.message,
            "meta": self.meta,
            "step_key": self.step_key,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class TaskProgressLatestDB(Base):
    __tablename__ = "task_progress_latest"
    task_id = Column(String, primary_key=True)
    task_name = Column(String, nullable=True)
    progress = Column(Float, default=0.0)
    message = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)
    step_key = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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


class TaskRegistryDB(Base):
    __tablename__ = "task_registry"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False, unique=True)
    human_readable_name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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


class TaskActionDB(Base):
    __tablename__ = "task_action"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    action_type = Column(String, nullable=False)
    status = Column(String, default="pending")
    summary = Column(Text, nullable=True)
    items = Column(JSON, nullable=True)
    item_total = Column(Integer, default=0)
    item_skipped = Column(Integer, default=0)
    item_changed = Column(Integer, default=0)
    item_failed = Column(Integer, default=0)
    item_noop = Column(Integer, default=0)
    item_created = Column(Integer, default=0)
    original_task_ids = Column(JSON, nullable=True)
    selection_size = Column(Integer, nullable=True)
    initiated_by = Column(String, nullable=True)
    initiated_by_user_id = Column(String, nullable=True)
    initiated_session_id = Column(String, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class TaskActionItemDB(Base):
    __tablename__ = "task_action_item"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    action_id = Column(String, ForeignKey("task_action.id"), nullable=False)
    original_task_id = Column(String, nullable=False)
    original_task_name = Column(String, nullable=True)
    attempted_task_id = Column(String, nullable=True)
    outcome = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    reason_code = Column(String, nullable=True)
    skip_category = Column(String, nullable=True)
    rerun_kind = Column(String, nullable=True)
    rerun_task_id = Column(String, nullable=True)
    rerun_task_name = Column(String, nullable=True)
    submitted_args = Column(JSON, nullable=True)
    submitted_kwargs = Column(JSON, nullable=True)
    target_queue = Column(String, nullable=True)
    review_fingerprint = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    action = None


class TaskRerunRelationshipDB(Base):
    __tablename__ = "task_rerun_relationship"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    action_id = Column(String, nullable=False)
    original_task_id = Column(String, nullable=False)
    rerun_task_id = Column(String, nullable=False)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RetryRelationshipDB(Base):
    __tablename__ = "retry_relationship"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    task_id = Column(String, nullable=False)
    original_id = Column(String, nullable=True)
    total_retries = Column(Integer, default=0)
    retry_chain = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskResolutionDB(Base):
    __tablename__ = "task_resolution"
    task_id = Column(String, primary_key=True)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, nullable=True)


class TaskStepsDB(Base):
    __tablename__ = "task_steps"
    task_id = Column(String, primary_key=True)
    task_name = Column(String, nullable=True)
    steps = Column(JSON, nullable=True)
    defined_at = Column(DateTime, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "steps": self.steps,
            "defined_at": self.defined_at.isoformat() if self.defined_at else None,
        }


class UserDB(Base):
    __tablename__ = "user"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, nullable=True, unique=True)
    avatar_url = Column(Text, nullable=True)
    provider = Column(String, nullable=True)
    provider_account_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime, nullable=True)
    sessions = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
            "sessions": self.sessions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserSessionDB(Base):
    __tablename__ = "user_session"
    session_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("user.id"), nullable=False)
    access_token_hash = Column(String, nullable=True)
    refresh_token_hash = Column(String, nullable=True)
    access_token_expires_at = Column(DateTime, nullable=True)
    refresh_token_expires_at = Column(DateTime, nullable=True)
    auth_provider = Column(String, nullable=True)
    token_scopes = Column(JSON, nullable=True)
    active_environment_id = Column(String, nullable=True)
    preferences = Column(JSON, nullable=True)
    last_active = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "access_token_hash": self.access_token_hash,
            "refresh_token_hash": self.refresh_token_hash,
            "access_token_expires_at": self.access_token_expires_at.isoformat() if self.access_token_expires_at else None,
            "refresh_token_expires_at": self.refresh_token_expires_at.isoformat() if self.refresh_token_expires_at else None,
            "auth_provider": self.auth_provider,
            "token_scopes": self.token_scopes,
            "active_environment_id": self.active_environment_id,
            "preferences": self.preferences,
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WorkerEventDB(Base):
    __tablename__ = "worker_event"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    hostname = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    status = Column(String, nullable=True)
    active_tasks = Column(Integer, default=0)
    processed = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)

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


class WorkflowDB(Base):
    __tablename__ = "workflow"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    trigger_type = Column(String, nullable=False)
    trigger_config = Column(JSON, nullable=True)
    conditions = Column(JSON, nullable=True)
    actions = Column(JSON, nullable=True)
    priority = Column(Integer, default=0)
    cooldown_seconds = Column(Integer, default=0)
    max_executions_per_hour = Column(Integer, default=0)
    circuit_breaker_config = Column(JSON, nullable=True)
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_executed_at = Column(DateTime, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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


class WorkflowExecutionDB(Base):
    __tablename__ = "workflow_execution"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    workflow_id = Column(String, ForeignKey("workflow.id"), nullable=False)
    trigger_type = Column(String, nullable=False)
    trigger_event = Column(JSON, nullable=True)
    status = Column(String, default="pending")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    actions_executed = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)
    circuit_breaker_key = Column(String, nullable=True)
    workflow_snapshot = Column(JSON, nullable=True)
    triggered_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "trigger_type": self.trigger_type,
            "trigger_event": self.trigger_event,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "actions_executed": self.actions_executed,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "circuit_breaker_key": self.circuit_breaker_key,
            "workflow_snapshot": self.workflow_snapshot,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
        }


class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine: Optional[Engine] = None
        self.SessionLocal: sessionmaker = None

    def run_migrations(self):
        if self.engine is None:
            self.engine = create_engine(self.database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_session(self) -> Session:
        if self.SessionLocal is None:
            raise RuntimeError("DatabaseManager not initialized. Call run_migrations first.")
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()


class ActionHandler(ABC):
    def __init__(self, db_manager: DatabaseManager, session: Session, monitor_instance: Optional[Any] = None):
        self.db_manager = db_manager
        self.session = session
        self.monitor_instance = monitor_instance

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        return string.Template(template).safe_substitute(context)

    @abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        pass

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        pass


class RetryActionHandler(ActionHandler):
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        valid, msg = self.validate_params(params)
        if not valid:
            return ActionResult(False, msg)
        task_id = context.get("task_id")
        if not task_id:
            return ActionResult(False, "Missing task_id in context")
        return ActionResult(True, f"Retry action initiated for task {task_id}", {"task_id": task_id})

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "max_retries" in params and (not isinstance(params["max_retries"], int) or params["max_retries"] < 0):
            return False, "max_retries must be a non-negative integer"
        return True, ""


class SlackActionHandler(ActionHandler):
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        valid, msg = self.validate_params(params)
        if not valid:
            return ActionResult(False, msg)
        webhook_url = params.get("webhook_url")
        message = params.get("message", "No message provided")
        if not webhook_url:
            return ActionResult(False, "Missing webhook_url")
        return ActionResult(True, "Slack notification enqueued", {"webhook_url": webhook_url})

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "webhook_url" not in params:
            return False, "webhook_url is required"
        if not isinstance(params["webhook_url"], str):
            return False, "webhook_url must be a string"
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
        self.client_modes[websocket] = "events"

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.client_filters.pop(websocket, None)
            self.client_modes.pop(websocket, None)

    def set_client_filters(self, websocket: WebSocket, filters: dict):
        if websocket in self.active_connections:
            self.client_filters[websocket] = filters

    def set_client_mode(self, websocket: WebSocket, mode: str):
        if websocket in self.active_connections:
            self.client_modes[websocket] = mode

    async def send_personal_message(self, message: str, websocket: WebSocket):
        if websocket in self.active_connections:
            await websocket.send_text(message)

    def queue_broadcast(self, task_event: TaskEvent):
        if self.message_queue is not None:
            self.message_queue.put_nowait(
                {"type": "task_event", "payload": task_event.__dict__}
            )

    def queue_progress_broadcast(self, progress_event: TaskProgressEvent):
        if self.message_queue is not None:
            self.message_queue.put_nowait(
                {"type": "progress_event", "payload": vars(progress_event)}
            )

    def queue_task_action_broadcast(self, action_event):
        if self.message_queue is not None:
            self.message_queue.put_nowait(
                {"type": "task_action", "payload": action_event}
            )

    def queue_worker_broadcast(self, worker_event: WorkerEvent):
        if self.message_queue is not None:
            self.message_queue.put_nowait(
                {"type": "worker_event", "payload": vars(worker_event)}
            )

    async def start_background_broadcaster(self):
        if self.message_queue is None:
            self.message_queue = asyncio.Queue()
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())

    async def _broadcast_loop(self):
        while True:
            try:
                msg = await self.message_queue.get()
                payload = msg["payload"]
                json_msg = json.dumps(payload, default=str)
                disconnected = []
                for ws in self.active_connections:
                    try:
                        await ws.send_text(json_msg)
                    except Exception:
                        disconnected.append(ws)
                for ws in disconnected:
                    self.disconnect(ws)
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def stop_background_broadcaster(self):
        if self._broadcast_task is not None:
            self._broadcast_task.cancel()
        self._broadcast_task = None
        self.message_queue = None


class CeleryEventMonitor:
    def __init__(self, app: Celery, broker_url: str,
                 progress_callback: Optional[Callable[[TaskProgressEvent], None]] = None,
                 steps_callback: Optional[Callable[[TaskStepsEvent], None]] = None,
                 task_callback: Optional[Callable[[TaskEvent], None]] = None,
                 worker_callback: Optional[Callable[[WorkerEvent], None]] = None):
        self.app = app
        self.broker_url = broker_url
        self.progress_callback = progress_callback
        self.steps_callback = steps_callback
        self.task_callback = task_callback
        self.worker_callback = worker_callback
        self.state: Optional[State] = None
        self.workers: Dict[str, Dict[str, Any]] = {}
        self._receiver: Optional[EventReceiver] = None
        self._monitor_thread = None

    def set_progress_callback(self, callback: Callable[[TaskProgressEvent], None]):
        self.progress_callback = callback

    def set_steps_callback(self, callback: Callable[[TaskStepsEvent], None]):
        self.steps_callback = callback

    def set_task_callback(self, callback: Callable[[TaskEvent], None]):
        self.task_callback = callback

    def set_worker_callback(self, callback: Callable[[WorkerEvent], None]):
        self.worker_callback = callback

    def start_monitoring(self):
        self.state = self.app.events.State()
        self._receiver = self.app.events.Receiver(None, handlers={
            'task-sent': self._handle_event,
            'task-received': self._handle_event,
            'task-started': self._handle_event,
            'task-succeeded': self._handle_event,
            'task-failed': self._handle_event,
            'task-rejected': self._handle_event,
            'task-revoked': self._handle_event,
            'task-retried': self._handle_event,
            'worker-online': self._handle_event,
            'worker-offline': self._handle_event,
            'worker-heartbeat': self._handle_event,
        })
        import threading
        self._monitor_thread = threading.Thread(target=self._receiver.capture, daemon=True)
        self._monitor_thread.start()

    def _handle_event(self, event):
        if self.state is not None:
            self.state.event(event)

        event_type = event.get('type')
        task_id = event.get('uuid')
        hostname = event.get('hostname')
        timestamp = event.get('timestamp')

        if event_type in ['worker-online', 'worker-offline', 'worker-heartbeat']:
            # Build WorkerEvent
            worker_event = WorkerEvent(
                hostname=hostname,
                status=event_type.replace('worker-', ''),
                active_tasks=0,
                processed=0,
                timestamp=datetime.fromtimestamp(timestamp)
            )
            if self.worker_callback:
                self.worker_callback(worker_event)
            # Update self.workers dict
            self.workers[hostname] = {
                'status': event_type,
                'timestamp': timestamp
            }
        else:
            task_event = TaskEvent(**event)
            if self.task_callback:
                self.task_callback(task_event)

    def stop(self):
        if self._receiver:
            self._receiver.should_stop = True
        self._receiver = None
        self.state = None

    def get_workers_info(self) -> Dict[str, Dict[str, Any]]:
        return self.workers


class EventHandler:
    def __init__(self, connection_manager: ConnectionManager, db_manager: DatabaseManager,
                 workflow_engine: Optional[Any] = None):
        self.connection_manager = connection_manager
        self.db_manager = db_manager
        self.workflow_engine = workflow_engine

    def handle_task_event(self, task_event: TaskEvent):
        self.connection_manager.queue_broadcast(task_event)

    def handle_worker_event(self, worker_event: WorkerEvent):
        self.connection_manager.queue_worker_broadcast(worker_event)

    def handle_progress_event(self, progress_event: TaskProgressEvent):
        self.connection_manager.queue_progress_broadcast(progress_event)

    def handle_steps_event(self, steps_event: TaskStepsEvent):
        pass