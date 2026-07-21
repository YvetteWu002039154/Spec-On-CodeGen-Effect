from __future__ import annotations

import asyncio
import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, JSON
    from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
    from sqlalchemy.engine import Engine
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    Engine = None

try:
    from fastapi import WebSocket
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    WebSocket = Any


# ---------------------------------------------------------------------------
# Event / result data classes
# ---------------------------------------------------------------------------

@dataclass
class TaskEvent:
    task_id: str = ""
    task_name: str = ""
    event_type: str = ""
    hostname: str = ""
    timestamp: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkerEvent:
    hostname: str = ""
    event_type: str = ""
    status: str = ""
    timestamp: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskProgressEvent:
    task_id: str = ""
    task_name: str = ""
    progress: float = 0.0
    message: str = ""
    step_key: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None


@dataclass
class TaskStepsEvent:
    task_id: str = ""
    task_name: str = ""
    steps: Any = None
    defined_at: Optional[datetime] = None


@dataclass
class ActionResult:
    success: bool = False
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Database models
# ---------------------------------------------------------------------------

if SQLALCHEMY_AVAILABLE:
    Base = declarative_base()

    class ActionConfigDB(Base):
        __tablename__ = "action_configs"

        id = Column(Integer, primary_key=True)
        name = Column(String, nullable=False)
        action_type = Column(String, nullable=False)
        config = Column(JSON, nullable=True)
        description = Column(Text, nullable=True)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)
        created_by = Column(String, nullable=True)
        last_used_at = Column(DateTime, nullable=True)
        usage_count = Column(Integer, default=0)

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "name": self.name,
                "action_type": self.action_type,
                "config": self.config,
                "description": self.description,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "created_by": self.created_by,
                "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
                "usage_count": self.usage_count,
            }

    class AppSettingDB(Base):
        __tablename__ = "app_settings"

        key = Column(String, primary_key=True)
        value = Column(Text, nullable=True)
        value_type = Column(String, nullable=True)
        category = Column(String, nullable=True)
        label = Column(String, nullable=True)
        description = Column(Text, nullable=True)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)

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

    class EnvironmentDB(Base):
        __tablename__ = "environments"

        id = Column(Integer, primary_key=True)
        name = Column(String, nullable=False)
        description = Column(Text, nullable=True)
        is_active = Column(Boolean, default=True)
        is_default = Column(Boolean, default=False)
        queue_patterns = Column(JSON, nullable=True)
        worker_patterns = Column(JSON, nullable=True)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)

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

    class RetryRelationshipDB(Base):
        __tablename__ = "retry_relationships"

        id = Column(Integer, primary_key=True)
        task_id = Column(String, nullable=False)
        original_id = Column(String, nullable=True)
        retry_chain = Column(JSON, nullable=True)
        total_retries = Column(Integer, default=0)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)

    class TaskActionDB(Base):
        __tablename__ = "task_actions"

        id = Column(Integer, primary_key=True)
        action_type = Column(String, nullable=False)
        status = Column(String, nullable=True)
        initiated_by = Column(String, nullable=True)
        initiated_by_user_id = Column(String, nullable=True)
        initiated_session_id = Column(String, nullable=True)
        selection_size = Column(Integer, default=0)
        item_total = Column(Integer, default=0)
        item_changed = Column(Integer, default=0)
        item_created = Column(Integer, default=0)
        item_failed = Column(Integer, default=0)
        item_noop = Column(Integer, default=0)
        item_skipped = Column(Integer, default=0)
        items = Column(JSON, nullable=True)
        original_task_ids = Column(JSON, nullable=True)
        summary = Column(Text, nullable=True)
        started_at = Column(DateTime, nullable=True)
        completed_at = Column(DateTime, nullable=True)
        created_at = Column(DateTime, nullable=True)

    class TaskActionItemDB(Base):
        __tablename__ = "task_action_items"

        id = Column(Integer, primary_key=True)
        action_id = Column(Integer, nullable=True)
        action = Column(String, nullable=True)
        original_task_id = Column(String, nullable=True)
        original_task_name = Column(String, nullable=True)
        attempted_task_id = Column(String, nullable=True)
        outcome = Column(String, nullable=True)
        reason = Column(Text, nullable=True)
        reason_code = Column(String, nullable=True)
        rerun_kind = Column(String, nullable=True)
        rerun_task_id = Column(String, nullable=True)
        rerun_task_name = Column(String, nullable=True)
        review_fingerprint = Column(String, nullable=True)
        skip_category = Column(String, nullable=True)
        submitted_args = Column(JSON, nullable=True)
        submitted_kwargs = Column(JSON, nullable=True)
        target_queue = Column(String, nullable=True)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)

    class TaskDailyStatsDB(Base):
        __tablename__ = "task_daily_stats"

        id = Column(Integer, primary_key=True)
        task_name = Column(String, nullable=False)
        date = Column(String, nullable=False)
        total_executions = Column(Integer, default=0)
        succeeded = Column(Integer, default=0)
        failed = Column(Integer, default=0)
        retried = Column(Integer, default=0)
        revoked = Column(Integer, default=0)
        pending = Column(Integer, default=0)
        orphaned = Column(Integer, default=0)
        avg_runtime = Column(Float, nullable=True)
        min_runtime = Column(Float, nullable=True)
        max_runtime = Column(Float, nullable=True)
        p50_runtime = Column(Float, nullable=True)
        p95_runtime = Column(Float, nullable=True)
        p99_runtime = Column(Float, nullable=True)
        first_execution = Column(DateTime, nullable=True)
        last_execution = Column(DateTime, nullable=True)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "task_name": self.task_name,
                "date": self.date,
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
        __tablename__ = "task_events"

        id = Column(Integer, primary_key=True)
        task_id = Column(String, nullable=False)
        task_name = Column(String, nullable=True)
        event_type = Column(String, nullable=False)
        hostname = Column(String, nullable=True)
        worker_name = Column(String, nullable=True)
        queue = Column(String, nullable=True)
        exchange = Column(String, nullable=True)
        routing_key = Column(String, nullable=True)
        args = Column(JSON, nullable=True)
        kwargs = Column(JSON, nullable=True)
        result = Column(Text, nullable=True)
        exception = Column(Text, nullable=True)
        traceback = Column(Text, nullable=True)
        runtime = Column(Float, nullable=True)
        retries = Column(Integer, default=0)
        retry_count = Column(Integer, default=0)
        retry_of = Column(String, nullable=True)
        retried_by = Column(String, nullable=True)
        has_retries = Column(Boolean, default=False)
        is_retry = Column(Boolean, default=False)
        is_orphan = Column(Boolean, default=False)
        orphaned_at = Column(DateTime, nullable=True)
        parent_id = Column(String, nullable=True)
        root_id = Column(String, nullable=True)
        eta = Column(DateTime, nullable=True)
        expires = Column(DateTime, nullable=True)
        timestamp = Column(DateTime, nullable=True)

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
                "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            }

    class TaskLatestDB(Base):
        __tablename__ = "task_latest"

        task_id = Column(String, primary_key=True)
        task_name = Column(String, nullable=True)
        event_id = Column(Integer, nullable=True)
        event_type = Column(String, nullable=True)
        hostname = Column(String, nullable=True)
        worker_name = Column(String, nullable=True)
        queue = Column(String, nullable=True)
        exchange = Column(String, nullable=True)
        routing_key = Column(String, nullable=True)
        args = Column(JSON, nullable=True)
        kwargs = Column(JSON, nullable=True)
        result = Column(Text, nullable=True)
        exception = Column(Text, nullable=True)
        traceback = Column(Text, nullable=True)
        runtime = Column(Float, nullable=True)
        retries = Column(Integer, default=0)
        retry_count = Column(Integer, default=0)
        retry_of = Column(String, nullable=True)
        retried_by = Column(String, nullable=True)
        has_retries = Column(Boolean, default=False)
        is_retry = Column(Boolean, default=False)
        is_orphan = Column(Boolean, default=False)
        orphaned_at = Column(DateTime, nullable=True)
        parent_id = Column(String, nullable=True)
        root_id = Column(String, nullable=True)
        eta = Column(DateTime, nullable=True)
        expires = Column(DateTime, nullable=True)
        timestamp = Column(DateTime, nullable=True)
        resolved = Column(Boolean, default=False)
        resolved_at = Column(DateTime, nullable=True)
        resolved_by = Column(String, nullable=True)

    class TaskProgressDB(Base):
        __tablename__ = "task_progress"

        id = Column(Integer, primary_key=True)
        task_id = Column(String, nullable=False)
        task_name = Column(String, nullable=True)
        progress = Column(Float, default=0.0)
        message = Column(Text, nullable=True)
        step_key = Column(String, nullable=True)
        meta = Column(JSON, nullable=True)
        timestamp = Column(DateTime, nullable=True)

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

    class TaskProgressLatestDB(Base):
        __tablename__ = "task_progress_latest"

        task_id = Column(String, primary_key=True)
        task_name = Column(String, nullable=True)
        progress = Column(Float, default=0.0)
        message = Column(Text, nullable=True)
        step_key = Column(String, nullable=True)
        meta = Column(JSON, nullable=True)
        updated_at = Column(DateTime, nullable=True)

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

    class TaskRegistryDB(Base):
        __tablename__ = "task_registry"

        id = Column(Integer, primary_key=True)
        name = Column(String, nullable=False, unique=True)
        human_readable_name = Column(String, nullable=True)
        description = Column(Text, nullable=True)
        tags = Column(JSON, nullable=True)
        first_seen = Column(DateTime, nullable=True)
        last_seen = Column(DateTime, nullable=True)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)

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

    class TaskRerunRelationshipDB(Base):
        __tablename__ = "task_rerun_relationships"

        id = Column(Integer, primary_key=True)
        original_task_id = Column(String, nullable=False)
        rerun_task_id = Column(String, nullable=False)
        action_id = Column(Integer, nullable=True)
        created_by = Column(String, nullable=True)
        created_at = Column(DateTime, nullable=True)

    class TaskResolutionDB(Base):
        __tablename__ = "task_resolutions"

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
        __tablename__ = "users"

        id = Column(String, primary_key=True)
        name = Column(String, nullable=True)
        email = Column(String, nullable=True)
        avatar_url = Column(String, nullable=True)
        provider = Column(String, nullable=True)
        provider_account_id = Column(String, nullable=True)
        is_active = Column(Boolean, default=True)
        last_login_at = Column(DateTime, nullable=True)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)
        sessions = relationship("UserSessionDB", back_populates="user")

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

    class UserSessionDB(Base):
        __tablename__ = "user_sessions"

        session_id = Column(String, primary_key=True)
        user_id = Column(String, nullable=False)
        auth_provider = Column(String, nullable=True)
        access_token_hash = Column(String, nullable=True)
        access_token_expires_at = Column(DateTime, nullable=True)
        refresh_token_hash = Column(String, nullable=True)
        refresh_token_expires_at = Column(DateTime, nullable=True)
        token_scopes = Column(JSON, nullable=True)
        active_environment_id = Column(Integer, nullable=True)
        preferences = Column(JSON, nullable=True)
        last_active = Column(DateTime, nullable=True)
        created_at = Column(DateTime, nullable=True)
        user = relationship("UserDB", back_populates="sessions")

        def to_dict(self) -> Dict[str, Any]:
            return {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "auth_provider": self.auth_provider,
                "access_token_hash": self.access_token_hash,
                "access_token_expires_at": self.access_token_expires_at.isoformat() if self.access_token_expires_at else None,
                "refresh_token_hash": self.refresh_token_hash,
                "refresh_token_expires_at": self.refresh_token_expires_at.isoformat() if self.refresh_token_expires_at else None,
                "token_scopes": self.token_scopes,
                "active_environment_id": self.active_environment_id,
                "preferences": self.preferences,
                "last_active": self.last_active.isoformat() if self.last_active else None,
                "created_at": self.created_at.isoformat() if self.created_at else None,
            }

    class WorkerEventDB(Base):
        __tablename__ = "worker_events"

        id = Column(Integer, primary_key=True)
        hostname = Column(String, nullable=False)
        event_type = Column(String, nullable=False)
        status = Column(String, nullable=True)
        active_tasks = Column(Integer, default=0)
        processed = Column(Integer, default=0)
        timestamp = Column(DateTime, nullable=True)

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
        __tablename__ = "workflows"

        id = Column(Integer, primary_key=True)
        name = Column(String, nullable=False)
        description = Column(Text, nullable=True)
        enabled = Column(Boolean, default=True)
        trigger_type = Column(String, nullable=False)
        trigger_config = Column(JSON, nullable=True)
        conditions = Column(JSON, nullable=True)
        actions = Column(JSON, nullable=True)
        priority = Column(Integer, default=0)
        cooldown_seconds = Column(Integer, default=0)
        max_executions_per_hour = Column(Integer, nullable=True)
        circuit_breaker_config = Column(JSON, nullable=True)
        execution_count = Column(Integer, default=0)
        success_count = Column(Integer, default=0)
        failure_count = Column(Integer, default=0)
        last_executed_at = Column(DateTime, nullable=True)
        created_by = Column(String, nullable=True)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)

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
        __tablename__ = "workflow_executions"

        id = Column(Integer, primary_key=True)
        workflow_id = Column(Integer, nullable=False)
        status = Column(String, nullable=True)
        trigger_type = Column(String, nullable=True)
        trigger_event = Column(JSON, nullable=True)
        workflow_snapshot = Column(JSON, nullable=True)
        actions_executed = Column(JSON, nullable=True)
        circuit_breaker_key = Column(String, nullable=True)
        error_message = Column(Text, nullable=True)
        stack_trace = Column(Text, nullable=True)
        duration_ms = Column(Integer, nullable=True)
        triggered_at = Column(DateTime, nullable=True)
        started_at = Column(DateTime, nullable=True)
        completed_at = Column(DateTime, nullable=True)

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "workflow_id": self.workflow_id,
                "status": self.status,
                "trigger_type": self.trigger_type,
                "trigger_event": self.trigger_event,
                "workflow_snapshot": self.workflow_snapshot,
                "actions_executed": self.actions_executed,
                "circuit_breaker_key": self.circuit_breaker_key,
                "error_message": self.error_message,
                "stack_trace": self.stack_trace,
                "duration_ms": self.duration_ms,
                "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            }

