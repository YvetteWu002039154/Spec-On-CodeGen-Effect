from __future__ import annotations

import datetime
import enum
from typing import Any, Dict, List, Optional, Set

import pydantic
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Float,
    Enum as SAEnum,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from starlette.websockets import WebSocket


# ---------- Enums ----------
class ServerStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"

class ServerType(str, enum.Enum):
    PHYSICAL = "physical"
    VIRTUAL = "virtual"

class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"

class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"


# ---------- ORM Base ----------
class Base(DeclarativeBase):
    pass


# ---------- ORM Models ----------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.USER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    projects: Mapped[List["Project"]] = relationship(back_populates="owner")
    tasks: Mapped[List["Task"]] = relationship(back_populates="assignee")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(50), default="folder")
    color: Mapped[str] = mapped_column(String(20), default="#6366f1")
    status: Mapped[ProjectStatus] = mapped_column(SAEnum(ProjectStatus), default=ProjectStatus.ACTIVE)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    owner: Mapped["User"] = relationship(back_populates="projects")
    tasks: Mapped[List["Task"]] = relationship(back_populates="project")


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    hostname: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    port: Mapped[int] = mapped_column(Integer, default=22)
    os_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)
    ssh_username: Mapped[Optional[str]] = mapped_column(String(100))
    ssh_key_path: Mapped[Optional[str]] = mapped_column(String(500))
    ssh_password_encrypted: Mapped[Optional[str]] = mapped_column(String(500))
    agent_id: Mapped[Optional[str]] = mapped_column(String(64))
    agent_version: Mapped[Optional[str]] = mapped_column(String(20))
    status: Mapped[ServerStatus] = mapped_column(SAEnum(ServerStatus), default=ServerStatus.OFFLINE)
    cpu_cores: Mapped[Optional[int]] = mapped_column(Integer)
    ram_total_gb: Mapped[Optional[float]] = mapped_column(Float)
    gpu_model: Mapped[Optional[str]] = mapped_column(String(200))
    last_heartbeat: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    metrics: Mapped[List["MetricSnapshot"]] = relationship(back_populates="server")
    tasks: Mapped[List["Task"]] = relationship(back_populates="server")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.TODO)
    priority: Mapped[TaskPriority] = mapped_column(SAEnum(TaskPriority), default=TaskPriority.MEDIUM)
    order: Mapped[int] = mapped_column(Integer, default=0)
    assignee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"))
    server_id: Mapped[Optional[int]] = mapped_column(ForeignKey("servers.id"))
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON)  # stored as JSON list
    deadline: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    assignee: Mapped[Optional["User"]] = relationship(back_populates="tasks")
    project: Mapped[Optional["Project"]] = relationship(back_populates="tasks")
    server: Mapped[Optional["Server"]] = relationship(back_populates="tasks")


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"))
    cpu_percent: Mapped[Optional[float]] = mapped_column(Float)
    cpu_per_core: Mapped[Optional[List[float]]] = mapped_column(JSON)
    ram_percent: Mapped[Optional[float]] = mapped_column(Float)
    ram_used_gb: Mapped[Optional[float]] = mapped_column(Float)
    ram_total_gb: Mapped[Optional[float]] = mapped_column(Float)
    disk_percent: Mapped[Optional[float]] = mapped_column(Float)
    disk_read_mb: Mapped[Optional[float]] = mapped_column(Float)
    disk_write_mb: Mapped[Optional[float]] = mapped_column(Float)
    net_sent_mb: Mapped[Optional[float]] = mapped_column(Float)
    net_recv_mb: Mapped[Optional[float]] = mapped_column(Float)
    net_connections: Mapped[Optional[int]] = mapped_column(Integer)
    download_speed_mbps: Mapped[Optional[float]] = mapped_column(Float)
    upload_speed_mbps: Mapped[Optional[float]] = mapped_column(Float)
    ping_ms: Mapped[Optional[float]] = mapped_column(Float)
    gpu_percent: Mapped[Optional[float]] = mapped_column(Float)
    gpu_memory_used_mb: Mapped[Optional[float]] = mapped_column(Float)
    gpu_memory_percent: Mapped[Optional[float]] = mapped_column(Float)
    gpu_temperature: Mapped[Optional[float]] = mapped_column(Float)
    gpu_processes: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    server: Mapped["Server"] = relationship(back_populates="metrics")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[Optional[int]] = mapped_column(Integer)
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


# ---------- Pydantic Schemas / DTOs ----------
# -- User --
class UserRegister(BaseModel):
    username: str
    password: str
    email: EmailStr
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    is_active: bool
    created_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

class TokenRefresh(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

# -- Project --
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: str = "folder"
    color: str = "#6366f1"

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    status: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    icon: str
    color: str
    status: str
    owner_id: int
    task_count: int
    completed_tasks: int
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

# -- Server --
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
    ssh_username: Optional[str] = None
    agent_id: Optional[str] = None
    agent_version: Optional[str] = None
    status: str
    cpu_cores: Optional[int] = None
    ram_total_gb: Optional[float] = None
    gpu_model: Optional[str] = None
    last_heartbeat: Optional[datetime.datetime] = None
    task_count: int
    created_at: Optional[datetime.datetime] = None
    updated_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

# -- Task --
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    due_date: Optional[datetime.datetime] = None
    tags: List[str] = []

class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    due_date: Optional[datetime.datetime] = None
    tags: Optional[List[str]] = None
    position: Optional[int] = None

class TaskResponse(TaskBase):
    id: int
    assignee_id: Optional[int] = None
    order: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True

class TaskReorder(BaseModel):
    task_id: int
    new_status: str
    new_order: int

# -- Dashboard --
class DashboardStats(BaseModel):
    total_servers: int
    online_servers: int
    total_projects: int
    active_projects: int
    total_tasks: int
    pending_tasks: int
    completed_tasks: int

class SystemHealth(BaseModel):
    status: str
    version: str
    database: bool
    redis: bool


# ---------- Settings ----------
class Settings(BaseModel):
    # Custom settings management (can be overridden with env)
    APP_NAME: str = "NexusCtrl"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"

    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "sqlite:///./nexusctrl.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    CORS_ORIGINS: List[str] = ["*"]
    SSH_KEY_PATH: str = "./keys"
    AGENT_SECRET: str = "agent-secret"

    class Config:
        case_sensitive = True
        env_file = ".env"


# ---------- Metrics Connection Manager ----------
class MetricsConnectionManager:
    """Manages WebSocket connections for real-time metrics."""

    def __init__(self) -> None:
        self.agent_connections: Dict[int, WebSocket] = {}
        self.client_connections: Dict[int, Set[WebSocket]] = {}

    async def connect_agent(self, websocket: WebSocket, server_id: int) -> None:
        await websocket.accept()
        self.agent_connections[server_id] = websocket

    async def disconnect_agent(self, server_id: int) -> None:
        if server_id in self.agent_connections:
            del self.agent_connections[server_id]

    async def connect_client(self, websocket: WebSocket, server_id: int) -> None:
        await websocket.accept()
        if server_id not in self.client_connections:
            self.client_connections[server_id] = set()
        self.client_connections[server_id].add(websocket)

    async def disconnect_client(self, websocket: WebSocket, server_id: int) -> None:
        if server_id in self.client_connections:
            self.client_connections[server_id].discard(websocket)
            if not self.client_connections[server_id]:
                del self.client_connections[server_id]

    async def broadcast_to_clients(self, server_id: int, data: dict) -> None:
        if server_id in self.client_connections:
            for client in self.client_connections[server_id]:
                await client.send_json(data)