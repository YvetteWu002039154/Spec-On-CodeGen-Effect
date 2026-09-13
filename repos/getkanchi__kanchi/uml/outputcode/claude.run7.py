from __future__ import annotations

import asyncio
import hashlib
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Lightweight stand-ins for SQLAlchemy / FastAPI types so the module is
# importable without those dependencies being present.
# ---------------------------------------------------------------------------
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
    from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON
    _SA_AVAILABLE = True
except ImportError:
    _SA_AVAILABLE = False

try:
    from fastapi import WebSocket
except ImportError:
    class WebSocket:  # type: ignore
        pass


# ---------------------------------------------------------------------------
# Named-tuple-like result type used by action handlers
# ---------------------------------------------------------------------------
class ActionResult:
    def __init__(self, success: bool, message: str = "", data: Optional[Dict[str, Any]] = None):
        self.success = success
        self.message = message
        self.data = data or {}

    def __repr__(self) -> str:
        return f"ActionResult(success={self.success}, message={self.message!r})"


# ---------------------------------------------------------------------------
# Event data-classes (lightweight, no SQLAlchemy dependency)
# ---------------------------------------------------------------------------
class TaskEvent:
    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)


class WorkerEvent:
    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TaskProgressEvent:
    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TaskStepsEvent:
    def __init__(self, **kwargs: Any):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# Database models
# ---------------------------------------------------------------------------
if _SA_AVAILABLE:
    class _Base(DeclarativeBase):
        pass
else:
    class _Base:  # type: ignore
        pass


class ActionConfigDB(_Base):
    __tablename__ = "action_configs"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True)
        name = Column(String)
        action_type = Column(String)
        config = Column(JSON)
        description = Column(Text)
        created_at = Column(DateTime)
        updated_at = Column(DateTime)
        created_by = Column(String)
        last_used_at = Column(DateTime)
        usage_count = Column(Integer, default=0)
    else:
        id: Any = None
        name: Any = None
        action_type: Any = None
        config: Any = None
        description: Any = None
        created_at: Any = None
        updated_at: Any = None
        created_by: Any = None
        last_used_at: Any = None
        usage_count: Any = None

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


class AppSettingDB(_Base):
    __tablename__ = "app_settings"

    if _SA_AVAILABLE:
        key = Column(String, primary_key=True)
        value = Column(Text)
        value_type = Column(String)
        category = Column(String)
        label = Column(String)
        description = Column(Text)
        created_at = Column(DateTime)
        updated_at = Column(DateTime)
    else:
        key: Any = None
        value: Any = None
        value_type: Any = None
        category: Any = None
        label: Any = None
        description: Any = None
        created_at: Any = None
        updated_at: Any = None

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


class EnvironmentDB(_Base):
    __tablename__ = "environments"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True)
        name = Column(String)
        description = Column(Text)
        is_active = Column(Boolean, default=True)
        is_default = Column(Boolean, default=False)
        queue_patterns = Column(JSON)
        worker_patterns = Column(JSON)
        created_at = Column(DateTime)
        updated_at = Column(DateTime)
    else:
        id: Any = None
        name: Any = None
        description: Any = None
        is_active: Any = None
        is_default: Any = None
        queue_patterns: Any = None
        worker_patterns: Any = None
        created_at: Any = None
        updated_at: Any = None

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


class RetryRelationshipDB(_Base):
    __tablename__ = "retry_relationships"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True)
        task_id = Column(String)
        original_id = Column(String)
        retry_chain = Column(JSON)
        total_retries = Column(Integer, default=0)
        created_at = Column(DateTime)
        updated_at = Column(DateTime)
    else:
        id: Any = None
        task_id: Any = None
        original_id: Any = None
        retry_chain: Any = None
        total_retries: Any = None
        created_at: Any = None
        updated_at: Any = None


