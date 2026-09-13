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
# Simple named-tuple / dataclass stand-ins for event types referenced in sigs
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

    def to_dict(self) -> Dict[str, Any]:
        return {"success": self.success, "message": self.message, "data": self.data}


# ---------------------------------------------------------------------------
# Minimal SQLAlchemy-like stubs so the DB models work without a real install
# ---------------------------------------------------------------------------

try:
    from sqlalchemy import (
        Column, Integer, String, Boolean, Float, DateTime, Text, JSON,
        ForeignKey, create_engine
    )
    from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
    from sqlalchemy.engine import Engine
    _SQLALCHEMY_AVAILABLE = True
except ImportError:
    _SQLALCHEMY_AVAILABLE = False

    class _FakeColumn:
        def __init__(self, *args, **kwargs):
            pass

    Column = _FakeColumn

    class _FakeMeta(type):
        def __new__(mcs, name, bases, namespace):
            cls = super().__new__(mcs, name, bases, namespace)
            return cls

    class _Base(metaclass=_FakeMeta):
        __tablename__ = ""
        metadata = None

        @classmethod
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)

    def declarative_base():
        return _Base

    class sessionmaker:
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, *args, **kwargs):
            return None

    class Session:
        pass

    class Engine:
        pass

    def create_engine(*args, **kwargs):
        return None

    Integer = String = Boolean = Float = DateTime = Text = JSON = ForeignKey = None

    def relationship(*args, **kwargs):
        return None


if _SQLALCHEMY_AVAILABLE:
    Base = declarative_base()
else:
    Base = declarative_base()


# ---------------------------------------------------------------------------
# Database Models
# ---------------------------------------------------------------------------

class ActionConfigDB(Base):
    __tablename__ = "action_configs"

    if _SQLALCHEMY_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String, nullable=False)
        action_type = Column(String, nullable=False)
        description = Column(Text, nullable=True)
        config = Column(JSON, nullable=True)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)
        last_used_at = Column(DateTime, nullable=True)
        usage_count = Column(Integer, default=0)
        created_by = Column(String, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": getattr(self, "id", None),
            "name": getattr(self, "name", None),
            "action_type": getattr(self, "action_type", None),
            "description": getattr(self, "description", None),
            "config": getattr(self, "config", None),
            "created_at": str(getattr(self, "created_at", None)),
            "updated_at": str(getattr(self, "updated_at", None)),
            "last_used_at": str(getattr(self, "last_used_at", None)),
            "usage_count": getattr(self, "usage_count", 0),
            "created_by": getattr(self, "created_by", None),
        }


class AppSettingDB(Base):
    __tablename__ = "app_settings"

    if _SQLALCHEMY_AVAILABLE:
        key = Column(String, primary_key=True)
        value = Column(Text, nullable=True)
        value_type = Column(String, nullable=True)
        label = Column(String, nullable=True)
        description = Column(Text, nullable=True)
        category = Column(String, nullable=True)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": getattr(self, "key", None),
            "value": getattr(self, "value", None),
            "value_type": getattr(self, "value_type", None),
            "label": getattr(self, "label", None),
            "description": getattr(self, "description", None),
            "category": getattr(self, "category", None),
            "created_at": str(getattr(self, "created_at", None)),
            "updated_at": str(getattr(self, "updated_at", None)),
        }


class EnvironmentDB(Base):
    __tablename__ = "environments"

    if _SQLALCHEMY_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String, nullable=False)
        description = Column(Text, nullable=True)
        is_active = Column(Boolean, default=True)
        is_default = Column(Boolean, default=False)
        queue_patterns = Column(JSON, nullable=True)
        worker_patterns = Column(JSON, nullable=True)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": getattr(self, "id", None),
            "name": getattr(self, "name", None),
            "description": getattr(self, "description", None),
            "is_active": getattr(self, "is_active", True),
            "is_default": getattr(self, "is_default", False),
            "queue_patterns": getattr(self, "queue_patterns", None),
            "worker_patterns": getattr(self, "worker_patterns", None),
            "created_at": str(getattr(self, "created_at", None)),
            "updated_at": str(getattr(self, "updated_at", None)),
        }


