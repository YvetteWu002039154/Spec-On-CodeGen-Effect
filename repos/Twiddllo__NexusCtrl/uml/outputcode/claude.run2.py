from __future__ import annotations

import enum
from datetime import datetime
from typing import Annotated, Dict, List, Optional, Set

from fastapi import WebSocket
from pydantic import BaseModel, EmailStr
from pydantic_settings import BaseSettings
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


# ---------------------------------------------------------------------------
# SQLAlchemy Base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class UserRole(enum.Enum):
    admin = "admin"
    member = "member"
    viewer = "viewer"


class ProjectStatus(enum.Enum):
    active = "active"
    archived = "archived"
    completed = "completed"


class ServerStatus(enum.Enum):
    online = "online"
    offline = "offline"
    maintenance = "maintenance"
    unknown = "unknown"


class ServerType(enum.Enum):
    physical = "physical"
    virtual = "virtual"
    cloud = "cloud"
    container = "container"


class TaskStatus(enum.Enum):
    todo = "todo"
    in_progress = "in_progress"
    review = "review"
    done = "done"


class TaskPriority(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


# ---------------------------------------------------------------------------
# SQLAlchemy ORM Models
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default=UserRole.member.value)
    is_active = Column(Boolean, default=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    projects = relationship("Project", back_populates="owner")
    tasks = relationship("Task", back_populates="assignee")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String, default="#3B82F6")
    icon = Column(String, default="folder")
    status = Column(String, default=ProjectStatus.active.value)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project")


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    hostname = Column(String, nullable=False)
    ip_address = Column(String, nullable=True)
    port = Column(Integer, default=22)
    os_type = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default=ServerStatus.unknown.value)
    ssh_username = Column(String, nullable=True)
    ssh_password_encrypted = Column(String, nullable=True)
    ssh_key_path = Column(String, nullable=True)
    agent_id = Column(String, nullable=True)
    agent_version = Column(String, nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    ram_total_gb = Column(Integer, nullable=True)
    gpu_model = Column(String, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    metrics = relationship("MetricSnapshot", back_populates="server")
    tasks = relationship("Task", back_populates="server")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default=TaskStatus.todo.value)
    priority = Column(String, default=TaskPriority.medium.value)
    tags = Column(JSON, default=list)
    order = Column(Integer, default=0)
    deadline = Column(DateTime, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    project = relationship("Project", back_populates="tasks")
    server = relationship("Server", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks")


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    timestamp = Column(DateTime, default=func.now())

    cpu_percent = Column(Float, nullable=True)
    cpu_per_core = Column(JSON, nullable=True)
    ram_percent = Column(Float, nullable=True)
    ram_used_gb = Column(Float, nullable=True)
    ram_total_gb = Column(Float, nullable=True)
    disk_percent = Column(Float, nullable=True)
    disk_read_mb = Column(Float, nullable=True)
    disk_write_mb = Column(Float, nullable=True)
    net_sent_mb = Column(Float, nullable=True)
    net_recv_mb = Column(Float, nullable=True)
    net_connections = Column(Integer, nullable=True)
    upload_speed_mbps = Column(Float, nullable=True)
    download_speed_mbps = Column(Float, nullable=True)
    ping_ms = Column(Float, nullable=True)
    gpu_percent = Column(Float, nullable=True)
    gpu_memory_percent = Column(Float, nullable=True)
    gpu_memory_used_mb = Column(Float, nullable=True)
    gpu_temperature = Column(Float, nullable=True)
    gpu_processes = Column(JSON, nullable=True)

    server = relationship("Server", back_populates="metrics")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=func.now())


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    APP_NAME: str = "NexusCtrl"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "sqlite:///./nexusctrl.db"
    REDIS_URL: str = "redis://localhost:6379"

    SECRET_KEY: str = "changeme-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    AGENT_SECRET: str = "changeme-agent-secret"
    SSH_KEY_PATH: str = "~/.ssh/id_rsa"

    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive: bool = True


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class UserRegister(BaseModel):
    username: str
    email: Annotated[str, EmailStr]
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes: bool = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse


class TokenRefresh(BaseModel):
    refresh_token: str


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#3B82F6"
    icon: str = "folder"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    color: str
    icon: str
    status: str
    owner_id: int
    task_count: int = 0
    completed_tasks: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes: bool = True


class ServerCreate(BaseModel):
    name: str
    hostname: str
    ip_address: Optional[str] = None
    port: int = 22
    os_type: str
    description: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_key_path: Optional[str] = None


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    os_type: Optional[str] = None
    description: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_key_path: Optional[str] = None
    status: Optional[str] = None


class ServerResponse(BaseModel):
    id: int
    name: str
    hostname: str
    ip_address: Optional[str] = None
    port: int
    os_type: str
    description: Optional[str] = None
    status: str
    ssh_username: Optional[str] = None
    agent_id: Optional[str] = None
    agent_version: Optional[str] = None
    cpu_cores: Optional[int] = None
    ram_total_gb: Optional[int] = None
    gpu_model: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    task_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes: bool = True


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.todo
    priority: TaskPriority = TaskPriority.medium
    tags: List[str] = []
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    due_date: Optional[datetime] = None


class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    tags: Optional[List[str]] = None
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    due_date: Optional[datetime] = None
    position: Optional[int] = None


class TaskResponse(TaskBase):
    id: int
    assignee_id: Optional[int] = None
    order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes: bool = True


class TaskReorder(BaseModel):
    task_id: int
    new_status: str
    new_order: int


class DashboardStats(BaseModel):
    total_projects: int
    active_projects: int
    total_servers: int
    online_servers: int
    total_tasks: int
    pending_tasks: int
    completed_tasks: int


class SystemHealth(BaseModel):
    status: str
    version: str
    database: bool
    redis: bool


# ---------------------------------------------------------------------------
# WebSocket Connection Manager
# ---------------------------------------------------------------------------

class MetricsConnectionManager:
    def __init__(self) -> None:
        self.agent_connections: Dict[int, WebSocket] = {}
        self.client_connections: Dict[int, Set[WebSocket]] = {}

    async def connect_agent(self, websocket: WebSocket, server_id: int) -> None:
        await websocket.accept()
        self.agent_connections[server_id] = websocket

    def disconnect_agent(self, server_id: int) -> None:
        self.agent_connections.pop(server_id, None)

    async def connect_client(self, websocket: WebSocket, server_id: int) -> None:
        await websocket.accept()
        if server_id not in self.client_connections:
            self.client_connections[server_id] = set()
        self.client_connections[server_id].add(websocket)

    def disconnect_client(self, websocket: WebSocket, server_id: int) -> None:
        if server_id in self.client_connections:
            self.client_connections[server_id].discard(websocket)
            if not self.client_connections[server_id]:
                del self.client_connections[server_id]

    async def broadcast_to_clients(self, server_id: int, data: dict) -> None:
        if server_id not in self.client_connections:
            return
        disconnected: Set[WebSocket] = set()
        for websocket in self.client_connections[server_id]:
            try:
                await websocket.send_json(data)
            except Exception:
                disconnected.add(websocket)
        for ws in disconnected:
            self.disconnect_client(ws, server_id)