else:
    Base = object

    class _FallbackDB:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class ActionConfigDB(_FallbackDB):
        id = None
        name = None
        action_type = None
        config = None
        description = None
        created_at = None
        updated_at = None
        created_by = None
        last_used_at = None
        usage_count = 0

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "name": self.name,
                "action_type": self.action_type,
                "config": self.config,
                "description": self.description,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                "created_by": self.created_by,
                "last_used_at": self.last_used_at,
                "usage_count": self.usage_count,
            }

    class AppSettingDB(_FallbackDB):
        key = None
        value = None
        value_type = None
        category = None
        label = None
        description = None
        created_at = None
        updated_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: getattr(self, k, None) for k in
                    ["key", "value", "value_type", "category", "label", "description", "created_at", "updated_at"]}

    class EnvironmentDB(_FallbackDB):
        id = None
        name = None
        description = None
        is_active = True
        is_default = False
        queue_patterns = None
        worker_patterns = None
        created_at = None
        updated_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: getattr(self, k, None) for k in
                    ["id", "name", "description", "is_active", "is_default", "queue_patterns", "worker_patterns",
                     "created_at", "updated_at"]}

    class RetryRelationshipDB(_FallbackDB):
        id = None
        task_id = None
        original_id = None
        retry_chain = None
        total_retries = 0
        created_at = None
        updated_at = None

    class TaskActionDB(_FallbackDB):
        id = None
        action_type = None
        status = None
        initiated_by = None
        initiated_by_user_id = None
        initiated_session_id = None
        selection_size = 0
        item_total = 0
        item_changed = 0
        item_created = 0
        item_failed = 0
        item_noop = 0
        item_skipped = 0
        items = None
        original_task_ids = None
        summary = None
        started_at = None
        completed_at = None
        created_at = None

    class TaskActionItemDB(_FallbackDB):
        id = None
        action_id = None
        action = None
        original_task_id = None
        original_task_name = None
        attempted_task_id = None
        outcome = None
        reason = None
        reason_code = None
        rerun_kind = None
        rerun_task_id = None
        rerun_task_name = None
        review_fingerprint = None
        skip_category = None
        submitted_args = None
        submitted_kwargs = None
        target_queue = None
        created_at = None
        updated_at = None

    class TaskDailyStatsDB(_FallbackDB):
        id = None
        task_name = None
        date = None
        total_executions = 0
        succeeded = 0
        failed = 0
        retried = 0
        revoked = 0
        pending = 0
        orphaned = 0
        avg_runtime = None
        min_runtime = None
        max_runtime = None
        p50_runtime = None
        p95_runtime = None
        p99_runtime = None
        first_execution = None
        last_execution = None
        created_at = None
        updated_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: getattr(self, k, None) for k in
                    ["id", "task_name", "date", "total_executions", "succeeded", "failed", "retried", "revoked",
                     "pending", "orphaned", "avg_runtime", "min_runtime", "max_runtime", "p50_runtime",
                     "p95_runtime", "p99_runtime", "first_execution", "last_execution", "created_at", "updated_at"]}

    class TaskEventDB(_FallbackDB):
        id = None
        task_id = None
        task_name = None
        event_type = None
        hostname = None
        worker_name = None
        queue = None
        exchange = None
        routing_key = None
        args = None
        kwargs = None
        result = None
        exception = None
        traceback = None
        runtime = None
        retries = 0
        retry_count = 0
        retry_of = None
        retried_by = None
        has_retries = False
        is_retry = False
        is_orphan = False
        orphaned_at = None
        parent_id = None
        root_id = None
        eta = None
        expires = None
        timestamp = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: getattr(self, k, None) for k in
                    ["id", "task_id", "task_name", "event_type", "hostname", "worker_name", "queue", "exchange",
                     "routing_key", "args", "kwargs", "result", "exception", "traceback", "runtime", "retries",
                     "retry_count", "retry_of", "retried_by", "has_retries", "is_retry", "is_orphan",
                     "orphaned_at", "parent_id", "root_id", "eta", "expires", "timestamp"]}

    class TaskLatestDB(_FallbackDB):
        task_id = None
        task_name = None
        event_id = None
        event_type = None
        hostname = None
        worker_name = None
        queue = None
        exchange = None
        routing_key = None
        args = None
        kwargs = None
        result = None
        exception = None
        traceback = None
        runtime = None
        retries = 0
        retry_count = 0
        retry_of = None
        retried_by = None
        has_retries = False
        is_retry = False
        is_orphan = False
        orphaned_at = None
        parent_id = None
        root_id = None
        eta = None
        expires = None
        timestamp = None
        resolved = False
        resolved_at = None
        resolved_by = None

    class TaskProgressDB(_FallbackDB):
        id = None
        task_id = None
        task_name = None
        progress = 0.0
        message = None
        step_key = None
        meta = None
        timestamp = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: getattr(self, k, None) for k in
                    ["id", "task_id", "task_name", "progress", "message", "step_key", "meta", "timestamp"]}

    class TaskProgressLatestDB(_FallbackDB):
        task_id = None
        task_name = None
        progress = 0.0
        message = None
        step_key = None
        meta = None
        updated_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: getattr(self, k, None) for k in
                    ["task_id", "task_name", "progress", "message", "step_key", "meta", "updated_at"]}

    class TaskRegistryDB(_FallbackDB):
        id = None
        name = None
        human_readable_name = None
        description = None
        tags = None
        first_seen = None
        last_seen = None
        created_at = None
        updated_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: getattr(self, k, None) for k in
                    ["id", "name", "human_readable_name", "description", "tags", "first_seen", "last_seen",
                     "created_at", "updated_at"]}

    class TaskRerunRelationshipDB(_FallbackDB):
        id = None
        original_task_id = None
        rerun_task_id = None
        action_id = None
        created_by = None
        created_at = None

    class TaskResolutionDB(_FallbackDB):
        task_id = None
        resolved = False
        resolved_at = None
        resolved_by = None

    class TaskStepsDB(_FallbackDB):
        task_id = None
        task_name = None
        steps = None
        defined_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: getattr(self, k, None) for k in ["task_id", "task_name", "steps", "defined_at"]}

    class UserDB(_FallbackDB):
        id = None
        name = None
        email = None
        avatar_url = None
        provider = None
        provider_account_id = None
        is_active = True
        last_login_at = None
        created_at = None
        updated_at = None
        sessions = []

        def to_dict(self) -> Dict[str, Any]:
            return {k: getattr(self, k, None) for k in
                    ["id", "name", "email", "avatar_url", "provider", "provider_account_id", "is_active",
                     "last_login_at", "created_at", "updated_at"]}

    class UserSessionDB(_FallbackDB):
        session_id = None
        user_id = None
        auth_provider = None
        access_token_hash = None
        access_token_expires_at = None
        refresh_token_hash = None
        refresh_token_expires_at = None
        token_scopes = None
        active_environment_id = None
        preferences = None
        last_active = None
        created_at = None
        user = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: getattr(self, k, None) for k in
                    ["session_id", "user_id", "auth_provider", "access_token_hash", "access_token_expires_at",
                     "refresh_token_hash", "refresh_token_expires_at", "token_scopes", "active_environment_id",
                     "preferences", "last_active", "created_at"]}

    class WorkerEventDB(_FallbackDB):
        id = None
        hostname = None
        event_type = None
        status = None
        active_tasks = 0
        processed = 0
        timestamp = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: getattr(self, k, None) for k in
                    ["id", "hostname", "event_type", "status", "active_tasks", "processed", "timestamp"]}

    class WorkflowDB(_FallbackDB):
        id = None
        name = None
        description = None
        enabled = True
        trigger_type = None
        trigger_config = None
        conditions = None
        actions = None
        priority = 0
        cooldown_seconds = 0
        max_executions_per_hour = None
        circuit_breaker_config = None
        execution_count = 0
        success_count = 0
        failure_count = 0
        last_executed_at = None
        created_by = None
        created_at = None
        updated_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: getattr(self, k, None) for k in
                    ["id", "name", "description", "enabled", "trigger_type", "trigger_config", "conditions",
                     "actions", "priority", "cooldown_seconds", "max_executions_per_hour", "circuit_breaker_config",
                     "execution_count", "success_count", "failure_count", "last_executed_at", "created_by",
                     "created_at", "updated_at"]}

    class WorkflowExecutionDB(_FallbackDB):
        id = None
        workflow_id = None
        status = None
        trigger_type = None
        trigger_event = None
        workflow_snapshot = None
        actions_executed = None
        circuit_breaker_key = None
        error_message = None
        stack_trace = None
        duration_ms = None
        triggered_at = None
        started_at = None
        completed_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: getattr(self, k, None) for k in
                    ["id", "workflow_id", "status", "trigger_type", "trigger_event", "workflow_snapshot",
                     "actions_executed", "circuit_breaker_key", "error_message", "stack_trace", "duration_ms",
                     "triggered_at", "started_at", "completed_at"]}


