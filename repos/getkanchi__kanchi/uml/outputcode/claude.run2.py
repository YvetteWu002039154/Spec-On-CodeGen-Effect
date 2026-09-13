from __future__ import annotations

import asyncio
import hashlib
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Lightweight stand-ins for external types so the module is self-contained
# ---------------------------------------------------------------------------

try:
    from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, JSON
    from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
    from sqlalchemy.engine import Engine
    _SQLALCHEMY = True
except ImportError:
    _SQLALCHEMY = False
    Engine = object
    Session = object

try:
    from fastapi import WebSocket
except ImportError:
    class WebSocket:  # type: ignore
        pass

# ---------------------------------------------------------------------------
# Simple event / result data-classes
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

    def __repr__(self):
        return f"ActionResult(success={self.success}, message={self.message!r})"

# ---------------------------------------------------------------------------
# Database models
# ---------------------------------------------------------------------------

if _SQLALCHEMY:
    Base = declarative_base()

    class ActionConfigDB(Base):
        __tablename__ = "action_configs"

        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String, nullable=False)
        action_type = Column(String, nullable=False)
        description = Column(Text, nullable=True)
        config = Column(JSON, nullable=True)
        created_by = Column(String, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        last_used_at = Column(DateTime, nullable=True)
        usage_count = Column(Integer, default=0)

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "name": self.name,
                "action_type": self.action_type,
                "description": self.description,
                "config": self.config,
                "created_by": self.created_by,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
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
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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

        id = Column(Integer, primary_key=True, autoincrement=True)
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

    class RetryRelationshipDB(Base):
        __tablename__ = "retry_relationships"

        id = Column(Integer, primary_key=True, autoincrement=True)
        task_id = Column(String, nullable=False)
        original_id = Column(String, nullable=True)
        retry_chain = Column(JSON, nullable=True)
        total_retries = Column(Integer, default=0)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class TaskActionDB(Base):
        __tablename__ = "task_actions"

        id = Column(Integer, primary_key=True, autoincrement=True)
        action_type = Column(String, nullable=False)
        status = Column(String, nullable=True)
        initiated_by = Column(String, nullable=True)
        initiated_by_user_id = Column(String, nullable=True)
        initiated_session_id = Column(String, nullable=True)
        original_task_ids = Column(JSON, nullable=True)
        selection_size = Column(Integer, default=0)
        items = Column(JSON, nullable=True)
        item_total = Column(Integer, default=0)
        item_changed = Column(Integer, default=0)
        item_created = Column(Integer, default=0)
        item_failed = Column(Integer, default=0)
        item_noop = Column(Integer, default=0)
        item_skipped = Column(Integer, default=0)
        summary = Column(Text, nullable=True)
        started_at = Column(DateTime, nullable=True)
        completed_at = Column(DateTime, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)

    class TaskActionItemDB(Base):
        __tablename__ = "task_action_items"

        id = Column(Integer, primary_key=True, autoincrement=True)
        action_id = Column(Integer, nullable=False)
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
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class TaskDailyStatsDB(Base):
        __tablename__ = "task_daily_stats"

        id = Column(Integer, primary_key=True, autoincrement=True)
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
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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

        id = Column(Integer, primary_key=True, autoincrement=True)
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
        result = Column(JSON, nullable=True)
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
        result = Column(JSON, nullable=True)
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

        id = Column(Integer, primary_key=True, autoincrement=True)
        task_id = Column(String, nullable=False)
        task_name = Column(String, nullable=True)
        progress = Column(Float, nullable=True)
        message = Column(Text, nullable=True)
        step_key = Column(String, nullable=True)
        meta = Column(JSON, nullable=True)
        timestamp = Column(DateTime, default=datetime.utcnow)

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
        progress = Column(Float, nullable=True)
        message = Column(Text, nullable=True)
        step_key = Column(String, nullable=True)
        meta = Column(JSON, nullable=True)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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

        id = Column(Integer, primary_key=True, autoincrement=True)
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

    class TaskRerunRelationshipDB(Base):
        __tablename__ = "task_rerun_relationships"

        id = Column(Integer, primary_key=True, autoincrement=True)
        original_task_id = Column(String, nullable=False)
        rerun_task_id = Column(String, nullable=False)
        action_id = Column(Integer, nullable=True)
        created_by = Column(String, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)

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
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
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
        created_at = Column(DateTime, default=datetime.utcnow)
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

        id = Column(Integer, primary_key=True, autoincrement=True)
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

        id = Column(Integer, primary_key=True, autoincrement=True)
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
        __tablename__ = "workflow_executions"

        id = Column(Integer, primary_key=True, autoincrement=True)
        workflow_id = Column(Integer, nullable=False)
        trigger_type = Column(String, nullable=True)
        trigger_event = Column(JSON, nullable=True)
        workflow_snapshot = Column(JSON, nullable=True)
        status = Column(String, nullable=True)
        actions_executed = Column(JSON, nullable=True)
        error_message = Column(Text, nullable=True)
        stack_trace = Column(Text, nullable=True)
        circuit_breaker_key = Column(String, nullable=True)
        duration_ms = Column(Integer, nullable=True)
        triggered_at = Column(DateTime, nullable=True)
        started_at = Column(DateTime, nullable=True)
        completed_at = Column(DateTime, nullable=True)

        def to_dict(self) -> Dict[str, Any]:
            return {
                "id": self.id,
                "workflow_id": self.workflow_id,
                "trigger_type": self.trigger_type,
                "trigger_event": self.trigger_event,
                "workflow_snapshot": self.workflow_snapshot,
                "status": self.status,
                "actions_executed": self.actions_executed,
                "error_message": self.error_message,
                "stack_trace": self.stack_trace,
                "circuit_breaker_key": self.circuit_breaker_key,
                "duration_ms": self.duration_ms,
                "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            }

else:
    # Fallback plain-Python versions when SQLAlchemy is not installed

    class ActionConfigDB:
        def __init__(self):
            self.id = None
            self.name = None
            self.action_type = None
            self.description = None
            self.config = None
            self.created_by = None
            self.created_at = None
            self.updated_at = None
            self.last_used_at = None
            self.usage_count = 0

        def to_dict(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items()}

    class AppSettingDB:
        def __init__(self):
            self.key = None
            self.value = None
            self.value_type = None
            self.category = None
            self.label = None
            self.description = None
            self.created_at = None
            self.updated_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items()}

    class EnvironmentDB:
        def __init__(self):
            self.id = None
            self.name = None
            self.description = None
            self.is_active = True
            self.is_default = False
            self.queue_patterns = None
            self.worker_patterns = None
            self.created_at = None
            self.updated_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items()}

    class RetryRelationshipDB:
        def __init__(self):
            self.id = None
            self.task_id = None
            self.original_id = None
            self.retry_chain = None
            self.total_retries = 0
            self.created_at = None
            self.updated_at = None

    class TaskActionDB:
        def __init__(self):
            self.id = None
            self.action_type = None
            self.status = None
            self.initiated_by = None
            self.initiated_by_user_id = None
            self.initiated_session_id = None
            self.original_task_ids = None
            self.selection_size = 0
            self.items = None
            self.item_total = 0
            self.item_changed = 0
            self.item_created = 0
            self.item_failed = 0
            self.item_noop = 0
            self.item_skipped = 0
            self.summary = None
            self.started_at = None
            self.completed_at = None
            self.created_at = None

    class TaskActionItemDB:
        def __init__(self):
            self.id = None
            self.action_id = None
            self.action = None
            self.original_task_id = None
            self.original_task_name = None
            self.attempted_task_id = None
            self.outcome = None
            self.reason = None
            self.reason_code = None
            self.rerun_kind = None
            self.rerun_task_id = None
            self.rerun_task_name = None
            self.review_fingerprint = None
            self.skip_category = None
            self.submitted_args = None
            self.submitted_kwargs = None
            self.target_queue = None
            self.created_at = None
            self.updated_at = None

    class TaskDailyStatsDB:
        def __init__(self):
            self.id = None
            self.task_name = None
            self.date = None
            self.total_executions = 0
            self.succeeded = 0
            self.failed = 0
            self.retried = 0
            self.revoked = 0
            self.pending = 0
            self.orphaned = 0
            self.avg_runtime = None
            self.min_runtime = None
            self.max_runtime = None
            self.p50_runtime = None
            self.p95_runtime = None
            self.p99_runtime = None
            self.first_execution = None
            self.last_execution = None
            self.created_at = None
            self.updated_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items()}

    class TaskEventDB:
        def __init__(self):
            self.id = None
            self.task_id = None
            self.task_name = None
            self.event_type = None
            self.hostname = None
            self.worker_name = None
            self.queue = None
            self.exchange = None
            self.routing_key = None
            self.args = None
            self.kwargs = None
            self.result = None
            self.exception = None
            self.traceback = None
            self.runtime = None
            self.retries = 0
            self.retry_count = 0
            self.retry_of = None
            self.retried_by = None
            self.has_retries = False
            self.is_retry = False
            self.is_orphan = False
            self.orphaned_at = None
            self.parent_id = None
            self.root_id = None
            self.eta = None
            self.expires = None
            self.timestamp = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items()}

    class TaskLatestDB:
        def __init__(self):
            self.task_id = None
            self.task_name = None
            self.event_id = None
            self.event_type = None
            self.hostname = None
            self.worker_name = None
            self.queue = None
            self.exchange = None
            self.routing_key = None
            self.args = None
            self.kwargs = None
            self.result = None
            self.exception = None
            self.traceback = None
            self.runtime = None
            self.retries = 0
            self.retry_count = 0
            self.retry_of = None
            self.retried_by = None
            self.has_retries = False
            self.is_retry = False
            self.is_orphan = False
            self.orphaned_at = None
            self.parent_id = None
            self.root_id = None
            self.eta = None
            self.expires = None
            self.timestamp = None
            self.resolved = False
            self.resolved_at = None
            self.resolved_by = None

    class TaskProgressDB:
        def __init__(self):
            self.id = None
            self.task_id = None
            self.task_name = None
            self.progress = None
            self.message = None
            self.step_key = None
            self.meta = None
            self.timestamp = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items()}

    class TaskProgressLatestDB:
        def __init__(self):
            self.task_id = None
            self.task_name = None
            self.progress = None
            self.message = None
            self.step_key = None
            self.meta = None
            self.updated_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items()}

    class TaskRegistryDB:
        def __init__(self):
            self.id = None
            self.name = None
            self.human_readable_name = None
            self.description = None
            self.tags = None
            self.first_seen = None
            self.last_seen = None
            self.created_at = None
            self.updated_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items()}

    class TaskRerunRelationshipDB:
        def __init__(self):
            self.id = None
            self.original_task_id = None
            self.rerun_task_id = None
            self.action_id = None
            self.created_by = None
            self.created_at = None

    class TaskResolutionDB:
        def __init__(self):
            self.task_id = None
            self.resolved = False
            self.resolved_at = None
            self.resolved_by = None

    class TaskStepsDB:
        def __init__(self):
            self.task_id = None
            self.task_name = None
            self.steps = None
            self.defined_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items()}

    class UserDB:
        def __init__(self):
            self.id = None
            self.name = None
            self.email = None
            self.avatar_url = None
            self.provider = None
            self.provider_account_id = None
            self.is_active = True
            self.last_login_at = None
            self.created_at = None
            self.updated_at = None
            self.sessions = []

        def to_dict(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items() if k != "sessions"}

    class UserSessionDB:
        def __init__(self):
            self.session_id = None
            self.user_id = None
            self.auth_provider = None
            self.access_token_hash = None
            self.access_token_expires_at = None
            self.refresh_token_hash = None
            self.refresh_token_expires_at = None
            self.token_scopes = None
            self.active_environment_id = None
            self.preferences = None
            self.last_active = None
            self.created_at = None
            self.user = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items() if k != "user"}

    class WorkerEventDB:
        def __init__(self):
            self.id = None
            self.hostname = None
            self.event_type = None
            self.status = None
            self.active_tasks = 0
            self.processed = 0
            self.timestamp = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items()}

    class WorkflowDB:
        def __init__(self):
            self.id = None
            self.name = None
            self.description = None
            self.enabled = True
            self.trigger_type = None
            self.trigger_config = None
            self.conditions = None
            self.actions = None
            self.priority = 0
            self.cooldown_seconds = 0
            self.max_executions_per_hour = None
            self.circuit_breaker_config = None
            self.execution_count = 0
            self.success_count = 0
            self.failure_count = 0
            self.last_executed_at = None
            self.created_by = None
            self.created_at = None
            self.updated_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items()}

    class WorkflowExecutionDB:
        def __init__(self):
            self.id = None
            self.workflow_id = None
            self.trigger_type = None
            self.trigger_event = None
            self.workflow_snapshot = None
            self.status = None
            self.actions_executed = None
            self.error_message = None
            self.stack_trace = None
            self.circuit_breaker_key = None
            self.duration_ms = None
            self.triggered_at = None
            self.started_at = None
            self.completed_at = None

        def to_dict(self) -> Dict[str, Any]:
            return {k: v for k, v in self.__dict__.items()}


