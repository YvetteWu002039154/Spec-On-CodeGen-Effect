import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from sqlalchemy.engine import Engine

Base = declarative_base()

# --- Dummy Classes for Type Hints ---

class WebSocket:
    async def send_text(self, data: str):
        pass

@dataclass
class TaskEvent:
    task_id: str
    event_type: str
    timestamp: datetime

@dataclass
class WorkerEvent:
    hostname: str
    event_type: str
    timestamp: datetime

@dataclass
class TaskProgressEvent:
    task_id: str
    progress: float
    message: str

@dataclass
class TaskStepsEvent:
    task_id: str
    steps: List[Dict[str, Any]]

@dataclass
class ActionResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

# --- Database Models ---

class ActionConfigDB(Base):
    __tablename__ = "action_config_db"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_type = Column(String)
    config = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String)
    description = Column(Text)
    last_used_at = Column(DateTime)
    name = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    usage_count = Column(Integer, default=0)

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class AppSettingDB(Base):
    __tablename__ = "app_setting_db"
    key = Column(String, primary_key=True)
    category = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)
    label = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    value = Column(JSON)
    value_type = Column(String)

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class EnvironmentDB(Base):
    __tablename__ = "environment_db"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    name = Column(String)
    queue_patterns = Column(JSON)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    worker_patterns = Column(JSON)

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class RetryRelationshipDB(Base):
    __tablename__ = "retry_relationship_db"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    original_id = Column(String)
    retry_chain = Column(JSON)
    task_id = Column(String)
    total_retries = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TaskActionDB(Base):
    __tablename__ = "task_action_db"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_type = Column(String)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    initiated_by = Column(String)
    initiated_by_user_id = Column(Integer)
    initiated_session_id = Column(String)
    item_changed = Column(Integer, default=0)
    item_created = Column(Integer, default=0)
    item_failed = Column(Integer, default=0)
    item_noop = Column(Integer, default=0)
    item_skipped = Column(Integer, default=0)
    item_total = Column(Integer, default=0)
    original_task_ids = Column(JSON)
    selection_size = Column(Integer, default=0)
    started_at = Column(DateTime)
    status = Column(String)
    summary = Column(Text)

    items = relationship("TaskActionItemDB", back_populates="action")

class TaskActionItemDB(Base):
    __tablename__ = "task_action_item_db"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(Integer, ForeignKey("task_action_db.id"))
    attempted_task_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    original_task_id = Column(String)
    original_task_name = Column(String)
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
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    action = relationship("TaskActionDB", back_populates="items")

class TaskDailyStatsDB(Base):
    __tablename__ = "task_daily_stats_db"
    id = Column(Integer, primary_key=True, autoincrement=True)
    avg_runtime = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    date = Column(DateTime)
    failed = Column(Integer, default=0)
    first_execution = Column(DateTime)
    last_execution = Column(DateTime)
    max_runtime = Column(Float)
    min_runtime = Column(Float)
    orphaned = Column(Integer, default=0)
    p50_runtime = Column(Float)
    p95_runtime = Column(Float)
    p99_runtime = Column(Float)
    pending = Column(Integer, default=0)
    retried = Column(Integer, default=0)
    revoked = Column(Integer, default=0)
    succeeded = Column(Integer, default=0)
    task_name = Column(String)
    total_executions = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class TaskEventDB(Base):
    __tablename__ = "task_event_db"
    id = Column(Integer, primary_key=True, autoincrement=True)
    args = Column(JSON)
    eta = Column(DateTime)
    event_type = Column(String)
    exception = Column(Text)
    exchange = Column(String)
    expires = Column(DateTime)
    has_retries = Column(Boolean, default=False)
    hostname = Column(String)
    is_orphan = Column(Boolean, default=False)
    is_retry = Column(Boolean, default=False)
    kwargs = Column(JSON)
    orphaned_at = Column(DateTime)
    parent_id = Column(String)
    queue = Column(String)
    result = Column(Text)
    retried_by = Column(String)
    retries = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    retry_of = Column(String)
    root_id = Column(String)
    routing_key = Column(String)
    runtime = Column(Float)
    task_id = Column(String)
    task_name = Column(String)
    timestamp = Column(DateTime)
    traceback = Column(Text)
    worker_name = Column(String)

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class TaskLatestDB(Base):
    __tablename__ = "task_latest_db"
    task_id = Column(String, primary_key=True)
    args = Column(JSON)
    eta = Column(DateTime)
    event_id = Column(Integer)
    event_type = Column(String)
    exception = Column(Text)
    exchange = Column(String)
    expires = Column(DateTime)
    has_retries = Column(Boolean, default=False)
    hostname = Column(String)
    is_orphan = Column(Boolean, default=False)
    is_retry = Column(Boolean, default=False)
    kwargs = Column(JSON)
    orphaned_at = Column(DateTime)
    parent_id = Column(String)
    queue = Column(String)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolved_by = Column(String)
    result = Column(Text)
    retried_by = Column(String)
    retries = Column(Integer, default=0)
    retry_count = Column(Integer, default=0)
    retry_of = Column(String)
    root_id = Column(String)
    routing_key = Column(String)
    runtime = Column(Float)
    task_name = Column(String)
    timestamp = Column(DateTime)
    traceback = Column(Text)
    worker_name = Column(String)