# ---------------------------------------------------------------------------
# DatabaseManager
# ---------------------------------------------------------------------------

class DatabaseManager:
    def __init__(self, database_url: str = "sqlite:///:memory:"):
        self.database_url: str = database_url
        self.engine: Optional[Any] = None
        self.SessionLocal: Optional[Any] = None
        self._initialize()

    def _initialize(self):
        if SQLALCHEMY_AVAILABLE:
            self.engine = create_engine(self.database_url, connect_args={"check_same_thread": False}
                                        if "sqlite" in self.database_url else {})
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        else:
            self.engine = None
            self.SessionLocal = None

    def get_session(self) -> Optional[Any]:
        if self.SessionLocal is None:
            return None
        return self.SessionLocal()

    def run_migrations(self):
        if SQLALCHEMY_AVAILABLE and self.engine is not None:
            Base.metadata.create_all(bind=self.engine)


# ---------------------------------------------------------------------------
# CeleryEventMonitor
# ---------------------------------------------------------------------------

class CeleryEventMonitor:
    def __init__(self, broker_url: str = "redis://localhost:6379/0", app: Any = None):
        self.broker_url: str = broker_url
        self.app: Any = app
        self.state: None = None
        self.workers: Dict[str, Dict[str, Any]] = {}
        self.task_callback: Optional[Callable[[TaskEvent], None]] = None
        self.worker_callback: Optional[Callable[[WorkerEvent], None]] = None
        self.progress_callback: Optional[Callable[[TaskProgressEvent], None]] = None
        self.steps_callback: Optional[Callable[[TaskStepsEvent], None]] = None
        self._running: bool = False

    def set_task_callback(self, callback: Callable[[TaskEvent], None]):
        self.task_callback = callback

    def set_worker_callback(self, callback: Callable[[WorkerEvent], None]):
        self.worker_callback = callback

    def set_progress_callback(self, callback: Callable[[TaskProgressEvent], None]):
        self.progress_callback = callback

    def set_steps_callback(self, callback: Callable[[TaskStepsEvent], None]):
        self.steps_callback = callback

    def get_workers_info(self) -> Dict[str, Dict[str, Any]]:
        return dict(self.workers)

    def start_monitoring(self):
        self._running = True

    def stop(self):
        self._running = False


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

    async def connect(self, websocket: Any):
        if hasattr(websocket, "accept"):
            await websocket.accept()
        self.active_connections.append(websocket)
        self.client_filters[websocket] = {}
        self.client_modes[websocket] = "default"

    def disconnect(self, websocket: Any):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.client_filters.pop(websocket, None)
        self.client_modes.pop(websocket, None)

    def set_client_filters(self, websocket: Any, filters: dict):
        self.client_filters[websocket] = filters

    def set_client_mode(self, websocket: Any, mode: str):
        self.client_modes[websocket] = mode

    async def send_personal_message(self, message: str, websocket: Any):
        if hasattr(websocket, "send_text"):
            await websocket.send_text(message)

    def queue_broadcast(self, task_event: TaskEvent):
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "task", "event": task_event})
            except asyncio.QueueFull:
                pass

    def queue_worker_broadcast(self, worker_event: WorkerEvent):
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "worker", "event": worker_event})
            except asyncio.QueueFull:
                pass

    def queue_progress_broadcast(self, progress_event: Any):
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "progress", "event": progress_event})
            except asyncio.QueueFull:
                pass

    def queue_task_action_broadcast(self, action_event: Any):
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "task_action", "event": action_event})
            except asyncio.QueueFull:
                pass

    async def _background_broadcaster(self):
        while True:
            if self.message_queue is None:
                break
            try:
                item = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                import json
                message = json.dumps({"type": item.get("type"), "data": str(item.get("event"))})
                for connection in list(self.active_connections):
                    try:
                        await self.send_personal_message(message, connection)
                    except Exception:
                        self.disconnect(connection)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception:
                continue

    def start_background_broadcaster(self):
        self.message_queue = asyncio.Queue()
        loop = asyncio.get_event_loop()
        self._broadcaster_task = loop.create_task(self._background_broadcaster())

    def stop_background_broadcaster(self):
        if self._broadcaster_task is not None:
            self._broadcaster_task.cancel()
            self._broadcaster_task = None
        self.message_queue = None