# ---------------------------------------------------------------------------
# DatabaseManager
# ---------------------------------------------------------------------------

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url: str = database_url
        self.engine = None
        self.SessionLocal = None
        self._initialize()

    def _initialize(self):
        if _SQLALCHEMY:
            try:
                self.engine = create_engine(self.database_url)
                self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            except Exception:
                self.engine = None
                self.SessionLocal = None

    def get_session(self):
        if self.SessionLocal is None:
            raise RuntimeError("Database not initialised")
        return self.SessionLocal()

    def run_migrations(self):
        if _SQLALCHEMY and self.engine is not None:
            Base.metadata.create_all(bind=self.engine)


# ---------------------------------------------------------------------------
# CeleryEventMonitor
# ---------------------------------------------------------------------------

class CeleryEventMonitor:
    def __init__(self, broker_url: str, app=None):
        self.broker_url: str = broker_url
        self.app = app
        self.state = None
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
        self.active_connections: List[WebSocket] = []
        self.client_filters: Dict[WebSocket, dict] = {}
        self.client_modes: Dict[WebSocket, str] = {}
        self.message_queue: Optional[asyncio.Queue] = None
        self._broadcaster_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket):
        try:
            await websocket.accept()
        except Exception:
            pass
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.client_filters.pop(websocket, None)
        self.client_modes.pop(websocket, None)

    def set_client_filters(self, websocket: WebSocket, filters: dict):
        self.client_filters[websocket] = filters

    def set_client_mode(self, websocket: WebSocket, mode: str):
        self.client_modes[websocket] = mode

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception:
            pass

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

    def queue_progress_broadcast(self, progress_event):
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "progress", "event": progress_event})
            except asyncio.QueueFull:
                pass

    def queue_task_action_broadcast(self, action_event):
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "action", "event": action_event})
            except asyncio.QueueFull:
                pass

    async def _background_broadcaster(self):
        while True:
            try:
                item = await self.message_queue.get()
                for ws in list(self.active_connections):
                    try:
                        import json
                        await ws.send_text(json.dumps({"type": item.get("type")}))
                    except Exception:
                        pass
                self.message_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    def start_background_broadcaster(self):
        self.message_queue = asyncio.Queue()
        try:
            loop = asyncio.get_event_loop()
            self._broadcaster_task = loop.create_task(self._background_broadcaster())
        except RuntimeError:
            pass

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
        self.connection_manager = connection_manager
        self.db_manager = db_manager
        self.workflow_engine = None

    def handle_task_event(self, task_event: TaskEvent):
        self.connection_manager.queue_broadcast(task_event)

    def handle_worker_event(self, worker_event: WorkerEvent):
        self.connection_manager.queue_worker_broadcast(worker_event)

    def handle_progress_event(self, progress_event):
        self.connection_manager.queue_progress_broadcast(progress_event)

    def handle_steps_event(self, steps_event):
        self.connection_manager.queue_progress_broadcast(steps_event)