class RetryRelationshipDB(Base):
    __tablename__ = "retry_relationships"

    if _SQLALCHEMY_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        task_id = Column(String, nullable=False)
        original_id = Column(String, nullable=True)
        retry_chain = Column(JSON, nullable=True)
        total_retries = Column(Integer, default=0)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TaskActionDB(Base):
    __tablename__ = "task_actions"

    if _SQLALCHEMY_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        action_type = Column(String, nullable=False)
        status = Column(String, nullable=True)
        initiated_by = Column(String, nullable=True)
        initiated_by_user_id = Column(Integer, nullable=True)
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

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TaskActionItemDB(Base):
    __tablename__ = "task_action_items"

    if _SQLALCHEMY_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        action_id = Column(Integer, ForeignKey("task_actions.id"), nullable=True)
        action = Column(String, nullable=True)
        original_task_id = Column(String, nullable=True)
        original_task_name = Column(String, nullable=True)
        attempted_task_id = Column(String, nullable=True)
        rerun_task_id = Column(String, nullable=True)
        rerun_task_name = Column(String, nullable=True)
        rerun_kind = Column(String, nullable=True)
        outcome = Column(String, nullable=True)
        reason = Column(Text, nullable=True)
        reason_code = Column(String, nullable=True)
        skip_category = Column(String, nullable=True)
        target_queue = Column(String, nullable=True)
        submitted_args = Column(JSON, nullable=True)
        submitted_kwargs = Column(JSON, nullable=True)
        review_fingerprint = Column(String, nullable=True)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TaskDailyStatsDB(Base):
    __tablename__ = "task_daily_stats"

    if _SQLALCHEMY_AVAILABLE:
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
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": getattr(self, "id", None),
            "task_name": getattr(self, "task_name", None),
            "date": getattr(self, "date", None),
            "total_executions": getattr(self, "total_executions", 0),
            "succeeded": getattr(self, "succeeded", 0),
            "failed": getattr(self, "failed", 0),
            "retried": getattr(self, "retried", 0),
            "revoked": getattr(self, "revoked", 0),
            "pending": getattr(self, "pending", 0),
            "orphaned": getattr(self, "orphaned", 0),
            "avg_runtime": getattr(self, "avg_runtime", None),
            "min_runtime": getattr(self, "min_runtime", None),
            "max_runtime": getattr(self, "max_runtime", None),
            "p50_runtime": getattr(self, "p50_runtime", None),
            "p95_runtime": getattr(self, "p95_runtime", None),
            "p99_runtime": getattr(self, "p99_runtime", None),
            "first_execution": str(getattr(self, "first_execution", None)),
            "last_execution": str(getattr(self, "last_execution", None)),
            "created_at": str(getattr(self, "created_at", None)),
            "updated_at": str(getattr(self, "updated_at", None)),
        }


class TaskEventDB(Base):
    __tablename__ = "task_events"

    if _SQLALCHEMY_AVAILABLE:
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

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": getattr(self, "id", None),
            "task_id": getattr(self, "task_id", None),
            "task_name": getattr(self, "task_name", None),
            "event_type": getattr(self, "event_type", None),
            "hostname": getattr(self, "hostname", None),
            "worker_name": getattr(self, "worker_name", None),
            "queue": getattr(self, "queue", None),
            "exchange": getattr(self, "exchange", None),
            "routing_key": getattr(self, "routing_key", None),
            "args": getattr(self, "args", None),
            "kwargs": getattr(self, "kwargs", None),
            "result": getattr(self, "result", None),
            "exception": getattr(self, "exception", None),
            "traceback": getattr(self, "traceback", None),
            "runtime": getattr(self, "runtime", None),
            "retries": getattr(self, "retries", 0),
            "retry_count": getattr(self, "retry_count", 0),
            "retry_of": getattr(self, "retry_of", None),
            "retried_by": getattr(self, "retried_by", None),
            "has_retries": getattr(self, "has_retries", False),
            "is_retry": getattr(self, "is_retry", False),
            "is_orphan": getattr(self, "is_orphan", False),
            "orphaned_at": str(getattr(self, "orphaned_at", None)),
            "parent_id": getattr(self, "parent_id", None),
            "root_id": getattr(self, "root_id", None),
            "eta": str(getattr(self, "eta", None)),
            "expires": str(getattr(self, "expires", None)),
            "timestamp": str(getattr(self, "timestamp", None)),
        }


class TaskLatestDB(Base):
    __tablename__ = "task_latest"

    if _SQLALCHEMY_AVAILABLE:
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

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TaskProgressDB(Base):
    __tablename__ = "task_progress"

    if _SQLALCHEMY_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        task_id = Column(String, nullable=False)
        task_name = Column(String, nullable=True)
        progress = Column(Float, nullable=True)
        message = Column(Text, nullable=True)
        step_key = Column(String, nullable=True)
        meta = Column(JSON, nullable=True)
        timestamp = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": getattr(self, "id", None),
            "task_id": getattr(self, "task_id", None),
            "task_name": getattr(self, "task_name", None),
            "progress": getattr(self, "progress", None),
            "message": getattr(self, "message", None),
            "step_key": getattr(self, "step_key", None),
            "meta": getattr(self, "meta", None),
            "timestamp": str(getattr(self, "timestamp", None)),
        }