class TaskActionDB(_Base):
    __tablename__ = "task_actions"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True)
        action_type = Column(String)
        status = Column(String)
        initiated_by = Column(String)
        initiated_by_user_id = Column(String)
        initiated_session_id = Column(String)
        original_task_ids = Column(JSON)
        selection_size = Column(Integer)
        item_total = Column(Integer)
        item_changed = Column(Integer)
        item_created = Column(Integer)
        item_failed = Column(Integer)
        item_noop = Column(Integer)
        item_skipped = Column(Integer)
        items = Column(JSON)
        started_at = Column(DateTime)
        completed_at = Column(DateTime)
        created_at = Column(DateTime)
        summary = Column(Text)
    else:
        id: Any = None
        action_type: Any = None
        status: Any = None
        initiated_by: Any = None
        initiated_by_user_id: Any = None
        initiated_session_id: Any = None
        original_task_ids: Any = None
        selection_size: Any = None
        item_total: Any = None
        item_changed: Any = None
        item_created: Any = None
        item_failed: Any = None
        item_noop: Any = None
        item_skipped: Any = None
        items: Any = None
        started_at: Any = None
        completed_at: Any = None
        created_at: Any = None
        summary: Any = None


class TaskActionItemDB(_Base):
    __tablename__ = "task_action_items"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True)
        action_id = Column(Integer)
        action = Column(String)
        original_task_id = Column(String)
        original_task_name = Column(String)
        attempted_task_id = Column(String)
        outcome = Column(String)
        reason = Column(Text)
        reason_code = Column(String)
        rerun_kind = Column(String)
        rerun_task_id = Column(String)
        rerun_task_name = Column(String)
        review_fingerprint = Column(String)
        skip_category = Column(String)
        submitted_args = Column(JSON)
        submitted_kwargs = Column(JSON)
        target_queue = Column(String)
        created_at = Column(DateTime)
        updated_at = Column(DateTime)
    else:
        id: Any = None
        action_id: Any = None
        action: Any = None
        original_task_id: Any = None
        original_task_name: Any = None
        attempted_task_id: Any = None
        outcome: Any = None
        reason: Any = None
        reason_code: Any = None
        rerun_kind: Any = None
        rerun_task_id: Any = None
        rerun_task_name: Any = None
        review_fingerprint: Any = None
        skip_category: Any = None
        submitted_args: Any = None
        submitted_kwargs: Any = None
        target_queue: Any = None
        created_at: Any = None
        updated_at: Any = None


class TaskDailyStatsDB(_Base):
    __tablename__ = "task_daily_stats"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True)
        task_name = Column(String)
        date = Column(DateTime)
        total_executions = Column(Integer, default=0)
        succeeded = Column(Integer, default=0)
        failed = Column(Integer, default=0)
        retried = Column(Integer, default=0)
        revoked = Column(Integer, default=0)
        pending = Column(Integer, default=0)
        orphaned = Column(Integer, default=0)
        avg_runtime = Column(Float)
        min_runtime = Column(Float)
        max_runtime = Column(Float)
        p50_runtime = Column(Float)
        p95_runtime = Column(Float)
        p99_runtime = Column(Float)
        first_execution = Column(DateTime)
        last_execution = Column(DateTime)
        created_at = Column(DateTime)
        updated_at = Column(DateTime)
    else:
        id: Any = None
        task_name: Any = None
        date: Any = None
        total_executions: Any = None
        succeeded: Any = None
        failed: Any = None
        retried: Any = None
        revoked: Any = None
        pending: Any = None
        orphaned: Any = None
        avg_runtime: Any = None
        min_runtime: Any = None
        max_runtime: Any = None
        p50_runtime: Any = None
        p95_runtime: Any = None
        p99_runtime: Any = None
        first_execution: Any = None
        last_execution: Any = None
        created_at: Any = None
        updated_at: Any = None

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
            "first_execution": self.first_execution,
            "last_execution": self.last_execution,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TaskEventDB(_Base):
    __tablename__ = "task_events"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True)
        task_id = Column(String)
        task_name = Column(String)
        event_type = Column(String)
        hostname = Column(String)
        worker_name = Column(String)
        timestamp = Column(DateTime)
        args = Column(JSON)
        kwargs = Column(JSON)
        result = Column(Text)
        exception = Column(Text)
        traceback = Column(Text)
        runtime = Column(Float)
        retries = Column(Integer)
        retry_count = Column(Integer)
        retry_of = Column(String)
        retried_by = Column(String)
        has_retries = Column(Boolean, default=False)
        is_retry = Column(Boolean, default=False)
        is_orphan = Column(Boolean, default=False)
        orphaned_at = Column(DateTime)
        parent_id = Column(String)
        root_id = Column(String)
        queue = Column(String)
        exchange = Column(String)
        routing_key = Column(String)
        eta = Column(DateTime)
        expires = Column(DateTime)
    else:
        id: Any = None
        task_id: Any = None
        task_name: Any = None
        event_type: Any = None
        hostname: Any = None
        worker_name: Any = None
        timestamp: Any = None
        args: Any = None
        kwargs: Any = None
        result: Any = None
        exception: Any = None
        traceback: Any = None
        runtime: Any = None
        retries: Any = None
        retry_count: Any = None
        retry_of: Any = None
        retried_by: Any = None
        has_retries: Any = None
        is_retry: Any = None
        is_orphan: Any = None
        orphaned_at: Any = None
        parent_id: Any = None
        root_id: Any = None
        queue: Any = None
        exchange: Any = None
        routing_key: Any = None
        eta: Any = None
        expires: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "event_type": self.event_type,
            "hostname": self.hostname,
            "worker_name": self.worker_name,
            "timestamp": self.timestamp,
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
            "orphaned_at": self.orphaned_at,
            "parent_id": self.parent_id,
            "root_id": self.root_id,
            "queue": self.queue,
            "exchange": self.exchange,
            "routing_key": self.routing_key,
            "eta": self.eta,
            "expires": self.expires,
        }


