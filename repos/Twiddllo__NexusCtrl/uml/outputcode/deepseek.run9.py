from __future__ import annotations
import datetime
from typing import Any, Dict, List, Optional, Set
from enum import Enum
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import asyncio
from fastapi import WebSocket

# --- Enums ---
class TaskPriority(str, Enum):
    name = ""

class TaskStatus(str, Enum):
    name = ""

class ServerStatus(str, Enum):
    name = ""

class ServerType(str, Enum):
    name = ""

class ProjectStatus(str, Enum):
    name = ""

class UserRole(str, Enum):
    name = ""

# --- SQLAlchemy Base ---
class Base(DeclarativeBase):
    pass

# --- Database Models (SQLAlchemy) ---
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str]
    details: Mapped[Optional[str]]
    ip_address: Mapped[Optional[str]]
    resource_id: Mapped[Optional[int]]
    resource_type: Mapped[Optional[str]]
    timestamp: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    user_id: Mapped[Optional[int]]

class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    cpu_per_core: Mapped[Optional[str]]
    cpu_percent: Mapped[Optional[float]]
    disk_percent: Mapped[Optional[float]]
    disk_read_mb: Mapped[Optional[float]]
    disk_write_mb: Mapped[Optional[float]]
    download_speed_mbps: Mapped[Optional[float]]
    gpu_memory_percent: Mapped[Optional[float]]
    gpu_memory_used_mb: Mapped[Optional[float]]
    gpu_percent: Mapped[Optional[float]]
    gpu_processes: Mapped[Optional[str]]
    gpu_temperature: Mapped[Optional[float]]
    net_connections: Mapped[Optional[int]]
    net_recv_mb: Mapped[Optional[float]]
    net_sent_mb: Mapped[Optional[float]]
    ping_ms: Mapped[Optional[float]]
    ram_percent: Mapped[Optional[float]]
    ram_total_gb: Mapped[Optional[float]]
    ram_used_gb: Mapped[Optional[float]]
    server_id: Mapped[int] = mapped_column(ForeignKey("servers.id"))
    timestamp: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    upload_speed_mbps: Mapped[Optional[float]]
    server: Mapped[Server] = relationship(back_populates="metrics")

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    avatar_url: Mapped[Optional[str]]
    created_at: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    email: Mapped[str] = mapped_column(unique=True)
    full_name: Mapped[Optional[str]]
    hashed_password: Mapped[str]
    is_active: Mapped[bool] = mapped_column(default=True)
    role: Mapped[str] = mapped_column(default=UserRole.name)
    updated_at: Mapped[Optional[datetime.datetime]]
    username: Mapped[str] = mapped_column(unique=True)
    projects: Mapped[List[Project]] = relationship(back_populates="owner")
    tasks: Mapped[List[Task]] = relationship(back_populates="assignee")

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    color: Mapped[str]
    created_at: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    description: Mapped[Optional[str]]
    icon: Mapped[str]
    name: Mapped[str]
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(default=ProjectStatus.name)
    updated_at: Mapped[Optional[datetime.datetime]]
    owner: Mapped[User] = relationship(back_populates="projects")
    tasks: Mapped[List[Task]] = relationship(back_populates="project")

class Server(Base):
    __tablename__ = "servers"
    id: Mapped[int] = mapped_column(primary_key=True)
    agent_id: Mapped[Optional[str]]
    agent_version: Mapped[Optional[str]]
    cpu_cores: Mapped[Optional[int]]
    created_at: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    description: Mapped[Optional[str]]
    gpu_model: Mapped[Optional[str]]
    hostname: Mapped[str]
    ip_address: Mapped[Optional[str]]
    last_heartbeat: Mapped[Optional[datetime.datetime]]
    name: Mapped[str]
    os_type: Mapped[str]
    port: Mapped[int]
    ram_total_gb: Mapped[Optional[int]]
    ssh_key_path: Mapped[Optional[str]]
    ssh_password_encrypted: Mapped[Optional[str]]
    ssh_username: Mapped[Optional[str]]
    status: Mapped[str] = mapped_column(default=ServerStatus.name)
    updated_at: Mapped[Optional[datetime.datetime]]
    metrics: Mapped[List[MetricSnapshot]] = relationship(back_populates="server")
    tasks: Mapped[List[Task]] = relationship(back_populates="server")

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    assignee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.utcnow)
    deadline: Mapped[Optional[datetime.datetime]]
    description: Mapped[Optional[str]]
    order: Mapped[int]
    priority: Mapped[str] = mapped_column(default=TaskPriority.name)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"))
    server_id: Mapped[Optional[int]] = mapped_column(ForeignKey("servers.id"))
    status: Mapped[str] = mapped_column(default=TaskStatus.name)
    tags: Mapped[Optional[str]]  # stored as JSON string or comma separated
    title: Mapped[str]
    updated_at: Mapped[Optional[datetime.datetime]]
    assignee: Mapped[Optional[User]] = relationship(back_populates="tasks")
    project: Mapped[Optional[Project]] = relationship(back_populates="tasks")
    server: Mapped[Optional[Server]] = relationship(back_populates="tasks")