class TaskProgressLatestDB(Base):
    __tablename__ = "task_progress_latest"

    if _SQLALCHEMY_AVAILABLE:
        task_id = Column(String, primary_key=True)
        task_name = Column(String, nullable=True)
        progress = Column(Float, nullable=True)
        message = Column(Text, nullable=True)
        step_key = Column(String, nullable=True)
        meta = Column(JSON, nullable=True)
        updated_at = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": getattr(self, "task_id", None),
            "task_name": getattr(self, "task_name", None),
            "progress": getattr(self, "progress", None),
            "message": getattr(self, "message", None),
            "step_key": getattr(self, "step_key", None),
            "meta": getattr(self, "meta", None),
            "updated_at": str(getattr(self, "updated_at", None)),
        }


class TaskRegistryDB(Base):
    __tablename__ = "task_registry"

    if _SQLALCHEMY_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        name = Column(String, nullable=False, unique=True)
        human_readable_name = Column(String, nullable=True)
        description = Column(Text, nullable=True)
        tags = Column(JSON, nullable=True)
        first_seen = Column(DateTime, nullable=True)
        last_seen = Column(DateTime, nullable=True)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": getattr(self, "id", None),
            "name": getattr(self, "name", None),
            "human_readable_name": getattr(self, "human_readable_name", None),
            "description": getattr(self, "description", None),
            "tags": getattr(self, "tags", None),
            "first_seen": str(getattr(self, "first_seen", None)),
            "last_seen": str(getattr(self, "last_seen", None)),
            "created_at": str(getattr(self, "created_at", None)),
            "updated_at": str(getattr(self, "updated_at", None)),
        }


class TaskRerunRelationshipDB(Base):
    __tablename__ = "task_rerun_relationships"

    if _SQLALCHEMY_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        original_task_id = Column(String, nullable=False)
        rerun_task_id = Column(String, nullable=False)
        action_id = Column(Integer, nullable=True)
        created_by = Column(String, nullable=True)
        created_at = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TaskResolutionDB(Base):
    __tablename__ = "task_resolutions"

    if _SQLALCHEMY_AVAILABLE:
        task_id = Column(String, primary_key=True)
        resolved = Column(Boolean, default=False)
        resolved_at = Column(DateTime, nullable=True)
        resolved_by = Column(String, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TaskStepsDB(Base):
    __tablename__ = "task_steps"

    if _SQLALCHEMY_AVAILABLE:
        task_id = Column(String, primary_key=True)
        task_name = Column(String, nullable=True)
        steps = Column(JSON, nullable=True)
        defined_at = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": getattr(self, "task_id", None),
            "task_name": getattr(self, "task_name", None),
            "steps": getattr(self, "steps", None),
            "defined_at": str(getattr(self, "defined_at", None)),
        }


class UserDB(Base):
    __tablename__ = "users"

    if _SQLALCHEMY_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        email = Column(String, nullable=False, unique=True)
        name = Column(String, nullable=True)
        avatar_url = Column(String, nullable=True)
        provider = Column(String, nullable=True)
        provider_account_id = Column(String, nullable=True)
        is_active = Column(Boolean, default=True)
        last_login_at = Column(DateTime, nullable=True)
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)
        sessions = relationship("UserSessionDB", back_populates="user") if _SQLALCHEMY_AVAILABLE else None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": getattr(self, "id", None),
            "email": getattr(self, "email", None),
            "name": getattr(self, "name", None),
            "avatar_url": getattr(self, "avatar_url", None),
            "provider": getattr(self, "provider", None),
            "provider_account_id": getattr(self, "provider_account_id", None),
            "is_active": getattr(self, "is_active", True),
            "last_login_at": str(getattr(self, "last_login_at", None)),
            "created_at": str(getattr(self, "created_at", None)),
            "updated_at": str(getattr(self, "updated_at", None)),
        }


class UserSessionDB(Base):
    __tablename__ = "user_sessions"

    if _SQLALCHEMY_AVAILABLE:
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
        created_at = Column(DateTime, nullable=True)
        user = relationship("UserDB", back_populates="sessions") if _SQLALCHEMY_AVAILABLE else None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": getattr(self, "session_id", None),
            "user_id": getattr(self, "user_id", None),
            "auth_provider": getattr(self, "auth_provider", None),
            "access_token_expires_at": str(getattr(self, "access_token_expires_at", None)),
            "refresh_token_expires_at": str(getattr(self, "refresh_token_expires_at", None)),
            "token_scopes": getattr(self, "token_scopes", None),
            "active_environment_id": getattr(self, "active_environment_id", None),
            "preferences": getattr(self, "preferences", None),
            "last_active": str(getattr(self, "last_active", None)),
            "created_at": str(getattr(self, "created_at", None)),
        }