# ---------------------------------------------------------------------------
# EventHandler
# ---------------------------------------------------------------------------

class EventHandler:
    def __init__(self, connection_manager: ConnectionManager, db_manager: DatabaseManager):
        self.connection_manager: ConnectionManager = connection_manager
        self.db_manager: DatabaseManager = db_manager
        self.workflow_engine: None = None

    def handle_task_event(self, task_event: TaskEvent):
        self.connection_manager.queue_broadcast(task_event)
        session = self.db_manager.get_session()
        if session is not None:
            try:
                session.close()
            except Exception:
                pass

    def handle_worker_event(self, worker_event: WorkerEvent):
        self.connection_manager.queue_worker_broadcast(worker_event)
        session = self.db_manager.get_session()
        if session is not None:
            try:
                session.close()
            except Exception:
                pass

    def handle_progress_event(self, progress_event: Any):
        self.connection_manager.queue_progress_broadcast(progress_event)
        session = self.db_manager.get_session()
        if session is not None:
            try:
                session.close()
            except Exception:
                pass

    def handle_steps_event(self, steps_event: Any):
        session = self.db_manager.get_session()
        if session is not None:
            try:
                session.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# ActionHandler (abstract base)
# ---------------------------------------------------------------------------

class ActionHandler(ABC):
    def __init__(self, db_manager: DatabaseManager, session: Any = None):
        self.db_manager: DatabaseManager = db_manager
        self.session: Any = session
        self.monitor_instance: None = None

    @abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        pass

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        pass

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        def replace_match(match: re.Match) -> str:
            key = match.group(1).strip()
            parts = key.split(".")
            value = context
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, "")
                else:
                    value = getattr(value, part, "")
            return str(value)

        return re.sub(r"\{\{(.*?)\}\}", replace_match, template)


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

        task_ids = params.get("task_ids") or ([params["task_id"]] if "task_id" in params else [])
        if not isinstance(task_ids, list):
            task_ids = [task_ids]

        results = []
        for task_id in task_ids:
            results.append({"task_id": task_id, "status": "retry_queued"})

        return ActionResult(
            success=True,
            message=f"Retry queued for {len(task_ids)} task(s)",
            data={"results": results, "count": len(task_ids)},
        )


# ---------------------------------------------------------------------------
# SlackActionHandler
# ---------------------------------------------------------------------------

class SlackActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "webhook_url" not in params and "channel" not in params:
            return False, "Either 'webhook_url' or 'channel' must be provided"
        if "message" not in params and "template" not in params:
            return False, "Either 'message' or 'template' must be provided"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        valid, message = self.validate_params(params)
        if not valid:
            return ActionResult(success=False, message=message)

        template = params.get("template") or params.get("message", "")
        rendered_message = self.render_template(template, context)

        webhook_url = params.get("webhook_url", "")
        channel = params.get("channel", "")

        return ActionResult(
            success=True,
            message="Slack message sent",
            data={
                "rendered_message": rendered_message,
                "webhook_url": webhook_url,
                "channel": channel,
            },
        )