class TaskLatestDB(_Base):
    __tablename__ = "task_latest"

    if _SA_AVAILABLE:
        task_id = Column(String, primary_key=True)
        task_name = Column(String)
        event_id = Column(Integer)
        event_type = Column(String)
        hostname = Column(String)
        worker_name = Column(String)
        timestamp = Column(DateTime)
        args = Column(JSON)
        kwargs = Column(JSON)
        result = Column(Text)
        exception = Column(Text)
        traceback = Column(Text)
        runtime = Column(Float)
        retries = Column(Integer)
        retry_count = Column(Integer)
        retry_of = Column(String)
        retried_by = Column(String)
        has_retries = Column(Boolean, default=False)
        is_retry = Column(Boolean, default=False)
        is_orphan = Column(Boolean, default=False)
        orphaned_at = Column(DateTime)
        parent_id = Column(String)
        root_id = Column(String)
        queue = Column(String)
        exchange = Column(String)
        routing_key = Column(String)
        eta = Column(DateTime)
        expires = Column(DateTime)
        resolved = Column(Boolean, default=False)
        resolved_at = Column(DateTime)
        resolved_by = Column(String)
    else:
        task_id: Any = None
        task_name: Any = None
        event_id: Any = None
        event_type: Any = None
        hostname: Any = None
        worker_name: Any = None
        timestamp: Any = None
        args: Any = None
        kwargs: Any = None
        result: Any = None
        exception: Any = None
        traceback: Any = None
        runtime: Any = None
        retries: Any = None
        retry_count: Any = None
        retry_of: Any = None
        retried_by: Any = None
        has_retries: Any = None
        is_retry: Any = None
        is_orphan: Any = None
        orphaned_at: Any = None
        parent_id: Any = None
        root_id: Any = None
        queue: Any = None
        exchange: Any = None
        routing_key: Any = None
        eta: Any = None
        expires: Any = None
        resolved: Any = None
        resolved_at: Any = None
        resolved_by: Any = None


class TaskProgressDB(_Base):
    __tablename__ = "task_progress"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True)
        task_id = Column(String)
        task_name = Column(String)
        progress = Column(Float)
        message = Column(Text)
        step_key = Column(String)
        meta = Column(JSON)
        timestamp = Column(DateTime)
    else:
        id: Any = None
        task_id: Any = None
        task_name: Any = None
        progress: Any = None
        message: Any = None
        step_key: Any = None
        meta: Any = None
        timestamp: Any = None

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


class TaskProgressLatestDB(_Base):
    __tablename__ = "task_progress_latest"

    if _SA_AVAILABLE:
        task_id = Column(String, primary_key=True)
        task_name = Column(String)
        progress = Column(Float)
        message = Column(Text)
        step_key = Column(String)
        meta = Column(JSON)
        updated_at = Column(DateTime)
    else:
        task_id: Any = None
        task_name: Any = None
        progress: Any = None
        message: Any = None
        step_key: Any = None
        meta: Any = None
        updated_at: Any = None

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