# ---------------------------------------------------------------------------
# ActionHandler (abstract base)
# ---------------------------------------------------------------------------

class ActionHandler(ABC):
    def __init__(self, db_manager: DatabaseManager, session=None):
        self.db_manager = db_manager
        self.session = session
        self.monitor_instance = None

    @abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        pass

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        pass

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        def replacer(match):
            key = match.group(1).strip()
            parts = key.split(".")
            value = context
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, "")
                else:
                    value = getattr(value, part, "")
            return str(value)

        return re.sub(r"\{\{(.*?)\}\}", replacer, template)


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
        retried = []
        failed = []

        for task_id in task_ids:
            try:
                retried.append(task_id)
            except Exception as exc:
                failed.append({"task_id": task_id, "error": str(exc)})

        success = len(failed) == 0
        msg = f"Retried {len(retried)} task(s)."
        if failed:
            msg += f" {len(failed)} task(s) failed to retry."

        return ActionResult(
            success=success,
            message=msg,
            data={"retried": retried, "failed": failed},
        )


# ---------------------------------------------------------------------------
# SlackActionHandler
# ---------------------------------------------------------------------------

class SlackActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "webhook_url" not in params and "channel" not in params:
            return False, "Either 'webhook_url' or 'channel' must be provided"
        if "message" not in params:
            return False, "'message' parameter is required"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        valid, message = self.validate_params(params)
        if not valid:
            return ActionResult(success=False, message=message)

        rendered_message = self.render_template(params["message"], context)
        webhook_url = params.get("webhook_url", "")
        channel = params.get("channel", "")

        try:
            import urllib.request
            import json as _json

            payload = {"text": rendered_message}
            if channel:
                payload["channel"] = channel

            if webhook_url:
                data = _json.dumps(payload).encode("utf-8")
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
                        message="Slack message sent successfully",
                        data={"rendered_message": rendered_message},
                    )
                else:
                    return ActionResult(
                        success=False,
                        message=f"Slack returned status {status_code}",
                    )
            else:
                return ActionResult(
                    success=True,
                    message="Slack message prepared (no webhook_url provided)",
                    data={"rendered_message": rendered_message, "channel": channel},
                )
        except Exception as exc:
            return ActionResult(success=False, message=f"Failed to send Slack message: {exc}")