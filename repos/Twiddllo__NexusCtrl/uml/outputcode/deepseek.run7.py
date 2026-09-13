from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic_settings import BaseSettings
from sqlalchemy import Column, DateTime, Integer, String, Boolean, Float, ForeignKey, Table, Text
from sqlalchemy.orm import declarative_base, relationship

# ------------------------------------------------------------------
# Enums
# ------------------------------------------------------------------

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"

class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class ServerStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    ERROR = "error"

class ServerType(str, enum.Enum):
    PHYSICAL = "physical"
    VIRTUAL = "virtual"

class TaskStatus(str, enum.Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"

class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

# ------------------------------------------------------------------
# ORM Base
# ------------------------------------------------------------------

Base = declarative_base()

# ------------------------------------------------------------------
# ORM Models
# ------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String)
    role = Column(String, default=UserRole.USER.value)
    is_active = Column(Boolean, default=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projects = relationship("Project", back_populates="owner")
    tasks = relationship("Task", back_populates="assignee")

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String, default="folder")
    color = Column(String, default="#3498db")
    status = Column(String, default=ProjectStatus.ACTIVE.value)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    tasks = relationship("Task", back_populates="project")

class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    hostname = Column(String)
    ip_address = Column(String, nullable=True)
    port = Column(Integer, default=22)
    os_type = Column(String)
    description = Column(Text, nullable=True)
    status = Column(String, default=ServerStatus.OFFLINE.value)
    ssh_username = Column(String, nullable=True)
    ssh_key_path = Column(String, nullable=True)
    ssh_password_encrypted = Column(String, nullable=True)
    cpu_cores = Column(Integer, nullable=True)
    ram_total_gb = Column(Float, nullable=True)
    gpu_model = Column(String, nullable=True)
    agent_id = Column(String, nullable=True, unique=True)
    agent_version = Column(String, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    metrics = relationship("MetricSnapshot", back_populates="server")
    tasks = relationship("Task", back_populates="server")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, nullable=True)
    priority = Column(String, default=TaskPriority.MEDIUM.value)
    status = Column(String, default=TaskStatus.TODO.value)
    order = Column(Integer, default=0)
    due_date = Column(DateTime, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # tags stored as JSON or separate table; using simple relation
    # but for simplicity we can store as comma-separated string or use JSON type
    # Since diagram shows List[str] in Pydantic models, we'll store as JSON
    # We'll keep a separate table for simplicity, but to match Pydantic list we can use JSON column
    tags = Column(String, nullable=True)  # will be stored as comma-separated or JSON in implementation

    project = relationship("Project", back_populates="tasks")
    server = relationship("Server", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks")

class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    cpu_percent = Column(Float, nullable=True)
    cpu_per_core = Column(String, nullable=True)  # could be JSON list
    ram_percent = Column(Float, nullable=True)
    ram_total_gb = Column(Float, nullable=True)
    ram_used_gb = Column(Float, nullable=True)
    disk_percent = Column(Float, nullable=True)
    disk_read_mb = Column(Float, nullable=True)
    disk_write_mb = Column(Float, nullable=True)
    net_sent_mb = Column(Float, nullable=True)
    net_recv_mb = Column(Float, nullable=True)
    net_connections = Column(Integer, nullable=True)
    download_speed_mbps = Column(Float, nullable=True)
    upload_speed_mbps = Column(Float, nullable=True)
    ping_ms = Column(Float, nullable=True)
    gpu_percent = Column(Float, nullable=True)
    gpu_memory_percent = Column(Float, nullable=True)
    gpu_memory_used_mb = Column(Float, nullable=True)
    gpu_temperature = Column(Float, nullable=True)
    gpu_processes = Column(String, nullable=True)  # could be JSON

    server = relationship("Server", back_populates="metrics")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String)
    resource_type = Column(String)
    resource_id = Column(Integer)
    ip_address = Column(String, nullable=True)
    details = Column(Text, nullable=True)

# ------------------------------------------------------------------
# Pydantic Models (Schemas)
# ------------------------------------------------------------------

class Settings(BaseSettings):
    APP_NAME: str = "NexusCtrl"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DATABASE_URL: str = "sqlite:///./nexusctrl.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    AGENT_SECRET: str = "change-me-agent-secret"
    CORS_ORIGINS: List[str] = ["*"]
    SSH_KEY_PATH: str = "./ssh_keys"

    class Config:
        case_sensitive = True
        env_file = ".env"

# User schemas
class UserRegister(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None

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
    full_name: Optional[str] = None
    role: str
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Project schemas
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: str = "folder"
    color: str = "#3498db"

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
    owner_id: int
    status: str
    task_count: int = 0
    completed_tasks: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Server schemas
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
    cpu_cores: Optional[int] = None
    ram_total_gb: Optional[float] = None
    gpu_model: Optional[str] = None
    agent_id: Optional[str] = None
    agent_version: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    task_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Task schemas
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.TODO
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    due_date: Optional[datetime] = None
    tags: List[str] = []

class TaskCreate(TaskBase):
    assignee_id: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    project_id: Optional[int] = None
    server_id: Optional[int] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None
    position: Optional[int] = None  # corresponds to order

class TaskReorder(BaseModel):
    task_id: int
    new_status: str
    new_order: int

class TaskResponse(TaskBase):
    id: int
    assignee_id: Optional[int] = None
    order: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Token schemas
class TokenRefresh(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

# System Health
class SystemHealth(BaseModel):
    status: str
    version: str
    database: bool
    redis: bool

# Dashboard Stats
class DashboardStats(BaseModel):
    total_projects: int
    active_projects: int
    total_servers: int
    online_servers: int
    total_tasks: int
    pending_tasks: int
    completed_tasks: int

# ------------------------------------------------------------------
# WebSocket Connection Manager
# ------------------------------------------------------------------

try:
    from fastapi import WebSocket
except ImportError:
    # Fallback for environments without FastAPI installed
    WebSocket = Any

class MetricsConnectionManager:
    def __init__(self):
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
        if server_id in self.client_connections:
            for client in self.client_connections[server_id]:
                await client.send_json(data)