class TaskRegistryDB(_Base):
    __tablename__ = "task_registry"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True)
        name = Column(String)
        human_readable_name = Column(String)
        description = Column(Text)
        tags = Column(JSON)
        first_seen = Column(DateTime)
        last_seen = Column(DateTime)
        created_at = Column(DateTime)
        updated_at = Column(DateTime)
    else:
        id: Any = None
        name: Any = None
        human_readable_name: Any = None
        description: Any = None
        tags: Any = None
        first_seen: Any = None
        last_seen: Any = None
        created_at: Any = None
        updated_at: Any = None

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


class TaskRerunRelationshipDB(_Base):
    __tablename__ = "task_rerun_relationships"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True)
        original_task_id = Column(String)
        rerun_task_id = Column(String)
        action_id = Column(Integer)
        created_by = Column(String)
        created_at = Column(DateTime)
    else:
        id: Any = None
        original_task_id: Any = None
        rerun_task_id: Any = None
        action_id: Any = None
        created_by: Any = None
        created_at: Any = None


class TaskResolutionDB(_Base):
    __tablename__ = "task_resolutions"

    if _SA_AVAILABLE:
        task_id = Column(String, primary_key=True)
        resolved = Column(Boolean, default=False)
        resolved_at = Column(DateTime)
        resolved_by = Column(String)
    else:
        task_id: Any = None
        resolved: Any = None
        resolved_at: Any = None
        resolved_by: Any = None


class TaskStepsDB(_Base):
    __tablename__ = "task_steps"

    if _SA_AVAILABLE:
        task_id = Column(String, primary_key=True)
        task_name = Column(String)
        steps = Column(JSON)
        defined_at = Column(DateTime)
    else:
        task_id: Any = None
        task_name: Any = None
        steps: Any = None
        defined_at: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "steps": self.steps,
            "defined_at": self.defined_at,
        }


class UserDB(_Base):
    __tablename__ = "users"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True)
        email = Column(String)
        name = Column(String)
        avatar_url = Column(String)
        provider = Column(String)
        provider_account_id = Column(String)
        is_active = Column(Boolean, default=True)
        last_login_at = Column(DateTime)
        created_at = Column(DateTime)
        updated_at = Column(DateTime)
    else:
        id: Any = None
        email: Any = None
        name: Any = None
        avatar_url: Any = None
        provider: Any = None
        provider_account_id: Any = None
        is_active: Any = None
        last_login_at: Any = None
        created_at: Any = None
        updated_at: Any = None

    sessions: Any = None

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
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class UserSessionDB(_Base):
    __tablename__ = "user_sessions"

    if _SA_AVAILABLE:
        session_id = Column(String, primary_key=True)
        user_id = Column(Integer)
        auth_provider = Column(String)
        access_token_hash = Column(String)
        access_token_expires_at = Column(DateTime)
        refresh_token_hash = Column(String)
        refresh_token_expires_at = Column(DateTime)
        token_scopes = Column(JSON)
        active_environment_id = Column(Integer)
        preferences = Column(JSON)
        last_active = Column(DateTime)
        created_at = Column(DateTime)
    else:
        session_id: Any = None
        user_id: Any = None
        auth_provider: Any = None
        access_token_hash: Any = None
        access_token_expires_at: Any = None
        refresh_token_hash: Any = None
        refresh_token_expires_at: Any = None
        token_scopes: Any = None
        active_environment_id: Any = None
        preferences: Any = None
        last_active: Any = None
        created_at: Any = None

    user: Any = None

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


class WorkerEventDB(_Base):
    __tablename__ = "worker_events"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True)
        hostname = Column(String)
        event_type = Column(String)
        status = Column(String)
        active_tasks = Column(Integer, default=0)
        processed = Column(Integer, default=0)
        timestamp = Column(DateTime)
    else:
        id: Any = None
        hostname: Any = None
        event_type: Any = None
        status: Any = None
        active_tasks: Any = None
        processed: Any = None
        timestamp: Any = None

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