# --- Pydantic Settings ---
class Settings(BaseSettings):
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    AGENT_SECRET: str = "change-me"
    ALGORITHM: str = "HS256"
    API_PREFIX: str = "/api/v1"
    APP_NAME: str = "NexusCtrl"
    APP_VERSION: str = "1.0.0"
    CORS_ORIGINS: List[str] = ["*"]
    DATABASE_URL: str = "sqlite:///./nexusctrl.db"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    REDIS_URL: str = "redis://localhost:6379/0"
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SECRET_KEY: str = "super-secret-key"
    SSH_KEY_PATH: str = "~/.ssh/id_rsa"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

# --- Pydantic Request/Response Schemas ---

class TaskBase(BaseModel):
    description: Optional[str] = None
    due_date: Optional[datetime.datetime] = None
    priority: TaskPriority = TaskPriority.name
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    status: TaskStatus = TaskStatus.name
    tags: List[str] = []
    title: str

class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None

class TaskResponse(TaskBase):
    assignee_id: Optional[int] = None
    created_at: datetime.datetime
    id: int
    order: int
    updated_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class TaskUpdate(BaseModel):
    description: Optional[str] = None
    due_date: Optional[datetime.datetime] = None
    position: Optional[int] = None
    priority: Optional[TaskPriority] = None
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    status: Optional[TaskStatus] = None
    tags: Optional[List[str]] = None
    title: Optional[str] = None

class TaskReorder(BaseModel):
    new_order: int
    new_status: str
    task_id: int

class ProjectCreate(BaseModel):
    color: str
    description: Optional[str] = None
    icon: str
    name: str

class ProjectUpdate(BaseModel):
    color: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None

class ProjectResponse(BaseModel):
    color: str
    completed_tasks: int
    created_at: Optional[datetime.datetime] = None
    description: Optional[str] = None
    icon: str
    id: int
    name: str
    owner_id: int
    status: str
    task_count: int
    updated_at: Optional[datetime.datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ServerCreate(BaseModel):
    description: Optional[str] = None
    hostname: str
    ip_address: Optional[str] = None
    name: str
    os_type: str
    port: int = 22
    ssh_key_path: Optional[str] = None
    ssh_username: Optional[str] = None

class ServerUpdate(BaseModel):
    description: Optional[str] = None
    hostname: Optional[str] = None
    ip_address: Optional[str] = None
    name: Optional[str] = None
    os_type: Optional[str] = None
    port: Optional[int] = None
    ssh_key_path: Optional[str] = None
    ssh_username: Optional[str] = None
    status: Optional[str] = None

class ServerResponse(BaseModel):
    agent_id: Optional[str] = None
    agent_version: Optional[str] = None
    cpu_cores: Optional[int] = None
    created_at: Optional[datetime.datetime] = None
    description: Optional[str] = None
    gpu_model: Optional[str] = None
    hostname: str
    id: int
    ip_address: Optional[str] = None
    last_heartbeat: Optional[datetime.datetime] = None
    name: str
    os_type: str
    port: int
    ram_total_gb: Optional[int] = None
    ssh_username: Optional[str] = None
    status: str
    task_count: int
    updated_at: Optional[datetime.datetime] = None
    model_config = ConfigDict(from_attributes=True)

class UserRegister(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: str
    username: str

class UserLogin(BaseModel):
    password: str
    username: str

class UserUpdate(BaseModel):
    avatar_url: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    avatar_url: Optional[str] = None
    created_at: Optional[datetime.datetime] = None
    email: str
    full_name: Optional[str] = None
    id: int
    is_active: bool
    role: str
    username: str
    model_config = ConfigDict(from_attributes=True)

class TokenRefresh(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class DashboardStats(BaseModel):
    active_projects: int
    completed_tasks: int
    online_servers: int
    pending_tasks: int
    total_projects: int
    total_servers: int
    total_tasks: int

class SystemHealth(BaseModel):
    database: bool
    redis: bool
    status: str
    version: str

# --- Metrics Connection Manager ---
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
            for client in self.client_connections[server_id]:
                await client.send_json(data)