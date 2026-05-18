from __future__ import annotations

import asyncio
from datetime import datetime
from enum import Enum
from typing import Annotated, Dict, List, Optional, Set

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Enum as SAEnum,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped, mapped_column
from starlette.websockets import WebSocket

Base = declarative_base()

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ProjectStatus(str, Enum):
    """Represents project status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class ServerStatus(str, Enum):
    """Represents server status."""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"

class ServerType(str, Enum):
    """Represents server type."""
    PHYSICAL = "physical"
    VIRTUAL = "virtual"
    CLOUD = "cloud"

class TaskStatus(str, Enum):
    """Represents task status."""
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    """Represents task priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class UserRole(str, Enum):
    """Represents user role."""
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"

# ---------------------------------------------------------------------------
# SQLAlchemy Models
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    action: Mapped[str] = mapped_column(String, index=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resource_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.USER)
    avatar_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projects = relationship("Project", back_populates="owner")
    tasks = relationship("Task", back_populates="assignee")

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(String, default="#3b82f6")
    icon: Mapped[str] = mapped_column(String, default="folder")
    status: Mapped[ProjectStatus] = mapped_column(SAEnum(ProjectStatus), default=ProjectStatus.ACTIVE)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project")

class Server(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    hostname: Mapped[str] = mapped_column(String)
    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    port: Mapped[int] = mapped_column(Integer, default=22)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    os_type: Mapped[str] = mapped_column(String)
    ssh_username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ssh_key_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ssh_password_encrypted: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[ServerStatus] = mapped_column(SAEnum(ServerStatus), default=ServerStatus.OFFLINE)
    agent_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True)
    agent_version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cpu_cores: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ram_total_gb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gpu_model: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    metrics = relationship("MetricSnapshot", back_populates="server")
    tasks = relationship("Task", back_populates="server")

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.TODO)
    priority: Mapped[TaskPriority] = mapped_column(SAEnum(TaskPriority), default=TaskPriority.MEDIUM)
    tags: Mapped[List[str]] = mapped_column(String, default="[]")  # stored as JSON string
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    project_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("projects.id"), nullable=True)
    server_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("servers.id"), nullable=True)
    assignee_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="tasks")
    server = relationship("Server", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks")

class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    server_id: Mapped[int] = mapped_column(Integer, ForeignKey("servers.id"))
    timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    cpu_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cpu_per_core: Mapped[Optional[List[float]]] = mapped_column(String, nullable=True)  # JSON
    ram_used_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ram_total_gb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ram_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_read_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disk_write_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_sent_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_recv_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_connections: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    download_speed_mbps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    upload_speed_mbps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ping_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_memory_used_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_memory_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gpu_processes: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # JSON

    server = relationship("Server", back_populates="metrics")

# ---------------------------------------------------------------------------
# Pydantic Schemas / Response Models
# ---------------------------------------------------------------------------

class DashboardStats(BaseModel):
    active_projects: int
    completed_tasks: int
    online_servers: int
    pending_tasks: int
    total_projects: int
    total_servers: int
    total_tasks: int

class SystemHealth(BaseModel):
    status: str
    version: str
    database: bool
    redis: bool

class Settings(BaseModel):
    APP_NAME: str = "NexusCtrl"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    AGENT_SECRET: str
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"
    CORS_ORIGINS: List[str] = ["*"]
    SSH_KEY_PATH: str = "~/.ssh"

    class Config:
        env_file: str = ".env"
        case_sensitive: bool = True

# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    role: str  # string representation of role
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class UserRegister(BaseModel):
    username: str
    email: Annotated[str, EmailStr]
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    email: Optional[Annotated[str, EmailStr]] = None
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

# ---------------------------------------------------------------------------
# Project schemas
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#3b82f6"
    icon: str = "folder"

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    status: Optional[str] = None  # should be ProjectStatus literal but string easier for PATCH

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    color: str
    icon: str
    status: str
    owner_id: int
    task_count: int
    completed_tasks: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------------------------
# Server schemas
# ---------------------------------------------------------------------------

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
    description: Optional[str] = None
    os_type: str
    ssh_username: Optional[str] = None
    status: str
    agent_id: Optional[str] = None
    agent_version: Optional[str] = None
    cpu_cores: Optional[int] = None
    ram_total_gb: Optional[int] = None
    gpu_model: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    task_count: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------------------------
# Task schemas
# ---------------------------------------------------------------------------

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority
    status: TaskStatus
    tags: List[str] = Field(default_factory=list)
    due_date: Optional[datetime] = None
    project_id: Optional[int] = None
    server_id: Optional[int] = None

class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None

class TaskResponse(TaskBase):
    id: int
    order: int
    assignee_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    tags: Optional[List[str]] = None
    due_date: Optional[datetime] = None
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    position: Optional[int] = None

class TaskReorder(BaseModel):
    task_id: int
    new_status: str
    new_order: int

# ---------------------------------------------------------------------------
# Token schemas
# ---------------------------------------------------------------------------

class TokenRefresh(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

# ---------------------------------------------------------------------------
# Metrics Connection Manager
# ---------------------------------------------------------------------------

class MetricsConnectionManager:
    def __init__(self):
        self.agent_connections: Dict[int, WebSocket] = {}
        self.client_connections: Dict[int, Set[WebSocket]] = {}

    async def connect_agent(self, websocket: WebSocket, server_id: int) -> None:
        await websocket.accept()
        self.agent_connections[server_id] = websocket

    async def connect_client(self, websocket: WebSocket, server_id: int) -> None:
        await websocket.accept()
        if server_id not in self.client_connections:
            self.client_connections[server_id] = set()
        self.client_connections[server_id].add(websocket)

    async def disconnect_agent(self, server_id: int) -> None:
        if server_id in self.agent_connections:
            del self.agent_connections[server_id]

    async def disconnect_client(self, websocket: WebSocket, server_id: int) -> None:
        if server_id in self.client_connections:
            self.client_connections[server_id].discard(websocket)
            if not self.client_connections[server_id]:
                del self.client_connections[server_id]

    async def broadcast_to_clients(self, server_id: int, data: dict) -> None:
        if server_id in self.client_connections:
            for client in self.client_connections[server_id]:
                try:
                    await client.send_json(data)
                except Exception:
                    # If send fails, we might want to remove the client, but simplest is to ignore
                    pass