class WorkflowDB(_Base):
    __tablename__ = "workflows"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True)
        name = Column(String)
        description = Column(Text)
        trigger_type = Column(String)
        trigger_config = Column(JSON)
        conditions = Column(JSON)
        actions = Column(JSON)
        enabled = Column(Boolean, default=True)
        priority = Column(Integer, default=0)
        cooldown_seconds = Column(Integer, default=0)
        max_executions_per_hour = Column(Integer)
        circuit_breaker_config = Column(JSON)
        execution_count = Column(Integer, default=0)
        success_count = Column(Integer, default=0)
        failure_count = Column(Integer, default=0)
        last_executed_at = Column(DateTime)
        created_by = Column(String)
        created_at = Column(DateTime)
        updated_at = Column(DateTime)
    else:
        id: Any = None
        name: Any = None
        description: Any = None
        trigger_type: Any = None
        trigger_config: Any = None
        conditions: Any = None
        actions: Any = None
        enabled: Any = None
        priority: Any = None
        cooldown_seconds: Any = None
        max_executions_per_hour: Any = None
        circuit_breaker_config: Any = None
        execution_count: Any = None
        success_count: Any = None
        failure_count: Any = None
        last_executed_at: Any = None
        created_by: Any = None
        created_at: Any = None
        updated_at: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger_type": self.trigger_type,
            "trigger_config": self.trigger_config,
            "conditions": self.conditions,
            "actions": self.actions,
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


class WorkflowExecutionDB(_Base):
    __tablename__ = "workflow_executions"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True)
        workflow_id = Column(Integer)
        trigger_type = Column(String)
        trigger_event = Column(JSON)
        triggered_at = Column(DateTime)
        started_at = Column(DateTime)
        completed_at = Column(DateTime)
        status = Column(String)
        actions_executed = Column(JSON)
        error_message = Column(Text)
        stack_trace = Column(Text)
        duration_ms = Column(Integer)
        circuit_breaker_key = Column(String)
        workflow_snapshot = Column(JSON)
    else:
        id: Any = None
        workflow_id: Any = None
        trigger_type: Any = None
        trigger_event: Any = None
        triggered_at: Any = None
        started_at: Any = None
        completed_at: Any = None
        status: Any = None
        actions_executed: Any = None
        error_message: Any = None
        stack_trace: Any = None
        duration_ms: Any = None
        circuit_breaker_key: Any = None
        workflow_snapshot: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "trigger_type": self.trigger_type,
            "trigger_event": self.trigger_event,
            "triggered_at": self.triggered_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "actions_executed": self.actions_executed,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "duration_ms": self.duration_ms,
            "circuit_breaker_key": self.circuit_breaker_key,
            "workflow_snapshot": self.workflow_snapshot,
        }


# ---------------------------------------------------------------------------
# DatabaseManager
# ---------------------------------------------------------------------------
class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url: str = database_url
        self.engine: Any = None
        self.SessionLocal: Any = None
        self._initialize()

    def _initialize(self) -> None:
        if _SA_AVAILABLE:
            self.engine = create_engine(self.database_url)
            self.SessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=self.engine
            )

    def get_session(self) -> Any:
        if self.SessionLocal is None:
            raise RuntimeError("Database not initialised")
        return self.SessionLocal()

    def run_migrations(self) -> None:
        if _SA_AVAILABLE and self.engine is not None:
            _Base.metadata.create_all(bind=self.engine)


# ---------------------------------------------------------------------------
# CeleryEventMonitor
# ---------------------------------------------------------------------------
class CeleryEventMonitor:
    def __init__(self, broker_url: str, app: Any = None):
        self.broker_url: str = broker_url
        self.app: Any = app
        self.state: None = None
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

    def stop(self) -> None:
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

    async def connect(self, websocket: WebSocket) -> None:
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
                self.message_queue.put_nowait(("task", task_event))
            except asyncio.QueueFull:
                pass

    def queue_worker_broadcast(self, worker_event: WorkerEvent) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait(("worker", worker_event))
            except asyncio.QueueFull:
                pass

    def queue_progress_broadcast(self, progress_event: Any) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait(("progress", progress_event))
            except asyncio.QueueFull:
                pass

    def queue_task_action_broadcast(self, action_event: Any) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait(("action", action_event))
            except asyncio.QueueFull:
                pass

    async def start_background_broadcaster(self) -> None:
        self.message_queue = asyncio.Queue()

        async def _broadcast_loop() -> None:
            while True:
                try:
                    item = await self.message_queue.get()
                    if item is None:
                        break
                    event_type, event = item
                    dead: List[WebSocket] = []
                    for ws in list(self.active_connections):
                        try:
                            await ws.send_text(str(event))
                        except Exception:
                            dead.append(ws)
                    for ws in dead:
                        self.disconnect(ws)
                except asyncio.CancelledError:
                    break
                except Exception:
                    pass

        self._broadcaster_task = asyncio.ensure_future(_broadcast_loop())

    async def stop_background_broadcaster(self) -> None:
        if self.message_queue is not None:
            await self.message_queue.put(None)
        if self._broadcaster_task is not None:
            self._broadcaster_task.cancel()
            try:
                await self._broadcaster_task
            except asyncio.CancelledError:
                pass
            self._broadcaster_task = None