class WorkerEventDB(Base):
    __tablename__ = "worker_events"

    if _SQLALCHEMY_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        hostname = Column(String, nullable=False)
        event_type = Column(String, nullable=False)
        status = Column(String, nullable=True)
        active_tasks = Column(Integer, default=0)
        processed = Column(Integer, default=0)
        timestamp = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": getattr(self, "id", None),
            "hostname": getattr(self, "hostname", None),
            "event_type": getattr(self, "event_type", None),
            "status": getattr(self, "status", None),
            "active_tasks": getattr(self, "active_tasks", 0),
            "processed": getattr(self, "processed", 0),
            "timestamp": str(getattr(self, "timestamp", None)),
        }


class WorkflowDB(Base):
    __tablename__ = "workflows"

    if _SQLALCHEMY_AVAILABLE:
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
        created_at = Column(DateTime, nullable=True)
        updated_at = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": getattr(self, "id", None),
            "name": getattr(self, "name", None),
            "description": getattr(self, "description", None),
            "enabled": getattr(self, "enabled", True),
            "trigger_type": getattr(self, "trigger_type", None),
            "trigger_config": getattr(self, "trigger_config", None),
            "conditions": getattr(self, "conditions", None),
            "actions": getattr(self, "actions", None),
            "priority": getattr(self, "priority", 0),
            "cooldown_seconds": getattr(self, "cooldown_seconds", 0),
            "max_executions_per_hour": getattr(self, "max_executions_per_hour", None),
            "circuit_breaker_config": getattr(self, "circuit_breaker_config", None),
            "execution_count": getattr(self, "execution_count", 0),
            "success_count": getattr(self, "success_count", 0),
            "failure_count": getattr(self, "failure_count", 0),
            "last_executed_at": str(getattr(self, "last_executed_at", None)),
            "created_by": getattr(self, "created_by", None),
            "created_at": str(getattr(self, "created_at", None)),
            "updated_at": str(getattr(self, "updated_at", None)),
        }


class WorkflowExecutionDB(Base):
    __tablename__ = "workflow_executions"

    if _SQLALCHEMY_AVAILABLE:
        id = Column(Integer, primary_key=True, autoincrement=True)
        workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
        trigger_type = Column(String, nullable=True)
        trigger_event = Column(JSON, nullable=True)
        status = Column(String, nullable=True)
        actions_executed = Column(JSON, nullable=True)
        error_message = Column(Text, nullable=True)
        stack_trace = Column(Text, nullable=True)
        duration_ms = Column(Integer, nullable=True)
        circuit_breaker_key = Column(String, nullable=True)
        workflow_snapshot = Column(JSON, nullable=True)
        triggered_at = Column(DateTime, nullable=True)
        started_at = Column(DateTime, nullable=True)
        completed_at = Column(DateTime, nullable=True)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": getattr(self, "id", None),
            "workflow_id": getattr(self, "workflow_id", None),
            "trigger_type": getattr(self, "trigger_type", None),
            "trigger_event": getattr(self, "trigger_event", None),
            "status": getattr(self, "status", None),
            "actions_executed": getattr(self, "actions_executed", None),
            "error_message": getattr(self, "error_message", None),
            "stack_trace": getattr(self, "stack_trace", None),
            "duration_ms": getattr(self, "duration_ms", None),
            "circuit_breaker_key": getattr(self, "circuit_breaker_key", None),
            "workflow_snapshot": getattr(self, "workflow_snapshot", None),
            "triggered_at": str(getattr(self, "triggered_at", None)),
            "started_at": str(getattr(self, "started_at", None)),
            "completed_at": str(getattr(self, "completed_at", None)),
        }


