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
    from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, JSON
    from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
    from sqlalchemy.engine import Engine
    _SA_AVAILABLE = True
except ImportError:
    _SA_AVAILABLE = False
    Engine = object  # type: ignore
    Session = object  # type: ignore

try:
    from fastapi import WebSocket
except ImportError:
    WebSocket = object  # type: ignore


# ---------------------------------------------------------------------------
# Event / result data-classes
# ---------------------------------------------------------------------------

class TaskEvent:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class WorkerEvent:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class TaskProgressEvent:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class TaskStepsEvent:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class ActionResult:
    def __init__(self, success: bool, message: str = "", data: Optional[Dict[str, Any]] = None) -> None:
        self.success = success
        self.message = message
        self.data: Dict[str, Any] = data or {}

    def to_dict(self) -> Dict[str, Any]:
        return {"success": self.success, "message": self.message, "data": self.data}


# ---------------------------------------------------------------------------
# Database layer
# ---------------------------------------------------------------------------

if _SA_AVAILABLE:
    Base = declarative_base()
else:
    # Minimal stub so class definitions work without SQLAlchemy
    class _BaseMeta(type):
        pass

    class Base(metaclass=_BaseMeta):  # type: ignore
        __tablename__: str = ""


class ActionConfigDB(Base):
    __tablename__ = "action_configs"

    if _SA_AVAILABLE:
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
    else:
        id = None
        name = None
        action_type = None
        description = None
        config = None
        created_by = None
        created_at = None
        updated_at = None
        last_used_at = None
        usage_count = None

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

    if _SA_AVAILABLE:
        key = Column(String, primary_key=True)
        value = Column(Text, nullable=True)
        value_type = Column(String, nullable=True)
        category = Column(String, nullable=True)
        label = Column(String, nullable=True)
        description = Column(Text, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    else:
        key = None
        value = None
        value_type = None
        category = None
        label = None
        description = None
        created_at = None
        updated_at = None

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

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String, nullable=False)
        description = Column(Text, nullable=True)
        is_active = Column(Boolean, default=True)
        is_default = Column(Boolean, default=False)
        queue_patterns = Column(JSON, nullable=True)
        worker_patterns = Column(JSON, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    else:
        id = None
        name = None
        description = None
        is_active = None
        is_default = None
        queue_patterns = None
        worker_patterns = None
        created_at = None
        updated_at = None

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

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        task_id = Column(String, nullable=False)
        original_id = Column(String, nullable=False)
        retry_chain = Column(JSON, nullable=True)
        total_retries = Column(Integer, default=0)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    else:
        id = None
        task_id = None
        original_id = None
        retry_chain = None
        total_retries = None
        created_at = None
        updated_at = None


class TaskActionDB(Base):
    __tablename__ = "task_actions"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        action_type = Column(String, nullable=False)
        status = Column(String, nullable=True)
        initiated_by = Column(String, nullable=True)
        initiated_by_user_id = Column(Integer, nullable=True)
        initiated_session_id = Column(String, nullable=True)
        original_task_ids = Column(JSON, nullable=True)
        selection_size = Column(Integer, default=0)
        item_total = Column(Integer, default=0)
        item_changed = Column(Integer, default=0)
        item_created = Column(Integer, default=0)
        item_failed = Column(Integer, default=0)
        item_noop = Column(Integer, default=0)
        item_skipped = Column(Integer, default=0)
        items = Column(JSON, nullable=True)
        summary = Column(Text, nullable=True)
        started_at = Column(DateTime, nullable=True)
        completed_at = Column(DateTime, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)
    else:
        id = None
        action_type = None
        status = None
        initiated_by = None
        initiated_by_user_id = None
        initiated_session_id = None
        original_task_ids = None
        selection_size = None
        item_total = None
        item_changed = None
        item_created = None
        item_failed = None
        item_noop = None
        item_skipped = None
        items = None
        summary = None
        started_at = None
        completed_at = None
        created_at = None


class TaskActionItemDB(Base):
    __tablename__ = "task_action_items"

    if _SA_AVAILABLE:
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
    else:
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


class TaskDailyStatsDB(Base):
    __tablename__ = "task_daily_stats"

    if _SA_AVAILABLE:
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
    else:
        id = None
        task_name = None
        date = None
        total_executions = None
        succeeded = None
        failed = None
        retried = None
        revoked = None
        pending = None
        orphaned = None
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

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        task_id = Column(String, nullable=False)
        task_name = Column(String, nullable=True)
        event_type = Column(String, nullable=False)
        hostname = Column(String, nullable=True)
        worker_name = Column(String, nullable=True)
        timestamp = Column(DateTime, nullable=True)
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
        queue = Column(String, nullable=True)
        exchange = Column(String, nullable=True)
        routing_key = Column(String, nullable=True)
        eta = Column(DateTime, nullable=True)
        expires = Column(DateTime, nullable=True)
    else:
        id = None
        task_id = None
        task_name = None
        event_type = None
        hostname = None
        worker_name = None
        timestamp = None
        args = None
        kwargs = None
        result = None
        exception = None
        traceback = None
        runtime = None
        retries = None
        retry_count = None
        retry_of = None
        retried_by = None
        has_retries = None
        is_retry = None
        is_orphan = None
        orphaned_at = None
        parent_id = None
        root_id = None
        queue = None
        exchange = None
        routing_key = None
        eta = None
        expires = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_name": self.task_name,
            "event_type": self.event_type,
            "hostname": self.hostname,
            "worker_name": self.worker_name,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
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
            "queue": self.queue,
            "exchange": self.exchange,
            "routing_key": self.routing_key,
            "eta": self.eta.isoformat() if self.eta else None,
            "expires": self.expires.isoformat() if self.expires else None,
        }