class TaskProgressDB(Base):
    __tablename__ = "task_progress_db"
    id = Column(Integer, primary_key=True, autoincrement=True)
    message = Column(Text)
    meta = Column(JSON)
    progress = Column(Float)
    step_key = Column(String)
    task_id = Column(String)
    task_name = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class TaskProgressLatestDB(Base):
    __tablename__ = "task_progress_latest_db"
    task_id = Column(String, primary_key=True)
    message = Column(Text)
    meta = Column(JSON)
    progress = Column(Float)
    step_key = Column(String)
    task_name = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class TaskRegistryDB(Base):
    __tablename__ = "task_registry_db"
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    description = Column(Text)
    first_seen = Column(DateTime)
    human_readable_name = Column(String)
    last_seen = Column(DateTime)
    name = Column(String)
    tags = Column(JSON)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class TaskRerunRelationshipDB(Base):
    __tablename__ = "task_rerun_relationship_db"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String)
    original_task_id = Column(String)
    rerun_task_id = Column(String)

class TaskResolutionDB(Base):
    __tablename__ = "task_resolution_db"
    task_id = Column(String, primary_key=True)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolved_by = Column(String)

class TaskStepsDB(Base):
    __tablename__ = "task_steps_db"
    task_id = Column(String, primary_key=True)
    defined_at = Column(DateTime, default=datetime.utcnow)
    steps = Column(JSON)
    task_name = Column(String)

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class UserDB(Base):
    __tablename__ = "user_db"
    id = Column(Integer, primary_key=True, autoincrement=True)
    avatar_url = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    email = Column(String, unique=True)
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime)
    name = Column(String)
    provider = Column(String)
    provider_account_id = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sessions = relationship("UserSessionDB", back_populates="user")

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class UserSessionDB(Base):
    __tablename__ = "user_session_db"
    session_id = Column(String, primary_key=True)
    access_token_expires_at = Column(DateTime)
    access_token_hash = Column(String)
    active_environment_id = Column(Integer)
    auth_provider = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime)
    preferences = Column(JSON)
    refresh_token_expires_at = Column(DateTime)
    refresh_token_hash = Column(String)
    token_scopes = Column(JSON)
    user_id = Column(Integer, ForeignKey("user_db.id"))

    user = relationship("UserDB", back_populates="sessions")

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class WorkerEventDB(Base):
    __tablename__ = "worker_event_db"
    id = Column(Integer, primary_key=True, autoincrement=True)
    active_tasks = Column(Integer, default=0)
    event_type = Column(String)
    hostname = Column(String)
    processed = Column(Integer, default=0)
    status = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class WorkflowDB(Base):
    __tablename__ = "workflow_db"
    id = Column(Integer, primary_key=True, autoincrement=True)
    actions = Column(JSON)
    circuit_breaker_config = Column(JSON)
    conditions = Column(JSON)
    cooldown_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String)
    description = Column(Text)
    enabled = Column(Boolean, default=True)
    execution_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_executed_at = Column(DateTime)
    max_executions_per_hour = Column(Integer, default=0)
    name = Column(String)
    priority = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    trigger_config = Column(JSON)
    trigger_type = Column(String)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class WorkflowExecutionDB(Base):
    __tablename__ = "workflow_execution_db"
    id = Column(Integer, primary_key=True, autoincrement=True)
    actions_executed = Column(JSON)
    circuit_breaker_key = Column(String)
    completed_at = Column(DateTime)
    duration_ms = Column(Integer)
    error_message = Column(Text)
    stack_trace = Column(Text)
    started_at = Column(DateTime)
    status = Column(String)
    trigger_event = Column(JSON)
    trigger_type = Column(String)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    workflow_id = Column(Integer)
    workflow_snapshot = Column(JSON)

    def to_dict(self) -> Dict[str, Any]:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

# --- Database Manager ---

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine: Optional[Engine] = create_engine(self.database_url)
        self.SessionLocal: sessionmaker = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    def run_migrations(self):
        if self.engine:
            Base.metadata.create_all(bind=self.engine)

# --- Action Handlers ---

class ActionHandler(ABC):
    def __init__(self, db_manager: DatabaseManager, session: Session, monitor_instance: Optional[Any] = None):
        self.db_manager = db_manager
        self.session = session
        self.monitor_instance = monitor_instance

    @abstractmethod
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        pass

    def render_template(self, template: str, context: Dict[str, Any]) -> str:
        try:
            return template.format(**context)
        except KeyError as e:
            return template

    @abstractmethod
    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        pass

class RetryActionHandler(ActionHandler):
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        is_valid, msg = self.validate_params(params)
        if not is_valid:
            return ActionResult(success=False, message=msg)
        return ActionResult(success=True, message="Retry action executed successfully", data={"retried": True})

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "task_id" not in params:
            return False, "Missing task_id in params"
        return True, "Valid"