# ---------------------------------------------------------------------------
# DatabaseManager
# ---------------------------------------------------------------------------

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url: str = database_url
        self.engine = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._initialize()

    def _initialize(self):
        if _SQLALCHEMY_AVAILABLE:
            try:
                self.engine = create_engine(self.database_url)
                self.SessionLocal = sessionmaker(bind=self.engine)
            except Exception:
                self.engine = None
                self.SessionLocal = None

    def get_session(self) -> Optional[Session]:
        if self.SessionLocal is not None:
            return self.SessionLocal()
        return None

    def run_migrations(self):
        if self.engine is not None and _SQLALCHEMY_AVAILABLE:
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
        self.active_connections: List[Any] = []
        self.client_filters: Dict[Any, dict] = {}
        self.client_modes: Dict[Any, str] = {}
        self.message_queue: Optional[asyncio.Queue] = None
        self._broadcaster_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: Any):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.client_filters[websocket] = {}
        self.client_modes[websocket] = "default"

    def disconnect(self, websocket: Any):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.client_filters.pop(websocket, None)
        self.client_modes.pop(websocket, None)

    async def send_personal_message(self, message: str, websocket: Any):
        await websocket.send_text(message)

    def set_client_filters(self, websocket: Any, filters: dict):
        self.client_filters[websocket] = filters

    def set_client_mode(self, websocket: Any, mode: str):
        self.client_modes[websocket] = mode

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
                self.message_queue.put_nowait({"type": "task_action", "event": action_event})
            except asyncio.QueueFull:
                pass

    async def _background_broadcaster(self):
        while True:
            try:
                item = await self.message_queue.get()
                if item is None:
                    break
                message = json.dumps(item, default=str)
                dead = []
                for ws in list(self.active_connections):
                    try:
                        await ws.send_text(message)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    self.disconnect(ws)
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    def start_background_broadcaster(self):
        self.message_queue = asyncio.Queue()
        loop = asyncio.get_event_loop()
        self._broadcaster_task = loop.create_task(self._background_broadcaster())

    def stop_background_broadcaster(self):
        if self.message_queue is not None:
            try:
                self.message_queue.put_nowait(None)
            except asyncio.QueueFull:
                pass
        if self._broadcaster_task is not None:
            self._broadcaster_task.cancel()
            self._broadcaster_task = None


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
        if self.workflow_engine is not None:
            try:
                self.workflow_engine.process_task_event(task_event)
            except Exception:
                pass

    def handle_worker_event(self, worker_event: WorkerEvent):
        self.connection_manager.queue_worker_broadcast(worker_event)
        if self.workflow_engine is not None:
            try:
                self.workflow_engine.process_worker_event(worker_event)
            except Exception:
                pass

    def handle_progress_event(self, progress_event):
        self.connection_manager.queue_progress_broadcast(progress_event)

    def handle_steps_event(self, steps_event):
        self.connection_manager.queue_broadcast(steps_event)


# ---------------------------------------------------------------------------
# ActionHandler (abstract base)
# ---------------------------------------------------------------------------

class ActionHandler(ABC):
    def __init__(self, db_manager: Optional[DatabaseManager] = None, session=None):
        self.db_manager = db_manager
        self.session = session
        self.monitor_instance = None

    @abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        raise NotImplementedError

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        raise NotImplementedError

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        try:
            return string.Template(template).safe_substitute(context)
        except Exception:
            return template


# ---------------------------------------------------------------------------
# RetryActionHandler
# ---------------------------------------------------------------------------

class RetryActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(params, dict):
            return False, "params must be a dictionary"
        task_ids = params.get("task_ids")
        if task_ids is None:
            task_ids = params.get("task_id")
        if task_ids is None:
            return False, "task_ids or task_id is required"
        return True, ""

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        valid, error = self.validate_params(params)
        if not valid:
            return ActionResult(success=False, message=error)

        task_ids = params.get("task_ids") or params.get("task_id")
        if isinstance(task_ids, str):
            task_ids = [task_ids]

        results = []
        for task_id in task_ids:
            rendered_id = self.render_template(str(task_id), context)
            results.append({"task_id": rendered_id, "status": "retry_queued"})

        return ActionResult(
            success=True,
            message=f"Retry queued for {len(results)} task(s)",
            data={"results": results},
        )


# ---------------------------------------------------------------------------
# SlackActionHandler
# ---------------------------------------------------------------------------

class SlackActionHandler(ActionHandler):
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if not isinstance(params, dict):
            return False, "params must be a dictionary"
        webhook_url = params.get("webhook_url")
        if not webhook_url:
            return False, "webhook_url is required"
        message = params.get("message")
        if not message:
            return False, "message is required"
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
            payload = json.dumps({"text": rendered_message}).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                status_code = resp.getcode()
                if status_code == 200:
                    return ActionResult(
                        success=True,
                        message="Slack message sent successfully",
                        data={"status_code": status_code},
                    )
                else:
                    return ActionResult(
                        success=False,
                        message=f"Slack returned status {status_code}",
                        data={"status_code": status_code},
                    )
        except Exception as exc:
            return ActionResult(
                success=False,
                message=f"Failed to send Slack message: {exc}",
            )