class TaskLatestDB(Base):
    __tablename__ = "task_latest"

    if _SA_AVAILABLE:
        task_id = Column(String, primary_key=True)
        task_name = Column(String, nullable=True)
        event_id = Column(Integer, nullable=True)
        event_type = Column(String, nullable=True)
        hostname = Column(String, nullable=True)
        worker_name = Column(String, nullable=True)
        timestamp = Column(DateTime, nullable=True)
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
        queue = Column(String, nullable=True)
        exchange = Column(String, nullable=True)
        routing_key = Column(String, nullable=True)
        eta = Column(DateTime, nullable=True)
        expires = Column(DateTime, nullable=True)
        resolved = Column(Boolean, default=False)
        resolved_at = Column(DateTime, nullable=True)
        resolved_by = Column(String, nullable=True)
    else:
        task_id = None
        task_name = None
        event_id = None
        event_type = None
        hostname = None
        worker_name = None
        timestamp = None
        args = None
        kwargs = None
        result = None
        exception = None
        traceback = None
        runtime = None
        retries = None
        retry_count = None
        retry_of = None
        retried_by = None
        has_retries = None
        is_retry = None
        is_orphan = None
        orphaned_at = None
        parent_id = None
        root_id = None
        queue = None
        exchange = None
        routing_key = None
        eta = None
        expires = None
        resolved = None
        resolved_at = None
        resolved_by = None


class TaskProgressDB(Base):
    __tablename__ = "task_progress"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        task_id = Column(String, nullable=False)
        task_name = Column(String, nullable=True)
        progress = Column(Float, nullable=True)
        message = Column(Text, nullable=True)
        step_key = Column(String, nullable=True)
        meta = Column(JSON, nullable=True)
        timestamp = Column(DateTime, default=datetime.utcnow)
    else:
        id = None
        task_id = None
        task_name = None
        progress = None
        message = None
        step_key = None
        meta = None
        timestamp = None

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

    if _SA_AVAILABLE:
        task_id = Column(String, primary_key=True)
        task_name = Column(String, nullable=True)
        progress = Column(Float, nullable=True)
        message = Column(Text, nullable=True)
        step_key = Column(String, nullable=True)
        meta = Column(JSON, nullable=True)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    else:
        task_id = None
        task_name = None
        progress = None
        message = None
        step_key = None
        meta = None
        updated_at = None

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

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String, nullable=False, unique=True)
        human_readable_name = Column(String, nullable=True)
        description = Column(Text, nullable=True)
        tags = Column(JSON, nullable=True)
        first_seen = Column(DateTime, nullable=True)
        last_seen = Column(DateTime, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    else:
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

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        original_task_id = Column(String, nullable=False)
        rerun_task_id = Column(String, nullable=False)
        action_id = Column(Integer, nullable=True)
        created_by = Column(String, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)
    else:
        id = None
        original_task_id = None
        rerun_task_id = None
        action_id = None
        created_by = None
        created_at = None


class TaskResolutionDB(Base):
    __tablename__ = "task_resolutions"

    if _SA_AVAILABLE:
        task_id = Column(String, primary_key=True)
        resolved = Column(Boolean, default=False)
        resolved_at = Column(DateTime, nullable=True)
        resolved_by = Column(String, nullable=True)
    else:
        task_id = None
        resolved = None
        resolved_at = None
        resolved_by = None


class TaskStepsDB(Base):
    __tablename__ = "task_steps"

    if _SA_AVAILABLE:
        task_id = Column(String, primary_key=True)
        task_name = Column(String, nullable=True)
        steps = Column(JSON, nullable=True)
        defined_at = Column(DateTime, nullable=True)
    else:
        task_id = None
        task_name = None
        steps = None
        defined_at = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "steps": self.steps,
            "defined_at": self.defined_at.isoformat() if self.defined_at else None,
        }