# ---------------------------------------------------------------------------
# EventHandler
# ---------------------------------------------------------------------------
class EventHandler:
    def __init__(self, connection_manager: ConnectionManager, db_manager: DatabaseManager):
        self.connection_manager: ConnectionManager = connection_manager
        self.db_manager: DatabaseManager = db_manager
        self.workflow_engine: None = None

    def handle_task_event(self, task_event: TaskEvent) -> None:
        self.connection_manager.queue_broadcast(task_event)

    def handle_worker_event(self, worker_event: WorkerEvent) -> None:
        self.connection_manager.queue_worker_broadcast(worker_event)

    def handle_progress_event(self, progress_event: Any) -> None:
        self.connection_manager.queue_progress_broadcast(progress_event)

    def handle_steps_event(self, steps_event: Any) -> None:
        self.connection_manager.queue_progress_broadcast(steps_event)


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
        ...

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        ...

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        def _replacer(match: re.Match) -> str:
            key = match.group(1).strip()
            parts = key.split(".")
            value: Any = context
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, "")
                else:
                    value = getattr(value, part, "")
            return str(value)

        return re.sub(r"\{\{(.*?)\}\}", _replacer, template)


# ---------------------------------------------------------------------------
# RetryActionHandler
# ---------------------------------------------------------------------------
class RetryActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "task_id" not in params:
            return False, "Missing required parameter: task_id"
        if not isinstance(params["task_id"], str) or not params["task_id"].strip():
            return False, "Parameter 'task_id' must be a non-empty string"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        valid, error = self.validate_params(params)
        if not valid:
            return ActionResult(success=False, message=error)

        task_id: str = params["task_id"]
        queue: Optional[str] = params.get("queue")
        countdown: Optional[int] = params.get("countdown")

        try:
            retry_data: Dict[str, Any] = {
                "task_id": task_id,
                "queue": queue,
                "countdown": countdown,
            }
            return ActionResult(
                success=True,
                message=f"Retry initiated for task {task_id}",
                data=retry_data,
            )
        except Exception as exc:
            return ActionResult(success=False, message=str(exc))


# ---------------------------------------------------------------------------
# SlackActionHandler
# ---------------------------------------------------------------------------
class SlackActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "webhook_url" not in params:
            return False, "Missing required parameter: webhook_url"
        if "message" not in params:
            return False, "Missing required parameter: message"
        if not isinstance(params["webhook_url"], str) or not params["webhook_url"].strip():
            return False, "Parameter 'webhook_url' must be a non-empty string"
        if not isinstance(params["message"], str) or not params["message"].strip():
            return False, "Parameter 'message' must be a non-empty string"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        valid, error = self.validate_params(params)
        if not valid:
            return ActionResult(success=False, message=error)

        webhook_url: str = params["webhook_url"]
        raw_message: str = params["message"]
        rendered_message: str = self.render_template(raw_message, context)

        try:
            import urllib.request
            import json as _json

            payload = _json.dumps({"text": rendered_message}).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                status_code: int = resp.status

            if status_code == 200:
                return ActionResult(
                    success=True,
                    message="Slack message sent successfully",
                    data={"status_code": status_code, "message": rendered_message},
                )
            return ActionResult(
                success=False,
                message=f"Slack webhook returned status {status_code}",
                data={"status_code": status_code},
            )
        except Exception as exc:
            return ActionResult(success=False, message=str(exc))