class SlackActionHandler(ActionHandler):
    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> ActionResult:
        is_valid, msg = self.validate_params(params)
        if not is_valid:
            return ActionResult(success=False, message=msg)
        message = self.render_template(params.get("message_template", ""), context)
        return ActionResult(success=True, message="Slack message sent", data={"sent_message": message})

    def validate_params(self, params: Dict[str, Any]) -> Tuple[bool, str]:
        if "channel" not in params:
            return False, "Missing channel in params"
        if "message_template" not in params:
            return False, "Missing message_template in params"
        return True, "Valid"

# --- Monitor ---

class CeleryEventMonitor:
    def __init__(self, broker_url: str, app: Optional[Any] = None):
        self.broker_url = broker_url
        self.app = app
        self.state: Optional[Any] = None
        self.workers: Dict[str, Dict[str, Any]] = {}
        self.progress_callback: Optional[Callable[[TaskProgressEvent], None]] = None
        self.steps_callback: Optional[Callable[[TaskStepsEvent], None]] = None
        self.task_callback: Optional[Callable[[TaskEvent], None]] = None
        self.worker_callback: Optional[Callable[[WorkerEvent], None]] = None

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

# --- Connection Manager ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.client_filters: Dict[WebSocket, dict] = {}
        self.client_modes: Dict[WebSocket, str] = {}
        self.message_queue: Optional[asyncio.Queue] = None
        self._broadcaster_task: Optional[asyncio.Task] = None

    def connect(self, websocket: WebSocket):
        self.active_connections.append(websocket)
        self.client_filters[websocket] = {}
        self.client_modes[websocket] = "default"

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.client_filters.pop(websocket, None)
        self.client_modes.pop(websocket, None)

    def queue_broadcast(self, task_event: TaskEvent):
        if self.message_queue:
            self.message_queue.put_nowait(("task", task_event))

    def queue_progress_broadcast(self, progress_event: TaskProgressEvent):
        if self.message_queue:
            self.message_queue.put_nowait(("progress", progress_event))

    def queue_task_action_broadcast(self, action_event: Any):
        if self.message_queue:
            self.message_queue.put_nowait(("action", action_event))

    def queue_worker_broadcast(self, worker_event: WorkerEvent):
        if self.message_queue:
            self.message_queue.put_nowait(("worker", worker_event))

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    def set_client_filters(self, websocket: WebSocket, filters: dict):
        if websocket in self.active_connections:
            self.client_filters[websocket] = filters

    def set_client_mode(self, websocket: WebSocket, mode: str):
        if websocket in self.active_connections:
            self.client_modes[websocket] = mode

    def start_background_broadcaster(self):
        if self.message_queue is None:
            self.message_queue = asyncio.Queue()
        
        async def _broadcast_loop():
            while True:
                if self.message_queue:
                    event_type, event_data = await self.message_queue.get()
                    for connection in self.active_connections:
                        await connection.send_text(json.dumps({"type": event_type, "data": str(event_data)}))
        
        self._broadcaster_task = asyncio.create_task(_broadcast_loop())

    def stop_background_broadcaster(self):
        if self._broadcaster_task:
            self._broadcaster_task.cancel()
            self._broadcaster_task = None

# --- Event Handler ---

class EventHandler:
    def __init__(self, connection_manager: ConnectionManager, db_manager: DatabaseManager, workflow_engine: Optional[Any] = None):
        self.connection_manager = connection_manager
        self.db_manager = db_manager
        self.workflow_engine = workflow_engine

    def handle_progress_event(self, progress_event: TaskProgressEvent):
        session = self.db_manager.get_session()
        try:
            db_progress = TaskProgressDB(
                task_id=progress_event.task_id,
                progress=progress_event.progress,
                message=progress_event.message
            )
            session.add(db_progress)
            session.commit()
            self.connection_manager.queue_progress_broadcast(progress_event)
        finally:
            session.close()

    def handle_steps_event(self, steps_event: TaskStepsEvent):
        session = self.db_manager.get_session()
        try:
            db_steps = TaskStepsDB(
                task_id=steps_event.task_id,
                steps=steps_event.steps
            )
            session.merge(db_steps)
            session.commit()
        finally:
            session.close()

    def handle_task_event(self, task_event: TaskEvent):
        session = self.db_manager.get_session()
        try:
            db_event = TaskEventDB(
                task_id=task_event.task_id,
                event_type=task_event.event_type,
                timestamp=task_event.timestamp
            )
            session.add(db_event)
            session.commit()
            self.connection_manager.queue_broadcast(task_event)
        finally:
            session.close()

    def handle_worker_event(self, worker_event: WorkerEvent):
        session = self.db_manager.get_session()
        try:
            db_worker = WorkerEventDB(
                hostname=worker_event.hostname,
                event_type=worker_event.event_type,
                timestamp=worker_event.timestamp
            )
            session.add(db_worker)
            session.commit()
            self.connection_manager.queue_worker_broadcast(worker_event)
        finally:
            session.close()