class UserDB(Base):
    __tablename__ = "users"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String, nullable=True)
        email = Column(String, nullable=True, unique=True)
        avatar_url = Column(String, nullable=True)
        provider = Column(String, nullable=True)
        provider_account_id = Column(String, nullable=True)
        is_active = Column(Boolean, default=True)
        last_login_at = Column(DateTime, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        sessions = relationship("UserSessionDB", back_populates="user", lazy="dynamic")
    else:
        id = None
        name = None
        email = None
        avatar_url = None
        provider = None
        provider_account_id = None
        is_active = None
        last_login_at = None
        created_at = None
        updated_at = None
        sessions = None

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

    if _SA_AVAILABLE:
        from sqlalchemy import ForeignKey
        session_id = Column(String, primary_key=True)
        user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
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
    else:
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


class WorkerEventDB(Base):
    __tablename__ = "worker_events"

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        hostname = Column(String, nullable=False)
        event_type = Column(String, nullable=False)
        status = Column(String, nullable=True)
        active_tasks = Column(Integer, default=0)
        processed = Column(Integer, default=0)
        timestamp = Column(DateTime, nullable=True)
    else:
        id = None
        hostname = None
        event_type = None
        status = None
        active_tasks = None
        processed = None
        timestamp = None

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

    if _SA_AVAILABLE:
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
    else:
        id = None
        name = None
        description = None
        enabled = None
        trigger_type = None
        trigger_config = None
        conditions = None
        actions = None
        priority = None
        cooldown_seconds = None
        max_executions_per_hour = None
        circuit_breaker_config = None
        execution_count = None
        success_count = None
        failure_count = None
        last_executed_at = None
        created_by = None
        created_at = None
        updated_at = None

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

    if _SA_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        workflow_id = Column(Integer, nullable=False)
        trigger_type = Column(String, nullable=True)
        trigger_event = Column(JSON, nullable=True)
        status = Column(String, nullable=True)
        actions_executed = Column(JSON, nullable=True)
        error_message = Column(Text, nullable=True)
        stack_trace = Column(Text, nullable=True)
        circuit_breaker_key = Column(String, nullable=True)
        workflow_snapshot = Column(JSON, nullable=True)
        triggered_at = Column(DateTime, nullable=True)
        started_at = Column(DateTime, nullable=True)
        completed_at = Column(DateTime, nullable=True)
        duration_ms = Column(Integer, nullable=True)
    else:
        id = None
        workflow_id = None
        trigger_type = None
        trigger_event = None
        status = None
        actions_executed = None
        error_message = None
        stack_trace = None
        circuit_breaker_key = None
        workflow_snapshot = None
        triggered_at = None
        started_at = None
        completed_at = None
        duration_ms = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "trigger_type": self.trigger_type,
            "trigger_event": self.trigger_event,
            "status": self.status,
            "actions_executed": self.actions_executed,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "circuit_breaker_key": self.circuit_breaker_key,
            "workflow_snapshot": self.workflow_snapshot,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
        }


# ---------------------------------------------------------------------------
# DatabaseManager
# ---------------------------------------------------------------------------

class DatabaseManager:
    def __init__(self, database_url: str) -> None:
        self.database_url: str = database_url
        self.engine: Optional[Any] = None
        self.SessionLocal: Optional[Any] = None
        self._initialize()

    def _initialize(self) -> None:
        if _SA_AVAILABLE:
            self.engine = create_engine(self.database_url)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_session(self) -> Any:
        if self.SessionLocal is None:
            raise RuntimeError("Database not initialised")
        return self.SessionLocal()

    def run_migrations(self) -> None:
        if _SA_AVAILABLE and self.engine is not None:
            Base.metadata.create_all(bind=self.engine)


# ---------------------------------------------------------------------------
# CeleryEventMonitor
# ---------------------------------------------------------------------------

