from __future__ import annotations

import datetime
import enum
from typing import Annotated, Dict, List, Optional, Set

from pydantic import BaseModel, EmailStr, Field
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
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from starlette.websockets import WebSocket


class Base(DeclarativeBase):
    pass


# ---------- Enums ----------
class ProjectStatus(str, enum.Enum):
    active = "active"
    archived = "archived"
    on_hold = "on_hold"
    completed = "completed"


class ServerStatus(str, enum.Enum):
    online = "online"
    offline = "offline"
    maintenance = "maintenance"
    error = "error"


class ServerType(str, enum.Enum):
    physical = "physical"
    virtual = "virtual"
    cloud = "cloud"


class TaskPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TaskStatus(str, enum.Enum):
    backlog = "backlog"
    todo = "todo"
    in_progress = "in_progress"
    review = "review"
    done = "done"
    cancelled = "cancelled"


class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    user = "user"
    viewer = "viewer"


# ---------- ORM Models ----------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        String(20), default=UserRole.user, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    projects: Mapped[List["Project"]] = relationship(back_populates="owner")
    tasks: Mapped[List["Task"]] = relationship(
        back_populates="assignee", foreign_keys="Task.assignee_id"
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String(7), default="#3B82F6")
    icon: Mapped[str] = mapped_column(String(50), default="folder")
    status: Mapped[ProjectStatus] = mapped_column(
        String(20), default=ProjectStatus.active
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    owner: Mapped[User] = relationship(back_populates="projects")
    tasks: Mapped[List["Task"]] = relationship(back_populates="project")


class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    port: Mapped[int] = mapped_column(Integer, default=22)
    os_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ssh_username: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ssh_key_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ssh_password_encrypted: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    agent_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    agent_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    status: Mapped[ServerStatus] = mapped_column(
        String(20), default=ServerStatus.offline
    )
    cpu_cores: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ram_total_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_heartbeat: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    metrics: Mapped[List["MetricSnapshot"]] = relationship(back_populates="server")
    tasks: Mapped[List["Task"]] = relationship(back_populates="server")


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"), nullable=False)
    server: Mapped[Server] = relationship(back_populates="metrics")
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    cpu_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cpu_per_core: Mapped[Optional[list[float]]] = mapped_column(JSON, nullable=True)
    ram_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ram_used_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ram_total_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_read_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_write_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_sent_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_recv_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    upload_speed_mbps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    download_speed_mbps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_connections: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ping_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_memory_used_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_memory_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_processes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        String(20), default=TaskStatus.backlog
    )
    priority: Mapped[TaskPriority] = mapped_column(
        String(20), default=TaskPriority.medium
    )
    order: Mapped[int] = mapped_column(Integer, default=0)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    deadline: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    project: Mapped[Optional[Project]] = relationship(back_populates="tasks")

    server_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("servers.id"), nullable=True
    )
    server: Mapped[Optional[Server]] = relationship(back_populates="tasks")

    assignee_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    assignee: Mapped[Optional[User]] = relationship(
        back_populates="tasks", foreign_keys=[assignee_id]
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )


# ---------- Pydantic Schemas ----------
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
    description: Optional[str]
    color: str
    icon: str
    status: str
    created_at: Optional[datetime.datetime]
    updated_at: Optional[datetime.datetime]
    owner_id: int
    task_count: int
    completed_tasks: int

    class Config:
        from_attributes = True


class ServerCreate(BaseModel):
    name: str
    hostname: str
    ip_address: Optional[str] = None
    port: int = 22
    os_type: str = "linux"
    description: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_key_path: Optional[str] = None


class ServerUpdate(BaseModel):
    name: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    os_type: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_key_path: Optional[str] = None


class ServerResponse(BaseModel):
    id: int
    name: str
    hostname: str
    ip_address: Optional[str]
    port: int
    os_type: str
    description: Optional[str]
    ssh_username: Optional[str]
    agent_id: Optional[str]
    agent_version: Optional[str]
    status: str
    cpu_cores: Optional[int]
    ram_total_gb: Optional[float]
    gpu_model: Optional[str]
    last_heartbeat: Optional[datetime.datetime]
    created_at: Optional[datetime.datetime]
    updated_at: Optional[datetime.datetime]
    task_count: int

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.backlog
    priority: TaskPriority = TaskPriority.medium
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


class TaskReorder(BaseModel):
    task_id: int
    new_order: int
    new_status: str


class TaskResponse(TaskBase):
    id: int
    assignee_id: Optional[int]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    order: int

    class Config:
        from_attributes = True


class UserRegister(BaseModel):
    username: str
    email: Annotated[str, EmailStr]
    full_name: Optional[str] = None
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    role: str
    is_active: bool
    created_at: Optional[datetime.datetime]

    class Config:
        from_attributes = True


class TokenRefresh(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse


class DashboardStats(BaseModel):
    total_projects: int
    active_projects: int
    total_tasks: int
    pending_tasks: int
    completed_tasks: int
    total_servers: int
    online_servers: int


class SystemHealth(BaseModel):
    status: str
    version: str
    database: bool
    redis: bool


class MetricsConnectionManager:
    def __init__(self):
        self.agent_connections: Dict[int, WebSocket] = {}
        self.client_connections: Dict[int, Set[WebSocket]] = {}

    async def connect_agent(self, websocket: WebSocket, server_id: int):
        await websocket.accept()
        self.agent_connections[server_id] = websocket

    def disconnect_agent(self, server_id: int):
        self.agent_connections.pop(server_id, None)

    async def connect_client(self, websocket: WebSocket, server_id: int):
        await websocket.accept()
        if server_id not in self.client_connections:
            self.client_connections[server_id] = set()
        self.client_connections[server_id].add(websocket)

    def disconnect_client(self, websocket: WebSocket, server_id: int):
        if server_id in self.client_connections:
            self.client_connections[server_id].discard(websocket)
            if not self.client_connections[server_id]:
                del self.client_connections[server_id]

    async def broadcast_to_clients(self, server_id: int, data: dict):
        if server_id in self.client_connections:
            for ws in self.client_connections[server_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    # Handle disconnection silently
                    pass


class Settings(BaseSettings):
    APP_NAME: str = "NexusCtrl"
    APP_VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DATABASE_URL: str = "sqlite+aiosqlite:///./nexusctrl.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    AGENT_SECRET: str = "agent-secret-change-me"

    CORS_ORIGINS: List[str] = ["*"]

    SSH_KEY_PATH: str = "/etc/ssh/ssh_host_rsa_key"

    class Config:
        case_sensitive = True
        env_file = ".env"