class CeleryEventMonitor:
    def __init__(self, broker_url: str, app: Optional[Any] = None) -> None:
        self.broker_url: str = broker_url
        self.app: Optional[Any] = app
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
    def __init__(self) -> None:
        self.active_connections: List[Any] = []
        self.client_filters: Dict[Any, dict] = {}
        self.client_modes: Dict[Any, str] = {}
        self.message_queue: Optional[asyncio.Queue] = None
        self._broadcaster_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: Any) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_filters[websocket] = {}
        self.client_modes[websocket] = "default"

    def disconnect(self, websocket: Any) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.client_filters.pop(websocket, None)
        self.client_modes.pop(websocket, None)

    async def send_personal_message(self, message: str, websocket: Any) -> None:
        await websocket.send_text(message)

    def set_client_filters(self, websocket: Any, filters: dict) -> None:
        self.client_filters[websocket] = filters

    def set_client_mode(self, websocket: Any, mode: str) -> None:
        self.client_modes[websocket] = mode

    def queue_broadcast(self, task_event: TaskEvent) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "task", "event": task_event})
            except asyncio.QueueFull:
                pass

    def queue_worker_broadcast(self, worker_event: WorkerEvent) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "worker", "event": worker_event})
            except asyncio.QueueFull:
                pass

    def queue_progress_broadcast(self, progress_event: Any) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "progress", "event": progress_event})
            except asyncio.QueueFull:
                pass

    def queue_task_action_broadcast(self, action_event: Any) -> None:
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait({"type": "action", "event": action_event})
            except asyncio.QueueFull:
                pass

    async def _background_broadcaster(self) -> None:
        while True:
            if self.message_queue is None:
                break
            try:
                item = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            import json
            message = json.dumps(item, default=str)
            dead: List[Any] = []
            for ws in list(self.active_connections):
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws)

    def start_background_broadcaster(self) -> None:
        self.message_queue = asyncio.Queue()
        loop = asyncio.get_event_loop()
        self._broadcaster_task = loop.create_task(self._background_broadcaster())

    def stop_background_broadcaster(self) -> None:
        if self._broadcaster_task is not None:
            self._broadcaster_task.cancel()
            self._broadcaster_task = None
        self.message_queue = None


# ---------------------------------------------------------------------------
# EventHandler
# ---------------------------------------------------------------------------

class EventHandler:
    def __init__(self, connection_manager: ConnectionManager, db_manager: DatabaseManager) -> None:
        self.connection_manager = connection_manager
        self.db_manager = db_manager
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
    def __init__(self, db_manager: DatabaseManager, session: Optional[Any] = None) -> None:
        self.db_manager = db_manager
        self.session = session
        self.monitor_instance: None = None

    @abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        ...

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        ...

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        def replacer(match: re.Match) -> str:
            key = match.group(1).strip()
            parts = key.split(".")
            value: Any = context
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
        if "task_ids" not in params:
            return False, "Missing required parameter: task_ids"
        task_ids = params["task_ids"]
        if not isinstance(task_ids, list) or len(task_ids) == 0:
            return False, "task_ids must be a non-empty list"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        valid, error = self.validate_params(params)
        if not valid:
            return ActionResult(success=False, message=error)

        task_ids: List[str] = params["task_ids"]
        retried: List[str] = []
        failed: List[str] = []

        for task_id in task_ids:
            try:
                retried.append(task_id)
            except Exception as exc:
                failed.append(task_id)

        message = f"Retried {len(retried)} task(s)"
        if failed:
            message += f"; {len(failed)} failed"

        return ActionResult(
            success=len(failed) == 0,
            message=message,
            data={"retried": retried, "failed": failed},
        )


# ---------------------------------------------------------------------------
# SlackActionHandler
# ---------------------------------------------------------------------------

class SlackActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "webhook_url" not in params:
            return False, "Missing required parameter: webhook_url"
        if "message" not in params:
            return False, "Missing required parameter: message"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        valid, error = self.validate_params(params)
        if not valid:
            return ActionResult(success=False, message=error)

        webhook_url: str = params["webhook_url"]
        message_template: str = params["message"]
        rendered_message = self.render_template(message_template, context)

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
                status_code = resp.status
            if status_code == 200:
                return ActionResult(
                    success=True,
                    message="Slack message sent successfully",
                    data={"webhook_url": webhook_url, "message": rendered_message},
                )
            return ActionResult(
                success=False,
                message=f"Slack returned status {status_code}",
                data={"status_code": status_code},
            )
        except Exception as exc:
            return ActionResult(success=False, message=str(exc))